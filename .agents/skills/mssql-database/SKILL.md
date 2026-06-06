---
name: mssql-database
description: Query, create, modify, and manage Microsoft SQL Server databases. Use when writing SQL queries, creating tables, inserting/updating data, building database scripts, connecting to MSSQL with pymssql/pyodbc, generating test data, or any SQL Server task.
license: MIT
compatibility: Requires Python 3.11+, pymssql or pyodbc, python-dotenv. Network access to target MSSQL server.
metadata:
  author: netdevops-team
  version: "1.0"
  domain: database
allowed-tools: Bash(python:*) Bash(pip:*) Read Glob Grep Write
---

# MSSQL Database Skill

You are a Database Engineer specialized in Microsoft SQL Server.
Write production-grade Python scripts and SQL for MSSQL.

## Connection Pattern

Always read credentials from `.env` file, never hard-code.

```python
import os
import pymssql
from dotenv import load_dotenv

load_dotenv()

conn = pymssql.connect(
    server=os.environ["DB_IP"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    database="TargetDB",       # or omit to connect to master
    port=1433,
    login_timeout=10,
)
conn.autocommit = False  # explicit transactions
cursor = conn.cursor()
```

## Non-Negotiable Rules

1. **Never hard-code credentials.** Use `${ENV_VAR}` placeholders, resolve at runtime via `.env`.
2. **Always close connections.** Use `try/finally` or context managers.
3. **Use parameterized queries.** Never interpolate user input into SQL strings.
   - Correct: `cursor.execute("SELECT * FROM Users WHERE name = %s", (name,))`
   - Wrong: `cursor.execute(f"SELECT * FROM Users WHERE name = '{name}'")`
4. **Wrap state-changing operations in transactions.** Commit explicitly; rollback on error.
5. **Validate input** with pydantic before executing.
6. **Back up before destructive changes** (DROP, DELETE, TRUNCATE).

## Common Operations

### List databases
```sql
SELECT name FROM sys.databases ORDER BY name;
```

### List tables in current DB
```sql
SELECT TABLE_SCHEMA, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_SCHEMA, TABLE_NAME;
```

### Table columns
```sql
SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE, COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'YourTable'
ORDER BY ORDINAL_POSITION;
```

### Row count
```sql
SELECT COUNT(*) FROM YourTable;
```

### Sample data
```sql
SELECT TOP 10 * FROM YourTable;
```

### Create database
```sql
CREATE DATABASE MyDB;
```

### Create table
```sql
CREATE TABLE MyTable (
    Id      INT NOT NULL IDENTITY(1,1) PRIMARY KEY,
    Name    VARCHAR(255) NOT NULL,
    Email   VARCHAR(255) NULL,
    Created DATETIME2 DEFAULT GETDATE()
);
```

### Insert with IDENTITY
```python
# Do NOT include the IDENTITY column in INSERT
cursor.execute(
    "INSERT INTO Users (name, email) VALUES (%s, %s)",
    ("John", "john@example.com"),
)
conn.commit()
```

### Bulk insert
```python
cursor.executemany(
    "INSERT INTO Users (name, email) VALUES (%s, %s)",
    [("User1", "u1@ex.com"), ("User2", "u2@ex.com")],
)
conn.commit()
```

### Update
```python
cursor.execute(
    "UPDATE Users SET email = %s WHERE id = %s",
    ("new@example.com", 1),
)
conn.commit()
```

### Delete
```python
cursor.execute("DELETE FROM Users WHERE id = %s", (1,))
conn.commit()
```

### Backup
```sql
BACKUP DATABASE MyDB TO DISK = '/path/to/backup.bak'
WITH FORMAT, INIT, NAME = 'MyDB Full Backup';
```

### Restore
```sql
RESTORE DATABASE MyDB FROM DISK = '/path/to/backup.bak'
WITH REPLACE;
```

## Transaction Pattern

```python
try:
    conn.autocommit = False
    cursor.execute("INSERT INTO Orders (...) VALUES (...)")
    cursor.execute("UPDATE Inventory SET qty = qty - 1 WHERE product_id = %s", (pid,))
    conn.commit()
except Exception:
    conn.rollback()
    raise
finally:
    conn.autocommit = True
```

## Error Handling

```python
try:
    cursor.execute(query, params)
except pymssql.OperationalError as e:
    print(f"Connection/query error: {e}")
except pymssql.ProgrammingError as e:
    print(f"SQL syntax or schema error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
finally:
    conn.close()
```

## Testing Scripts

Write scripts as standalone files with `if __name__ == "__main__":` block.
Use `argparse` for CLI flags (`--dry-run`, `--database`, `--query`).

## Safety

- `SELECT` is always safe — run freely.
- `INSERT/UPDATE` — dry-run first, show affected rows count.
- `DELETE/TRUNCATE/DROP` — always backup first, confirm with user, show preview.
- Never run destructive queries in a loop without LIMIT/TOP.

See [references/REFERENCE.md](references/REFERENCE.md) for advanced SQL patterns.
See [scripts/](scripts/) for ready-to-use database utilities.
