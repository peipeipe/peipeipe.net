#!/usr/bin/env python3
"""Merge GPS activities from Intervals.icu into the existing activity archive."""
import argparse
import base64
import getpass
import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from generate_strava_activities_from_export import encode_polyline, simplify_points

OUTPUT = Path(__file__).resolve().parents[1] / "astro/data/strava_activities.json"


def utc_start(activity):
  value = activity.get("start_date")
  if value:
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if date.tzinfo is None:
      raise ValueError("UTC start_date is missing a timezone")
  else:
    date = datetime.fromisoformat(activity["start_date_local"])
    date = date.replace(tzinfo=ZoneInfo(activity.get("timezone") or "Asia/Tokyo"))
  return date.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def gps_points(streams):
  stream = next((item for item in streams if item.get("type") == "latlng"), {})
  data = stream.get("data") or []
  if stream.get("data2") is not None and len(data) != len(stream["data2"]):
    raise ValueError("GPS latitude/longitude lengths differ")
  pairs = zip(data, stream["data2"]) if stream.get("data2") is not None else data
  points = []
  for pair in pairs:
    if not isinstance(pair, (list, tuple)) or len(pair) != 2:
      raise ValueError("Unexpected GPS stream shape")
    lat, lng = pair
    if lat is None or lng is None:
      continue
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in pair):
      raise ValueError("Invalid GPS coordinate")
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
      raise ValueError("GPS coordinate out of range")
    points.append((lat, lng))
  return points


def normalize(activity, points):
  identifier = str(activity["id"])
  result = {field: activity.get(field) or 0 for field in
            ("moving_time", "elapsed_time", "total_elevation_gain", "average_speed", "max_speed")}
  result.update({
    "id": identifier, "intervals_id": identifier, "source": "intervals",
    "url": f"https://intervals.icu/activities/{quote(identifier, safe='')}",
    "name": activity.get("name") or activity.get("type") or "Activity",
    "sport_type": activity.get("type") or "Workout",
    "distance": activity.get("icu_distance") if activity.get("icu_distance") is not None else activity.get("distance") or 0,
    "start_date": utc_start(activity), "start_date_local": activity.get("start_date_local", ""),
    "start_latlng": list(points[0]),
    "summary_polyline": encode_polyline(simplify_points(points, 10)),
  })
  return result


def same_record(old, new):
  if old.get("intervals_id") == new["intervals_id"]:
    return True
  if old.get("source") == "intervals":
    return False
  if old.get("sport_type") != new["sport_type"]:
    return False
  try:
    delta = abs((datetime.fromisoformat(utc_start(old).replace("Z", "+00:00")) -
                 datetime.fromisoformat(new["start_date"].replace("Z", "+00:00"))).total_seconds())
  except (ValueError, KeyError):
    return False
  distance = new["distance"]
  return delta <= 5 and abs((old.get("distance") or 0) - distance) <= max(100, distance * .03)


def merge_activity(archive, activity):
  matches = [index for index, old in enumerate(archive) if same_record(old, activity)]
  if len(matches) > 1:
    raise ValueError("Ambiguous duplicate activity; archive left unchanged")
  if matches:
    index = matches[0]
    activity = dict(activity, id=archive[index]["id"])
    archive[index] = activity
  else:
    archive.append(activity)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--oldest", default="1970-01-01", help="First local date to sync")
  parser.add_argument("--output", type=Path, default=OUTPUT)
  args = parser.parse_args()
  key = os.environ.get("INTERVALS_API_KEY")
  if not key and os.isatty(0):
    key = getpass.getpass("Intervals.icu API key: ")
  if not key:
    parser.error("INTERVALS_API_KEY is required")
  authorization = base64.b64encode(f"API_KEY:{key.strip()}".encode()).decode()

  def fetch(path):
    request = Request(f"https://intervals.icu/api/v1/{path}", headers={
      "Authorization": f"Basic {authorization}", "Accept": "application/json",
      "User-Agent": "Mozilla/5.0 (peipeipe.net personal activity sync)",
    })
    with urlopen(request, timeout=60) as response:
      return json.load(response)

  archive = json.loads(args.output.read_text()) if args.output.exists() else []
  # Read the full metadata history so delayed uploads are not missed. Fetch GPS
  # only for new activities and the last 30 days (where edits are most likely).
  today = datetime.now(ZoneInfo("Asia/Tokyo")).date()
  query = urlencode({"oldest": args.oldest, "newest": str(today + timedelta(days=1))})
  activities = fetch(f"athlete/0/activities?{query}")
  if not isinstance(activities, list):
    raise ValueError("Unexpected activity response")
  known = {item.get("intervals_id") for item in archive}
  processed = 0
  for item in activities:
    if item.get("source") == "STRAVA" or item.get("_note"):
      continue
    if "latlng" not in (item.get("stream_types") or []):
      continue
    if str(item["id"]) in known and item.get("start_date_local", "")[:10] < str(today - timedelta(days=30)):
      continue
    streams = fetch(f"activity/{quote(str(item['id']), safe='')}/streams.json?types=latlng")
    points = gps_points(streams)
    if not points:
      continue
    merge_activity(archive, normalize(item, points))
    processed += 1
  archive.sort(key=lambda item: item.get("start_date", ""), reverse=True)
  # All requests and conversions must succeed before replacing the archive.
  temporary = args.output.with_suffix(".json.tmp")
  temporary.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + "\n")
  temporary.replace(args.output)
  print(f"Synced {processed} GPS activities; archive contains {len(archive)} activities")


if __name__ == "__main__":
  main()
