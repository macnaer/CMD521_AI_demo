#!/usr/bin/env python3
"""Fetch ALL SWAPI data and export to JSON files.

Usage:
    python fetch_all.py                    # Fetch everything
    python fetch_all.py --resource people  # Fetch one resource
    python fetch_all.py --output ./data    # Custom output dir
"""
import argparse
import json
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)

BASE_URL = "https://swapi.info/api"
RESOURCES = ["people", "films", "planets", "species", "vehicles", "starships"]


def fetch_resource(resource: str) -> list[dict]:
    print(f"Fetching {resource}...", end=" ", flush=True)
    resp = httpx.get(f"{BASE_URL}/{resource}", timeout=30)
    resp.raise_for_status()
    data = resp.json()
    print(f"{len(data)} items")
    return data


def export(data: list[dict], output_dir: Path, resource: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{resource}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {filepath}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch SWAPI data")
    parser.add_argument("--resource", choices=RESOURCES, help="Single resource to fetch")
    parser.add_argument("--output", default="swapi_data", help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output)
    resources = [args.resource] if args.resource else RESOURCES

    total = 0
    for res in resources:
        data = fetch_resource(res)
        export(data, output_dir, res)
        total += len(data)

    print(f"\nDone: {total} total items exported to {output_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
