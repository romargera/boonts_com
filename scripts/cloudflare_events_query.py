#!/usr/bin/env python3
"""Query Boonts event counters from Cloudflare Workers KV."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any


DEFAULT_NAMESPACE_ID = "06a769c07a404aae9d8d740a62274b55"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-id", default=os.getenv("CLOUDFLARE_ACCOUNT_ID"))
    parser.add_argument("--api-token", default=os.getenv("CLOUDFLARE_API_TOKEN"))
    parser.add_argument("--namespace-id", default=os.getenv("BOONTS_EVENTS_KV_NAMESPACE_ID", DEFAULT_NAMESPACE_ID))
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a table")
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Optional dotenv file to load before reading env vars (default: .env)",
    )
    return parser.parse_args()


def load_env(path: str) -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def decode_event_key(key: str) -> dict[str, str]:
    if key.startswith("event2:"):
        _, day, event_name, encoded_path, channel, receipt = key.split(":", 5)
        return {"date": day, "event_name": event_name, "path": urllib.parse.unquote(encoded_path), "channel": channel}
    parts = key.split(":", 3)
    if len(parts) != 4 or parts[0] != "event":
        raise ValueError(f"Unexpected event key: {key}")
    _, day, event_name, encoded_path = parts
    return {
        "date": day,
        "event_name": event_name,
        "path": urllib.parse.unquote(encoded_path),
    }


def aggregate_kv_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[tuple[str, str, str], int] = {}
    for item in items:
        decoded = decode_event_key(str(item["name"]))
        is_receipt = str(item["name"]).startswith("event2:")
        value = 1 if is_receipt else int(item.get("value") or 0)
        channel = decoded.get("channel", "legacy-unknown")
        key = (decoded["date"], decoded["event_name"], decoded["path"], channel)
        totals[key] = totals.get(key, 0) + value

    rows = [
        {"date": day, "event_name": event_name, "path": path, "count": count, "channel": channel}
        for (day, event_name, path, channel), count in totals.items()
    ]
    rows.sort(key=lambda row: (row["date"], row["count"], row["event_name"]), reverse=True)
    return rows


def cf_request(account_id: str, namespace_id: str, token: str, path: str) -> Any:
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/storage/kv/namespaces/{namespace_id}{path}"
    )
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return json.loads(body)
            return body
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Cloudflare API HTTP {error.code}: {body}") from error


def list_keys(account_id: str, namespace_id: str, token: str, prefix: str) -> list[str]:
    keys: list[str] = []
    cursor = ""
    while True:
        query = urllib.parse.urlencode({"prefix": prefix, "limit": 1000, "cursor": cursor})
        payload = cf_request(account_id, namespace_id, token, f"/keys?{query}")
        keys.extend(item["name"] for item in payload.get("result", []))
        cursor = payload.get("result_info", {}).get("cursor") or ""
        if not cursor:
            return keys


def fetch_event_rows(account_id: str, namespace_id: str, token: str, days: int) -> list[dict[str, Any]]:
    cutoff = (date.today() - timedelta(days=days - 1)).isoformat()
    keys = [key for prefix in ("event:", "event2:") for key in list_keys(account_id, namespace_id, token, prefix) if key.split(":", 3)[1] >= cutoff]
    rows = []
    for key in keys:
        value = "1" if key.startswith("event2:") else cf_request(account_id, namespace_id, token, f"/values/{urllib.parse.quote(key, safe='')}")
        rows.append({"name": key, "value": value})
    return rows


def print_table(rows: list[dict[str, Any]]) -> None:
    headers = ["date", "event_name", "path", "channel", "count"]
    widths = {header: len(header) for header in headers}
    for row in rows:
        for header in headers:
            widths[header] = max(widths[header], len(str(row.get(header, ""))))

    print(" | ".join(header.ljust(widths[header]) for header in headers))
    print("-+-".join("-" * widths[header] for header in headers))
    for row in rows:
        print(" | ".join(str(row.get(header, "")).ljust(widths[header]) for header in headers))


def main() -> int:
    args = parse_args()
    load_env(args.env_file)

    account_id = args.account_id or os.getenv("CLOUDFLARE_ACCOUNT_ID")
    token = args.api_token or os.getenv("CLOUDFLARE_API_TOKEN")
    if not account_id or not token:
        print("Missing CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN.", file=sys.stderr)
        return 2

    try:
        rows = aggregate_kv_rows(fetch_event_rows(account_id, args.namespace_id, token, args.days))
    except Exception as error:  # noqa: BLE001
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    rows = rows[: args.limit]
    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        print_table(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
