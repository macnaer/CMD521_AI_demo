# MSSQL Reference Guide

Advanced SQL patterns and operations for Microsoft SQL Server.

## Data Types Cheat Sheet

| Category | Types |
|----------|-------|
| Integer | `INT`, `BIGINT`, `SMALLINT`, `TINYINT` |
| Decimal | `DECIMAL(p,s)`, `NUMERIC`, `FLOAT`, `REAL` |
| String | `VARCHAR(n)`, `NVARCHAR(n)`, `CHAR(n)`, `TEXT` |
| Date/Time | `DATE`, `TIME`, `DATETIME2`, `DATETIMEOFFSET`, `DATETIME` |
| Binary | `VARBINARY(n)`, `BINARY(n)`, `IMAGE` |
| Other | `UNIQUEIDENTIFIER`, `BIT`, `XML`, `JSON` |

## Useful System Views

```sql
-- Database sizes
SELECT
    d.name,
    CAST(mf.size * 8 / 1024.0 AS DECIMAL(10,2)) AS size_mb
FROM sys.databases d
JOIN sys.master_files mf ON d.database_id = mf.database_id
GROUP BY d.name, mf.size;

-- Active connections
SELECT session_id, login_name, status, program_name
FROM sys.dm_exec_sessions
WHERE is_user_process = 1;

-- Running queries
SELECT r.session_id, r.status, r.command, t.text AS sql_text
FROM sys.dm_exec_requests r
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) t;

-- Index usage
SELECT
    OBJECT_NAME(i.object_id) AS table_name,
    i.name AS index_name,
    ius.user_seeks,
    ius.user_scans,
    ius.user_lookups
FROM sys.indexes i
LEFT JOIN sys.dm_db_index_usage_stats ius
    ON i.object_id = ius.object_id AND i.index_id = ius.index_id;

-- Table row counts
SELECT
    s.name AS schema_name,
    t.name AS table_name,
    p.rows AS row_count
FROM sys.tables t
JOIN sys.schemas s ON t.schema_id = s.schema_id
JOIN sys.partitions p ON t.object_id = p.object_id
WHERE p.index_id IN (0, 1)
ORDER BY p.rows DESC;
```

## JSON Support

```sql
-- Parse JSON column
SELECT
    id,
    JSON_VALUE(data, '$.name') AS name,
    JSON_VALUE(data, '$.age') AS age
FROM Users;

-- FOR JSON output
SELECT id, name, email
FROM Users
FOR JSON PATH, ROOT('users');
```

## Window Functions

```sql
-- Row number per group
SELECT *,
    ROW_NUMBER() OVER (PARTITION BY country ORDER BY salary DESC) AS rank
FROM Users;

-- Running total
SELECT
    id, name, salary,
    SUM(salary) OVER (ORDER BY id) AS running_total
FROM Users;

-- Percent of total
SELECT
    name, salary,
    CAST(salary * 100.0 / SUM(salary) OVER () AS DECIMAL(5,2)) AS pct
FROM Users;
```

## Common Table Expressions (CTE)

```sql
-- Recursive CTE (org chart, tree traversal)
WITH OrgChart AS (
    SELECT id, name, manager_id, 0 AS level
    FROM Employees
    WHERE manager_id IS NULL
    UNION ALL
    SELECT e.id, e.name, e.manager_id, c.level + 1
    FROM Employees e
    JOIN OrgChart c ON e.manager_id = c.id
)
SELECT * FROM OrgChart ORDER BY level, name;
```

## Temporary Tables

```sql
-- Local temp table (session-scoped)
CREATE TABLE #TempResults (
    id INT,
    name VARCHAR(255)
);

INSERT INTO #TempResults
SELECT id, name FROM Users WHERE salary > 5000;

SELECT * FROM #TempResults;
DROP TABLE #TempResults;
```

## Stored Procedure Pattern

```sql
CREATE PROCEDURE GetUsersByCountry
    @Country VARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT UsersID, name, surname, email, city, salary
    FROM Users
    WHERE country = @Country
    ORDER BY salary DESC;
END;
```

```python
# Call from Python
cursor.execute("EXEC GetUsersByCountry @Country = %s", ("Ukraine",))
for row in cursor.fetchall():
    print(row)
```

## Error Handling in SQL

```sql
BEGIN TRY
    INSERT INTO Users (name, email) VALUES ('Test', 'test@test.com');
    SELECT 'Success' AS result;
END TRY
BEGIN CATCH
    SELECT
        ERROR_NUMBER() AS error_number,
        ERROR_MESSAGE() AS error_message,
        ERROR_SEVERITY() AS severity;
END CATCH
```

## Performance Tips

1. Always specify column names in `INSERT` — never `INSERT INTO t VALUES (...)`.
2. Use `TOP` or `LIMIT` to avoid unbounded result sets.
3. Add indexes on columns used in `WHERE`, `JOIN`, `ORDER BY`.
4. Use `SET NOCOUNT ON` in stored procedures to reduce network traffic.
5. Avoid `SELECT *` in production queries.
6. Use `EXISTS` instead of `IN` for subqueries when possible.
