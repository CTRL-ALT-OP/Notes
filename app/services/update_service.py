from __future__ import annotations

import contextlib
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

try:
    # Local version of the running app
    from app import __version__ as LOCAL_VERSION
except Exception:
    LOCAL_VERSION = "0.0.0"


@dataclass
class UpdateConfig:
    repo: Optional[str]
    branch: Optional[str]
    token: Optional[str]
    enabled: bool


def _parse_version(version: str) -> Tuple[int, ...]:
    v = version.strip().lstrip("vV")
    parts = []
    for p in v.split("."):
        num = 0
        for ch in p:
            if ch.isdigit():
                num = num * 10 + int(ch)
            else:
                break
        parts.append(num)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


class UpdateService:
    """Checks GitHub for a newer version and self-updates from a ZIP archive.

    Does not require git; uses raw and codeload endpoints. On finding a newer
    version, it downloads the repository ZIP, extracts to a temp directory, and
    launches a transient updater script to copy files over this working tree and
    relaunch the app.
    """

    def __init__(self, config: Optional[UpdateConfig] = None) -> None:
        if config is None:
            config = self._load_env_config()
        self.config = config

    def _load_env_config(self) -> UpdateConfig:
        repo = os.environ.get("NOTES_UPDATE_REPO")
        branch = os.environ.get("NOTES_UPDATE_BRANCH")
        token = os.environ.get("NOTES_GITHUB_TOKEN")
        enabled = os.environ.get("NOTES_AUTO_UPDATE", "1").strip() not in {
            "0",
            "false",
            "False",
        }
        # Try default branches if not provided
        if not branch:
            branch = None  # We'll probe main, then master
        return UpdateConfig(repo=repo, branch=branch, token=token, enabled=enabled)

    def check_and_apply_update_async(self) -> None:
        if not self.config.enabled:
            return
        if not self.config.repo:
            # No repository configured; nothing to do
            return
        t = threading.Thread(
            target=self._check_and_apply_update, name="UpdateServiceThread", daemon=True
        )
        t.start()

    # ---------- Core flow ----------

    def _check_and_apply_update(self) -> None:
        try:
            remote_version, download_url = self._get_remote_version_and_zip_url()
            if not remote_version or not download_url:
                return
            if _parse_version(remote_version) <= _parse_version(LOCAL_VERSION):
                return

            extract_dir = self._download_and_extract(download_url)
            if not extract_dir:
                return
            # The zip contains a single root directory; use it as source
            candidates = list(Path(extract_dir).iterdir())
            if not candidates:
                return
            source_root = candidates[0]
            # Launch updater and exit current process
            self._launch_updater_and_exit(source_root)
        except Exception:
            # Silent failure to avoid disrupting the app
            return

    def _get_remote_version_and_zip_url(self) -> Tuple[str, str]:
        repo = self.config.repo or ""
        token = self.config.token
        branches_to_try = (
            [self.config.branch] if self.config.branch else ["main", "master"]
        )

        # Probe raw __version__ from branch and build codeload zip URL
        for branch in branches_to_try:
            version = self._fetch_remote_version_from_branch(repo, branch, token)
            if version:
                zip_url = f"https://codeload.github.com/{repo}/zip/refs/heads/{branch}"
                return version, zip_url

        # Fallback: try latest release tag
        version, tag = self._fetch_latest_release_version_and_tag(repo, token)
        if version and tag:
            zip_url = f"https://codeload.github.com/{repo}/zip/refs/tags/{tag}"
            return version, zip_url
        return "", ""

    # ---------- Network helpers (stdlib urllib) ----------

    def _build_request(self, url: str, token: Optional[str]) -> object:  # noqa: ANN401
        import urllib.request

        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Notes-Updater")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        return req

    def _fetch_text(self, url: str, token: Optional[str], timeout: float = 8.0) -> str:
        import urllib.request

        req = self._build_request(url, token)
        with contextlib.closing(
            urllib.request.urlopen(req, timeout=timeout)
        ) as resp:  # noqa: S310
            data = resp.read()
            try:
                return data.decode("utf-8", errors="ignore")
            except Exception:
                return ""

    def _fetch_remote_version_from_branch(
        self, repo: str, branch: str, token: Optional[str]
    ) -> str:
        try:
            url = f"https://raw.githubusercontent.com/{repo}/{branch}/app/__init__.py"
            text = self._fetch_text(url, token)
            if not text:
                return ""
            # Very small parse to find __version__ = "x.y.z"
            for line in text.splitlines():
                if "__version__" in line and "=" in line:
                    parts = line.split("=", 1)
                    rhs = parts[1].strip().strip("\"'")
                    if rhs:
                        return rhs
        except Exception:
            return ""
        return ""

    def _fetch_latest_release_version_and_tag(
        self, repo: str, token: Optional[str]
    ) -> Tuple[str, str]:
        try:
            api = f"https://api.github.com/repos/{repo}/releases/latest"
            text = self._fetch_text(api, token)
            if not text:
                return "", ""
            obj = json.loads(text)
            tag = (obj.get("tag_name") or obj.get("name") or "").strip()
            if not tag:
                return "", ""
            version = tag.lstrip("vV").strip()
            return version, tag
        except Exception:
            return "", ""

    def _download_and_extract(self, zip_url: str) -> Optional[Path]:
        import urllib.request

        token = self.config.token
        with tempfile.TemporaryDirectory(prefix="notes_update_dl_") as tmp:
            zip_path = Path(tmp) / "repo.zip"
            try:
                req = self._build_request(zip_url, token)
                with contextlib.closing(
                    urllib.request.urlopen(req, timeout=30.0)
                ) as resp:  # noqa: S310
                    with open(zip_path, "wb") as f:
                        shutil.copyfileobj(resp, f)
            except Exception:
                return None

            extract_dir = Path(tempfile.mkdtemp(prefix="notes_update_extracted_"))
            try:
                with zipfile.ZipFile(zip_path) as zf:
                    zf.extractall(extract_dir)
            except Exception:
                with contextlib.suppress(Exception):
                    shutil.rmtree(extract_dir, ignore_errors=True)
                return None
            return extract_dir

    def _launch_updater_and_exit(self, source_root: Path) -> None:
        updater_code = self._generate_updater_script()
        tmp_dir = Path(tempfile.mkdtemp(prefix="notes_updater_"))
        updater_path = tmp_dir / "run_updater.py"
        with open(updater_path, "w", encoding="utf-8") as f:
            f.write(updater_code)

        target_root = Path(__file__).resolve().parents[2]
        py = sys.executable or "python"
        args = [
            py,
            str(updater_path),
            str(target_root),
            str(source_root),
            py,
            str(target_root / "main.py"),
        ]
        with contextlib.suppress(Exception):
            # Launch detached; do not wait
            import subprocess

            creationflags = 0
            if sys.platform == "win32":
                creationflags = 0x00000010  # CREATE_NEW_CONSOLE
            subprocess.Popen(
                args, cwd=str(target_root), creationflags=creationflags, close_fds=False
            )

        # Give the updater a head start then exit this process
        with contextlib.suppress(Exception):
            time.sleep(0.25)
        os._exit(0)  # noqa: SLF001

    def _generate_updater_script(self) -> str:
        # Standalone minimal updater to run in a separate Python process
        return (
            "import os, shutil, sys, time\n"
            "from pathlib import Path\n"
            "\n"
            "def copy_tree(src: Path, dst: Path) -> None:\n"
            "    for root, dirs, files in os.walk(src):\n"
            "        rel = Path(root).relative_to(src)\n"
            "        target_dir = dst / rel\n"
            "        target_dir.mkdir(parents=True, exist_ok=True)\n"
            "        for name in files:\n"
            "            s = Path(root) / name\n"
            "            d = target_dir / name\n"
            "            for _ in range(10):\n"
            "                try:\n"
            "                    shutil.copy2(s, d)\n"
            "                    break\n"
            "                except Exception:\n"
            "                    time.sleep(0.3)\n"
            "\n"
            "def main() -> int:\n"
            "    if len(sys.argv) < 5:\n"
            "        return 0\n"
            "    target_root = Path(sys.argv[1])\n"
            "    source_root = Path(sys.argv[2])\n"
            "    py = sys.argv[3]\n"
            "    entry = Path(sys.argv[4])\n"
            "\n"
            "    # Wait for parent process files to be unlocked\n"
            "    for _ in range(40):\n"
            "        try:\n"
            "            probe = target_root / '.update_probe'\n"
            "            with open(probe, 'w') as f: f.write('ok')\n"
            "            probe.unlink()\n"
            "            break\n"
            "        except Exception:\n"
            "            time.sleep(0.25)\n"
            "\n"
            "    copy_tree(source_root, target_root)\n"
            "\n"
            "    # Relaunch application\n"
            "    try:\n"
            "        import subprocess\n"
            "        creationflags = 0x00000010 if os.name == 'nt' else 0\n"
            "        subprocess.Popen([py, str(entry)], cwd=str(target_root), creationflags=creationflags, close_fds=False)\n"
            "    except Exception:\n"
            "        pass\n"
            "    return 0\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    raise SystemExit(main())\n"
        )
