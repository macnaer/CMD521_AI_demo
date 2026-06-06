#!/usr/bin/env python3
"""Generate statistics and analytics from SWAPI data.

Usage:
    python stats.py                      # Full stats
    python stats.py --resource people    # People stats only
    python stats.py --resource planets   # Planets stats only
"""
import argparse
import json
import sys
from collections import Counter

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)

BASE_URL = "https://swapi.info/api"


def fetch(resource: str) -> list[dict]:
    resp = httpx.get(f"{BASE_URL}/{resource}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def safe_int(val) -> int | None:
    if val is None or val in ("unknown", "n/a", "none", ""):
        return None
    try:
        return int(str(val).replace(",", ""))
    except (ValueError, AttributeError):
        return None


def safe_float(val) -> float | None:
    if val is None or val in ("unknown", "n/a", "none", ""):
        return None
    try:
        return float(str(val).replace(",", ""))
    except (ValueError, AttributeError):
        return None


def stats_people(data: list[dict]):
    print("\n=== PEOPLE STATS ===")
    print(f"Total: {len(data)}")

    genders = Counter(p["gender"] for p in data)
    print(f"By gender: {dict(genders)}")

    heights = [safe_int(p["height"]) for p in data]
    heights = [h for h in heights if h]
    if heights:
        print(f"Height: min={min(heights)}, max={max(heights)}, avg={sum(heights)/len(heights):.0f} cm")

    masses = [safe_int(p["mass"]) for p in data]
    masses = [m for m in masses if m]
    if masses:
        print(f"Mass: min={min(masses)}, max={max(masses)}, avg={sum(masses)/len(masses):.0f} kg")

    homeworlds = Counter(p["homeworld"].split("/")[-2] for p in data if p.get("homeworld"))
    print(f"Top homeworlds (by planet ID): {homeworlds.most_common(5)}")


def stats_films(data: list[dict]):
    print("\n=== FILMS STATS ===")
    print(f"Total: {len(data)}")
    for f in sorted(data, key=lambda x: x["episode_id"]):
        chars = len(f.get("characters", []))
        planets = len(f.get("planets", []))
        ships = len(f.get("starships", []))
        print(f"  Ep {f['episode_id']}: {f['title']} ({f['release_date']}) — {chars} chars, {planets} planets, {ships} ships")


def stats_planets(data: list[dict]):
    print("\n=== PLANETS STATS ===")
    print(f"Total: {len(data)}")

    climates = Counter(p["climate"] for p in data)
    print(f"By climate: {dict(climates.most_common(5))}")

    terrains = Counter()
    for p in data:
        for t in p["terrain"].split(","):
            terrains[t.strip()] += 1
    print(f"Top terrains: {dict(terrains.most_common(5))}")

    pops = [(p["name"], safe_int(p["population"])) for p in data]
    pops = [(n, p) for n, p in pops if p]
    if pops:
        pops.sort(key=lambda x: x[1], reverse=True)
        print(f"Most populated: {pops[0][0]} ({pops[0][1]:,})")
        print(f"Least populated: {pops[-1][0]} ({pops[-1][1]:,})")


def stats_species(data: list[dict]):
    print("\n=== SPECIES STATS ===")
    print(f"Total: {len(data)}")

    classifications = Counter(s["classification"] for s in data)
    print(f"By classification: {dict(classifications)}")

    lifespans = [(s["name"], safe_int(s["average_lifespan"])) for s in data]
    lifespans = [(n, l) for n, l in lifespans if l]
    if lifespans:
        lifespans.sort(key=lambda x: x[1], reverse=True)
        print(f"Longest-lived: {lifespans[0][0]} ({lifespans[0][1]} years)")
        print(f"Shortest-lived: {lifespans[-1][0]} ({lifespans[-1][1]} years)")


def stats_starships(data: list[dict]):
    print("\n=== STARSHIPS STATS ===")
    print(f"Total: {len(data)}")

    classes = Counter(s["starship_class"] for s in data)
    print(f"By class: {dict(classes.most_common(5))}")

    costs = [(s["name"], safe_int(s["cost_in_credits"])) for s in data]
    costs = [(n, c) for n, c in costs if c]
    if costs:
        costs.sort(key=lambda x: x[1], reverse=True)
        print(f"Most expensive: {costs[0][0]} ({costs[0][1]:,} credits)")
        print(f"Least expensive: {costs[-1][0]} ({costs[-1][1]:,} credits)")

    hyperdrives = [(s["name"], safe_float(s["hyperdrive_rating"])) for s in data]
    hyperdrives = [(n, h) for n, h in hyperdrives if h]
    if hyperdrives:
        hyperdrives.sort(key=lambda x: x[1])
        print(f"Fastest hyperdrive: {hyperdrives[0][0]} (rating {hyperdrives[0][1]})")


def main() -> int:
    parser = argparse.ArgumentParser(description="SWAPI statistics")
    parser.add_argument("--resource", choices=["people", "films", "planets", "species", "starships", "all"], default="all")
    args = parser.parse_args()

    resources = {
        "people": ("people", stats_people),
        "films": ("films", stats_films),
        "planets": ("planets", stats_planets),
        "species": ("species", stats_species),
        "starships": ("starships", stats_starships),
    }

    if args.resource == "all":
        for key, (res, func) in resources.items():
            data = fetch(res)
            func(data)
    else:
        res, func = resources[args.resource]
        data = fetch(res)
        func(data)

    return 0


if __name__ == "__main__":
    sys.exit(main())
