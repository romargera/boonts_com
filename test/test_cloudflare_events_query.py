from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.cloudflare_events_query import aggregate_kv_rows, decode_event_key


class CloudflareEventsQueryTest(unittest.TestCase):
    def test_decodes_event_counter_keys(self):
        decoded = decode_event_key("event:2026-05-12:click-linkedin:%2F")

        self.assertEqual(decoded["date"], "2026-05-12")
        self.assertEqual(decoded["event_name"], "click-linkedin")
        self.assertEqual(decoded["path"], "/")

    def test_aggregates_kv_rows(self):
        rows = aggregate_kv_rows(
            [
                {"name": "event:2026-05-12:click-linkedin:%2F", "value": "2"},
                {"name": "event:2026-05-12:click-linkedin:%2F", "value": "3"},
                {"name": "event:2026-05-12:scroll-50:%2F", "value": "1"},
            ]
        )

        self.assertEqual(
            rows,
            [
                {
                    "date": "2026-05-12",
                    "event_name": "click-linkedin",
                    "path": "/",
                    "count": 5,
                    "channel": "legacy-unknown",
                },
                {
                    "date": "2026-05-12",
                    "event_name": "scroll-50",
                    "path": "/",
                    "count": 1,
                    "channel": "legacy-unknown",
                },
            ],
        )

    def test_receipts_count_individually_by_source(self):
        rows = aggregate_kv_rows([
            {"name": "event2:2026-09-05:click-gcal-hiring:%2F:google:a", "value": "1"},
            {"name": "event2:2026-09-05:click-gcal-hiring:%2F:google:b", "value": "1"},
            {"name": "event2:2026-09-05:click-gcal-hiring:%2F:ai:c", "value": "1"},
        ])
        self.assertEqual({r["channel"]: r["count"] for r in rows}, {"google": 2, "ai": 1})

if __name__ == "__main__":
    unittest.main()
