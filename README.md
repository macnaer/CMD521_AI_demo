# CMD521 AI Demo — NetDevOps + Database Automation

A demo project showcasing AI-assisted network automation and MSSQL database
engineering, with a built-in Star Wars API (SWAPI) → MSSQL data pipeline
as a working example.

## What's in the box

| Area | What you get |
|------|--------------|
| **Agent Skills** | 3 reusable skills in `.agents/skills/` (agentskills.io format) |
| **MSSQL integration** | `Starwars` database with 15 normalized tables (807 rows) |
| **SWAPI client** | Interactive importer with menu, backup, statistics, show |
| **NetDevOps ready** | Conventions for multi-vendor automation, dry-run, rollback |
| **Test data** | `SuperCompany` DB with 1000 generated users |

## Tech stack

- **Python 3.11+**
- **MSSQL** via `pymssql` + `python-dotenv`
- **HTTP** via `httpx` (sync + async)
- **Data** via `pydantic` v2
- **Config** via `.env` (gitignored) + YAML/JSON

## Project structure

```
CMD521_AI_demo/
├── .agents/skills/                # Agent Skills (agentskills.io)
│   ├── netdevops-automation/       # Network device automation
│   ├── mssql-database/             # MSSQL queries, tables, backups
│   └── swapi-client/               # SWAPI fetcher, query, stats, export
├── src/
│   └── starwars_importer.py        # Interactive SWAPI → Starwars DB importer
├── backups/                        # SQL backups (gitignored)
├── logs/                           # Runtime logs (gitignored)
├── .env                            # DB credentials (gitignored)
├── .env.example                    # Example env vars
├── .gitignore
├── requirements.txt                # Python dependencies
├── AGENTS.md                       # Agent conventions and rules
├── system_prompt.md                # AI assistant configuration
└── README.md                       # This file
```

## Quick start

### 1. Clone and configure

```bash
# Copy env template and fill in real credentials
cp .env.example .env
# Edit .env:
#   DB_IP="10.20.42.103"
#   DB_USER="sa"
#   DB_PASSWORD="Qwerty-1"
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Starwars importer

```bash
python src/starwars_importer.py
```

Interactive menu — 18 options:

```
--- Setup ---                --- Show from DB ---      --- Utilities ---
 1. Create DB & tables        9. Show: people          15. Statistics
--- Import ---              10. Show: films           16. Backup database
 2. Import: people          11. Show: planets         17. Truncate all
 3. Import: films           12. Show: species         18. Drop database
 4. Import: planets         13. Show: vehicles         0. Exit
 5. Import: species         14. Show: starships
 6. Import: vehicles
 7. Import: starships
 8. Import: ALL
```

### 4. Use the skills

```bash
# Fetch all SWAPI data to JSON
python .agents/skills/swapi-client/scripts/fetch_all.py

# Show statistics for a resource
python .agents/skills/swapi-client/scripts/stats.py --resource films

# Query and filter
python .agents/skills/swapi-client/scripts/query.py --resource people --sort height --limit 10

# MSSQL operations
python .agents/skills/mssql-database/scripts/list_tables.py --database Starwars --info
python .agents/skills/mssql-database/scripts/query.py --database Starwars --sql "SELECT * FROM sw_people"
```

## Starwars database schema

Normalized schema, 15 tables total.

**Main tables (6):**

| Table | Rows | Description |
|-------|------|-------------|
| `sw_planets` | 60 | All SWAPI planets with climate, population, terrain |
| `sw_films` | 6 | All 6 Star Wars films |
| `sw_people` | 82 | All characters with FK to homeworld |
| `sw_species` | 37 | Species with FK to homeworld |
| `sw_vehicles` | 39 | Vehicles (speeders, walkers, etc.) |
| `sw_starships` | 36 | Starships (X-wing, Falcon, Death Star) |

**Junction tables (9) — M:N relationships:**

| Table | Purpose |
|-------|---------|
| `sw_film_characters` | Which characters appear in each film |
| `sw_film_planets` | Planets in each film |
| `sw_film_starships` | Starships in each film |
| `sw_film_vehicles` | Vehicles in each film |
| `sw_film_species` | Species in each film |
| `sw_person_species` | Species per character |
| `sw_person_vehicles` | Vehicles per pilot |
| `sw_person_starships` | Starships per pilot |
| `sw_planet_residents` | Characters living on each planet |

### Example queries

```sql
-- Top 10 tallest characters with their homeworld
SELECT TOP 10 p.name, p.height, pl.name AS homeworld
FROM sw_people p
LEFT JOIN sw_planets pl ON p.homeworld_id = pl.id
ORDER BY TRY_CAST(p.height AS INT) DESC;

-- Pilots of the Millennium Falcon
SELECT p.name FROM sw_people p
JOIN sw_person_starships ps ON p.id = ps.person_id
JOIN sw_starships s ON s.id = ps.starship_id
WHERE s.name = 'Millennium Falcon';

-- Planets with most residents
SELECT pl.name, COUNT(*) AS residents
FROM sw_planet_residents pr
JOIN sw_planets pl ON pl.id = pr.planet_id
GROUP BY pl.name
ORDER BY residents DESC;
```

## How import works

The importer uses a two-phase approach to satisfy FK constraints:

```
Phase 1: Upsert main tables (parents first)
  planets → films → people → species → vehicles → starships

Phase 2: Populate junction tables (children)
  planet_residents → film_characters → film_planets → ...
```

Each row is `MERGE INTO ... USING (VALUES ...) WHEN MATCHED UPDATE WHEN NOT MATCHED INSERT` — fully **idempotent**. Re-running the script updates existing rows and adds new ones, never creates duplicates.

## Backup / restore

`Menu → 16. Backup database` writes a self-contained SQL dump to `backups/Starwars_YYYYMMDD_HHMMSS.sql`:

- All 15 tables, parents first
- `NOCHECK CONSTRAINT ALL` at start, `WITH CHECK CHECK CONSTRAINT ALL` at end
- Restores in correct order to satisfy FKs
- Round-trip tested: truncate → restore → 807 rows recovered

## Skills reference

### `netdevops-automation`
Multi-vendor network automation with netmiko, nornir, napalm, scrapli, Jinja2.
See `.agents/skills/netdevops-automation/SKILL.md`.

### `mssql-database`
MSSQL queries, table management, test data generation, backups.
See `.agents/skills/mssql-database/SKILL.md`.

### `swapi-client`
Fetch, query, and export data from SWAPI (swapi.info). No auth, no pagination.
See `.agents/skills/swapi-client/SKILL.md`.

## Configuration

`.env` (gitignored):

```ini
DB_IP="10.20.42.103"
DB_USER="sa"
DB_PASSWORD="Qwerty-1"
```

## Logs

Runtime logs are written to `logs/YYYY-MM-DD_<module>.log` (gitignored).
The Starwars importer logs to `logs/YYYY-MM-DD_starwars_importer.log`.

## License

MIT
