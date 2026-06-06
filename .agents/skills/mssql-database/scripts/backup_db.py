#!/usr/bin/env python3
"""Backup an MSSQL database to a .bak file on the server.

Usage:
    python scripts/backup_db.py --database SuperCompany
    python scripts/backup_db.py --database SuperCompany --output-dir /backups
    python scripts/backup_db.py --database SuperCompany --dry-run
"""
import argparse
import os
import sys
from datetime import datetime

import pymssql
from dotenv import load_dotenv

load_dotenv()


def backup_database(database: str, output_dir: str, dry_run: bool = False) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{database}_{timestamp}.bak"

    if dry_run:
        return f"[DRY-RUN] Would backup [{database}] to {output_dir}/{filename}"

    conn = pymssql.connect(
        server=os.environ["DB_IP"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        port=1433,
        login_timeout=10,
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Build backup path (SQL Server needs Windows-style or shared path)
    backup_path = f"{output_dir}/{filename}".replace("\\", "/")
    sql = f"BACKUP DATABASE [{database}] TO DISK = N'{backup_path}' WITH FORMAT, INIT, NAME = N'{database} Full Backup'"

    cur.execute(sql)
    conn.close()
    return f"Backup saved: {backup_path}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup MSSQL database")
    parser.add_argument("--database", required=True, help="Database to backup")
    parser.add_argument("--output-dir", default="/var/opt/mssql/backup", help="Backup directory on server")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    result = backup_database(args.database, args.output_dir, args.dry_run)
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
