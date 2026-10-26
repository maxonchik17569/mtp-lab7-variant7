"""Демонстрация всех заданий варианта на in-memory базе."""

import sqlite3
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lab7.api import Base, create_app
from lab7.csv_export import export_books
from lab7.db import connect, init_schema, table_names
from lab7.loans import (
    BookUnavailable,
    LoanAlreadyReturned,
    borrow_book,
    return_book,
)
from lab7.queries import (
    add_author,
    add_book,
    all_books,
    available_books,
    books_by_author,
)


def main() -> None:
    """Выполнить демонстрацию без сети и без запуска uvicorn."""
    conn = connect()
    try:
        init_schema(conn)
        _show_tables(conn)
        _show_queries(conn)
        _show_csv(conn)
        _show_loans(conn)
    finally:
        conn.close()
    _show_api()


def _show_tables(conn: sqlite3.Connection) -> None:
    """Показать таблицы, созданные в задании №7."""
    print("Medium task 7: schema")
    print(f"  tables -> {table_names(conn)}")


def _show_queries(conn: sqlite3.Connection) -> None:
    """Показать выборки из задания №3."""
    alice = add_author(conn, "alice")
    bob = add_author(conn, "bob")
    add_book(conn, "Dune", alice, year=1965)
    add_book(conn, "Emma", alice, year=1815)
    add_book(conn, "Solaris", bob, year=1961)

    print("Medium task 3: selection")
    print(f"  all_books -> {[book['title'] for book in all_books(conn)]}")
    print(
        "  books_by_author(alice) -> "
        f"{[book['title'] for book in books_by_author(conn, alice)]}"
    )
    print(
        "  available_books -> "
        f"{[book['title'] for book in available_books(conn)]}"
    )


def _show_csv(conn: sqlite3.Connection) -> None:
    """Показать экспорт в CSV из задания №9."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "books.csv"
        count = export_books(conn, path)
        text = path.read_text(encoding="utf-8")
        print("Medium task 9: CSV export")
        print(f"  exported rows -> {count}")
        print(f"  header -> {text.splitlines()[0]}")
        print(f"  first data row -> {text.splitlines()[1]}")


def _show_loans(conn: sqlite3.Connection) -> None:
    """Показать транзакции выдачи и возврата из задания №5."""
    print("Advanced task 5: transactions")
    books = available_books(conn)
    book_id = int(books[0]["id"])
    loan_id = borrow_book(conn, book_id, "reader-1")
    print(f"  borrowed loan_id -> {loan_id}")
    try:
        borrow_book(conn, book_id, "reader-2")
    except BookUnavailable as error:
        print(f"  second borrow rejected -> {error}")
    return_book(conn, loan_id)
    print("  returned -> available again")
    try:
        return_book(conn, loan_id)
    except LoanAlreadyReturned as error:
        print(f"  second return rejected -> {error}")


def _show_api() -> None:
    """Показать REST-интерфейс из задания №7 через TestClient."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = create_app(factory)
    try:
        with TestClient(app) as client:
            created = client.post(
                "/books",
                json={
                    "title": "Dune",
                    "author": "Frank Herbert",
                    "year": 1965,
                },
            )
            print("Advanced task 7: FastAPI + SQLAlchemy")
            print(f"  POST /books -> {created.status_code}")
            print(f"  GET /books -> {client.get('/books').json()}")
            book_id = created.json()["id"]
            deleted = client.delete(f"/books/{book_id}")
            print(f"  DELETE /books/{book_id} -> {deleted.status_code}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
