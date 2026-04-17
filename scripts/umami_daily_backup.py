#!/usr/bin/env python3
"""Collect one-day aggregated analytics snapshot from Umami."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


class BackupError(RuntimeError):
    """Raised when backup collection cannot be completed."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Umami base URL, e.g. https://analytics.example.com")
    parser.add_argument("--username", required=True, help="Umami username")
    parser.add_argument("--password", required=True, help="Umami password")
    parser.add_argument("--website-id", required=True, help="Umami website UUID")
    parser.add_argument("--site-key", required=True, help="Local key used in backup folder names")
    parser.add_argument("--timezone", default="UTC", help="IANA timezone, e.g. Europe/Belgrade")
    parser.add_argument("--date", help="Date in YYYY-MM-DD format; default is yesterday in selected timezone")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    return parser.parse_args()


def to_utc_z(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve_day(date_str: str | None, timezone_name: str) -> tuple[str, int, int, str, str]:
    tz = ZoneInfo(timezone_name)
    if date_str:
        try:
            day = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as exc:
            raise BackupError("Invalid --date format. Expected YYYY-MM-DD.") from exc
    else:
        day = datetime.now(tz).date() - timedelta(days=1)

    start = datetime(day.year, day.month, day.day, tzinfo=tz)
    end = start + timedelta(days=1) - timedelta(milliseconds=1)

    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)

    return day.isoformat(), start_ms, end_ms, to_utc_z(start), to_utc_z(end)


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    token: str | None = None,
    payload: dict[str, Any] | None = None,
) -> tuple[int, Any, str]:
    base = base_url.rstrip("/")
    if path.startswith("http://") or path.startswith("https://"):
        url = path
    else:
        url = f"{base}{path}"

    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw else None
            return response.status, data, url
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            data = {"raw": raw}
        return error.code, data, url


def login(base_url: str, username: str, password: str) -> str:
    status, payload, url = request_json(
        base_url,
        "/api/auth/login",
        method="POST",
        payload={"username": username, "password": password},
    )
    token = payload.get("token") if isinstance(payload, dict) else None
    if status != 200 or not token:
        raise BackupError(f"Umami auth failed on {url} with HTTP {status}.")
    return token


def first_success(
    base_url: str,
    token: str,
    paths: list[str],
) -> tuple[Any | None, dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    for path in paths:
        status, payload, url = request_json(base_url, path, token=token)
        attempts.append({"path": path, "status": status})
        if status == 200 and payload is not None:
            return payload, {"endpoint": path, "url": url, "attempts": attempts}
    return None, {"endpoint": None, "url": None, "attempts": attempts}


def number(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(round(value))
    if isinstance(value, str):
        try:
            return int(round(float(value)))
        except ValueError:
            return 0
    if isinstance(value, dict):
        for key in ("value", "total", "count", "y", "sum"):
            if key in value:
                return number(value[key])
    return 0


def parse_totals(stats: Any) -> dict[str, int]:
    if not isinstance(stats, dict):
        return {"pageviews": 0, "visitors": 0, "visits": 0, "bounces": 0, "totaltime": 0}

    def pick(*keys: str) -> int:
        for key in keys:
            if key in stats:
                return number(stats[key])
        return 0

    return {
        "pageviews": pick("pageviews", "pageViews"),
        "visitors": pick("visitors", "uniqueVisitors"),
        "visits": pick("visits", "sessions"),
        "bounces": pick("bounces", "bounce"),
        "totaltime": pick("totaltime", "totalTime", "avgVisitTime"),
    }


def extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("data", "results", "metrics", "items", "rows", "events", "pageviews", "urls"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []


def normalize_rows(rows: list[dict[str, Any]], *, row_type: str) -> list[dict[str, Any]]:
    name_keys = ["x", "name", "label", "eventName", "event", "url", "pathname", "path"]
    value_keys = ["y", "value", "count", "visits", "pageviews", "total", "sum"]

    merged: dict[str, int] = {}
    for row in rows:
        row_name = ""
        for key in name_keys:
            value = row.get(key)
            if value not in (None, ""):
                row_name = str(value)
                break
        if not row_name and row_type == "events":
            for key, value in row.items():
                if key.lower().endswith("name") and value not in (None, ""):
                    row_name = str(value)
                    break
        if not row_name:
            continue

        row_count = 0
        for key in value_keys:
            if key in row:
                row_count = number(row.get(key))
                break
        if row_count == 0:
            for value in row.values():
                if isinstance(value, (int, float)):
                    row_count = number(value)
                    break

        merged[row_name] = merged.get(row_name, 0) + row_count

    normalized = [{"name": key, "count": value} for key, value in merged.items()]
    normalized.sort(key=lambda item: (-item["count"], item["name"]))
    return normalized


def fetch_totals(base_url: str, token: str, website_id: str, start_ms: int, end_ms: int) -> tuple[dict[str, int], dict[str, Any]]:
    query = urllib.parse.urlencode({"startAt": start_ms, "endAt": end_ms})
    payload, meta = first_success(
        base_url,
        token,
        [f"/api/websites/{website_id}/stats?{query}", f"/api/websites/{website_id}/stats?{query}&unit=day"],
    )
    return parse_totals(payload), meta


def fetch_breakdown(
    base_url: str,
    token: str,
    website_id: str,
    start_ms: int,
    end_ms: int,
    *,
    kind: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    query = urllib.parse.urlencode({"startAt": start_ms, "endAt": end_ms})
    if kind == "pages":
        candidates = [
            f"/api/websites/{website_id}/metrics?type=url&{query}",
            f"/api/websites/{website_id}/event-data?type=url&{query}",
            f"/api/websites/{website_id}/events?type=url&{query}",
            f"/api/websites/{website_id}/pageviews?{query}",
        ]
        row_type = "pages"
    else:
        candidates = [
            f"/api/websites/{website_id}/metrics?type=event&{query}",
            f"/api/websites/{website_id}/event-data?type=event&{query}",
            f"/api/websites/{website_id}/events?type=event&{query}",
            f"/api/websites/{website_id}/events?{query}",
        ]
        row_type = "events"

    payload, meta = first_success(base_url, token, candidates)
    rows = extract_rows(payload)
    return normalize_rows(rows, row_type=row_type), meta


def write_json(path: str, payload: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    try:
        date_iso, start_ms, end_ms, start_utc, end_utc = resolve_day(args.date, args.timezone)
        token = login(args.base_url, args.username, args.password)

        totals, totals_meta = fetch_totals(args.base_url, token, args.website_id, start_ms, end_ms)
        pages, pages_meta = fetch_breakdown(args.base_url, token, args.website_id, start_ms, end_ms, kind="pages")
        events, events_meta = fetch_breakdown(args.base_url, token, args.website_id, start_ms, end_ms, kind="events")

        snapshot = {
            "schema_version": 1,
            "provider": "umami",
            "site_key": args.site_key,
            "website_id": args.website_id,
            "date": date_iso,
            "timezone": args.timezone,
            "window": {
                "start_at_ms": start_ms,
                "end_at_ms": end_ms,
                "start_at_utc": start_utc,
                "end_at_utc": end_utc,
            },
            "totals": totals,
            "pages": pages,
            "events": events,
            "meta": {
                "collected_at_utc": to_utc_z(datetime.now(timezone.utc)),
                "endpoints": {
                    "totals": totals_meta,
                    "pages": pages_meta,
                    "events": events_meta,
                },
            },
        }
        write_json(args.output, snapshot)
        print(f"Wrote daily snapshot for {date_iso} to {args.output}")
        return 0
    except BackupError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except Exception as error:  # noqa: BLE001
        print(f"ERROR: unexpected failure: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
