"""
bd.py - pyodbc connection factory for WoundCareDB
"""
import os
from contextlib import contextmanager
import pyodbc
from dotenv import load_dotenv
load_dotenv()

def build_connection_string() -> str:
    driver   = os.getenv("MSSQL_DRIVER", "ODBC Driver 17 for SQL Server")
    server   = os.getenv("MSSQL_SERVER", "localhost")
    port     = os.getenv("MSSQL_PORT", "")
    database = os.getenv("MSSQL_DATABASE", "master")
    username = os.getenv("MSSQL_USERNAME", "")
    password = os.getenv("MSSQL_PASSWORD", "")
    trust    = os.getenv("MSSQL_TRUST_SERVER_CERT", "no")

    server_str = f"{server},{port}" if port else server

    if username and password:
        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={server_str};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"TrustServerCertificate={trust};"
        )
    else:
        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={server_str};"
            f"DATABASE={database};"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate={trust};"
        )
@contextmanager
def get_connection():
    """
    open pyodbc connection and close it when done.
    """
    conn = pyodbc.connect(build_connection_string(), timeout=30)
    try:
        yield conn
    finally:
        conn.close()
def rows_to_dicts(cursor) -> List[dict]:
    """
        Convert cursor rows to a list of dicts using column names.
    """
    columns = [col[0] for col in cursor.description]
    return[dict(zip(columns, row)) for row in cursor.fetchall()]