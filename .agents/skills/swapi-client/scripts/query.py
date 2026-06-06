#!/usr/bin/env python3
"""Query SWAPI data with filters and sorting.

Usage:
    python query.py --resource people --sort height --limit 10
    python query.py --resource planets --filter population>1000000000
    python query.py --resource species --sort average_lifespan --desc
    python query.py --resource starships --filter hyperdrive_rating<2
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)

BASE_URL = "https://swapi.info/api"


def fetch_resource(resource: str) -> list[dict]:
    resp = httpx.get(f"{BASE_URL}/{resource}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def safe_num(val) -> float | None:
    if val is None or val in ("unknown", "n/a", "none", ""):
        return None
    try:
        return float(str(val).replace(",", "").replace(" km", ""))
    except (ValueError, AttributeError):
        return None


def parse_filter(filter_str: str) -> tuple[str, str, float]:
    match = re.match(r"(\w+)([><=]+)(.+)", filter_str)
    if not match:
        raise ValueError(f"Invalid filter: {filter_str}")
    field, op, val = match.groups()
    return field, op, float(val)


def apply_filter(data: list[dict], field: str, op: str, threshold: float) -> list[dict]:
    result = []
    for item in data:
        val = safe_num(item.get(field))
        if val is None:
            continue
        if op == ">" and val > threshold:
            result.append(item)
        elif op == "<" and val < threshold:
            result.append(item)
        elif op == ">=" and val >= threshold:
            result.append(item)
        elif op == "<=" and val <= threshold:
            result.append(item)
        elif op == "==" and val == threshold:
            result.append(item)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Query SWAPI data")
    parser.add_argument("--resource", required=True, help="Resource to query")
    parser.add_argument("--sort", help="Field to sort by")
    parser.add_argument("--desc", action="store_true", help="Sort descending")
    parser.add_argument("--filter", help="Filter e.g. population>1000000000")
    parser.add_argument("--limit", type=int, help="Limit results")
    parser.add_argument("--fields", help="Comma-separated fields to show")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    data = fetch_resource(args.resource)
    print(f"Fetched {len(data)} {args.resource}")

    if args.filter:
        field, op, val = parse_filter(args.filter)
        data = apply_filter(data, field, op, val)
        print(f"After filter {args.filter}: {len(data)} items")

    if args.sort:
        data = sorted(data, key=lambda x: safe_num(x.get(args.sort)) or 0, reverse=args.desc)

    if args.limit:
        data = data[:args.limit]

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        fields = args.fields.split(",") if args.fields else list(data[0].keys()) if data else []
        if not fields:
            print("No data")
            return 0

        header = "\t".join(fields)
        print(f"\n{header}")
        print("-" * len(header))
        for item in data:
            vals = [str(item.get(f, "")) for f in fields]
            print("\t".join(vals))

    return 0


if __name__ == "__main__":
    sys.exit(main())
