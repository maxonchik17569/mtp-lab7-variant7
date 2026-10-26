"""Параметризованные запросы к таблицам авторов и книг."""

import sqlite3
from collections.abc import Sequence

Book = dict[str, object]

_BOOK_COLUMNS = (
    "id, title, author_id, year, total_copies, available"
)


def add_author(conn: sqlite3.Connection, name: str) -> int:
    """Добавить автора и вернуть его идентификатор."""
    cursor = conn.execute(
        "INSERT INTO authors (name) VALUES (?)",
        (name,),
    )
    return int(cursor.lastrowid)


def add_book(
    conn: sqlite3.Connection,
    title: str,
    author_id: int,
    year: int | None = None,
    total_copies: int = 1,
    available: bool = True,
) -> int:
    """Добавить книгу и вернуть её идентификатор."""
    cursor = conn.execute(
        "INSERT INTO books "
        "(title, author_id, year, total_copies, available) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            title,
            author_id,
            year,
            total_copies,
            int(available),
        ),
    )
    return int(cursor.lastrowid)


def books_by_author(
    conn: sqlite3.Connection,
    author_id: int,
) -> list[Book]:
    """Вернуть книги указанного автора в порядке добавления."""
    rows = conn.execute(
        f"SELECT {_BOOK_COLUMNS} FROM books "
        "WHERE author_id = ? ORDER BY id",
        (author_id,),
    ).fetchall()
    return _to_books(rows)


def all_books(conn: sqlite3.Connection) -> list[Book]:
    """Вернуть все книги в порядке добавления."""
    rows = conn.execute(
        f"SELECT {_BOOK_COLUMNS} FROM books ORDER BY id"
    ).fetchall()
    return _to_books(rows)


def available_books(conn: sqlite3.Connection) -> list[Book]:
    """Вернуть доступные книги, отсортированные по названию."""
    rows = conn.execute(
        f"SELECT {_BOOK_COLUMNS} FROM books "
        "WHERE available = 1 ORDER BY title, id"
    ).fetchall()
    return _to_books(rows)


def _to_books(rows: Sequence[sqlite3.Row]) -> list[Book]:
    """Преобразовать строки SQLite в словари с булевым флагом."""
    books: list[Book] = []
    for row in rows:
        books.append(
            {
                "id": int(row["id"]),
                "title": str(row["title"]),
                "author_id": int(row["author_id"]),
                "year": row["year"],
                "total_copies": int(row["total_copies"]),
                "available": bool(row["available"]),
            }
        )
    return books
