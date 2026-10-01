#!/usr/bin/env python3
"""Read activity metadata and check GPS availability without changing site data."""

import argparse
import base64
import getpass
import json
import os
import sys
from collections import Counter
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--oldest", default="2026-09-01", help="First local date (YYYY-MM-DD)")
  parser.add_argument("--newest", default="2026-10-01", help="Last local date (YYYY-MM-DD)")
  args = parser.parse_args()
  key = os.environ.get("INTERVALS_API_KEY") or getpass.getpass("Intervals.icu API key: ")
  if not key.strip():
    parser.error("API key is required")
  authorization = base64.b64encode(f"API_KEY:{key.strip()}".encode()).decode()

  def fetch(path):
    request = Request(
      f"https://intervals.icu/api/v1/{path}",
      headers={"Authorization": f"Basic {authorization}", "Accept": "application/json",
               "User-Agent": "Mozilla/5.0 (personal activity API probe)"},
    )
    with urlopen(request, timeout=60) as response:
      return json.load(response)

  try:
    query = urlencode({"oldest": args.oldest, "newest": args.newest})
    activities = fetch(f"athlete/0/activities?{query}")
    if not isinstance(activities, list):
      raise ValueError("Unexpected activity response")
    print(f"Activities: {len(activities)}")
    print("Sources:", dict(Counter(item.get("source", "UNKNOWN") for item in activities)))
    restricted = sum(bool(item.get("_note")) for item in activities)
    print(f"Activities with API restriction notes: {restricted}")
    candidates = [item for item in activities if not item.get("_note") and
                  "latlng" in (item.get("stream_types") or [])]
    if not candidates:
      print("No unrestricted activity advertising a GPS stream in this date range.")
      return
    activity = max(candidates, key=lambda item: item.get("start_date_local", ""))
    print("Sample:", json.dumps({field: activity.get(field) for field in
          ("id", "source", "type", "start_date_local", "distance", "moving_time",
           "total_elevation_gain")}, ensure_ascii=False))
    activity_id = quote(str(activity["id"]), safe="")
    streams = fetch(f"activity/{activity_id}/streams.json?types=latlng")
    if not isinstance(streams, list):
      raise ValueError("Unexpected stream response")
    gps = next((stream for stream in streams if stream.get("type") == "latlng"), None)
    print(f"GPS stream present: {gps is not None}")
    print(f"GPS samples: {len((gps or {}).get('data') or [])}")
  except HTTPError as error:
    print(f"API HTTP error: {error.code} (response body omitted)", file=sys.stderr)
    sys.exit(1)
  except (URLError, ValueError, KeyError) as error:
    print(f"Probe failed: {type(error).__name__}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
  main()
