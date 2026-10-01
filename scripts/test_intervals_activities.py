import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from fetch_intervals_activities import gps_points, main, merge_activity, normalize, utc_start


class IntervalsTests(unittest.TestCase):
  def test_gps_stream_formats_and_nulls(self):
    expected = [(35, 139), (35.1, 139.1)]
    self.assertEqual(gps_points([{"type": "latlng", "data": [[35, 139], [None, None], [35.1, 139.1]]}]), expected)
    self.assertEqual(gps_points([{"type": "latlng", "data": [35, None, 35.1], "data2": [139, None, 139.1]}]), expected)

  def test_local_time_converts_to_utc(self):
    self.assertEqual(utc_start({"start_date_local": "2026-09-30T19:32:19", "timezone": "Asia/Tokyo"}), "2026-09-30T10:32:19Z")
    self.assertEqual(utc_start({"start_date_local": "2026-09-30T19:32:19", "timezone": "Europe/Paris"}), "2026-09-30T17:32:19Z")

  def test_archive_merge_preserves_history_and_is_idempotent(self):
    activity = normalize({"id": "i192194275", "type": "Run", "distance": 4407.21,
                          "start_date": "2026-09-30T10:32:19Z"}, [(35, 139), (35.01, 139.01)])
    archive = [{"id": 123, "sport_type": "Run", "distance": 4410, "start_date": "2026-09-30T10:32:20Z"},
               {"id": 456, "sport_type": "Hike", "distance": 1000, "start_date": "2020-01-01T00:00:00Z"}]
    merge_activity(archive, activity)
    self.assertEqual(len(archive), 2)
    self.assertEqual(archive[0]["id"], 123)
    self.assertEqual(archive[1]["id"], 456)
    merge_activity(archive, activity)
    self.assertEqual(len(archive), 2)
    self.assertTrue(archive[0]["summary_polyline"])
    self.assertIn("i192194275", archive[0]["url"])

  def test_different_activity_is_not_merged(self):
    activity = normalize({"id": "i1", "type": "Run", "distance": 4000,
                          "start_date": "2026-09-30T10:32:19Z"}, [(35, 139)])
    archive = [{"id": 123, "sport_type": "Run", "distance": 9000, "start_date": activity["start_date"]}]
    merge_activity(archive, activity)
    self.assertEqual(len(archive), 2)

  def test_ambiguous_match_leaves_archive_unchanged(self):
    activity = normalize({"id": "i1", "type": "Run", "distance": 4000,
                          "start_date": "2026-09-30T10:32:19Z"}, [(35, 139)])
    archive = [{"id": n, "sport_type": "Run", "distance": 4000, "start_date": activity["start_date"]} for n in (1, 2)]
    with self.assertRaises(ValueError):
      merge_activity(archive, activity)
    self.assertEqual([item["id"] for item in archive], [1, 2])

  def test_failed_fetch_does_not_write_partial_archive(self):
    activity = {"id": "i1", "source": "COROS", "type": "Run", "distance": 4000,
                "start_date": "2026-09-30T10:32:19Z", "stream_types": ["latlng"]}
    with tempfile.TemporaryDirectory() as directory:
      output = Path(directory) / "archive.json"
      original = '[{"id": 123}]'
      output.write_text(original)
      with patch("sys.argv", ["sync", "--output", str(output)]), \
           patch.dict("os.environ", {"INTERVALS_API_KEY": "test-key"}), \
           patch("fetch_intervals_activities.urlopen") as request:
        request.return_value.__enter__.return_value.read.return_value = json.dumps([activity])
        request.side_effect = [request.return_value, OSError("connection lost")]
        with self.assertRaises(OSError):
          main()
      self.assertEqual(output.read_text(), original)


if __name__ == "__main__":
  unittest.main()
