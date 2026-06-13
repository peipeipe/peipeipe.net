#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strava export ZIP から _data/strava_activities.json を生成する。

使い方:
  python3 scripts/generate_strava_activities_from_export.py /path/to/export.zip

外部依存を増やさないため、FIT は record message の GPS 点列に必要な範囲だけ
標準ライブラリで解析する。
"""

import argparse
import csv
import gzip
import io
import json
import math
import os
import struct
import sys
import zipfile
from datetime import datetime, timezone
from xml.etree import ElementTree

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUTPUT_JSON = os.path.join(BASE_DIR, "_data", "strava_activities.json")
SEMICIRCLE_TO_DEGREES = 180.0 / (2**31)
INVALID_SINT32 = 0x7FFFFFFF

# FIT base type id -> (name, size, struct format, invalid value)
BASE_TYPES = {
    0x00: ("enum", 1, "B", 0xFF),
    0x01: ("sint8", 1, "b", 0x7F),
    0x02: ("uint8", 1, "B", 0xFF),
    0x83: ("sint16", 2, "h", 0x7FFF),
    0x84: ("uint16", 2, "H", 0xFFFF),
    0x85: ("sint32", 4, "i", INVALID_SINT32),
    0x86: ("uint32", 4, "I", 0xFFFFFFFF),
    0x07: ("string", 1, None, 0x00),
    0x88: ("float32", 4, "f", None),
    0x89: ("float64", 8, "d", None),
    0x0A: ("uint8z", 1, "B", 0x00),
    0x8B: ("uint16z", 2, "H", 0x0000),
    0x8C: ("uint32z", 4, "I", 0x00000000),
    0x0D: ("byte", 1, "B", 0xFF),
    0x8E: ("sint64", 8, "q", 0x7FFFFFFFFFFFFFFF),
    0x8F: ("uint64", 8, "Q", 0xFFFFFFFFFFFFFFFF),
    0x90: ("uint64z", 8, "Q", 0x0000000000000000),
}

SPORT_TYPE_MAP = {
    "Alpine Ski": "AlpineSki",
    "Hike": "Hike",
    "Ride": "Ride",
    "Run": "Run",
    "Snowboard": "Snowboard",
    "Swim": "Swim",
    "Walk": "Walk",
    "Weight Training": "WeightTraining",
    "Workout": "Workout",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate _data/strava_activities.json from a Strava export ZIP."
    )
    parser.add_argument("export_zip", help="Path to Strava export ZIP")
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_JSON,
        help=f"Output JSON path (default: {DEFAULT_OUTPUT_JSON})",
    )
    parser.add_argument(
        "--no-existing-merge",
        action="store_true",
        help="Do not reuse values from the existing output JSON for matching activity IDs.",
    )
    parser.add_argument(
        "--existing-json",
        default=DEFAULT_OUTPUT_JSON,
        help=f"Existing JSON used to preserve API-only values (default: {DEFAULT_OUTPUT_JSON})",
    )
    parser.add_argument(
        "--tolerance-m",
        type=float,
        default=10.0,
        help="Polyline simplification tolerance in meters (default: 10)",
    )
    return parser.parse_args()


def load_existing(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return {int(item["id"]): item for item in json.load(f) if "id" in item}


def parse_float(value, default=0.0):
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def parse_int(value, default=0):
    return int(round(parse_float(value, default)))


def parse_activity_date(value):
    if not value:
        return ""
    for fmt in ("%b %d, %Y, %I:%M:%S %p", "%b %d, %Y, %H:%M:%S"):
        try:
            dt = datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            return dt.isoformat().replace("+00:00", "Z")
        except ValueError:
            pass
    return value


def decode_field(data, endian, field_def):
    field_num, size, base_type = field_def
    base = BASE_TYPES.get(base_type & 0x1F) or BASE_TYPES.get(base_type)
    if not base:
        return None

    name, base_size, fmt, invalid = base
    if name == "string":
        return data.split(b"\x00", 1)[0].decode("utf-8", errors="replace")

    if not fmt or size < base_size:
        return None

    values = []
    prefix = "<" if endian == "little" else ">"
    for offset in range(0, size - base_size + 1, base_size):
        chunk = data[offset : offset + base_size]
        value = struct.unpack(prefix + fmt, chunk)[0]
        if invalid is not None and value == invalid:
            values.append(None)
        else:
            values.append(value)

    if not values:
        return None
    return values[0] if len(values) == 1 else values


def iter_fit_messages(fit_bytes):
    if len(fit_bytes) < 14:
        return

    header_size = fit_bytes[0]
    if header_size not in (12, 14):
        raise ValueError(f"Unsupported FIT header size: {header_size}")

    data_size = struct.unpack_from("<I", fit_bytes, 4)[0]
    pos = header_size
    end = min(pos + data_size, len(fit_bytes))
    definitions = {}

    while pos < end:
        record_header = fit_bytes[pos]
        pos += 1

        if record_header & 0x80:
            local_msg_type = (record_header >> 5) & 0x03
            is_definition = False
            has_developer_fields = False
        else:
            local_msg_type = record_header & 0x0F
            is_definition = bool(record_header & 0x40)
            has_developer_fields = bool(record_header & 0x20)

        if is_definition:
            pos += 1  # reserved
            architecture = fit_bytes[pos]
            pos += 1
            endian = "big" if architecture == 1 else "little"
            prefix = ">" if endian == "big" else "<"
            global_msg_num = struct.unpack_from(prefix + "H", fit_bytes, pos)[0]
            pos += 2

            field_count = fit_bytes[pos]
            pos += 1
            fields = []
            for _ in range(field_count):
                field_num = fit_bytes[pos]
                size = fit_bytes[pos + 1]
                base_type = fit_bytes[pos + 2]
                pos += 3
                fields.append((field_num, size, base_type))

            if has_developer_fields:
                dev_field_count = fit_bytes[pos]
                pos += 1 + dev_field_count * 3

            definitions[local_msg_type] = {
                "global_msg_num": global_msg_num,
                "endian": endian,
                "fields": fields,
            }
            continue

        definition = definitions.get(local_msg_type)
        if not definition:
            raise ValueError(f"Data message references unknown local type {local_msg_type}")

        values = {}
        for field_def in definition["fields"]:
            field_num, size, _base_type = field_def
            chunk = fit_bytes[pos : pos + size]
            pos += size
            values[field_num] = decode_field(chunk, definition["endian"], field_def)

        yield definition["global_msg_num"], values


def extract_fit_points(fit_gz_bytes):
    fit_bytes = gzip.decompress(fit_gz_bytes)
    points = []

    for global_msg_num, values in iter_fit_messages(fit_bytes):
        if global_msg_num != 20:  # record
            continue
        lat_raw = values.get(0)
        lng_raw = values.get(1)
        if lat_raw is None or lng_raw is None:
            continue
        if lat_raw == INVALID_SINT32 or lng_raw == INVALID_SINT32:
            continue
        points.append((lat_raw * SEMICIRCLE_TO_DEGREES, lng_raw * SEMICIRCLE_TO_DEGREES))

    return points


def extract_gpx_points(gpx_gz_bytes):
    gpx_bytes = gzip.decompress(gpx_gz_bytes)
    root = ElementTree.fromstring(gpx_bytes)
    points = []

    for element in root.iter():
        if not element.tag.endswith("trkpt"):
            continue
        lat = element.attrib.get("lat")
        lng = element.attrib.get("lon")
        if lat is None or lng is None:
            continue
        points.append((float(lat), float(lng)))

    return points


def extract_activity_points(filename, data):
    if filename.endswith(".fit.gz"):
        return extract_fit_points(data)
    if filename.endswith(".gpx.gz"):
        return extract_gpx_points(data)
    raise ValueError(f"Unsupported activity file type: {filename}")


def encode_signed(value):
    value = ~(value << 1) if value < 0 else value << 1
    output = []
    while value >= 0x20:
        output.append(chr((0x20 | (value & 0x1F)) + 63))
        value >>= 5
    output.append(chr(value + 63))
    return "".join(output)


def encode_polyline(points):
    result = []
    prev_lat = 0
    prev_lng = 0
    for lat, lng in points:
        lat_i = int(round(lat * 1e5))
        lng_i = int(round(lng * 1e5))
        result.append(encode_signed(lat_i - prev_lat))
        result.append(encode_signed(lng_i - prev_lng))
        prev_lat = lat_i
        prev_lng = lng_i
    return "".join(result)


def point_segment_distance_m(point, start, end):
    lat, lng = point
    lat1, lng1 = start
    lat2, lng2 = end
    mean_lat_rad = math.radians((lat + lat1 + lat2) / 3)
    meters_per_lat = 111_320.0
    meters_per_lng = 111_320.0 * math.cos(mean_lat_rad)

    px = lng * meters_per_lng
    py = lat * meters_per_lat
    x1 = lng1 * meters_per_lng
    y1 = lat1 * meters_per_lat
    x2 = lng2 * meters_per_lng
    y2 = lat2 * meters_per_lat

    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)

    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def simplify_points(points, tolerance_m):
    if len(points) <= 2 or tolerance_m <= 0:
        return points

    keep = [False] * len(points)
    keep[0] = True
    keep[-1] = True
    stack = [(0, len(points) - 1)]

    while stack:
        start, end = stack.pop()
        max_distance = -1.0
        index = None
        for i in range(start + 1, end):
            distance = point_segment_distance_m(points[i], points[start], points[end])
            if distance > max_distance:
                max_distance = distance
                index = i
        if index is not None and max_distance > tolerance_m:
            keep[index] = True
            stack.append((start, index))
            stack.append((index, end))

    return [point for point, should_keep in zip(points, keep) if should_keep]


def read_activities_csv(zip_file):
    data = zip_file.read("activities.csv").decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(data)))


def build_activity(row, points, existing_by_id, tolerance_m):
    activity_id = int(row["Activity ID"])
    existing = existing_by_id.get(activity_id, {})
    simplified = simplify_points(points, tolerance_m)
    summary_polyline = encode_polyline(simplified)

    sport_type = existing.get("sport_type") or SPORT_TYPE_MAP.get(row.get("Activity Type", ""), row.get("Activity Type", ""))

    return {
        "id": activity_id,
        "name": row.get("Activity Name", ""),
        "sport_type": sport_type,
        "distance": parse_float(row.get("Distance")),
        "moving_time": parse_int(row.get("Moving Time")),
        "elapsed_time": parse_int(row.get("Elapsed Time")),
        "total_elevation_gain": parse_float(row.get("Elevation Gain")),
        "start_date": parse_activity_date(row.get("Activity Date", "")),
        "start_latlng": [round(points[0][0], 6), round(points[0][1], 6)],
        "average_speed": parse_float(row.get("Average Speed")),
        "max_speed": parse_float(row.get("Max Speed")),
        "summary_polyline": summary_polyline,
    }


def main():
    args = parse_args()
    existing_by_id = {} if args.no_existing_merge else load_existing(args.existing_json)
    activities = []
    skipped_no_file = 0
    skipped_no_points = 0
    failed_fit = 0

    with zipfile.ZipFile(args.export_zip) as z:
        zip_names = set(z.namelist())
        rows = read_activities_csv(z)
        for index, row in enumerate(rows, start=1):
            filename = row.get("Filename", "")
            if not filename:
                skipped_no_file += 1
                continue
            if filename not in zip_names:
                skipped_no_file += 1
                continue

            try:
                points = extract_activity_points(filename, z.read(filename))
            except Exception as exc:
                failed_fit += 1
                print(
                    f"Warning: FIT parse failed for {row.get('Activity ID')} {filename}: {exc}",
                    file=sys.stderr,
                )
                continue

            if not points:
                skipped_no_points += 1
                continue

            activities.append(build_activity(row, points, existing_by_id, args.tolerance_m))

            if index % 200 == 0:
                print(f"Processed {index}/{len(rows)} rows, generated {len(activities)} activities")

    activities.sort(key=lambda item: item.get("start_date", ""), reverse=True)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(activities, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Generated: {args.output}")
    print(f"Activities with GPS: {len(activities)}")
    print(f"Skipped without file: {skipped_no_file}")
    print(f"Skipped without GPS points: {skipped_no_points}")
    print(f"FIT parse failures: {failed_fit}")


if __name__ == "__main__":
    main()
