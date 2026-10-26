"""Экспорт результатов SQL-запросов в CSV-файлы."""

import csv
import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path

Params = Sequence[object] | Mapping[str, object]

_BOOKS_QUERY = (
    "SELECT id, title, author_id, year, available "
    "FROM books ORDER BY id"
)


def export_query(
    conn: sqlite3.Connection,
    sql: str,
    params: Params = (),
    path: str | Path = "export.csv",
) -> int:
    """Выполнить запрос и записать результат в CSV с заголовками.

    Файл создаётся только после успешного выполнения запроса.
    Возвращается количество записанных строк без заголовка.
    """
    cursor = conn.execute(sql, params)
    if cursor.description is None:
        raise ValueError("query must return rows")
    header = [column[0] for column in cursor.description]
    rows = cursor.fetchall()

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for row in rows:
            writer.writerow([value for value in row])
    return len(rows)


def export_books(
    conn: sqlite3.Connection,
    path: str | Path,
) -> int:
    """Выгрузить таблицу книг в CSV и вернуть число строк."""
    return export_query(conn, _BOOKS_QUERY, (), path)
