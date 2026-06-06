#!/usr/bin/env python3
"""Generate random test data and insert into a MSSQL table.

Usage:
    python scripts/generate_data.py --database SuperCompany --table Users --count 100
    python scripts/generate_data.py --database SuperCompany --table Users --count 1000 --dry-run
"""
import argparse
import os
import random
import sys
import uuid

import pymssql
from dotenv import load_dotenv

load_dotenv()

FIRST_NAMES = [
    "James","Mary","Robert","Patricia","John","Jennifer","Michael","Linda",
    "David","Elizabeth","William","Barbara","Richard","Susan","Joseph","Jessica",
    "Thomas","Sarah","Christopher","Karen","Charles","Lisa","Daniel","Nancy",
    "Matthew","Betty","Anthony","Margaret","Mark","Sandra","Donald","Ashley",
    "Steven","Kimberly","Paul","Emily","Andrew","Donna","Joshua","Michelle",
    "Kenneth","Dorothy","Kevin","Carol","Brian","Amanda","George","Melissa",
    "Timothy","Deborah","Ronald","Stephanie","Edward","Rebecca","Jason","Sharon",
    "Jeffrey","Laura","Ryan","Cynthia","Jacob","Kathleen","Gary","Amy",
    "Nicholas","Angela","Eric","Shirley","Jonathan","Anna","Stephen","Brenda",
    "Larry","Pamela","Justin","Emma","Scott","Nicole","Brandon","Helen",
    "Benjamin","Samantha","Samuel","Katherine","Raymond","Christine","Gregory","Debra",
    "Frank","Rachel","Alexander","Carolyn","Patrick","Janet","Jack","Catherine",
    "Dennis","Maria","Jerry","Heather","Tyler","Diane","Aaron","Ruth",
    "Jose","Julie","Adam","Olivia","Nathan","Joyce","Henry","Virginia",
    "Douglas","Victoria","Zachary","Kelly","Peter","Lauren","Kyle","Christina",
    "Ethan","Joan","Noah","Evelyn","Jeremy","Judith","Walter","Megan",
    "Christian","Andrea","Keith","Cheryl","Roger","Hannah","Terry","Jacqueline",
    "Austin","Martha","Sean","Gloria","Gerald","Teresa","Carl","Ann",
    "Harold","Sara","Dylan","Madison","Arthur","Frances","Lawrence","Kathryn",
    "Jordan","Janice","Jesse","Jean","Bryan","Abigail","Billy","Alice",
    "Bruce","Judy","Gabriel","Sophia","Joe","Grace","Logan","Denise",
    "Albert","Amber","Willie","Doris","Alan","Marilyn","Eugene","Danielle",
    "Russell","Beverly","Vincent","Isabella","Philip","Theresa","Bobby","Diana",
    "Johnny","Natalie","Bradley","Brittany","Roy","Charlotte","Elijah","Marie",
    "Randy","Kayla","Wayne","Alexis",
]

LAST_NAMES = [
    "Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
    "Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson",
    "Thomas","Taylor","Moore","Jackson","Martin","Lee","Perez","Thompson",
    "White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson","Walker",
    "Young","Allen","King","Wright","Scott","Torres","Nguyen","Hill",
    "Flores","Green","Adams","Nelson","Baker","Hall","Rivera","Campbell",
    "Mitchell","Carter","Roberts","Gomez","Phillips","Evans","Turner","Diaz",
    "Parker","Cruz","Edwards","Collins","Reyes","Stewart","Morris","Morales",
    "Murphy","Cook","Rogers","Gutierrez","Ortiz","Morgan","Cooper","Peterson",
    "Bailey","Reed","Kelly","Howard","Ramos","Kim","Cox","Ward",
    "Richardson","Watson","Brooks","Chavez","Wood","James","Bennett","Gray",
    "Mendoza","Ruiz","Hughes","Price","Alvarez","Castillo","Sanders","Patel",
    "Myers","Long","Ross","Foster","Jimenez","Powell","Jenkins","Perry",
    "Russell","Sullivan","Bell","Coleman","Butler","Henderson","Barnes","Gonzales",
    "Fisher","Vasquez","Simmons","Patterson","Jordan","Reynolds","Hamilton","Graham",
]

COUNTRIES_CITIES = {
    "USA": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"],
    "Canada": ["Toronto", "Montreal", "Vancouver", "Calgary", "Ottawa"],
    "UK": ["London", "Manchester", "Birmingham", "Glasgow", "Liverpool"],
    "Germany": ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne"],
    "France": ["Paris", "Marseille", "Lyon", "Toulouse", "Nice"],
    "Italy": ["Rome", "Milan", "Naples", "Turin", "Florence"],
    "Spain": ["Madrid", "Barcelona", "Valencia", "Seville", "Bilbao"],
    "Ukraine": ["Kyiv", "Lviv", "Odesa", "Kharkiv", "Dnipro"],
    "Poland": ["Warsaw", "Krakow", "Wroclaw", "Poznan", "Gdansk"],
    "Netherlands": ["Amsterdam", "Rotterdam", "The Hague", "Utrecht"],
    "Australia": ["Sydney", "Melbourne", "Brisbane", "Perth"],
    "Japan": ["Tokyo", "Osaka", "Yokohama", "Nagoya"],
    "India": ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata"],
    "Brazil": ["Sao Paulo", "Rio de Janeiro", "Brasilia", "Salvador"],
    "South Africa": ["Johannesburg", "Cape Town", "Durban", "Pretoria"],
}

EMAIL_DOMAINS = ["gmail.com", "outlook.com", "yahoo.com", "protonmail.com", "icloud.com"]


def generate_rows(n: int) -> list[tuple]:
    countries = list(COUNTRIES_CITIES.keys())
    rows = []
    for _ in range(n):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        country = random.choice(countries)
        city = random.choice(COUNTRIES_CITIES[country])
        email = f"{first.lower()}.{last.lower()}{random.randint(1,999)}@{random.choice(EMAIL_DOMAINS)}"
        salary = random.randint(2500, 15000)
        rows.append((str(uuid.uuid4()), first, last, email, country, city, salary))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate random user data")
    parser.add_argument("--database", required=True, help="Target database")
    parser.add_argument("--table", default="Users", help="Target table")
    parser.add_argument("--count", type=int, default=100, help="Number of rows")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    conn = pymssql.connect(
        server=os.environ["DB_IP"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=args.database,
        port=1433,
        login_timeout=10,
    )

    rows = generate_rows(args.count)

    if args.dry_run:
        print(f"[DRY-RUN] Would insert {len(rows)} rows into [{args.table}]:")
        for r in rows[:5]:
            print(f"  {r}")
        print(f"  ... and {len(rows) - 5} more")
        conn.close()
        return 0

    cur = conn.cursor()
    cur.executemany(
        f"INSERT INTO [{args.table}] (id, name, surname, email, country, city, salary) "
        "VALUES (%s, %s, %s, %s, %s, %s, %d)",
        rows,
    )
    conn.commit()

    cur.execute(f"SELECT COUNT(*) FROM [{args.table}]")
    total = cur.fetchone()[0]
    print(f"Inserted {len(rows)} rows. Total in [{args.table}]: {total}")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
