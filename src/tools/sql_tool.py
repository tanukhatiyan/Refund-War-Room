"""
Refund War Room - Read-Only SQL Tool.
Executes queries against SQLite with strict read-only enforcement and deterministic result hashing.
"""
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Dict, Any, List

from src.config import DB_PATH

DISALLOWED_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "REPLACE", "ATTACH", "DETACH", "VACUUM", "REINDEX", "EXEC", "EXECUTE"
}


def compute_result_hash(query: str, rows: List[Any], columns: List[str]) -> str:
    """Computes a deterministic SHA-256 hash of query and sorted canonical results."""
    canonical_payload = {
        "query": query.strip().lower(),
        "columns": columns,
        "rows": rows
    }
    encoded = json.dumps(canonical_payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def is_safe_read_only_query(query: str) -> bool:
    """Validates that query is strictly a read-only SELECT or WITH statement."""
    # Check for multiple statements separated by semicolon
    cleaned = re.sub(r"--[^\n]*", "", query)  # strip comments
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)
    statements = [s.strip() for s in cleaned.split(";") if s.strip()]
    if len(statements) != 1:
        return False

    stmt = statements[0].strip()
    # Check initial keyword
    if not re.match(r"^(SELECT|WITH)\b", stmt, re.IGNORECASE):
        return False

    # Tokenize and check for mutation keywords
    tokens = set(re.findall(r"\b[A-Z_]+\b", stmt.upper()))
    if tokens.intersection(DISALLOWED_KEYWORDS):
        return False

    return True


def run_sql(query: str, db_path: Path = DB_PATH) -> Dict[str, Any]:
    """Executes a read-only SQL query and returns rows, columns, count, and result hash."""
    if not is_safe_read_only_query(query):
        return {
            "status": "error",
            "error": "Query blocked by Security Guardrail: Only read-only SELECT statements are allowed.",
            "query": query,
            "row_count": 0,
            "rows": [],
            "result_hash": None
        }

    try:
        # Open in URI read-only mode if supported or standard connection
        uri_path = f"file:{Path(db_path).resolve().as_posix()}?mode=ro"
        conn = sqlite3.connect(uri_path, uri=True)
    except Exception:
        # Fallback to standard connection
        conn = sqlite3.connect(str(db_path))

    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(query)
        raw_rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = [list(row) for row in raw_rows]
        result_hash = compute_result_hash(query, rows, columns)

        return {
            "status": "success",
            "query": query,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "result_hash": result_hash
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"SQL Execution Error: {str(e)}",
            "query": query,
            "row_count": 0,
            "rows": [],
            "result_hash": None
        }
    finally:
        conn.close()
