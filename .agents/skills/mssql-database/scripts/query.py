#!/usr/bin/env python3
"""Execute a SQL query or file against an MSSQL database.

Usage:
    python scripts/query.py --database SuperCompany --sql "SELECT TOP 10 * FROM Users"
    python scripts/query.py --database SuperCompany --file query.sql
    python scripts/query.py --database SuperCompany --file query.sql --output results.csv
"""
import argparse
import csv
import os
import sys

import pymssql
from dotenv import load_dotenv

load_dotenv()


def run_query(database: str, sql: str, output: str | None = None) -> None:
    conn = pymssql.connect(
        server=os.environ["DB_IP"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=database,
        port=1433,
        login_timeout=10,
    )

    cur = conn.cursor()
    cur.execute(sql)

    if cur.description:
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

        # Print table
        print("\t".join(columns))
        print("-" * 80)
        for row in rows:
            print("\t".join(str(v) for v in row))

        print(f"\n({len(rows)} rows)")

        # Export to CSV if requested
        if output:
            with open(output, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                writer.writerows(rows)
            print(f"Exported to {output}")
    else:
        conn.commit()
        print(f"Query executed. Rows affected: {cur.rowcount}")

    conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute SQL query on MSSQL")
    parser.add_argument("--database", required=True, help="Target database")
    parser.add_argument("--sql", help="SQL query string")
    parser.add_argument("--file", help="SQL file to execute")
    parser.add_argument("--output", help="Export results to CSV")
    args = parser.parse_args()

    if args.sql:
        sql = args.sql
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            sql = f.read()
    else:
        print("Error: provide --sql or --file")
        return 1

    run_query(args.database, sql, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
