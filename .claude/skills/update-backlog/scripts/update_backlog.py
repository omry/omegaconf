#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from omegaconf import DictConfig, OmegaConf

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parents[2]
BACKLOG_PATH = REPO_ROOT / "BACKLOG.md"
UPDATES_PATH = REPO_ROOT / "BACKLOG-UPDATES.md"
TEMPLATE_PATH = SKILL_DIR / "templates" / "backlog.md.tmpl"
STATE_PATH = SKILL_DIR / "state" / "last_snapshot.json"
CONFIG_PATH = SCRIPT_DIR / "config.yaml"

BEGIN_GENERATED = "<!-- BEGIN GENERATED BACKLOG -->"
END_GENERATED = "<!-- END GENERATED BACKLOG -->"
BEGIN_MANUAL = "<!-- BEGIN MANUAL COMMENTS -->"
END_MANUAL = "<!-- END MANUAL COMMENTS -->"
MANUAL_FENCE = '```json\n{\n  "issues": {},\n  "general": []\n}\n```'

STATUS_ORDER = ["in progress", "community PR", "blocked", "not started", "done"]


@dataclass
class CategoryConfig:
    labels: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


@dataclass
class BacklogConfig:
    done_expire_days: int | None = 14
    backlog_filename: str = "BACKLOG.md"
    updates_filename: str = "BACKLOG-UPDATES.md"
    categories: dict[str, CategoryConfig] = field(
        default_factory=lambda: {k: CategoryConfig(list(v.labels), list(v.keywords)) for k, v in _DEFAULT_CATEGORIES.items()}
    )


def load_config() -> DictConfig:
    defaults = OmegaConf.structured(BacklogConfig)
    if CONFIG_PATH.exists():
        return OmegaConf.merge(defaults, OmegaConf.load(CONFIG_PATH))
    return defaults


CATEGORY_EMOJI = {
    "Bug": "🐛",
    "Enhancement": "✨",
    "Refactor": "🔧",
    "Build": "🏗️",
    "Documentation": "📄",
    "Question": "❓",
}

STATUS_EMOJI = {
    "in progress": "🔄",
    "community PR": "🤝",
    "blocked": "🚫",
    "not started": "⬜",
    "done": "✅",
}

CATEGORY_ORDER = [
    "Bug",
    "Enhancement",
    "Refactor",
    "Build",
    "Documentation",
    "Question",
]

_DEFAULT_CATEGORIES: dict[str, CategoryConfig] = {
    "Bug": CategoryConfig(
        labels=["bug"],
        keywords=["bug", "error", "fail", "broken", "crash", "exception", "runtimeerror", "assertionerror"],
    ),
    "Enhancement": CategoryConfig(
        labels=["enhancement", "good first issue", "help wanted", "performance",
                "duplicate", "invalid", "wontfix", "discussion", "awaiting response", "wishlist"],
        keywords=["feature", "add", "support", "allow", "enable", "implement", "enhancement",
                  "request", "wishlist", "consider",
                  "performance", "speed", "slow", "optimize", "memory", "cpu", "latency"],
    ),
    "Documentation": CategoryConfig(
        labels=["documentation"],
        keywords=["doc", "documentation", "readme", "comment", "typo", "spelling"],
    ),
    "Question": CategoryConfig(
        labels=["question"],
        keywords=["question", "how to", "help", "confused", "unclear", "wonder"],
    ),
    "Refactor": CategoryConfig(
        labels=["refactor"],
        keywords=["refactor", "cleanup", "clean up", "remove", "delete", "deprecated", "modernize"],
    ),
    "Build": CategoryConfig(
        labels=["build", "dependencies"],
        keywords=["build", "package", "release", "ci", "github actions", "setup.py", "pyproject", "wheel", "packaging"],
    ),
}


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", text)


def run_command(args: list[str]) -> str:
    completed = subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "NO_COLOR": "1", "CLICOLOR": "0"},
    )
    if completed.returncode != 0:
        stderr = strip_ansi(completed.stderr).strip()
        stdout = strip_ansi(completed.stdout).strip()
        details = stderr or stdout or "unknown command failure"
        raise RuntimeError(f"{' '.join(args)} failed: {details}")
    return strip_ansi(completed.stdout)


def try_command(args: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "NO_COLOR": "1", "CLICOLOR": "0"},
        )
    except FileNotFoundError:
        return None
    if completed.returncode != 0:
        return None
    return strip_ansi(completed.stdout)


def parse_github_repo(url: str) -> str | None:
    text = (url or "").strip()
    patterns = [
        r"^(?:ssh://)?git@github\.com[:/](?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$",
        r"^https://github\.com/(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$",
        r"^git://github\.com/(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$",
    ]
    for pattern in patterns:
        match = re.match(pattern, text)
        if match:
            return match.group("repo")
    return None


def detect_repo_from_sl() -> str | None:
    output = try_command(["sl", "paths"])
    if not output:
        return None
    for line in output.splitlines():
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() not in {"default", "default-push"}:
            continue
        repo = parse_github_repo(value)
        if repo:
            return repo
    return None


def detect_repo_from_git() -> str | None:
    for args in (
        ["git", "remote", "get-url", "origin"],
        ["git", "remote", "get-url", "upstream"],
    ):
        output = try_command(args)
        if not output:
            continue
        repo = parse_github_repo(output.strip())
        if repo:
            return repo
    return None


def resolve_repo(explicit_repo: str | None) -> str:
    if explicit_repo:
        repo = explicit_repo.strip()
    else:
        repo = detect_repo_from_sl() or detect_repo_from_git() or ""
    if re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", repo):
        return repo
    raise RuntimeError(
        "could not determine GitHub repo; pass --repo owner/name or ensure Sapling/Git remotes point at GitHub"
    )


def split_repo(repo: str) -> tuple[str, str]:
    owner, name = repo.split("/", 1)
    return owner, name


def issue_url(repo: str, number: str) -> str:
    return f"https://github.com/{repo}/issues/{number}"


def pr_url(repo: str, number: str) -> str:
    return f"https://github.com/{repo}/pull/{number}"


def run_gh(args: list[str]) -> str:
    completed = subprocess.run(
        ["gh", *args],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "NO_COLOR": "1", "CLICOLOR": "0"},
    )
    if completed.returncode != 0:
        stderr = strip_ansi(completed.stderr).strip()
        stdout = strip_ansi(completed.stdout).strip()
        details = stderr or stdout or "unknown gh failure"
        raise RuntimeError(f"gh {' '.join(args)} failed: {details}")
    return strip_ansi(completed.stdout)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists():
        current = read_text(path)
        if current == content:
            return False
    path.write_text(content, encoding="utf-8")
    return True


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def load_json_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(read_text(path))


def save_snapshot(snapshot: dict[str, Any], path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def truncate_title(title: str, limit: int = 58) -> str:
    title = normalize_whitespace(title)
    if len(title) <= limit:
        return title
    return title[: limit - 3].rstrip() + "..."


def escape_table_cell(text: str) -> str:
    return (text or "").replace("|", r"\|").replace("\r", " ").replace("\n", " ")


def issue_link(repo: str, number: str) -> str:
    return f"[#{number}]({issue_url(repo, number)})"


def pr_link(repo: str, number: str) -> str:
    return f"[#{number}]({pr_url(repo, number)})"


def parse_labels(issue: dict[str, Any]) -> list[str]:
    labels = []
    for label in issue.get("labels", []) or []:
        name = label.get("name") if isinstance(label, dict) else str(label)
        if name:
            labels.append(name)
    return labels


def _keyword_matches(title: str, keyword: str) -> bool:
    if keyword == "bug":
        return bool(re.search(r"(?<![A-Za-z0-9_])bug(?![A-Za-z0-9_])", title))
    return keyword in title


def categorize_issue(
    issue: dict[str, Any],
    label_to_category: dict[str, str],
    category_keywords: dict[str, list[str]],
) -> str:
    labels = [label.lower().strip() for label in parse_labels(issue)]
    for label in labels:
        if label in label_to_category:
            return label_to_category[label]

    # Fallback classification uses the title only — issue bodies contain generic
    # triage wording that makes body-based matching too noisy.
    title = (issue.get("title") or "").lower()
    for category, keywords in category_keywords.items():
        if any(_keyword_matches(title, kw) for kw in keywords):
            return category
    return "Enhancement"


def extract_issue_numbers(text: str, repo: str | None = None) -> list[str]:
    numbers = []
    seen: set[str] = set()

    def add(number: str) -> None:
        if number not in seen:
            seen.add(number)
            numbers.append(number)

    for match in re.finditer(r"(?<![A-Za-z0-9_])#(\d+)", text or ""):
        add(match.group(1))

    if repo:
        url_pattern = rf"https?://github\.com/{re.escape(repo)}/issues/(\d+)"
        for match in re.finditer(url_pattern, text or "", flags=re.IGNORECASE):
            add(match.group(1))

    return numbers


def parse_issue_table_rows(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    rows: list[dict[str, Any]] = []
    header_index = None
    for index, line in enumerate(lines):
        if (
            line.strip()
            == "| Issue | Title | Category | Status | PR | Created | Updated | Labels |"
        ):
            header_index = index
            break
    if header_index is None:
        return rows

    for line in lines[header_index + 2 :]:
        if not line.startswith("|"):
            break
        parts = re.split(r"(?<!\\)\|", line.strip())
        cells = [part.strip() for part in parts[1:-1]]
        if len(cells) != 8:
            continue
        issue_match = re.search(r"#(\d+)", cells[0])
        if not issue_match:
            continue
        issue_number = issue_match.group(1)
        pr_numbers = re.findall(r"#(\d+)", cells[4])
        labels = [label.strip() for label in cells[7].split(",") if label.strip()]
        status_match = re.match(r'<span\s+title="([^"]*)">', cells[3].strip())
        status = status_match.group(1) if status_match else cells[3]
        rows.append(
            {
                "number": issue_number,
                "title": cells[1].replace(r"\|", "|"),
                "status": status,
                "pr_numbers": pr_numbers,
                "created": cells[5],
                "updated": cells[6],
                "labels": labels,
            }
        )
    return rows


def load_existing_manual_block(text: str) -> str | None:
    match = re.search(
        rf"{re.escape(BEGIN_MANUAL)}.*?{re.escape(END_MANUAL)}",
        text,
        flags=re.DOTALL,
    )
    if not match:
        return None
    block = match.group(0)
    fence_match = re.search(r"```json\n(.*?)\n```", block, flags=re.DOTALL)
    if not fence_match:
        raise RuntimeError(
            "existing manual-comments block is malformed: missing JSON fence"
        )
    json.loads(fence_match.group(1))
    return block


def canonical_manual_block() -> str:
    return "\n".join(
        [
            BEGIN_MANUAL,
            MANUAL_FENCE,
            END_MANUAL,
        ]
    )


def render_template(template: str, context: dict[str, Any]) -> str:
    loop_pattern = re.compile(r"{{#([A-Za-z_][A-Za-z0-9_]*)}}([\s\S]*?){{/\1}}")

    def resolve(name: str, scope: dict[str, Any]) -> str:
        value = scope.get(name, "")
        if value is None:
            return ""
        return str(value)

    def render_section(section: str, scope: dict[str, Any]) -> str:
        while True:
            match = loop_pattern.search(section)
            if not match:
                break
            key = match.group(1)
            body = match.group(2)
            items = scope.get(key, []) or []
            rendered = []
            for item in items:
                item_scope = dict(scope)
                if isinstance(item, dict):
                    item_scope.update(item)
                else:
                    item_scope[key] = item
                rendered.append(render_section(body, item_scope))
            section = (
                section[: match.start()] + "".join(rendered) + section[match.end() :]
            )

        return re.sub(
            r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}",
            lambda m: resolve(m.group(1), scope),
            section,
        )

    return render_section(template, context)


def fetch_collaborators(repo: str) -> set[str]:
    output = run_gh(
        ["api", f"repos/{repo}/collaborators", "--paginate", "--jq", ".[].login"]
    )
    return {line.strip() for line in output.splitlines() if line.strip()}


def fetch_open_issues(repo: str) -> list[dict[str, Any]]:
    owner, name = split_repo(repo)
    issues: list[dict[str, Any]] = []
    cursor: str | None = None

    while True:
        after_clause = f", after: {json.dumps(cursor)}" if cursor else ""
        query = f"""
query {{
  repository(owner: \"{owner}\", name: \"{name}\") {{
    issues(first: 100, states: OPEN{after_clause}) {{
      nodes {{
        number
        title
        body
        state
        createdAt
        updatedAt
        labels(first: 100) {{ nodes {{ name }} }}
      }}
      pageInfo {{
        hasNextPage
        endCursor
      }}
    }}
  }}
}}
"""
        output = run_gh(["api", "graphql", "-f", f"query={query}"])
        data = json.loads(output)
        issue_connection = data["data"]["repository"]["issues"]
        for node in issue_connection["nodes"]:
            labels = (node.get("labels") or {}).get("nodes") or []
            issues.append(
                {
                    "number": node["number"],
                    "title": node.get("title") or "",
                    "body": node.get("body") or "",
                    "labels": labels,
                    "state": node.get("state") or "OPEN",
                    "createdAt": node.get("createdAt") or "",
                    "updatedAt": node.get("updatedAt") or "",
                }
            )

        if not issue_connection["pageInfo"]["hasNextPage"]:
            break
        cursor = issue_connection["pageInfo"]["endCursor"]

    return issues


def fetch_open_prs(repo: str) -> list[dict[str, Any]]:
    owner, name = split_repo(repo)
    prs: list[dict[str, Any]] = []
    cursor: str | None = None

    while True:
        after_clause = f", after: {json.dumps(cursor)}" if cursor else ""
        query = f"""
query {{
  repository(owner: \"{owner}\", name: \"{name}\") {{
    pullRequests(first: 100, states: OPEN{after_clause}) {{
      nodes {{
        number
        title
        body
        author {{ login }}
        closingIssuesReferences(first: 50) {{ nodes {{ number }} }}
      }}
      pageInfo {{
        hasNextPage
        endCursor
      }}
    }}
  }}
}}
"""
        output = run_gh(["api", "graphql", "-f", f"query={query}"])
        data = json.loads(output)
        pull_requests = data["data"]["repository"]["pullRequests"]
        for node in pull_requests["nodes"]:
            closing_refs = node.get("closingIssuesReferences", {})
            linked_numbers: list[str] = []

            def walk(value: Any) -> None:
                if isinstance(value, dict):
                    number = value.get("number")
                    if number is not None:
                        linked_numbers.append(str(number))
                    for item in value.values():
                        walk(item)
                elif isinstance(value, list):
                    for item in value:
                        walk(item)

            walk(closing_refs)
            linked_numbers.extend(
                extract_issue_numbers(node.get("body") or "", repo=repo)
            )
            linked_numbers = sorted(set(linked_numbers), key=lambda item: int(item))
            prs.append(
                {
                    "number": str(node["number"]),
                    "title": node.get("title") or "",
                    "body": node.get("body") or "",
                    "author_login": (
                        (node.get("author") or {}).get("login") or ""
                    ).strip(),
                    "linked_issue_numbers": linked_numbers,
                }
            )

        if not pull_requests["pageInfo"]["hasNextPage"]:
            break
        cursor = pull_requests["pageInfo"]["endCursor"]

    return prs


def build_pr_lookup(
    open_prs: list[dict[str, Any]], open_issue_numbers: set[str]
) -> dict[str, list[dict[str, Any]]]:
    lookup: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pr in open_prs:
        linked_numbers = [
            n for n in pr["linked_issue_numbers"] if n in open_issue_numbers
        ]
        pr_record = {
            "number": pr["number"],
            "title": pr.get("title") or "",
            "body": pr.get("body") or "",
            "author_login": pr.get("author_login") or "",
            "linked_issue_numbers": linked_numbers,
        }
        for issue_number in linked_numbers:
            lookup[issue_number].append(pr_record)
    return lookup


def format_label_string(labels: list[str]) -> str:
    return ", ".join(escape_table_cell(label) for label in labels)


def normalize_previous_row(
    repo: str,
    row: dict[str, Any],
    label_to_category: dict[str, str],
    category_keywords: dict[str, list[str]],
) -> dict[str, Any]:
    pr_numbers = sorted(row.get("pr_numbers", []), key=lambda value: int(value))
    title = row.get("title") or ""
    labels = row.get("labels", []) or []
    return {
        **row,
        "title": title,
        "title_display": escape_table_cell(truncate_title(title)),
        "category": categorize_issue({"title": title, "labels": [{"name": label} for label in labels]}, label_to_category, category_keywords),
        "labels": labels,
        "labels_display": escape_table_cell(format_label_string(labels)),
        "issue_link": issue_link(repo, row["number"]),
        "pr_numbers": pr_numbers,
        "pr_links": ", ".join(pr_link(repo, pr_number) for pr_number in pr_numbers),
    }


def build_current_issue_records(
    repo: str,
    open_issues: list[dict[str, Any]],
    collaborators: set[str],
    pr_lookup: dict[str, list[dict[str, Any]]],
    label_to_category: dict[str, str],
    category_keywords: dict[str, list[str]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for issue in open_issues:
        number = str(issue["number"])
        labels = parse_labels(issue)
        linked_prs = pr_lookup.get(number, [])
        has_open_pr = bool(linked_prs)
        is_maintainer_pr = any(
            pr.get("author_login") in collaborators for pr in linked_prs
        )

        if is_maintainer_pr:
            status = "in progress"
        elif has_open_pr:
            status = "community PR"
        elif "awaiting response" in {label.lower().strip() for label in labels}:
            status = "blocked"
        else:
            status = "not started"

        pr_numbers = sorted(pr["number"] for pr in linked_prs)
        pr_links = ", ".join(pr_link(repo, pr_number) for pr_number in pr_numbers)
        records.append(
            {
                "number": number,
                "title": issue.get("title") or "",
                "title_display": escape_table_cell(
                    truncate_title(issue.get("title") or "")
                ),
                "labels": labels,
                "labels_display": escape_table_cell(format_label_string(labels)),
                "created_at": issue.get("createdAt") or "",
                "updated_at": issue.get("updatedAt") or "",
                "created": (issue.get("createdAt") or "")[:10].replace("-", "‑"),
                "updated": (issue.get("updatedAt") or "")[:10].replace("-", "‑"),
                "category": categorize_issue(issue, label_to_category, category_keywords),
                "status": status,
                "pr_numbers": pr_numbers,
                "issue_link": issue_link(repo, number),
                "pr_links": pr_links,
            }
        )

    return records


def build_previous_row_maps(
    rows: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    rows_by_number: dict[str, dict[str, Any]] = {}
    order_by_status: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        number = row["number"]
        rows_by_number[number] = row
        order_by_status[row["status"]].append(number)
    return rows_by_number, order_by_status


def _is_done_expired(row: dict[str, Any], closed_at: dict[str, str], expire_days: int | None) -> bool:
    if expire_days is None:
        return False
    close_date_str = closed_at.get(row["number"])
    if not close_date_str:
        # Fall back to updated date stored in the row (uses non-breaking hyphens)
        close_date_str = row.get("updated", "").replace("‑", "-")
    if not close_date_str:
        return False
    try:
        return (date.today() - date.fromisoformat(close_date_str)).days > expire_days
    except ValueError:
        return False


def merge_rows_for_render(
    current_records: list[dict[str, Any]],
    previous_rows: list[dict[str, Any]],
    closed_at: dict[str, str] | None = None,
    expire_days: int | None = 14,
) -> list[dict[str, Any]]:
    closed_at = closed_at or {}
    previous_by_number, previous_order = build_previous_row_maps(previous_rows)
    current_by_number = {record["number"]: record for record in current_records}
    current_numbers = set(current_by_number)

    groups: dict[str, list[dict[str, Any]]] = {status: [] for status in STATUS_ORDER}

    for record in current_records:
        previous = previous_by_number.get(record["number"])
        if previous and previous["status"] == record["status"]:
            record["sort_key"] = (
                0,
                previous_order[record["status"]].index(record["number"]),
            )
        else:
            record["sort_key"] = (1, int(record["number"]))
        groups[record["status"]].append(record)

    for status in STATUS_ORDER:
        groups[status].sort(key=lambda item: item["sort_key"])

    done_rows: list[dict[str, Any]] = []
    for row in previous_rows:
        if row["status"] == "done" and row["number"] not in current_numbers:
            if _is_done_expired(row, closed_at, expire_days):
                continue
            row = dict(row)
            row["sort_key"] = (0, previous_order["done"].index(row["number"]))
            done_rows.append(row)

    for row in previous_rows:
        if row["status"] != "done" and row["number"] not in current_numbers:
            current = current_by_number.get(row["number"])
            if current is not None:
                continue
            closed_row = dict(row)
            closed_row["status"] = "done"
            closed_row["sort_key"] = (1, int(closed_row["number"]))
            done_rows.append(closed_row)

    done_rows.sort(key=lambda item: item["sort_key"])

    render_rows: list[dict[str, Any]] = []
    for status in STATUS_ORDER[:-1]:
        render_rows.extend(groups[status])
    render_rows.extend(done_rows)

    return render_rows


def compute_summary_rows(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    open_rows = [row for row in rows if row["status"] != "done"]
    open_total = len(open_rows)

    category_counts: dict[str, int] = defaultdict(int)
    for row in open_rows:
        category_counts[row["category"]] += 1

    category_rows = []
    for category in CATEGORY_ORDER:
        count = category_counts.get(category, 0)
        percentage = f"{(count / open_total * 100):.1f}%" if open_total else "0.0%"
        category_rows.append(
            {"category": category, "count": str(count), "percentage": percentage}
        )

    status_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        status_counts[row["status"]] += 1
    status_rows = [
        {"status": status, "count": str(status_counts.get(status, 0))}
        for status in STATUS_ORDER
    ]
    return category_rows, status_rows, open_total


def render_backlog_file(
    repo: str, rows: list[dict[str, Any]], generated_on: str, manual_block: str
) -> str:
    category_rows, status_rows, open_total = compute_summary_rows(rows)
    template = read_text(TEMPLATE_PATH)
    context = {
        "generated_on": generated_on,
        "open_total": str(open_total),
        "category_rows": [
            {**r, "category": f"{CATEGORY_EMOJI.get(r['category'], '')} {r['category']}"}
            for r in category_rows
        ],
        "status_rows": [
            {**r, "status": f"{STATUS_EMOJI.get(r['status'], '')} {r['status']}"}
            for r in status_rows
        ],
        "issue_rows": [
            {
                "issue_link": row["issue_link"],
                "title": row["title_display"],
                "category": f'<span title="{row["category"]}">{CATEGORY_EMOJI.get(row["category"], row["category"])}</span>',
                "status": f'<span title="{row["status"]}">{STATUS_EMOJI.get(row["status"], row["status"])}</span>',
                "pr_links": row["pr_links"],
                "created": row["created"],
                "updated": row["updated"],
                "labels": row["labels_display"],
            }
            for row in rows
        ],
    }
    generated_block = f"{BEGIN_GENERATED}\n{render_template(template, context).rstrip()}\n{END_GENERATED}"
    return f"# Detailed Open Issues: {repo}\n\n{generated_block}\n\n## Manual comments\n{manual_block}\n"


def render_updates_lines(
    generated_at: str,
    new_issues: list[dict[str, Any]],
    status_changes: list[dict[str, Any]],
    label_changes: list[dict[str, Any]],
    closed_issues: list[dict[str, Any]],
) -> str:
    ts = f"`{generated_at}`"
    lines = []
    for row in new_issues:
        title = row.get("title_display") or row.get("title") or ""
        lines.append(f"- {ts} new: {row['issue_link']} {title}")
    for change in status_changes:
        pr_suffix = f" ({change['pr_links']})" if change.get("pr_links") else ""
        title = change.get("title") or ""
        lines.append(
            f"- {ts} status: {change['issue_link']} {title}:"
            f" {change['old_status']} → {change['new_status']}{pr_suffix}"
        )
    for change in label_changes:
        pieces = []
        if change.get("added"):
            pieces.append("added " + ", ".join(f'"{lb}"' for lb in change["added"]))
        if change.get("removed"):
            pieces.append("removed " + ", ".join(f'"{lb}"' for lb in change["removed"]))
        title = change.get("title") or ""
        lines.append(
            f"- {ts} label: {change['issue_link']} {title}: {'; '.join(pieces)}"
        )
    for row in closed_issues:
        title = row.get("title_display") or row.get("title") or ""
        lines.append(f"- {ts} closed: {row['issue_link']} {title}")
    return "\n".join(lines) + "\n" if lines else ""


def snapshot_from_open_records(
    repo: str, records: list[dict[str, Any]], generated_at: str
) -> dict[str, Any]:
    return {
        "repo": repo,
        "generated_at": generated_at,
        "issues": {
            record["number"]: {
                "title": record["title"],
                "state": "OPEN",
                "category": record["category"],
                "status": record["status"],
                "labels": sorted(record["labels"]),
                "pr_numbers": sorted(
                    record["pr_numbers"], key=lambda value: int(value)
                ),
                "created_at": record["created_at"],
                "updated_at": record["updated_at"],
            }
            for record in records
            if record["status"] != "done"
        },
    }


def compare_snapshots(
    previous_snapshot: dict[str, Any] | None,
    current_snapshot: dict[str, Any],
    current_rows_by_number: dict[str, dict[str, Any]],
    previous_rows_by_number: dict[str, dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    if not previous_snapshot:
        return [], [], [], [], []

    previous_issues = previous_snapshot.get("issues", {})
    current_issues = current_snapshot.get("issues", {})

    new_issues: list[dict[str, Any]] = []
    status_changes: list[dict[str, Any]] = []
    label_changes: list[dict[str, Any]] = []
    closed_issues: list[dict[str, Any]] = []
    pr_changes: list[dict[str, Any]] = []

    for issue_number, current in current_issues.items():
        previous = previous_issues.get(issue_number)
        if previous is None:
            new_issues.append(current_rows_by_number[issue_number])
            continue

        if previous.get("status") != current.get("status"):
            status_changes.append(
                {
                    "number": issue_number,
                    "title": current_rows_by_number[issue_number]["title"],
                    "issue_link": current_rows_by_number[issue_number]["issue_link"],
                    "old_status": previous.get("status", "not started"),
                    "new_status": current.get("status", "not started"),
                    "pr_links": current_rows_by_number[issue_number]["pr_links"],
                    "current_pr_numbers": current_rows_by_number[issue_number][
                        "pr_numbers"
                    ],
                }
            )

        previous_labels = previous.get("labels", [])
        current_labels = current.get("labels", [])
        added_labels = [
            label for label in current_labels if label not in previous_labels
        ]
        removed_labels = [
            label for label in previous_labels if label not in current_labels
        ]
        if added_labels or removed_labels:
            label_changes.append(
                {
                    "number": issue_number,
                    "title": current_rows_by_number[issue_number]["title"],
                    "issue_link": current_rows_by_number[issue_number]["issue_link"],
                    "added": added_labels,
                    "removed": removed_labels,
                }
            )

        previous_prs = set(previous.get("pr_numbers", []))
        current_prs = set(current.get("pr_numbers", []))
        added_prs = sorted(current_prs - previous_prs, key=int)
        removed_prs = sorted(previous_prs - current_prs, key=int)
        if added_prs or removed_prs:
            pr_changes.append(
                {
                    "number": issue_number,
                    "title": current_rows_by_number[issue_number]["title"],
                    "issue_link": current_rows_by_number[issue_number]["issue_link"],
                    "added_prs": added_prs,
                    "removed_prs": removed_prs,
                }
            )

    for issue_number, previous in previous_issues.items():
        if issue_number not in current_issues:
            previous_row = previous_rows_by_number.get(issue_number)
            if previous_row is None or previous_row.get("status") == "done":
                continue
            closed_issues.append(previous_row)

    return new_issues, status_changes, label_changes, closed_issues, pr_changes


def build_commit_message(
    new_issues: list[dict[str, Any]],
    status_changes: list[dict[str, Any]],
    label_changes: list[dict[str, Any]],
    closed_issues: list[dict[str, Any]],
    pr_changes: list[dict[str, Any]],
    open_count: int,
) -> str:
    parts: list[str] = []

    if new_issues:
        nums = ", ".join(f"#{r['number']}" for r in new_issues[:3])
        suffix = f" +{len(new_issues) - 3} more" if len(new_issues) > 3 else ""
        parts.append(f"new {nums}{suffix}")

    if closed_issues:
        nums = ", ".join(f"#{r['number']}" for r in closed_issues[:3])
        suffix = f" +{len(closed_issues) - 3} more" if len(closed_issues) > 3 else ""
        parts.append(f"closed {nums}{suffix}")

    for c in status_changes[:3]:
        parts.append(f"#{c['number']} {c['old_status']} → {c['new_status']}")
    if len(status_changes) > 3:
        parts.append(f"+{len(status_changes) - 3} more status changes")

    for c in pr_changes[:3]:
        if c["added_prs"]:
            prs = ", ".join(f"#{p}" for p in c["added_prs"])
            parts.append(f"link {prs} to #{c['number']}")
        if c["removed_prs"]:
            prs = ", ".join(f"#{p}" for p in c["removed_prs"])
            parts.append(f"unlink {prs} from #{c['number']}")
    if len(pr_changes) > 3:
        parts.append(f"+{len(pr_changes) - 3} more PR changes")

    for c in label_changes[:2]:
        pieces = []
        if c.get("added"):
            pieces.append("+" + ", ".join(c["added"]))
        if c.get("removed"):
            pieces.append("-" + ", ".join(c["removed"]))
        parts.append(f"#{c['number']} labels: {'; '.join(pieces)}")
    if len(label_changes) > 2:
        parts.append(f"+{len(label_changes) - 2} more label changes")

    if not parts:
        return f"backlog: sync ({open_count} open) [skip ci]"

    return "backlog: " + "; ".join(parts) + " [skip ci]"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate BACKLOG.md and BACKLOG-UPDATES.md from GitHub state."
    )
    parser.add_argument(
        "--repo",
        help="GitHub repo in owner/name format. Defaults to Sapling/Git remote detection.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing files",
    )
    parser.add_argument(
        "--snapshot-path",
        help="Path to snapshot JSON file. Defaults to the state/ directory next to this script.",
    )
    parser.add_argument(
        "--event-log-path",
        help="Path to events.jsonl. Cleared after a successful update.",
    )
    parser.add_argument(
        "--commit-msg-path",
        help="Write the descriptive commit message to this file.",
    )
    args = parser.parse_args()

    cfg = load_config()
    repo = resolve_repo(args.repo)
    generated_on = today()
    generated_at = iso_now()

    snapshot_path = Path(args.snapshot_path) if args.snapshot_path else STATE_PATH
    event_log_path = Path(args.event_log_path) if args.event_log_path else None
    backlog_path = REPO_ROOT / cfg.backlog_filename
    updates_path = REPO_ROOT / cfg.updates_filename
    categories: dict[str, CategoryConfig] = OmegaConf.to_object(cfg.categories)  # type: ignore[assignment]
    label_to_category: dict[str, str] = {
        label: cat for cat, c in categories.items() for label in c.labels
    }
    category_keywords: dict[str, list[str]] = {
        cat: c.keywords for cat, c in categories.items()
    }

    backlog_text = read_text(backlog_path) if backlog_path.exists() else ""
    previous_rows = [
        normalize_previous_row(repo, row, label_to_category, category_keywords)
        for row in parse_issue_table_rows(backlog_text)
    ]
    previous_rows_by_number = {row["number"]: row for row in previous_rows}
    manual_block = load_existing_manual_block(backlog_text) or canonical_manual_block()
    previous_snapshot = load_json_file(snapshot_path)
    if previous_snapshot and previous_snapshot.get("repo") not in {None, repo}:
        previous_snapshot = None

    collaborators = fetch_collaborators(repo)
    open_issues = fetch_open_issues(repo)
    preserved_done_numbers = {
        row["number"] for row in previous_rows if row["status"] == "done"
    }
    active_open_issues = [
        issue
        for issue in open_issues
        if str(issue["number"]) not in preserved_done_numbers
    ]
    open_issue_numbers = {str(issue["number"]) for issue in active_open_issues}
    open_prs = fetch_open_prs(repo)
    pr_lookup = build_pr_lookup(open_prs, open_issue_numbers)
    current_records = build_current_issue_records(
        repo, active_open_issues, collaborators, pr_lookup, label_to_category, category_keywords
    )
    current_snapshot = snapshot_from_open_records(repo, current_records, generated_at)

    prev_open = set((previous_snapshot or {}).get("issues", {}).keys())
    curr_open = set(current_snapshot["issues"].keys())
    run_date = generated_at[:10]
    closed_at: dict[str, str] = dict((previous_snapshot or {}).get("closed_at", {}))
    for num in prev_open - curr_open:
        closed_at.setdefault(num, run_date)

    render_rows = merge_rows_for_render(current_records, previous_rows, closed_at, expire_days=cfg.done_expire_days)
    rendered_numbers = {row["number"] for row in render_rows}
    current_snapshot["closed_at"] = {
        num: dt for num, dt in closed_at.items() if num in rendered_numbers
    }
    new_issues, status_changes, label_changes, closed_issues, pr_changes = compare_snapshots(
        previous_snapshot,
        current_snapshot,
        {record["number"]: record for record in current_records},
        previous_rows_by_number,
    )
    updates_lines = render_updates_lines(
        generated_at, new_issues, status_changes, label_changes, closed_issues
    )

    backlog_content = render_backlog_file(repo, render_rows, generated_on, manual_block)
    backlog_changed = (
        not backlog_path.exists() or read_text(backlog_path) != backlog_content
    )
    updates_changed = bool(updates_lines)

    if args.dry_run:
        print(f"Resolved GitHub repo: {repo}")
        print(f"BACKLOG.md would {'change' if backlog_changed else 'remain unchanged'}")
        print(
            f"BACKLOG-UPDATES.md would {'prepend lines' if updates_changed else 'remain unchanged'}"
        )
        print(f"Snapshot would contain {len(current_snapshot['issues'])} open issues")
        return 0

    if backlog_changed:
        write_text(backlog_path, backlog_content)

    if updates_changed:
        existing_updates = read_text(updates_path) if updates_path.exists() else ""
        separator = "\n" if existing_updates and not existing_updates.startswith("\n") else ""
        write_text(updates_path, updates_lines + separator + existing_updates)

    save_snapshot(current_snapshot, snapshot_path)
    if event_log_path and event_log_path.exists():
        event_log_path.write_text("", encoding="utf-8")
    print(
        "Updated BACKLOG.md" if backlog_changed else "BACKLOG.md already up to date",
        file=sys.stdout,
    )
    if updates_changed:
        print("Prepended lines to BACKLOG-UPDATES.md", file=sys.stdout)
    else:
        print("No backlog updates needed", file=sys.stdout)
    print(
        f"Saved snapshot for {repo} with {len(current_snapshot['issues'])} open issues",
        file=sys.stdout,
    )
    if args.commit_msg_path:
        commit_msg = build_commit_message(
            new_issues,
            status_changes,
            label_changes,
            closed_issues,
            pr_changes,
            len(current_snapshot["issues"]),
        )
        Path(args.commit_msg_path).write_text(commit_msg, encoding="utf-8")
        print(f"Commit message: {commit_msg}", file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
