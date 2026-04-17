#!/usr/bin/env python3
"""Read daily analytics backups and print a date-level summary."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-key", required=True, help="Site key used in backup files")
    parser.add_argument(
        "--data-root",
        default="analytics/daily",
        help="Root folder for analytics backup files (default: analytics/daily)",
    )
    parser.add_argument(
        "--git-ref",
        default="origin/analytics-data",
        help="Git ref containing backup files (default: origin/analytics-data). Use empty string to read local files only.",
    )
    parser.add_argument("--from-date", help="Filter start date YYYY-MM-DD")
    parser.add_argument("--to-date", help="Filter end date YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=90, help="Max rows in output (default: 90)")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of table")
    return parser.parse_args()


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def run_git(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(args, check=False, capture_output=True, text=True)
    return proc.returncode, proc.stdout


def list_backup_paths_from_git(git_ref: str, site_root: str) -> list[str]:
    code, output = run_git(["git", "ls-tree", "-r", "--name-only", git_ref, "--", site_root])
    if code != 0:
        return []
    return [line.strip() for line in output.splitlines() if line.strip().endswith(".json")]


def load_json_from_git(git_ref: str, file_path: str) -> dict[str, Any] | None:
    code, output = run_git(["git", "show", f"{git_ref}:{file_path}"])
    if code != 0:
        return None
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def list_backup_paths_local(site_root: Path) -> list[Path]:
    if not site_root.exists():
        return []
    return [path for path in site_root.glob("*.json") if path.is_file()]


def normalize_row(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    date_value = str(snapshot.get("date", ""))
    if not DATE_RE.match(date_value):
        return None

    totals = snapshot.get("totals", {})
    if not isinstance(totals, dict):
        totals = {}

    events = snapshot.get("events", [])
    if not isinstance(events, list):
        events = []

    clicks_total = 0
    for event in events:
        if not isinstance(event, dict):
            continue
        name = str(event.get("name", ""))
        if name.startswith("click-"):
            value = event.get("count", 0)
            if isinstance(value, (int, float)):
                clicks_total += int(value)

    return {
        "date": date_value,
        "pageviews": int(totals.get("pageviews", 0) or 0),
        "visitors": int(totals.get("visitors", 0) or 0),
        "visits": int(totals.get("visits", 0) or 0),
        "bounces": int(totals.get("bounces", 0) or 0),
        "clicks": clicks_total,
        "events_count": len(events),
    }


def print_table(rows: list[dict[str, Any]]) -> None:
    headers = ["date", "pageviews", "visitors", "visits", "bounces", "clicks", "events_count"]
    widths = {header: len(header) for header in headers}
    for row in rows:
        for header in headers:
            widths[header] = max(widths[header], len(str(row.get(header, ""))))

    line = " | ".join(header.ljust(widths[header]) for header in headers)
    divider = "-+-".join("-" * widths[header] for header in headers)
    print(line)
    print(divider)
    for row in rows:
        print(" | ".join(str(row.get(header, "")).ljust(widths[header]) for header in headers))


def main() -> int:
    args = parse_args()

    start = parse_date(args.from_date)
    end = parse_date(args.to_date)

    site_root = f"{args.data_root.rstrip('/')}/{args.site_key}"
    collected: list[dict[str, Any]] = []

    if args.git_ref:
        if args.git_ref.startswith("origin/"):
            remote_branch = args.git_ref.split("/", 1)[1]
            run_git(["git", "fetch", "origin", remote_branch])
        for file_path in list_backup_paths_from_git(args.git_ref, site_root):
            name = Path(file_path).name
            if name == "latest.json":
                continue
            if not DATE_RE.match(Path(name).stem):
                continue
            snapshot = load_json_from_git(args.git_ref, file_path)
            if snapshot:
                row = normalize_row(snapshot)
                if row:
                    collected.append(row)
    else:
        for local_path in list_backup_paths_local(Path(site_root)):
            name = local_path.name
            if name == "latest.json":
                continue
            if not DATE_RE.match(local_path.stem):
                continue
            try:
                snapshot = json.loads(local_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if isinstance(snapshot, dict):
                row = normalize_row(snapshot)
                if row:
                    collected.append(row)

    unique_by_date = {row["date"]: row for row in collected}
    rows = [unique_by_date[key] for key in sorted(unique_by_date.keys())]

    if start:
        rows = [row for row in rows if datetime.strptime(row["date"], "%Y-%m-%d").date() >= start]
    if end:
        rows = [row for row in rows if datetime.strptime(row["date"], "%Y-%m-%d").date() <= end]
    if args.limit > 0:
        rows = rows[-args.limit :]

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        if not rows:
            print("No daily backup rows found for the provided filters.")
        else:
            print_table(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
