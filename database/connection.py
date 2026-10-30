"""Database connection manager for SQLite.
Provides safe connection handling, row-factory mappings, and transaction management.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
import config


def get_db_path(custom_path: Optional[Path] = None) -> Path:
    """Return the active SQLite database path."""
    return Path(custom_path) if custom_path else config.DATABASE_PATH


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Establish and configure a connection to the SQLite database.
    
    Enforces foreign keys, WAL mode for concurrency, and dict-like row access.
    """
    path = get_db_path(db_path)
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(path), timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    # WAL mode improves performance and concurrency in Streamlit's multi-threaded model
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


@contextmanager
def get_db_cursor(db_path: Optional[Path] = None) -> Generator[sqlite3.Cursor, None, None]:
    """Context manager for database transactions.
    
    Automatically commits if all operations succeed, or rolls back if an exception occurs.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
