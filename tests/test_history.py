import csv
from collections import Counter
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from history import generate


class HistoryTests(unittest.TestCase):
    def test_reproducible_and_cross_source_consistency(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            manifest = generate(out / "a", days=9, students=12, courses=3)
            generate(out / "b", days=9, students=12, courses=3)
            for name in ["manifest.json", "metrics.csv", "http.jsonl", "tickets.json"]:
                self.assertEqual((out / "a" / name).read_bytes(), (out / "b" / name).read_bytes())
            with (out / "a/metrics.csv").open() as source:
                metrics = list(csv.DictReader(source))
            events = [json.loads(line) for line in (out / "a/http.jsonl").read_text().splitlines()]
            self.assertEqual(len(metrics), 9 * 24 * 4)
            self.assertEqual(sum(int(m["requests"]) for m in metrics), len(events))
            self.assertEqual(sum(int(m["errors_5xx"]) for m in metrics), sum(e["status"] >= 500 for e in events))
            self.assertEqual(manifest["http_events"], len(events))
            buckets = Counter()
            errors = Counter()
            for event in events:
                dt = datetime.fromisoformat(event["timestamp"])
                bucket = dt.replace(minute=dt.minute // 15 * 15, second=0).isoformat()
                buckets[bucket] += 1
                errors[bucket] += event["status"] >= 500
                self.assertEqual(event["source"], "synthetic")
                self.assertLessEqual(int(event["actor"].replace("estudiante", "")), 12)
            tickets = json.loads((out / "a/tickets.json").read_text())
            for metric in metrics:
                self.assertEqual(int(metric["requests"]), buckets[metric["timestamp"]])
                self.assertEqual(int(metric["errors_5xx"]), errors[metric["timestamp"]])
                self.assertLessEqual(datetime.fromisoformat(metric["cron_last_success"]), datetime.fromisoformat(metric["timestamp"]))
            for event in events:
                if event["status"] >= 500:
                    dt = datetime.fromisoformat(event["timestamp"])
                    self.assertTrue(any(datetime.fromisoformat(t["start"]) <= dt < datetime.fromisoformat(t["end"]) for t in tickets))
            for filename, digest in manifest["sha256"].items():
                self.assertEqual(hashlib.sha256((out / "a" / filename).read_bytes()).hexdigest(), digest)
            last = datetime.fromisoformat(metrics[-1]["timestamp"])
            self.assertEqual(last + timedelta(minutes=15), datetime.fromisoformat(manifest["end_exclusive"]))

    def test_invalid_scale(self):
        with tempfile.TemporaryDirectory() as directory:
            for days, courses, students in [(0, 3, 12), (367, 3, 12), (1, 0, 12), (1, 3, 0)]:
                with self.assertRaises(ValueError):
                    generate(Path(directory), days=days, courses=courses, students=students)
