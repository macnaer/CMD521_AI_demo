---
name: swapi-client
description: Fetch, query, and export data from the Star Wars API (SWAPI) at swapi.info. Use when working with Star Wars people, films, planets, species, vehicles, starships; when building SWAPI clients, exporting SWAPI data to JSON/CSV/database, or analyzing Star Wars dataset relationships.
license: MIT
compatibility: Requires Python 3.11+, httpx or requests. No auth needed.
metadata:
  author: netdevops-team
  version: "1.0"
  domain: api-client
allowed-tools: Bash(python:*) Bash(pip:*) Read Glob Grep Write
---

# SWAPI Client Skill

You are a Python developer working with the Star Wars API (SWAPI).
Base URL: `https://swapi.info/api`

## API Overview

| Endpoint | Count | Description |
|----------|-------|-------------|
| `/films` | 6 | Films |
| `/people` | 83 | Characters |
| `/planets` | 60 | Planets |
| `/species` | 37 | Species |
| `/vehicles` | 39 | Vehicles |
| `/starships` | 36 | Starships |

## Key Facts

- **No authentication** required.
- **No pagination** — all data returned in one response.
- **No filtering/sorting** — fetch all, then filter locally.
- **JSON responses** — `Content-Type: application/json`.
- **Cross-references** via URLs (e.g. `people.homeworld` → `/planets/1`).
- **Quirky data**: `"unknown"` as string, numbers as strings, some `null` values.

## Fetching Data

### All resources at once

```python
import httpx

BASE = "https://swapi.info/api"

def fetch_all(resource: str) -> list[dict]:
    """Fetch ALL items for a SWAPI resource."""
    resp = httpx.get(f"{BASE}/{resource}", timeout=30)
    resp.raise_for_status()
    return resp.json()

people = fetch_all("people")   # 83 items
films = fetch_all("films")     # 6 items
planets = fetch_all("planets") # 60 items
species = fetch_all("species") # 37 items
vehicles = fetch_all("vehicles") # 39 items
starships = fetch_all("starships") # 36 items
```

### Single item by ID

```python
def fetch_one(resource: str, item_id: int) -> dict:
    resp = httpx.get(f"{BASE}/{resource}/{item_id}", timeout=30)
    resp.raise_for_status()
    return resp.json()

luke = fetch_one("people", 1)
```

### Resolve URL references

```python
def resolve_url(url: str) -> dict:
    resp = httpx.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()

# Get Luke's homeworld
luke = fetch_one("people", 1)
homeworld = resolve_url(luke["homeworld"])  # Tatooine
```

### Batch resolve with async

```python
import asyncio
import httpx

async def resolve_urls(urls: list[str]) -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [client.get(u) for u in urls if u]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        return [r.json() for r in responses if not isinstance(r, Exception)]
```

## Data Processing

### Safe numeric parsing

```python
def safe_int(val) -> int | None:
    if val is None or val == "unknown" or val == "n/a":
        return None
    try:
        return int(val.replace(",", ""))
    except (ValueError, AttributeError):
        return None

def safe_float(val) -> float | None:
    if val is None or val == "unknown" or val == "n/a":
        return None
    try:
        return float(val.replace(",", ""))
    except (ValueError, AttributeError):
        return None
```

### Extract ID from URL

```python
import re

def url_to_id(url: str) -> int | None:
    match = re.search(r"/(\d+)/?$", url)
    return int(match.group(1)) if match else None

# url_to_id("https://swapi.info/api/people/1") → 1
```

## Exporting

### To JSON

```python
import json

def export_json(data: list[dict], filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
```

### To CSV

```python
import csv

def export_csv(data: list[dict], filename: str):
    if not data:
        return
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
```

### To MSSQL (uses mssql-database skill)

```python
import pymssql, os
from dotenv import load_dotenv

load_dotenv()

conn = pymssql.connect(
    server=os.environ["DB_IP"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    port=1433,
)
# Create table, insert data, etc.
```

## Common Queries

```python
# People sorted by height
sorted(people, key=lambda p: safe_int(p["height"]) or 0, reverse=True)

# Films by episode
sorted(films, key=lambda f: f["episode_id"])

# Characters in a specific film
film_urls = film["characters"]
film_characters = [resolve_url(u) for u in file_urls]

# Planets with population > 1 billion
[p for p in planets if (safe_int(p["population"]) or 0) > 1_000_000_000]

# Species sorted by average lifespan
sorted(species, key=lambda s: safe_int(s["average_lifespan"]) or 0, reverse=True)

# Starships by hyperdrive rating
sorted(starships, key=lambda s: safe_float(s["hyperdrive_rating"]) or 99)
```

## Response Style

- Use `httpx` (preferred) or `requests` — check which is installed.
- Always handle connection errors and HTTP errors.
- Use `timeout=30` for all requests.
- Print progress when fetching large datasets.
- Cache fetched data locally if re-processing.

See [references/DATA.md](references/DATA.md) for field schemas and relationships.
