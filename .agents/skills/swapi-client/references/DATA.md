# SWAPI Data Reference

Field schemas, relationships, and data notes for all SWAPI resources.

## People (83 items)

| Field | Type | Notes |
|-------|------|-------|
| name | string | Unique display name |
| height | string | In cm. Parse to int. "unknown" possible |
| mass | string | In kg. Parse to int. "unknown" possible |
| hair_color | string | Comma-separated if multiple |
| skin_color | string | Comma-separated if multiple |
| eye_color | string | Comma-separated if multiple |
| birth_year | string | e.g. "19BBY", "unknown" |
| gender | string | male, female, hermaphrodite, n/a, none |
| homeworld | URL | → /planets/{id} |
| films | URL[] | → /films/{id} |
| species | URL[] | → /species/{id} |
| vehicles | URL[] | → /vehicles/{id} |
| starships | URL[] | → /starships/{id} |

### People IDs: 1-83 (with gaps: no 17, 20-22, etc.)

Key characters:
- 1: Luke Skywalker
- 2: C-3PO
- 3: R2-D2
- 4: Darth Vader
- 5: Leia Organa
- 10: Obi-Wan Kenobi
- 11: Anakin Skywalker
- 13: Chewbacca
- 14: Han Solo
- 20: Yoda
- 21: Palpatine
- 22: Boba Fett

## Films (6 items)

| Field | Type | Notes |
|-------|------|-------|
| title | string | |
| episode_id | int | 1-6 |
| opening_crawl | string | Multi-line text |
| director | string | |
| producer | string | Comma-separated |
| release_date | string | ISO date (YYYY-MM-DD) |
| characters | URL[] | → /people/{id} |
| planets | URL[] | → /planets/{id} |
| starships | URL[] | → /starships/{id} |
| vehicles | URL[] | → /vehicles/{id} |
| species | URL[] | → /species/{id} |

Order by episode_id: 1 (Phantom Menace) → 6 (Revenge of the Sith)

## Planets (60 items)

| Field | Type | Notes |
|-------|------|-------|
| name | string | |
| rotation_period | string | Hours. Parse to int |
| orbital_period | string | Days. Parse to int |
| diameter | string | In km. Parse to int |
| climate | string | e.g. "arid", "temperate" |
| gravity | string | e.g. "1 standard", "0.9" |
| terrain | string | Comma-separated |
| surface_water | string | Percentage. Parse to int |
| population | string | Parse to int. "unknown" possible |
| residents | URL[] | → /people/{id} |
| films | URL[] | → /films/{id} |

## Species (37 items)

| Field | Type | Notes |
|-------|------|-------|
| name | string | |
| classification | string | mammal, reptile, amphibian, insectoid, etc. |
| designation | string | sentient, reptilian |
| average_height | string | In cm. "n/a" for droids |
| skin_colors | string | Comma-separated |
| hair_colors | string | Comma-separated. "n/a" for non-hairy |
| eye_colors | string | Comma-separated |
| average_lifespan | string | In years. "unknown", "indefinite" possible |
| homeworld | URL or null | → /planets/{id}. null for some species |
| language | string | |
| people | URL[] | → /people/{id} |
| films | URL[] | → /films/{id} |

## Vehicles (39 items)

| Field | Type | Notes |
|-------|------|-------|
| name | string | |
| model | string | |
| manufacturer | string | |
| cost_in_credits | string | Parse to int. "unknown" possible |
| length | string | In meters. Parse to float |
| max_atmosphering_speed | string | Parse to int. "unknown" possible |
| crew | string | Parse to int. Range "30-165" possible |
| passengers | string | Parse to int |
| cargo_capacity | string | In kg. Parse to int |
| consumables | string | e.g. "2 months", "unknown" |
| vehicle_class | string | |
| pilots | URL[] | → /people/{id} |
| films | URL[] | → /films/{id} |

## Starships (36 items)

| Field | Type | Notes |
|-------|------|-------|
| name | string | |
| model | string | |
| manufacturer | string | |
| cost_in_credits | string | Parse to int. "unknown" possible |
| length | string | In meters. Parse to float |
| max_atmosphering_speed | string | Parse to int. "n/a" for space-only |
| crew | string | Parse to int. Range "30-165" possible |
| passengers | string | Parse to int |
| cargo_capacity | string | In kg. Parse to int |
| consumables | string | |
| hyperdrive_rating | string | Parse to float. "unknown" possible |
| MGLT | string | Parse to int. "unknown" possible |
| starship_class | string | |
| pilots | URL[] | → /people/{id} |
| films | URL[] | → /films/{id} |

## Cross-Reference Map

```
people.homeworld ────→ planets
people.films ────────→ films
people.species ──────→ species
people.vehicles ─────→ vehicles
people.starships ────→ starships

films.characters ────→ people
films.planets ───────→ planets
films.starships ─────→ starships
films.vehicles ──────→ vehicles
films.species ───────→ species

planets.residents ───→ people
planets.films ───────→ films

species.homeworld ───→ planets
species.people ──────→ people
species.films ───────→ films

vehicles.pilots ─────→ people
vehicles.films ──────→ films

starships.pilots ────→ people
starships.films ─────→ films
```

## Data Quirks

1. `"unknown"` appears as a string, not null
2. Numeric fields are strings: `"172"`, `"1,358"`, `"150000"`
3. Some fields have `"n/a"` instead of "unknown"
4. `birth_year` uses BBY/ABY format: `"19BBY"`, `"41.9BBY"`
5. `crew` can be a range: `"30-165"`
6. `consumables` is human-readable: `"2 months"`, `"1 year"`
7. Some URL arrays are empty: `[]`
8. `species.homeworld` can be `null`
