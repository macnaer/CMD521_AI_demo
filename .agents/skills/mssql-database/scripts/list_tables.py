#!/usr/bin/env python3
"""List all databases and their tables on an MSSQL server.

Usage:
    python scripts/list_tables.py
    python scripts/list_tables.py --database SuperCompany
    python scripts/list_tables.py --database SuperCompany --schema dbo
"""
import argparse
import os
import sys

import pymssql
from dotenv import load_dotenv

load_dotenv()


def connect(database: str = "master") -> pymssql.Connection:
    return pymssql.connect(
        server=os.environ["DB_IP"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=database,
        port=1433,
        login_timeout=10,
    )


def list_databases(conn: pymssql.Connection) -> list[str]:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sys.databases ORDER BY name")
    return [row[0] for row in cur.fetchall()]


def list_tables(conn: pymssql.Connection, schema: str | None = None) -> list[dict]:
    cur = conn.cursor()
    if schema:
        cur.execute(
            "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA = %s "
            "ORDER BY TABLE_SCHEMA, TABLE_NAME",
            (schema,),
        )
    else:
        cur.execute(
            "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_SCHEMA, TABLE_NAME"
        )
    return [{"schema": r[0], "table": r[1]} for r in cur.fetchall()]


def table_info(conn: pymssql.Connection, table: str) -> list[dict]:
    cur = conn.cursor()
    cur.execute(
        "SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE "
        "FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = %s ORDER BY ORDINAL_POSITION",
        (table,),
    )
    return [
        {
            "column": r[0],
            "type": r[1],
            "max_length": r[2],
            "nullable": r[3] == "YES",
        }
        for r in cur.fetchall()
    ]


def row_count(conn: pymssql.Connection, table: str) -> int:
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM [{table}]")
    return cur.fetchone()[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="List MSSQL databases and tables")
    parser.add_argument("--database", help="Show tables for a specific database")
    parser.add_argument("--schema", help="Filter by schema (e.g. dbo)")
    parser.add_argument("--info", action="store_true", help="Show column details for tables")
    args = parser.parse_args()

    conn = connect()

    if args.database:
        conn.close()
        conn = connect(args.database)
        tables = list_tables(conn, args.schema)
        print(f"\n=== Tables in [{args.database}] ===")
        for t in tables:
            count = row_count(conn, t["table"]) if args.info else None
            suffix = f" ({count} rows)" if count is not None else ""
            print(f"  [{t['schema']}].[{t['table']}]{suffix}")
            if args.info:
                cols = table_info(conn, t["table"])
                for c in cols:
                    ml = f"({c['max_length']})" if c["max_length"] else ""
                    nn = "NOT NULL" if not c["nullable"] else "NULL"
                    print(f"    {c['column']:<30} {c['type']:<15} {ml:<10} {nn}")
    else:
        dbs = list_databases(conn)
        print("\n=== Databases ===")
        for db in dbs:
            print(f"  {db}")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
