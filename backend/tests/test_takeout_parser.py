from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ingest.takeout_parser import build_ingest_payload, compute_anchor_scores, parse_takeout


class TakeoutParserTests(unittest.TestCase):
    def _write_takeout(self, items: list[dict[str, str]]) -> Path:
        handle = tempfile.NamedTemporaryFile("w", delete=False, suffix=".json")
        with handle:
            json.dump(items, handle)
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return Path(handle.name)

    def test_build_ingest_payload_uses_seed_catalog_and_intents(self) -> None:
        path = self._write_takeout(
            [
                {
                    "header": "Search",
                    "title": "Searched for Lahore Kebab House",
                    "time": "2026-05-10T12:00:00Z",
                },
                {
                    "header": "Search",
                    "title": "Searched for directions to Lahore Kebab House",
                    "time": "2026-05-11T12:00:00Z",
                },
                {
                    "header": "Search",
                    "title": "Searched for St. John menu",
                    "time": "2026-05-09T12:00:00Z",
                },
            ]
        )

        events = parse_takeout(path)
        scores = compute_anchor_scores(events)
        venues, anchors = build_ingest_payload(path, top_anchors=2)
        by_id = {venue.id: venue for venue in venues}

        self.assertEqual(len(events), 3)
        self.assertGreater(scores["lahore_kebab"], scores["st_john"])
        self.assertIn("lahore_kebab", anchors)
        self.assertIn("st_john", anchors)
        self.assertEqual(by_id["lahore_kebab"].search_count, 2)
        self.assertEqual(by_id["lahore_kebab"].directions, 1)
        self.assertEqual(by_id["st_john"].search_count, 1)
        self.assertEqual(by_id["st_john"].dishes, ["bone_marrow", "roast_pork", "welsh_rarebit"])


if __name__ == "__main__":
    unittest.main()
