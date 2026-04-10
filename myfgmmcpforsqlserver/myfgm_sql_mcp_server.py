"""
myfgm_sql_mcp_server.py — MCP server for WoundCareDB
Tools: list_tables, describe_table, table_stats, run_query
"""
import re
import json
from typing import Any
from mcp.server.fastmcp import FastMCP
from db import get_connection, rows_to_dicts

mcp = FastMCP(
    name="myfgm-sql-server",
    instructions=(
        "You are connected to WoundCareDB on a local SQL Server instance. "
        "Use the available tools to explore schemas, understand table structures, "
        "get row statistics, and run read-only SELECT queries. "
        "Never attempt INSERT, UPDATE, DELETE, DROP, or any DDL statements."
    ),
)

# ── Tool 1 — list_tables ─────────────────────────────────────────────────────

@mcp.tool()
def list_tables(schema: str = "") -> str:
    """
    List all user tables and views in the database.

    Args:
        schema: Optional schema name to filter (e.g. 'dbo').
                Leave empty to list all schemas.

    Returns:
        JSON array with schema_name, table_name, table_type.
    """
    query = """
        SELECT
            TABLE_SCHEMA AS schema_name,
            TABLE_NAME   AS table_name,
            TABLE_TYPE   AS table_type
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW')
    """
    params: list[Any] = []
    if schema:
        query += " AND TABLE_SCHEMA = ?"
        params.append(schema)
    query += " ORDER BY TABLE_SCHEMA, TABLE_NAME"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = rows_to_dicts(cursor)

    return json.dumps(results, default=str)


# ── Tool 2 — describe_table ──────────────────────────────────────────────────

@mcp.tool()
def describe_table(table_name: str, schema: str = "dbo") -> str:
    """
    Describe columns, primary keys, and foreign keys of a table.

    Args:
        table_name: Name of the table to describe.
        schema:     Schema name (default 'dbo').

    Returns:
        JSON object with 'columns' and 'foreign_keys' arrays.
    """
    col_query = """
        SELECT
            c.COLUMN_NAME                               AS column_name,
            c.DATA_TYPE                                 AS data_type,
            c.CHARACTER_MAXIMUM_LENGTH                  AS max_length,
            c.NUMERIC_PRECISION                         AS numeric_precision,
            c.NUMERIC_SCALE                             AS numeric_scale,
            c.IS_NULLABLE                               AS is_nullable,
            c.COLUMN_DEFAULT                            AS column_default,
            CASE WHEN pk.COLUMN_NAME IS NOT NULL
                 THEN 'YES' ELSE 'NO' END               AS is_primary_key
        FROM INFORMATION_SCHEMA.COLUMNS c
        LEFT JOIN (
            SELECT ku.TABLE_SCHEMA, ku.TABLE_NAME, ku.COLUMN_NAME
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
              ON tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
             AND tc.TABLE_SCHEMA    = ku.TABLE_SCHEMA
            WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
        ) pk
          ON  pk.TABLE_SCHEMA = c.TABLE_SCHEMA
          AND pk.TABLE_NAME   = c.TABLE_NAME
          AND pk.COLUMN_NAME  = c.COLUMN_NAME
        WHERE c.TABLE_SCHEMA = ?
          AND c.TABLE_NAME   = ?
        ORDER BY c.ORDINAL_POSITION
    """

    fk_query = """
        SELECT
            kcu.COLUMN_NAME     AS column_name,
            ccu.TABLE_SCHEMA    AS referenced_schema,
            ccu.TABLE_NAME      AS referenced_table,
            ccu.COLUMN_NAME     AS referenced_column
        FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
          ON rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE ccu
          ON rc.UNIQUE_CONSTRAINT_NAME = ccu.CONSTRAINT_NAME
        WHERE kcu.TABLE_SCHEMA = ?
          AND kcu.TABLE_NAME   = ?
    """

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(col_query, [schema, table_name])
        columns = rows_to_dicts(cursor)
        cursor.execute(fk_query, [schema, table_name])
        foreign_keys = rows_to_dicts(cursor)

    return json.dumps({"columns": columns, "foreign_keys": foreign_keys}, default=str)


# ── Tool 3 — table_stats ─────────────────────────────────────────────────────

@mcp.tool()
def table_stats(table_name: str, schema: str = "dbo") -> str:
    """
    Return row count and storage size for a table.

    Args:
        table_name: Name of the table.
        schema:     Schema name (default 'dbo').

    Returns:
        JSON object with row_count, size info, and column_count.
    """
    stats_query = """
        SELECT
            SUM(p.rows)                                   AS row_count,
            SUM(a.total_pages) * 8                        AS total_size_kb,
            SUM(a.used_pages)  * 8                        AS used_size_kb,
            (SUM(a.total_pages) - SUM(a.used_pages)) * 8 AS unused_size_kb
        FROM sys.tables t
        JOIN sys.schemas s      ON t.schema_id   = s.schema_id
        JOIN sys.indexes i      ON t.object_id   = i.object_id
        JOIN sys.partitions p   ON i.object_id   = p.object_id
                               AND i.index_id    = p.index_id
        JOIN sys.allocation_units a ON p.partition_id = a.container_id
        WHERE s.name    = ?
          AND t.name    = ?
          AND i.index_id IN (0, 1)
    """

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(stats_query, [schema, table_name])
        stats = rows_to_dicts(cursor)

        cursor.execute(f"SELECT TOP 0 * FROM [{schema}].[{table_name}]")
        col_count = len(cursor.description) if cursor.description else 0

    result = stats[0] if stats else {}
    result["column_count"] = col_count
    result["table"] = f"{schema}.{table_name}"

    return json.dumps(result, default=str)


# ── Tool 4 — run_query ───────────────────────────────────────────────────────

@mcp.tool()
def run_query(sql: str, max_rows: int = 200) -> str:
    """
    Execute a read-only SELECT query and return results as JSON.

    Args:
        sql:      A SELECT or WITH (CTE) statement only.
        max_rows: Max rows to return (default 200, capped at 1000).

    Returns:
        JSON object with columns, rows, row_count, and truncated flag.
    """
    forbidden = (
        "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE",
        "ALTER", "CREATE", "EXEC", "EXECUTE", "MERGE",
        "GRANT", "REVOKE", "DENY", "BULK"
    )
    normalized = sql.strip().upper()
    for kw in forbidden:
        if re.search(rf"\b{kw}\b", normalized):
            return json.dumps({
                "error": f"Blocked: '{kw}' statements are not permitted. "
                         "Only SELECT queries are allowed."
            })

    max_rows = min(max_rows, 1000)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchmany(max_rows)

    serialized = [
        [str(v) if not isinstance(v, (int, float, bool, type(None))) else v
         for v in row]
        for row in rows
    ]

    return json.dumps({
        "columns": columns,
        "rows": serialized,
        "row_count": len(rows),
        "truncated": len(rows) == max_rows,
    }, default=str)


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()