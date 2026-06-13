#!/usr/bin/env python3
"""Starwars DB Importer — import SWAPI data into MSSQL Starwars database.

Interactive menu-driven script with:
- Idempotent database & table creation
- MERGE/UPSERT for all 6 SWAPI resources (people, films, planets, species, vehicles, starships)
- Normalized schema with 9 junction tables for M:N relationships
- Show queries to inspect data from DB
- Statistics, backup, truncate, drop utilities
- Logging to logs/YYYY-MM-DD_starwars_importer.log

Usage:
    python src/starwars_importer.py
"""
from __future__ import annotations

import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import httpx
import pymssql
from dotenv import load_dotenv

load_dotenv()

DB_NAME = "Starwars"
DB_IP = os.environ["DB_IP"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_PORT = 1433
BASE_URL = "https://swapi.info/api"

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
BACKUP_DIR = ROOT / "backups"
LOG_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / f"{datetime.now():%Y-%m-%d}_starwars_importer.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger("starwars")


def get_connection(database: str | None = None) -> pymssql.Connection:
    params = {
        "server": DB_IP,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "port": DB_PORT,
        "login_timeout": 10,
    }
    if database:
        params["database"] = database
    return pymssql.connect(**params)


def database_exists(name: str) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT DB_ID(%s)", (name,))
        row = cur.fetchone()
        return bool(row and row[0] is not None)
    finally:
        conn.close()


def create_database(name: str) -> None:
    conn = get_connection()
    try:
        conn.autocommit(True)
        cur = conn.cursor()
        cur.execute(f"IF DB_ID(%s) IS NULL CREATE DATABASE [{name}]", (name,))
        log.info("Database [%s] ensured", name)
    finally:
        conn.close()


def create_schema() -> None:
    conn = get_connection(DB_NAME)
    try:
        conn.autocommit(True)
        cur = conn.cursor()
        for ddl in DDL_STATEMENTS:
            cur.execute(ddl)
        log.info("Schema ensured (all tables created if missing)")
    finally:
        conn.close()


def fetch_resource(resource: str) -> list[dict]:
    log.info("Fetching %s from SWAPI...", resource)
    resp = httpx.get(f"{BASE_URL}/{resource}", timeout=30)
    resp.raise_for_status()
    data = resp.json()
    log.info("Fetched %d %s", len(data), resource)
    return data


def url_to_id(url: str | None) -> int | None:
    if not url:
        return None
    m = re.search(r"/(\d+)/?$", url)
    return int(m.group(1)) if m else None


def upsert_rows(cur, table: str, id_col: str, all_cols: list[str], rows: list[tuple]) -> int:
    if not rows:
        return 0
    placeholders = ",".join(["%s"] * len(all_cols))
    col_list = ",".join(all_cols)
    src_cols = ",".join([f"source.{c}" for c in all_cols])
    updates = ",".join([f"{c}=source.{c}" for c in all_cols if c != id_col])
    sql = (
        f"MERGE INTO {table} AS target "
        f"USING (VALUES ({placeholders})) AS source ({col_list}) "
        f"ON target.{id_col} = source.{id_col} "
        f"WHEN MATCHED THEN UPDATE SET {updates} "
        f"WHEN NOT MATCHED THEN INSERT ({col_list}) VALUES ({src_cols});"
    )
    cur.executemany(sql, rows)
    return cur.rowcount


def replace_junction(cur, table: str, parent_col: str, child_col: str,
                     parent_id: int, child_urls: list[str]) -> int:
    cur.execute(f"DELETE FROM {table} WHERE {parent_col} = %s", (parent_id,))
    child_ids = [url_to_id(u) for u in child_urls if u]
    child_ids = [c for c in child_ids if c is not None]
    if not child_ids:
        return 0
    rows = [(parent_id, cid) for cid in child_ids]
    cur.executemany(
        f"INSERT INTO {table} ({parent_col}, {child_col}) VALUES (%s, %s)", rows
    )
    return len(rows)


def flatten_planet(item: dict) -> tuple:
    return (
        url_to_id(item["url"]),
        item["name"],
        item.get("rotation_period", ""),
        item.get("orbital_period", ""),
        item.get("diameter", ""),
        item.get("climate", ""),
        item.get("gravity", ""),
        item.get("terrain", ""),
        item.get("surface_water", ""),
        item.get("population", ""),
        item["url"],
        item.get("created", ""),
        item.get("edited", ""),
    )


PLANET_COLS = [
    "id", "name", "rotation_period", "orbital_period", "diameter", "climate",
    "gravity", "terrain", "surface_water", "population", "url", "created", "edited",
]


def flatten_film(item: dict) -> tuple:
    return (
        url_to_id(item["url"]),
        item["title"],
        item["episode_id"],
        item.get("opening_crawl", ""),
        item.get("director", ""),
        item.get("producer", ""),
        item.get("release_date", ""),
        item["url"],
        item.get("created", ""),
        item.get("edited", ""),
    )


FILM_COLS = [
    "id", "title", "episode_id", "opening_crawl", "director", "producer",
    "release_date", "url", "created", "edited",
]


def flatten_person(item: dict) -> tuple:
    return (
        url_to_id(item["url"]),
        item["name"],
        item.get("height", ""),
        item.get("mass", ""),
        item.get("hair_color", ""),
        item.get("skin_color", ""),
        item.get("eye_color", ""),
        item.get("birth_year", ""),
        item.get("gender", ""),
        url_to_id(item.get("homeworld")),
        item["url"],
        item.get("created", ""),
        item.get("edited", ""),
    )


PERSON_COLS = [
    "id", "name", "height", "mass", "hair_color", "skin_color", "eye_color",
    "birth_year", "gender", "homeworld_id", "url", "created", "edited",
]


def flatten_species(item: dict) -> tuple:
    return (
        url_to_id(item["url"]),
        item["name"],
        item.get("classification", ""),
        item.get("designation", ""),
        item.get("average_height", ""),
        item.get("skin_colors", ""),
        item.get("hair_colors", ""),
        item.get("eye_colors", ""),
        item.get("average_lifespan", ""),
        url_to_id(item.get("homeworld")),
        item.get("language", ""),
        item["url"],
        item.get("created", ""),
        item.get("edited", ""),
    )


SPECIES_COLS = [
    "id", "name", "classification", "designation", "average_height", "skin_colors",
    "hair_colors", "eye_colors", "average_lifespan", "homeworld_id", "language",
    "url", "created", "edited",
]


def flatten_vehicle(item: dict) -> tuple:
    return (
        url_to_id(item["url"]),
        item["name"],
        item.get("model", ""),
        item.get("manufacturer", ""),
        item.get("cost_in_credits", ""),
        item.get("length", ""),
        item.get("max_atmosphering_speed", ""),
        item.get("crew", ""),
        item.get("passengers", ""),
        item.get("cargo_capacity", ""),
        item.get("consumables", ""),
        item.get("vehicle_class", ""),
        item["url"],
        item.get("created", ""),
        item.get("edited", ""),
    )


VEHICLE_COLS = [
    "id", "name", "model", "manufacturer", "cost_in_credits", "length",
    "max_atmosphering_speed", "crew", "passengers", "cargo_capacity",
    "consumables", "vehicle_class", "url", "created", "edited",
]


def flatten_starship(item: dict) -> tuple:
    return (
        url_to_id(item["url"]),
        item["name"],
        item.get("model", ""),
        item.get("manufacturer", ""),
        item.get("cost_in_credits", ""),
        item.get("length", ""),
        item.get("max_atmosphering_speed", ""),
        item.get("crew", ""),
        item.get("passengers", ""),
        item.get("cargo_capacity", ""),
        item.get("consumables", ""),
        item.get("hyperdrive_rating", ""),
        item.get("MGLT", ""),
        item.get("starship_class", ""),
        item["url"],
        item.get("created", ""),
        item.get("edited", ""),
    )


STARSHIP_COLS = [
    "id", "name", "model", "manufacturer", "cost_in_credits", "length",
    "max_atmosphering_speed", "crew", "passengers", "cargo_capacity",
    "consumables", "hyperdrive_rating", "mglt", "starship_class", "url", "created", "edited",
]


DDL_STATEMENTS = [
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sw_planets' AND xtype='U')
    CREATE TABLE sw_planets (
        id INT PRIMARY KEY,
        name NVARCHAR(255) NOT NULL,
        rotation_period NVARCHAR(50),
        orbital_period NVARCHAR(50),
        diameter NVARCHAR(50),
        climate NVARCHAR(500),
        gravity NVARCHAR(100),
        terrain NVARCHAR(500),
        surface_water NVARCHAR(50),
        population NVARCHAR(50),
        url NVARCHAR(500),
        created NVARCHAR(50),
        edited NVARCHAR(50)
    )""",
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sw_films' AND xtype='U')
    CREATE TABLE sw_films (
        id INT PRIMARY KEY,
        title NVARCHAR(255) NOT NULL,
        episode_id INT,
        opening_crawl NVARCHAR(MAX),
        director NVARCHAR(255),
        producer NVARCHAR(500),
        release_date NVARCHAR(20),
        url NVARCHAR(500),
        created NVARCHAR(50),
        edited NVARCHAR(50)
    )""",
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sw_people' AND xtype='U')
    CREATE TABLE sw_people (
        id INT PRIMARY KEY,
        name NVARCHAR(255) NOT NULL,
        height NVARCHAR(50),
        mass NVARCHAR(50),
        hair_color NVARCHAR(255),
        skin_color NVARCHAR(255),
        eye_color NVARCHAR(255),
        birth_year NVARCHAR(50),
        gender NVARCHAR(50),
        homeworld_id INT NULL,
        url NVARCHAR(500),
        created NVARCHAR(50),
        edited NVARCHAR(50),
        CONSTRAINT FK_sw_people_homeworld FOREIGN KEY (homeworld_id) REFERENCES sw_planets(id)
    )""",
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sw_species' AND xtype='U')
    CREATE TABLE sw_species (
        id INT PRIMARY KEY,
        name NVARCHAR(255) NOT NULL,
        classification NVARCHAR(100),
        designation NVARCHAR(100),
        average_height NVARCHAR(50),
        skin_colors NVARCHAR(500),
        hair_colors NVARCHAR(500),
        eye_colors NVARCHAR(500),
        average_lifespan NVARCHAR(50),
        homeworld_id INT NULL,
        language NVARCHAR(255),
        url NVARCHAR(500),
        created NVARCHAR(50),
        edited NVARCHAR(50),
        CONSTRAINT FK_sw_species_homeworld FOREIGN KEY (homeworld_id) REFERENCES sw_planets(id)
    )""",
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sw_vehicles' AND xtype='U')
    CREATE TABLE sw_vehicles (
        id INT PRIMARY KEY,
        name NVARCHAR(255) NOT NULL,
        model NVARCHAR(255),
        manufacturer NVARCHAR(500),
        cost_in_credits NVARCHAR(50),
        length NVARCHAR(50),
        max_atmosphering_speed NVARCHAR(50),
        crew NVARCHAR(50),
        passengers NVARCHAR(50),
        cargo_capacity NVARCHAR(50),
        consumables NVARCHAR(100),
        vehicle_class NVARCHAR(255),
        url NVARCHAR(500),
        created NVARCHAR(50),
        edited NVARCHAR(50)
    )""",
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sw_starships' AND xtype='U')
    CREATE TABLE sw_starships (
        id INT PRIMARY KEY,
        name NVARCHAR(255) NOT NULL,
        model NVARCHAR(255),
        manufacturer NVARCHAR(500),
        cost_in_credits NVARCHAR(50),
        length NVARCHAR(50),
        max_atmosphering_speed NVARCHAR(50),
        crew NVARCHAR(50),
        passengers NVARCHAR(50),
        cargo_capacity NVARCHAR(50),
        consumables NVARCHAR(100),
        hyperdrive_rating NVARCHAR(50),
        mglt NVARCHAR(50),
        starship_class NVARCHAR(255),
        url NVARCHAR(500),
        created NVARCHAR(50),
        edited NVARCHAR(50)
    )""",
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sw_film_characters' AND xtype='U')
    CREATE TABLE sw_film_characters (
        film_id INT NOT NULL,
        person_id INT NOT NULL,
        PRIMARY KEY (film_id, person_id),
        CONSTRAINT FK_fc_film FOREIGN KEY (film_id) REFERENCES sw_films(id) ON DELETE CASCADE,
        CONSTRAINT FK_fc_person FOREIGN KEY (person_id) REFERENCES sw_people(id) ON DELETE CASCADE
    )""",
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sw_film_planets' AND xtype='U')
    CREATE TABLE sw_film_planets (
        film_id INT NOT NULL,
        planet_id INT NOT NULL,
        PRIMARY KEY (film_id, planet_id),
        CONSTRAINT FK_fp_film FOREIGN KEY (film_id) REFERENCES sw_films(id) ON DELETE CASCADE,
        CONSTRAINT FK_fp_planet FOREIGN KEY (planet_id) REFERENCES sw_planets(id) ON DELETE CASCADE
    )""",
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sw_film_starships' AND xtype='U')
    CREATE TABLE sw_film_starships (
        film_id INT NOT NULL,
        starship_id INT NOT NULL,
        PRIMARY KEY (film_id, starship_id),
        CONSTRAINT FK_fs_film FOREIGN KEY (film_id) REFERENCES sw_films(id) ON DELETE CASCADE,
        CONSTRAINT FK_fs_starship FOREIGN KEY (starship_id) REFERENCES sw_starships(id) ON DELETE CASCADE
    )""",
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sw_film_vehicles' AND xtype='U')
    CREATE TABLE sw_film_vehicles (
        film_id INT NOT NULL,
        vehicle_id INT NOT NULL,
        PRIMARY KEY (film_id, vehicle_id),
        CONSTRAINT FK_fv_film FOREIGN KEY (film_id) REFERENCES sw_films(id) ON DELETE CASCADE,
        CONSTRAINT FK_fv_vehicle FOREIGN KEY (vehicle_id) REFERENCES sw_vehicles(id) ON DELETE CASCADE
    )""",
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sw_film_species' AND xtype='U')
    CREATE TABLE sw_film_species (
        film_id INT NOT NULL,
        species_id INT NOT NULL,
        PRIMARY KEY (film_id, species_id),
        CONSTRAINT FK_fsp_film FOREIGN KEY (film_id) REFERENCES sw_films(id) ON DELETE CASCADE,
        CONSTRAINT FK_fsp_species FOREIGN KEY (species_id) REFERENCES sw_species(id) ON DELETE CASCADE
    )""",
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sw_person_species' AND xtype='U')
    CREATE TABLE sw_person_species (
        person_id INT NOT NULL,
        species_id INT NOT NULL,
        PRIMARY KEY (person_id, species_id),
        CONSTRAINT FK_ps_person FOREIGN KEY (person_id) REFERENCES sw_people(id) ON DELETE CASCADE,
        CONSTRAINT FK_ps_species FOREIGN KEY (species_id) REFERENCES sw_species(id) ON DELETE CASCADE
    )""",
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sw_person_vehicles' AND xtype='U')
    CREATE TABLE sw_person_vehicles (
        person_id INT NOT NULL,
        vehicle_id INT NOT NULL,
        PRIMARY KEY (person_id, vehicle_id),
        CONSTRAINT FK_pv_person FOREIGN KEY (person_id) REFERENCES sw_people(id) ON DELETE CASCADE,
        CONSTRAINT FK_pv_vehicle FOREIGN KEY (vehicle_id) REFERENCES sw_vehicles(id) ON DELETE CASCADE
    )""",
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sw_person_starships' AND xtype='U')
    CREATE TABLE sw_person_starships (
        person_id INT NOT NULL,
        starship_id INT NOT NULL,
        PRIMARY KEY (person_id, starship_id),
        CONSTRAINT FK_pst_person FOREIGN KEY (person_id) REFERENCES sw_people(id) ON DELETE CASCADE,
        CONSTRAINT FK_pst_starship FOREIGN KEY (starship_id) REFERENCES sw_starships(id) ON DELETE CASCADE
    )""",
    """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sw_planet_residents' AND xtype='U')
    CREATE TABLE sw_planet_residents (
        planet_id INT NOT NULL,
        person_id INT NOT NULL,
        PRIMARY KEY (planet_id, person_id),
        CONSTRAINT FK_pr_planet FOREIGN KEY (planet_id) REFERENCES sw_planets(id) ON DELETE CASCADE,
        CONSTRAINT FK_pr_person FOREIGN KEY (person_id) REFERENCES sw_people(id) ON DELETE CASCADE
    )""",
]


def import_planets(conn) -> int:
    data = fetch_resource("planets")
    rows = [flatten_planet(it) for it in data]
    cur = conn.cursor()
    n = upsert_rows(cur, "sw_planets", "id", PLANET_COLS, rows)
    conn.commit()
    log.info("Upserted %d planets", n)
    return n


def import_films(conn) -> int:
    data = fetch_resource("films")
    rows = [flatten_film(it) for it in data]
    cur = conn.cursor()
    n = upsert_rows(cur, "sw_films", "id", FILM_COLS, rows)
    conn.commit()
    log.info("Upserted %d films", n)
    return n


def import_people(conn) -> int:
    data = fetch_resource("people")
    rows = [flatten_person(it) for it in data]
    cur = conn.cursor()
    n = upsert_rows(cur, "sw_people", "id", PERSON_COLS, rows)
    conn.commit()
    log.info("Upserted %d people", n)
    return n


def import_species(conn) -> int:
    data = fetch_resource("species")
    rows = [flatten_species(it) for it in data]
    cur = conn.cursor()
    n = upsert_rows(cur, "sw_species", "id", SPECIES_COLS, rows)
    conn.commit()
    log.info("Upserted %d species", n)
    return n


def import_vehicles(conn) -> int:
    data = fetch_resource("vehicles")
    rows = [flatten_vehicle(it) for it in data]
    cur = conn.cursor()
    n = upsert_rows(cur, "sw_vehicles", "id", VEHICLE_COLS, rows)
    conn.commit()
    log.info("Upserted %d vehicles", n)
    return n


def import_starships(conn) -> int:
    data = fetch_resource("starships")
    rows = [flatten_starship(it) for it in data]
    cur = conn.cursor()
    n = upsert_rows(cur, "sw_starships", "id", STARSHIP_COLS, rows)
    conn.commit()
    log.info("Upserted %d starships", n)
    return n


def populate_planet_junctions(conn, data: list[dict]) -> int:
    cur = conn.cursor()
    total = 0
    for it in data:
        pid = url_to_id(it["url"])
        total += replace_junction(cur, "sw_planet_residents", "planet_id", "person_id",
                                  pid, it.get("residents", []))
    conn.commit()
    log.info("Planet residents: %d junction rows", total)
    return total


def populate_film_junctions(conn, data: list[dict]) -> int:
    cur = conn.cursor()
    total = 0
    for it in data:
        fid = url_to_id(it["url"])
        total += replace_junction(cur, "sw_film_characters", "film_id", "person_id",
                                  fid, it.get("characters", []))
        total += replace_junction(cur, "sw_film_planets", "film_id", "planet_id",
                                  fid, it.get("planets", []))
        total += replace_junction(cur, "sw_film_starships", "film_id", "starship_id",
                                  fid, it.get("starships", []))
        total += replace_junction(cur, "sw_film_vehicles", "film_id", "vehicle_id",
                                  fid, it.get("vehicles", []))
        total += replace_junction(cur, "sw_film_species", "film_id", "species_id",
                                  fid, it.get("species", []))
    conn.commit()
    log.info("Film junctions: %d total rows", total)
    return total


def populate_person_junctions(conn, data: list[dict]) -> int:
    cur = conn.cursor()
    total = 0
    for it in data:
        pid = url_to_id(it["url"])
        total += replace_junction(cur, "sw_person_species", "person_id", "species_id",
                                  pid, it.get("species", []))
        total += replace_junction(cur, "sw_person_vehicles", "person_id", "vehicle_id",
                                  pid, it.get("vehicles", []))
        total += replace_junction(cur, "sw_person_starships", "person_id", "starship_id",
                                  pid, it.get("starships", []))
    conn.commit()
    log.info("Person junctions: %d total rows", total)
    return total


IMPORT_HANDLERS = {
    "planets": import_planets,
    "films": import_films,
    "people": import_people,
    "species": import_species,
    "vehicles": import_vehicles,
    "starships": import_starships,
}

JUNCTION_HANDLERS = {
    "planets": populate_planet_junctions,
    "films": populate_film_junctions,
    "people": populate_person_junctions,
}


def import_all() -> None:
    conn = get_connection(DB_NAME)
    try:
        log.info("=== Phase 1: upsert main tables ===")
        main_data: dict[str, list[dict]] = {}
        for resource in ["planets", "films", "people", "species", "vehicles", "starships"]:
            log.info("--- %s ---", resource)
            main_data[resource] = fetch_resource(resource)
            rows_attr = {
                "planets": PLANET_COLS, "films": FILM_COLS, "people": PERSON_COLS,
                "species": SPECIES_COLS, "vehicles": VEHICLE_COLS, "starships": STARSHIP_COLS,
            }[resource]
            flatten = {
                "planets": flatten_planet, "films": flatten_film, "people": flatten_person,
                "species": flatten_species, "vehicles": flatten_vehicle, "starships": flatten_starship,
            }[resource]
            cur = conn.cursor()
            rows = [flatten(it) for it in main_data[resource]]
            n = upsert_rows(cur, f"sw_{resource}", "id", rows_attr, rows)
            conn.commit()
            log.info("Upserted %d %s", n, resource)

        log.info("=== Phase 2: populate junction tables ===")
        for resource in ["planets", "films", "people"]:
            JUNCTION_HANDLERS[resource](conn, main_data[resource])

        log.info("=== Import ALL complete ===")
    finally:
        conn.close()


def import_one(resource: str) -> None:
    conn = get_connection(DB_NAME)
    try:
        IMPORT_HANDLERS[resource](conn)
        if resource in JUNCTION_HANDLERS:
            try:
                data = fetch_resource(resource)
                JUNCTION_HANDLERS[resource](conn, data)
            except Exception as e:
                log.warning("Junction populate skipped for %s: %s", resource, e)
    finally:
        conn.close()


def print_rows(headers: list[str], rows: list[tuple], max_width: int = 50) -> None:
    if not rows:
        print("  (no rows)")
        return
    str_rows = []
    for row in rows:
        cells = []
        for v in row:
            s = "" if v is None else str(v)
            if len(s) > max_width:
                s = s[: max_width - 3] + "..."
            cells.append(s)
        str_rows.append(cells)
    widths = [len(h) for h in headers]
    for r in str_rows:
        for i, c in enumerate(r):
            if len(c) > widths[i]:
                widths[i] = len(c)
    sep = "-+-".join("-" * w for w in widths)
    print("  | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)))
    print("  " + sep)
    for r in str_rows:
        print("  | ".join(c.ljust(widths[i]) for i, c in enumerate(r)))


def fetch_rows(conn, sql: str, params: tuple = ()) -> tuple[list[str], list[tuple]]:
    cur = conn.cursor()
    cur.execute(sql, params)
    headers = [c[0] for c in cur.description]
    return headers, cur.fetchall()


def show_resource(resource: str, table: str, base_columns: list[str],
                  name_col: str = "name") -> None:
    if not database_exists(DB_NAME):
        print(f"  Database [{DB_NAME}] does not exist. Run option 1 first.")
        return
    conn = get_connection(DB_NAME)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = %s",
            (table,),
        )
        if not cur.fetchone()[0]:
            print(f"  Table {table} does not exist. Run option 1 first.")
            return
        limit_in = input(f"  Limit (default 25, max 1000): ").strip() or "25"
        try:
            limit = max(1, min(1000, int(limit_in)))
        except ValueError:
            limit = 25
        filter_in = input(f"  Filter {name_col} LIKE (default none): ").strip()
        cols_csv = ",".join(base_columns)
        sql = f"SELECT TOP {limit} {cols_csv} FROM {table}"
        params: tuple = ()
        if filter_in:
            sql += f" WHERE {name_col} LIKE %s"
            params = (f"%{filter_in}%",)
        sql += f" ORDER BY id"
        headers, rows = fetch_rows(conn, sql, params)
        print_rows(headers, rows)
        print(f"  Showing {len(rows)} row(s)")
    finally:
        conn.close()


def show_people() -> None:
    show_resource("people", "sw_people",
                  ["id", "name", "height", "mass", "gender", "homeworld_id"])


def show_films() -> None:
    show_resource("films", "sw_films",
                  ["id", "title", "episode_id", "director", "release_date"])


def show_planets() -> None:
    show_resource("planets", "sw_planets",
                  ["id", "name", "climate", "population", "diameter"])


def show_species() -> None:
    show_resource("species", "sw_species",
                  ["id", "name", "classification", "language", "homeworld_id"])


def show_vehicles() -> None:
    show_resource("vehicles", "sw_vehicles",
                  ["id", "name", "model", "manufacturer", "vehicle_class"])


def show_starships() -> None:
    show_resource("starships", "sw_starships",
                  ["id", "name", "model", "starship_class", "hyperdrive_rating"])


SHOW_HANDLERS = {
    "people": show_people,
    "films": show_films,
    "planets": show_planets,
    "species": show_species,
    "vehicles": show_vehicles,
    "starships": show_starships,
}


def show_statistics() -> None:
    if not database_exists(DB_NAME):
        print(f"  Database [{DB_NAME}] does not exist. Run option 1 first.")
        return
    conn = get_connection(DB_NAME)
    try:
        cur = conn.cursor()
        tables = [
            "sw_planets", "sw_films", "sw_people", "sw_species",
            "sw_vehicles", "sw_starships",
            "sw_film_characters", "sw_film_planets", "sw_film_starships",
            "sw_film_vehicles", "sw_film_species",
            "sw_person_species", "sw_person_vehicles", "sw_person_starships",
            "sw_planet_residents",
        ]
        print("  Table                          Rows")
        print("  ------------------------------  -----")
        for t in tables:
            cur.execute(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = %s",
                (t,),
            )
            if not cur.fetchone()[0]:
                print(f"  {t:<30}  (missing)")
                continue
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            n = cur.fetchone()[0]
            print(f"  {t:<30}  {n}")
    finally:
        conn.close()


def backup_database() -> None:
    if not database_exists(DB_NAME):
        print(f"  Database [{DB_NAME}] does not exist.")
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bk_path = BACKUP_DIR / f"Starwars_{ts}.sql"
    conn = get_connection(DB_NAME)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME LIKE 'sw_%'"
        )
        existing = {r[0] for r in cur.fetchall()}
        order = [
            "sw_planets", "sw_films", "sw_people", "sw_species",
            "sw_vehicles", "sw_starships",
            "sw_film_characters", "sw_film_planets", "sw_film_species",
            "sw_film_starships", "sw_film_vehicles",
            "sw_person_species", "sw_person_starships", "sw_person_vehicles",
            "sw_planet_residents",
        ]
        tables = [t for t in order if t in existing]
        log.info("Starting SQL dump of %d tables to %s", len(tables), bk_path)
        with open(bk_path, "w", encoding="utf-8") as f:
            f.write(f"-- Starwars database backup\n")
            f.write(f"-- Generated: {datetime.now().isoformat()}\n")
            f.write(f"-- Database: {DB_NAME}\n")
            f.write(f"-- Server: {DB_IP}:{DB_PORT}\n")
            f.write(f"-- Restore order: parents first, junctions last\n\n")
            f.write(f"USE [{DB_NAME}];\n\n")
            f.write("SET QUOTED_IDENTIFIER ON;\n")
            f.write("SET NOCOUNT ON;\n\n")
            f.write("ALTER TABLE sw_film_characters NOCHECK CONSTRAINT ALL;\n")
            f.write("ALTER TABLE sw_film_planets NOCHECK CONSTRAINT ALL;\n")
            f.write("ALTER TABLE sw_film_species NOCHECK CONSTRAINT ALL;\n")
            f.write("ALTER TABLE sw_film_starships NOCHECK CONSTRAINT ALL;\n")
            f.write("ALTER TABLE sw_film_vehicles NOCHECK CONSTRAINT ALL;\n")
            f.write("ALTER TABLE sw_person_species NOCHECK CONSTRAINT ALL;\n")
            f.write("ALTER TABLE sw_person_starships NOCHECK CONSTRAINT ALL;\n")
            f.write("ALTER TABLE sw_person_vehicles NOCHECK CONSTRAINT ALL;\n")
            f.write("ALTER TABLE sw_planet_residents NOCHECK CONSTRAINT ALL;\n\n")
            total_rows = 0
            for t in tables:
                cur.execute(f"SELECT * FROM {t}")
                if not cur.description:
                    f.write(f"-- {t}: empty\n\n")
                    continue
                cols = [c[0] for c in cur.description]
                f.write(f"PRINT 'Loading {t}...';\n")
                f.write(f"IF OBJECT_ID('{t}','U') IS NOT NULL DELETE FROM {t};\n")
                rows = cur.fetchall()
                if not rows:
                    f.write(f"-- {t}: 0 rows\n\n")
                    continue
                batch = []
                for row in rows:
                    vals = []
                    for v in row:
                        if v is None:
                            vals.append("NULL")
                        elif isinstance(v, (int, float)):
                            vals.append(str(v))
                        elif isinstance(v, bytes):
                            vals.append(f"0x{v.hex()}")
                        else:
                            s = str(v).replace("'", "''")
                            vals.append(f"N'{s}'")
                    batch.append(f"({','.join(vals)})")
                    if len(batch) >= 500:
                        f.write(f"INSERT INTO {t} ({','.join(cols)}) VALUES\n")
                        f.write(",\n".join(batch) + ";\n")
                        batch = []
                if batch:
                    f.write(f"INSERT INTO {t} ({','.join(cols)}) VALUES\n")
                    f.write(",\n".join(batch) + ";\n")
                f.write(f"-- {t}: {len(rows)} rows\n\n")
                total_rows += len(rows)
            f.write("ALTER TABLE sw_film_characters WITH CHECK CHECK CONSTRAINT ALL;\n")
            f.write("ALTER TABLE sw_film_planets WITH CHECK CHECK CONSTRAINT ALL;\n")
            f.write("ALTER TABLE sw_film_species WITH CHECK CHECK CONSTRAINT ALL;\n")
            f.write("ALTER TABLE sw_film_starships WITH CHECK CHECK CONSTRAINT ALL;\n")
            f.write("ALTER TABLE sw_film_vehicles WITH CHECK CHECK CONSTRAINT ALL;\n")
            f.write("ALTER TABLE sw_person_species WITH CHECK CHECK CONSTRAINT ALL;\n")
            f.write("ALTER TABLE sw_person_starships WITH CHECK CHECK CONSTRAINT ALL;\n")
            f.write("ALTER TABLE sw_person_vehicles WITH CHECK CHECK CONSTRAINT ALL;\n")
            f.write("ALTER TABLE sw_planet_residents WITH CHECK CHECK CONSTRAINT ALL;\n")
            f.write(f"\nPRINT 'Restore complete: {total_rows} rows in {len(tables)} tables';\n")
        size_kb = bk_path.stat().st_size / 1024
        log.info("Backup written: %s (%.1f KB, %d tables, %d rows)",
                 bk_path, size_kb, len(tables), total_rows)
        print(f"  Backup file: {bk_path} ({size_kb:.1f} KB, {total_rows} rows)")
    except Exception as e:
        log.error("Backup failed: %s", e)
        print(f"  Backup failed: {e}")
    finally:
        conn.close()


def truncate_all() -> None:
    if not database_exists(DB_NAME):
        print(f"  Database [{DB_NAME}] does not exist.")
        return
    if input("  Type 'yes' to confirm TRUNCATE all tables: ").strip().lower() != "yes":
        print("  Cancelled.")
        return
    conn = get_connection(DB_NAME)
    try:
        conn.autocommit(True)
        cur = conn.cursor()
        tables = [
            "sw_film_characters", "sw_film_planets", "sw_film_starships",
            "sw_film_vehicles", "sw_film_species",
            "sw_person_species", "sw_person_vehicles", "sw_person_starships",
            "sw_planet_residents",
            "sw_people", "sw_species", "sw_vehicles", "sw_starships",
            "sw_films", "sw_planets",
        ]
        for t in tables:
            cur.execute(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = %s",
                (t,),
            )
            if cur.fetchone()[0]:
                cur.execute(f"DELETE FROM {t}")
                log.info("Cleared %s", t)
    finally:
        conn.close()


def drop_database() -> None:
    if not database_exists(DB_NAME):
        print(f"  Database [{DB_NAME}] does not exist.")
        return
    if input(f"  Type 'DROP' to confirm dropping database [{DB_NAME}]: ").strip() != "DROP":
        print("  Cancelled.")
        return
    conn = get_connection()
    try:
        conn.autocommit(True)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM sys.databases WHERE name = %s", (DB_NAME,)
        )
        if cur.fetchone()[0]:
            cur.execute(
                f"ALTER DATABASE [{DB_NAME}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE"
            )
            cur.execute(f"DROP DATABASE [{DB_NAME}]")
            log.info("Database [%s] dropped", DB_NAME)
    finally:
        conn.close()


def print_menu() -> None:
    print()
    print("=" * 50)
    print("         STARWARS DB IMPORTER")
    print("=" * 50)
    print("  --- Setup ---")
    print("  1.  Create database & tables")
    print("  --- Import ---")
    print("  2.  Import: people")
    print("  3.  Import: films")
    print("  4.  Import: planets")
    print("  5.  Import: species")
    print("  6.  Import: vehicles")
    print("  7.  Import: starships")
    print("  8.  Import: ALL (in correct order)")
    print("  --- Show from DB ---")
    print("  9.  Show: people")
    print(" 10.  Show: films")
    print(" 11.  Show: planets")
    print(" 12.  Show: species")
    print(" 13.  Show: vehicles")
    print(" 14.  Show: starships")
    print("  --- Utilities ---")
    print(" 15.  Show statistics (row counts)")
    print(" 16.  Backup database")
    print(" 17.  Truncate all tables")
    print(" 18.  Drop database")
    print("  0.  Exit")
    print("=" * 50)


def ensure_ready_for_import() -> bool:
    if not database_exists(DB_NAME):
        print(f"  Database [{DB_NAME}] does not exist. Run option 1 first.")
        return False
    return True


def run_auto() -> int:
    log.info("=== AUTO MODE: create DB + import all ===")
    print(f"Connected to MSSQL {DB_IP}:{DB_PORT} as {DB_USER}")
    print(f"Log file: {LOG_FILE}")
    try:
        create_database(DB_NAME)
        create_schema()
        print(f"  Database [{DB_NAME}] and tables are ready.")
        import_all()
        log.info("=== AUTO MODE: all done ===")
        print("  All imports complete.")
        return 0
    except Exception as e:
        log.error("AUTO MODE failed: %s", e)
        print(f"  Error: {e}")
        return 1


def main() -> int:
    if "--auto" in sys.argv:
        return run_auto()

    print(f"Connected to MSSQL {DB_IP}:{DB_PORT} as {DB_USER}")
    print(f"Log file: {LOG_FILE}")
    while True:
        try:
            print_menu()
            choice = input("Choice> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return 0

        if choice == "0":
            print("Bye.")
            return 0
        elif choice == "1":
            create_database(DB_NAME)
            create_schema()
            print(f"  Database [{DB_NAME}] and tables are ready.")
        elif choice == "2":
            if ensure_ready_for_import():
                import_one("people")
        elif choice == "3":
            if ensure_ready_for_import():
                import_one("films")
        elif choice == "4":
            if ensure_ready_for_import():
                import_one("planets")
        elif choice == "5":
            if ensure_ready_for_import():
                import_one("species")
        elif choice == "6":
            if ensure_ready_for_import():
                import_one("vehicles")
        elif choice == "7":
            if ensure_ready_for_import():
                import_one("starships")
        elif choice == "8":
            if ensure_ready_for_import():
                import_all()
        elif choice == "9":
            show_people()
        elif choice == "10":
            show_films()
        elif choice == "11":
            show_planets()
        elif choice == "12":
            show_species()
        elif choice == "13":
            show_vehicles()
        elif choice == "14":
            show_starships()
        elif choice == "15":
            show_statistics()
        elif choice == "16":
            backup_database()
        elif choice == "17":
            truncate_all()
        elif choice == "18":
            drop_database()
        else:
            print("  Invalid choice.")


if __name__ == "__main__":
    sys.exit(main())
