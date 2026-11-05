import sqlite3
from datetime import datetime
from threading import Lock

DB_PATH = "support.db"
COLUMNS = ["id", "user_id", "message", "status", "created_at"]

_lock = Lock()


def get_connection():
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with _lock:
        connection = get_connection()
        try:
            existing = [
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(specialist_requests)"
                ).fetchall()
            ]
            if existing and existing != COLUMNS:
                connection.execute("DROP TABLE specialist_requests")

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS specialist_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.commit()
        finally:
            connection.close()


def add_request(user_id, message):
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _lock:
        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO specialist_requests (user_id, message, status, created_at)
                VALUES (?, ?, 'open', ?)
                """,
                (user_id, message, created_at),
            )
            connection.commit()
            return cursor.lastrowid
        finally:
            connection.close()


def list_requests(status=None, limit=20):
    with _lock:
        connection = get_connection()
        try:
            if status:
                rows = connection.execute(
                    """
                    SELECT * FROM specialist_requests
                    WHERE status = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (status, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM specialist_requests
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()


def get_request(request_id):
    with _lock:
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT * FROM specialist_requests WHERE id = ?",
                (request_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            connection.close()


def set_status(request_id, status):
    with _lock:
        connection = get_connection()
        try:
            cursor = connection.execute(
                "UPDATE specialist_requests SET status = ? WHERE id = ?",
                (status, request_id),
            )
            connection.commit()
            return cursor.rowcount > 0
        finally:
            connection.close()
