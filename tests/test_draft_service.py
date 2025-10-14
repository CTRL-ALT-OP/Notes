from pathlib import Path

from app.services.draft_service import DraftService


def test_draft_claim_save_load_clear(tmp_path: Path):
    svc = DraftService(base_dir=tmp_path)
    idx = svc.claim_instance_index()
    assert 1 <= idx <= svc.max_instances

    # Save and load
    text = "Some draft text"
    path = svc.save_draft(idx, text)
    assert path.exists()
    assert svc.load_draft(idx) == text

    # Clear
    svc.clear_draft(idx)
    assert svc.load_draft(idx) == ""

    # Release lock (idempotent)
    svc.release_instance_index(idx)
