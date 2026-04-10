"""
tests/test_server.py — lean test suite
"""
import os
import sys
import json
import pyodbc
import pytest
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv()
from db import build_connection_string


# ── Shared fixture ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def connection():
    try:
        conn = pyodbc.connect(build_connection_string(), timeout=10)
    except pyodbc.Error as e:
        pytest.fail(f"Could not connect to SQL Server:\n{e}")
    yield conn
    conn.close()


# ── Step 1 — Connection ──────────────────────────────────────────────────────

class TestConnection:

    @pytest.mark.parametrize("key", ["MSSQL_DRIVER", "MSSQL_SERVER", "MSSQL_DATABASE"])
    def test_env_var_is_set(self, key):
        assert os.getenv(key), f"{key} is missing from .env"

    def test_server_is_reachable(self, connection):
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        assert cursor.fetchone()[0] == 1
        cursor.close()

    def test_target_database_exists(self, connection):
        db = os.getenv("MSSQL_DATABASE")
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sys.databases WHERE name = ?", db)
        assert cursor.fetchone() is not None, f"Database '{db}' not found"
        cursor.close()


# ── Step 2 — list_tables ─────────────────────────────────────────────────────

class TestListTables:

    def test_returns_known_woundcaredb_tables(self):
        """One test — covers: returns list, has rows, correct schema, known tables."""
        from myfgm_sql_mcp_server import list_tables
        result = json.loads(list_tables(schema="dbo"))
        found = {r["table_name"] for r in result}
        expected = {"dim_patient", "dim_clinician", "dim_date",
                    "fact_clinical_visit", "fact_wound_assessment"}
        assert expected.issubset(found), f"Missing tables: {expected - found}"

    def test_each_row_has_required_keys(self):
        from myfgm_sql_mcp_server import list_tables
        result = json.loads(list_tables(schema="dbo"))
        for row in result:
            assert {"schema_name", "table_name", "table_type"}.issubset(row.keys())


# ── Step 3 — describe_table ──────────────────────────────────────────────────

class TestDescribeTable:

    def test_columns_have_required_fields(self):
        from myfgm_sql_mcp_server import describe_table
        result = json.loads(describe_table(table_name="dim_patient"))
        assert len(result["columns"]) > 0
        for col in result["columns"]:
            assert {"column_name", "data_type", "is_nullable", "is_primary_key"}.issubset(col.keys())

    def test_unknown_table_returns_empty(self):
        from myfgm_sql_mcp_server import describe_table
        result = json.loads(describe_table(table_name="nonexistent_xyz"))
        assert result["columns"] == [] and result["foreign_keys"] == []


# ── Step 4 — table_stats ─────────────────────────────────────────────────────

class TestTableStats:

    def test_returns_valid_stats(self):
        """Covers: required fields, non-negative row_count, positive column_count."""
        from myfgm_sql_mcp_server import table_stats
        result = json.loads(table_stats(table_name="dim_patient"))
        assert {"row_count", "total_size_kb", "column_count", "table"}.issubset(result.keys())
        assert int(result["row_count"])    >= 0
        assert int(result["column_count"]) > 0

    def test_column_count_matches_describe_table(self):
        from myfgm_sql_mcp_server import table_stats, describe_table
        stats = json.loads(table_stats(table_name="dim_clinician"))
        desc  = json.loads(describe_table(table_name="dim_clinician"))
        assert int(stats["column_count"]) == len(desc["columns"])


# ── Step 5 — run_query ───────────────────────────────────────────────────────

class TestRunQuery:

    def test_valid_select_returns_results(self):
        """Covers: columns, rows, row_count, max_rows, truncated flag."""
        from myfgm_sql_mcp_server import run_query
        result = json.loads(run_query("SELECT * FROM dbo.dim_date", max_rows=3))
        assert {"columns", "rows", "row_count", "truncated"}.issubset(result.keys())
        assert result["row_count"] <= 3

    @pytest.mark.parametrize("sql, keyword", [
        ("DELETE FROM dbo.dim_patient",             "DELETE"),
        ("DROP TABLE dbo.dim_patient",              "DROP"),
        ("INSERT INTO dbo.dim_patient VALUES (1)",  "INSERT"),
        ("UPDATE dbo.dim_patient SET col = 1",      "UPDATE"),
        ("TRUNCATE TABLE dbo.dim_patient",          "TRUNCATE"),
        ("EXEC sp_who",                             "EXEC"),
        ("ALTER TABLE dbo.dim_patient ADD col INT", "ALTER"),
        ("CREATE TABLE dbo.evil (id INT)",          "CREATE"),
    ])
    def test_dangerous_statements_are_blocked(self, sql, keyword):
        from myfgm_sql_mcp_server import run_query
        result = json.loads(run_query(sql))
        assert "error" in result and "Blocked" in result["error"], \
            f"'{keyword}' should have been blocked"