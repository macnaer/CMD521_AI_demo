#!/usr/bin/env python3
"""Export SWAPI data to MSSQL database.

Usage:
    python export_to_db.py --database SuperCompany --resource people
    python export_to_db.py --database SuperCompany --resource all
    python export_to_db.py --database SuperCompany --resource people --dry-run
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)

try:
    import pymssql
except ImportError:
    print("Install pymssql: pip install pymssql")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_URL = "https://swapi.info/api"
RESOURCES = ["people", "films", "planets", "species", "vehicles", "starships"]


def fetch_resource(resource: str) -> list[dict]:
    resp = httpx.get(f"{BASE_URL}/{resource}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def url_to_id(url: str) -> int | None:
    if not url:
        return None
    match = re.search(r"/(\d+)/?$", url)
    return int(match.group(1)) if match else None


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


CREATE_TABLES = {
    "people": """
        CREATE TABLE swapi_people (
            id INT PRIMARY KEY,
            name VARCHAR(255),
            height INT,
            mass INT,
            hair_color VARCHAR(255),
            skin_color VARCHAR(255),
            eye_color VARCHAR(255),
            birth_year VARCHAR(50),
            gender VARCHAR(50),
            homeworld_id INT,
            species_count INT,
            films_count INT,
            vehicles_count INT,
            starships_count INT
        )
    """,
    "films": """
        CREATE TABLE swapi_films (
            id INT PRIMARY KEY,
            title VARCHAR(255),
            episode_id INT,
            director VARCHAR(255),
            producer VARCHAR(500),
            release_date VARCHAR(20),
            characters_count INT,
            planets_count INT,
            starships_count INT,
            vehicles_count INT,
            species_count INT
        )
    """,
    "planets": """
        CREATE TABLE swapi_planets (
            id INT PRIMARY KEY,
            name VARCHAR(255),
            rotation_period INT,
            orbital_period INT,
            diameter INT,
            climate VARCHAR(255),
            gravity VARCHAR(100),
            terrain VARCHAR(500),
            surface_water INT,
            population BIGINT,
            residents_count INT,
            films_count INT
        )
    """,
    "species": """
        CREATE TABLE swapi_species (
            id INT PRIMARY KEY,
            name VARCHAR(255),
            classification VARCHAR(100),
            designation VARCHAR(100),
            average_height INT,
            skin_colors VARCHAR(500),
            hair_colors VARCHAR(500),
            eye_colors VARCHAR(500),
            average_lifespan INT,
            homeworld_id INT,
            language VARCHAR(100),
            people_count INT,
            films_count INT
        )
    """,
    "vehicles": """
        CREATE TABLE swapi_vehicles (
            id INT PRIMARY KEY,
            name VARCHAR(255),
            model VARCHAR(255),
            manufacturer VARCHAR(500),
            cost_in_credits BIGINT,
            length DECIMAL(10,2),
            max_atmosphering_speed INT,
            crew INT,
            passengers INT,
            cargo_capacity BIGINT,
            consumables VARCHAR(100),
            vehicle_class VARCHAR(100),
            pilots_count INT,
            films_count INT
        )
    """,
    "starships": """
        CREATE TABLE swapi_starships (
            id INT PRIMARY KEY,
            name VARCHAR(255),
            model VARCHAR(255),
            manufacturer VARCHAR(500),
            cost_in_credits BIGINT,
            length DECIMAL(10,2),
            max_atmosphering_speed INT,
            crew INT,
            passengers INT,
            cargo_capacity BIGINT,
            consumables VARCHAR(100),
            hyperdrive_rating DECIMAL(4,1),
            mglt INT,
            starship_class VARCHAR(100),
            pilots_count INT,
            films_count INT
        )
    """,
}


def flatten_person(item: dict) -> tuple:
    return (
        url_to_id(item["url"]),
        item["name"],
        safe_int(item["height"]),
        safe_int(item["mass"]),
        item["hair_color"],
        item["skin_color"],
        item["eye_color"],
        item["birth_year"],
        item["gender"],
        url_to_id(item.get("homeworld")),
        len(item.get("species", [])),
        len(item.get("films", [])),
        len(item.get("vehicles", [])),
        len(item.get("starships", [])),
    )


def flatten_film(item: dict) -> tuple:
    return (
        url_to_id(item["url"]),
        item["title"],
        item["episode_id"],
        item["director"],
        item["producer"],
        item["release_date"],
        len(item.get("characters", [])),
        len(item.get("planets", [])),
        len(item.get("starships", [])),
        len(item.get("vehicles", [])),
        len(item.get("species", [])),
    )


def flatten_planet(item: dict) -> tuple:
    return (
        url_to_id(item["url"]),
        item["name"],
        safe_int(item["rotation_period"]),
        safe_int(item["orbital_period"]),
        safe_int(item["diameter"]),
        item["climate"],
        item["gravity"],
        item["terrain"],
        safe_int(item["surface_water"]),
        safe_int(item["population"]),
        len(item.get("residents", [])),
        len(item.get("films", [])),
    )


def flatten_species(item: dict) -> tuple:
    return (
        url_to_id(item["url"]),
        item["name"],
        item["classification"],
        item["designation"],
        safe_int(item["average_height"]),
        item["skin_colors"],
        item["hair_colors"],
        item["eye_colors"],
        safe_int(item["average_lifespan"]),
        url_to_id(item.get("homeworld")),
        item["language"],
        len(item.get("people", [])),
        len(item.get("films", [])),
    )


def flatten_vehicle(item: dict) -> tuple:
    return (
        url_to_id(item["url"]),
        item["name"],
        item["model"],
        item["manufacturer"],
        safe_int(item["cost_in_credits"]),
        safe_float(item["length"]),
        safe_int(item["max_atmosphering_speed"]),
        safe_int(item["crew"]),
        safe_int(item["passengers"]),
        safe_int(item["cargo_capacity"]),
        item["consumables"],
        item["vehicle_class"],
        len(item.get("pilots", [])),
        len(item.get("films", [])),
    )


def flatten_starship(item: dict) -> tuple:
    return (
        url_to_id(item["url"]),
        item["name"],
        item["model"],
        item["manufacturer"],
        safe_int(item["cost_in_credits"]),
        safe_float(item["length"]),
        safe_int(item["max_atmosphering_speed"]),
        safe_int(item["crew"]),
        safe_int(item["passengers"]),
        safe_int(item["cargo_capacity"]),
        item["consumables"],
        safe_float(item["hyperdrive_rating"]),
        safe_int(item.get("MGLT")),
        item["starship_class"],
        len(item.get("pilots", [])),
        len(item.get("films", [])),
    )


FLATTENERS = {
    "people": flatten_person,
    "films": flatten_film,
    "planets": flatten_planet,
    "species": flatten_species,
    "vehicles": flatten_vehicle,
    "starships": flatten_starship,
}

INSERT_QUERIES = {
    "people": "INSERT INTO swapi_people VALUES (%d,%s,%d,%d,%s,%s,%s,%s,%s,%d,%d,%d,%d,%d)",
    "films": "INSERT INTO swapi_films VALUES (%d,%s,%d,%s,%s,%s,%d,%d,%d,%d,%d)",
    "planets": "INSERT INTO swapi_planets VALUES (%d,%s,%d,%d,%d,%s,%s,%s,%d,%d,%d,%d)",
    "species": "INSERT INTO swapi_species VALUES (%d,%s,%s,%s,%d,%s,%s,%s,%d,%d,%s,%d,%d)",
    "vehicles": "INSERT INTO swapi_vehicles VALUES (%d,%s,%s,%s,%d,%d,%d,%d,%d,%d,%s,%s,%d,%d)",
    "starships": "INSERT INTO swapi_starships VALUES (%d,%s,%s,%s,%d,%d,%d,%d,%d,%d,%s,%d,%d,%s,%d,%d)",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Export SWAPI to MSSQL")
    parser.add_argument("--database", required=True, help="Target database")
    parser.add_argument("--resource", choices=RESOURCES + ["all"], default="all")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    resources = RESOURCES if args.resource == "all" else [args.resource]

    conn = pymssql.connect(
        server=os.environ["DB_IP"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=args.database,
        port=1433,
        login_timeout=10,
    )
    conn.autocommit = True
    cur = conn.cursor()

    for res in resources:
        print(f"\n=== {res} ===")

        # Drop and create table
        cur.execute(f"IF OBJECT_ID('swapi_{res}', 'U') IS NOT NULL DROP TABLE swapi_{res}")
        cur.execute(CREATE_TABLES[res])
        print(f"  Table swapi_{res} created")

        if args.dry_run:
            data = fetch_resource(res)
            print(f"  [DRY-RUN] Would insert {len(data)} rows")
            continue

        # Fetch and insert
        data = fetch_resource(res)
        rows = [FLATTENERS[res](item) for item in data]
        cur.executemany(INSERT_QUERIES[res], rows)
        print(f"  Inserted {len(rows)} rows")

    conn.close()
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
