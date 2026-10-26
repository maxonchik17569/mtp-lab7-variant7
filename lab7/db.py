"""Подключение к SQLite и создание схемы библиотеки."""

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS authors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author_id INTEGER NOT NULL,
    year INTEGER,
    total_copies INTEGER NOT NULL DEFAULT 1 CHECK (total_copies >= 1),
    available INTEGER NOT NULL DEFAULT 1 CHECK (available IN (0, 1)),
    FOREIGN KEY (author_id) REFERENCES authors (id) ON DELETE RESTRICT,
    UNIQUE (title, author_id)
);

CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    reader TEXT NOT NULL,
    borrowed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    returned_at TEXT,
    FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_books_author ON books (author_id);
CREATE INDEX IF NOT EXISTS idx_loans_book ON loans (book_id);
"""


def connect(path: str | Path = ":memory:") -> sqlite3.Connection:
    """Открыть соединение SQLite с включёнными внешними ключами.

    Режим ``isolation_level=None`` оставляет управление транзакциями
    явным командам ``BEGIN``/``COMMIT``, которые используют функции
    выдачи и возврата книг.
    """
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Создать таблицы и индексы, если их ещё нет."""
    conn.executescript(SCHEMA)


def table_names(conn: sqlite3.Connection) -> list[str]:
    """Вернуть имена пользовательских таблиц без служебных SQLite."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()
    return [str(row["name"]) for row in rows]
