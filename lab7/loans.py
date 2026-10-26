"""Выдача и возврат книг с явными транзакциями SQLite."""

import sqlite3


class BookUnavailable(Exception):
    """Книга не найдена или уже выдана читателю."""


class LoanNotFound(Exception):
    """Выдача с указанным идентификатором не существует."""


class LoanAlreadyReturned(Exception):
    """Книга по этой выдаче уже возвращена."""


def borrow_book(
    conn: sqlite3.Connection,
    book_id: int,
    reader: str,
) -> int:
    """Выдать доступную книгу читателю и вернуть id выдачи.

    Транзакция начинается с ``BEGIN IMMEDIATE``, чтобы проверка
    доступности и запись выдачи были атомарными. Любая ошибка
    откатывает и вставку, и обновление книги.
    """
    name = reader.strip()
    if not name:
        raise ValueError("reader must not be empty")

    conn.execute("BEGIN IMMEDIATE")
    try:
        book = conn.execute(
            "SELECT available FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()
        if book is None or not book["available"]:
            raise BookUnavailable(f"book {book_id} is unavailable")

        cursor = conn.execute(
            "INSERT INTO loans (book_id, reader) VALUES (?, ?)",
            (book_id, name),
        )
        loan_id = int(cursor.lastrowid)

        updated = conn.execute(
            "UPDATE books SET available = 0 "
            "WHERE id = ? AND available = 1",
            (book_id,),
        )
        if updated.rowcount != 1:
            raise BookUnavailable(f"book {book_id} is unavailable")

        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    return loan_id


def return_book(conn: sqlite3.Connection, loan_id: int) -> None:
    """Вернуть книгу по выдаче и снова сделать её доступной."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        loan = conn.execute(
            "SELECT book_id, returned_at FROM loans WHERE id = ?",
            (loan_id,),
        ).fetchone()
        if loan is None:
            raise LoanNotFound(f"loan {loan_id} not found")
        if loan["returned_at"] is not None:
            raise LoanAlreadyReturned(f"loan {loan_id} is closed")

        closed = conn.execute(
            "UPDATE loans SET returned_at = CURRENT_TIMESTAMP "
            "WHERE id = ? AND returned_at IS NULL",
            (loan_id,),
        )
        if closed.rowcount != 1:
            raise LoanAlreadyReturned(f"loan {loan_id} is closed")

        conn.execute(
            "UPDATE books SET available = 1 WHERE id = ?",
            (loan["book_id"],),
        )
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
