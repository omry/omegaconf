"""Unit tests for update_backlog.py."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import update_backlog as ub  # noqa: E402

# ---------------------------------------------------------------------------
# try_command
# ---------------------------------------------------------------------------


def test_try_command_missing_binary():
    assert ub.try_command(["nonexistent_binary_xyz"]) is None


def test_try_command_nonzero_exit():
    assert ub.try_command(["false"]) is None


def test_try_command_success():
    result = ub.try_command(["echo", "hello"])
    assert result is not None
    assert "hello" in result


# ---------------------------------------------------------------------------
# render_template
# ---------------------------------------------------------------------------


def test_render_template_simple_var():
    assert ub.render_template("hello {{name}}", {"name": "world"}) == "hello world"


def test_render_template_missing_var_is_empty():
    assert ub.render_template("{{x}}", {}) == ""


def test_render_template_section_loop():
    tmpl = "{{#items}}[{{val}}]{{/items}}"
    result = ub.render_template(tmpl, {"items": [{"val": "a"}, {"val": "b"}]})
    assert result == "[a][b]"


def test_render_template_empty_section():
    assert ub.render_template("{{#items}}x{{/items}}", {"items": []}) == ""


def test_render_template_none_section():
    assert ub.render_template("{{#items}}x{{/items}}", {"items": None}) == ""


# ---------------------------------------------------------------------------
# categorize_issue
# ---------------------------------------------------------------------------


def _issue(labels: list[str], title: str = "", body: str = "") -> dict[str, Any]:
    return {
        "title": title,
        "body": body,
        "labels": [{"name": name} for name in labels],
    }


def test_categorize_bug_label():
    assert ub.categorize_issue(_issue(["bug"])) == "Bug"


def test_categorize_enhancement_label():
    assert ub.categorize_issue(_issue(["enhancement"])) == "Enhancement"


def test_categorize_refactor_label():
    assert ub.categorize_issue(_issue(["refactor"])) == "Refactor"


def test_categorize_documentation_label():
    assert ub.categorize_issue(_issue(["documentation"])) == "Documentation"


def test_categorize_question_label():
    assert ub.categorize_issue(_issue(["question"])) == "Question"


def test_categorize_bug_keyword_in_title():
    assert ub.categorize_issue(_issue([], title="crash when using merge")) == "Bug"


def test_categorize_enhancement_fallback():
    assert ub.categorize_issue(_issue([])) == "Enhancement"


def test_categorize_bug_label_beats_enhancement_keyword():
    assert ub.categorize_issue(_issue(["bug"], title="add feature")) == "Bug"


# ---------------------------------------------------------------------------
# status determination via build_current_issue_records
# ---------------------------------------------------------------------------


def _open_issue(number: int, labels: list[str] = []) -> dict[str, Any]:
    return {
        "number": number,
        "title": f"Issue {number}",
        "body": "",
        "labels": [{"name": name} for name in labels],
        "state": "OPEN",
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
    }


def _pr(number: str, author: str, linked: list[str]) -> dict[str, Any]:
    return {
        "number": number,
        "title": f"PR {number}",
        "body": "",
        "author_login": author,
        "linked_issue_numbers": linked,
    }


def test_status_not_started():
    issues = [_open_issue(1)]
    pr_lookup: dict[str, Any] = {}
    records = ub.build_current_issue_records("o/r", issues, set(), pr_lookup)
    assert records[0]["status"] == "not started"


def test_status_in_progress_maintainer_pr():
    issues = [_open_issue(1)]
    collaborators = {"maintainer"}
    pr_lookup = ub.build_pr_lookup([_pr("10", "maintainer", ["1"])], {"1"})
    records = ub.build_current_issue_records("o/r", issues, collaborators, pr_lookup)
    assert records[0]["status"] == "in progress"


def test_status_community_pr():
    issues = [_open_issue(1)]
    pr_lookup = ub.build_pr_lookup([_pr("10", "community_user", ["1"])], {"1"})
    records = ub.build_current_issue_records("o/r", issues, set(), pr_lookup)
    assert records[0]["status"] == "community PR"


def test_status_blocked_awaiting_response():
    issues = [_open_issue(1, labels=["awaiting response"])]
    records = ub.build_current_issue_records("o/r", issues, set(), {})
    assert records[0]["status"] == "blocked"


def test_status_in_progress_beats_blocked():
    issues = [_open_issue(1, labels=["awaiting response"])]
    collaborators = {"maintainer"}
    pr_lookup = ub.build_pr_lookup([_pr("10", "maintainer", ["1"])], {"1"})
    records = ub.build_current_issue_records("o/r", issues, collaborators, pr_lookup)
    assert records[0]["status"] == "in progress"


# ---------------------------------------------------------------------------
# compare_snapshots
# ---------------------------------------------------------------------------


def _snapshot(issues: dict[str, Any]) -> dict[str, Any]:
    return {"repo": "o/r", "generated_at": "2024-01-01T00:00:00Z", "issues": issues}


def _record(number: str, status: str = "not started", labels: list[str] = []) -> dict[str, Any]:
    return {
        "number": number,
        "title": f"Issue {number}",
        "title_display": f"Issue {number}",
        "status": status,
        "category": "Enhancement",
        "labels": labels,
        "labels_display": "",
        "pr_numbers": [],
        "pr_links": "",
        "issue_link": f"[#{number}](url)",
        "created": "2024-01-01",
        "updated": "2024-01-01",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


def test_compare_no_previous_snapshot():
    current = _snapshot({"1": {"title": "t", "status": "not started", "labels": [], "category": "Enhancement"}})
    new, status, labels, closed = ub.compare_snapshots(None, current, {"1": _record("1")}, {})
    assert new == [] and status == [] and labels == [] and closed == []


def test_compare_detects_new_issue():
    prev = _snapshot({})
    curr = _snapshot({"1": {"title": "t", "status": "not started", "labels": [], "category": "Enhancement"}})
    new, _, _, _ = ub.compare_snapshots(prev, curr, {"1": _record("1")}, {})
    assert len(new) == 1 and new[0]["number"] == "1"


def test_compare_detects_status_change():
    prev = _snapshot({"1": {"title": "t", "status": "not started", "labels": [], "category": "Enhancement"}})
    curr = _snapshot({"1": {"title": "t", "status": "in progress", "labels": [], "category": "Enhancement"}})
    _, status, _, _ = ub.compare_snapshots(prev, curr, {"1": _record("1", "in progress")}, {})
    assert len(status) == 1 and status[0]["new_status"] == "in progress"


def test_compare_detects_closed():
    prev = _snapshot({"1": {"title": "t", "status": "not started", "labels": [], "category": "Enhancement"}})
    curr = _snapshot({})
    _, _, _, closed = ub.compare_snapshots(prev, curr, {}, {"1": _record("1")})
    assert len(closed) == 1


# ---------------------------------------------------------------------------
# save_snapshot / load_json_file with custom path
# ---------------------------------------------------------------------------


def test_save_and_load_snapshot_custom_path(tmp_path: Path):
    snap = {"repo": "o/r", "generated_at": "2024-01-01T00:00:00Z", "issues": {}}
    path = tmp_path / "snap.json"
    ub.save_snapshot(snap, path)
    loaded = ub.load_json_file(path)
    assert loaded == snap


def test_save_snapshot_creates_parent_dirs(tmp_path: Path):
    snap = {"repo": "o/r", "issues": {}}
    path = tmp_path / "deep" / "dir" / "snap.json"
    ub.save_snapshot(snap, path)
    assert path.exists()


# ---------------------------------------------------------------------------
# event log cleared after processing
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# normalize_previous_row — category derived from title/labels, not HTML
# ---------------------------------------------------------------------------


def _prev_row(number: str, title: str, status: str = "done", labels: list[str] = []) -> dict[str, Any]:
    return {
        "number": number,
        "title": title,
        "status": status,
        "pr_numbers": [],
        "created": "2024‑01‑01",
        "updated": "2024‑01‑01",
        "labels": labels,
    }


def test_normalize_previous_row_derives_category_from_title():
    row = ub.normalize_previous_row("o/r", _prev_row("803", "[Question] Why hide this?"))
    assert row["category"] == "Question"


def test_normalize_previous_row_derives_category_from_label():
    row = ub.normalize_previous_row("o/r", _prev_row("1", "Something", labels=["bug"]))
    assert row["category"] == "Bug"


def test_normalize_previous_row_ignores_stale_category_field():
    # Even if a corrupted category was parsed and stored, normalize re-derives it
    raw = {**_prev_row("1", "Add a feature"), "category": '<span title="<span>garbage</span>">✨</span>'}
    row = ub.normalize_previous_row("o/r", raw)
    assert row["category"] == "Enhancement"


# ---------------------------------------------------------------------------
# _is_done_expired
# ---------------------------------------------------------------------------


def test_is_done_expired_not_expired_via_closed_at():
    from datetime import date, timedelta
    recent = (date.today() - timedelta(days=5)).isoformat()
    row = _prev_row("1", "t")
    assert not ub._is_done_expired(row, {"1": recent})


def test_is_done_expired_expired_via_closed_at():
    from datetime import date, timedelta
    old = (date.today() - timedelta(days=15)).isoformat()
    row = _prev_row("1", "t")
    assert ub._is_done_expired(row, {"1": old})


def test_is_done_expired_boundary_exactly_14_days():
    from datetime import date, timedelta
    boundary = (date.today() - timedelta(days=14)).isoformat()
    row = _prev_row("1", "t")
    assert not ub._is_done_expired(row, {"1": boundary})


def test_is_done_expired_fallback_to_updated_field():
    from datetime import date, timedelta
    old = (date.today() - timedelta(days=20)).isoformat().replace("-", "‑")
    row = {**_prev_row("1", "t"), "updated": old}
    assert ub._is_done_expired(row, {})


def test_is_done_expired_no_date_not_expired():
    row = {**_prev_row("1", "t"), "updated": ""}
    assert not ub._is_done_expired(row, {})


# ---------------------------------------------------------------------------
# merge_rows_for_render — done expiry
# ---------------------------------------------------------------------------


def _done_prev_row(number: str, days_old: int) -> dict[str, Any]:
    from datetime import date, timedelta
    updated = (date.today() - timedelta(days=days_old)).isoformat().replace("-", "‑")
    row = _prev_row(number, f"Issue {number}", status="done")
    row["updated"] = updated
    row["title_display"] = f"Issue {number}"
    row["labels_display"] = ""
    row["issue_link"] = f"[#{number}](url)"
    row["pr_links"] = ""
    row["category"] = "Enhancement"
    return row


def test_merge_keeps_fresh_done_row():
    prev = [_done_prev_row("1", days_old=5)]
    rows = ub.merge_rows_for_render([], prev)
    assert any(r["number"] == "1" for r in rows)


def test_merge_expires_old_done_row():
    prev = [_done_prev_row("1", days_old=20)]
    rows = ub.merge_rows_for_render([], prev)
    assert not any(r["number"] == "1" for r in rows)


def test_merge_closed_at_overrides_updated_field():
    from datetime import date, timedelta
    # updated says old, but closed_at says recent → should keep
    prev = [_done_prev_row("1", days_old=20)]
    recent = (date.today() - timedelta(days=3)).isoformat()
    rows = ub.merge_rows_for_render([], prev, closed_at={"1": recent})
    assert any(r["number"] == "1" for r in rows)


# ---------------------------------------------------------------------------
# closed_at snapshot tracking and pruning via main()
# ---------------------------------------------------------------------------


def test_event_log_cleared_after_update(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    event_log = tmp_path / "events.jsonl"
    event_log.write_text('{"event": "issues", "action": "opened"}\n', encoding="utf-8")
    snapshot_path = tmp_path / "snap.json"

    def fake_fetch_collaborators(repo: str) -> set[str]:
        return set()

    def fake_fetch_open_issues(repo: str) -> list[dict[str, Any]]:
        return []

    def fake_fetch_open_prs(repo: str) -> list[dict[str, Any]]:
        return []

    monkeypatch.setattr(ub, "fetch_collaborators", fake_fetch_collaborators)
    monkeypatch.setattr(ub, "fetch_open_issues", fake_fetch_open_issues)
    monkeypatch.setattr(ub, "fetch_open_prs", fake_fetch_open_prs)
    monkeypatch.setattr(ub, "BACKLOG_PATH", tmp_path / "BACKLOG.md")
    monkeypatch.setattr(ub, "UPDATES_PATH", tmp_path / "BACKLOG-UPDATES.md")

    with patch.object(ub, "resolve_repo", return_value="o/r"):
        sys.argv = [
            "update_backlog.py",
            "--snapshot-path", str(snapshot_path),
            "--event-log-path", str(event_log),
        ]
        ub.main()

    assert event_log.read_text(encoding="utf-8") == ""
