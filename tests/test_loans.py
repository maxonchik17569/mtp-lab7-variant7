"""Тесты выдачи и возврата книг с транзакциями."""

import sqlite3
import unittest

from lab7.db import connect, init_schema
from lab7.loans import (
    BookUnavailable,
    LoanAlreadyReturned,
    LoanNotFound,
    borrow_book,
    return_book,
)
from lab7.queries import add_author, add_book


class LoanTests(unittest.TestCase):
    """Проверки модуля ``lab7.loans``."""

    def setUp(self) -> None:
        """Создать схему, автора и доступную книгу."""
        self.conn = connect()
        init_schema(self.conn)
        author_id = add_author(self.conn, "alice")
        self.book_id = add_book(self.conn, "Dune", author_id)

    def tearDown(self) -> None:
        """Закрыть соединение."""
        self.conn.close()

    def test_borrow_marks_book_unavailable(self) -> None:
        """Выдача создаёт запись и снимает книгу с полки."""
        loan_id = borrow_book(self.conn, self.book_id, "reader-1")
        row = self.conn.execute(
            "SELECT book_id, reader, returned_at "
            "FROM loans WHERE id = ?",
            (loan_id,),
        ).fetchone()
        self.assertEqual(row["book_id"], self.book_id)
        self.assertEqual(row["reader"], "reader-1")
        self.assertIsNone(row["returned_at"])
        self.assertEqual(self._available(), 0)

    def test_borrow_twice_raises(self) -> None:
        """Занятую книгу нельзя выдать повторно."""
        borrow_book(self.conn, self.book_id, "reader-1")
        with self.assertRaises(BookUnavailable):
            borrow_book(self.conn, self.book_id, "reader-2")
        self.assertEqual(self._loan_count(), 1)

    def test_borrow_unknown_book_raises(self) -> None:
        """Несуществующая книга даёт BookUnavailable."""
        with self.assertRaises(BookUnavailable):
            borrow_book(self.conn, 999, "reader-1")
        self.assertEqual(self._loan_count(), 0)

    def test_borrow_empty_reader_raises(self) -> None:
        """Пустое имя читателя отклоняется до транзакции."""
        with self.assertRaises(ValueError):
            borrow_book(self.conn, self.book_id, "   ")
        self.assertEqual(self._loan_count(), 0)
        self.assertEqual(self._available(), 1)

    def test_return_restores_availability(self) -> None:
        """Возврат заполняет дату и снова делает книгу доступной."""
        loan_id = borrow_book(self.conn, self.book_id, "reader-1")
        return_book(self.conn, loan_id)
        row = self.conn.execute(
            "SELECT returned_at FROM loans WHERE id = ?",
            (loan_id,),
        ).fetchone()
        self.assertIsNotNone(row["returned_at"])
        self.assertEqual(self._available(), 1)

    def test_return_unknown_loan_raises(self) -> None:
        """Неизвестная выдача не меняет состояние базы."""
        with self.assertRaises(LoanNotFound):
            return_book(self.conn, 999)
        self.assertEqual(self._available(), 1)

    def test_return_twice_raises(self) -> None:
        """Повторный возврат отклоняется без изменения данных."""
        loan_id = borrow_book(self.conn, self.book_id, "reader-1")
        return_book(self.conn, loan_id)
        with self.assertRaises(LoanAlreadyReturned):
            return_book(self.conn, loan_id)
        self.assertEqual(self._available(), 1)

    def test_book_can_be_borrowed_again_after_return(self) -> None:
        """После возврата книгу можно выдать следующему читателю."""
        first = borrow_book(self.conn, self.book_id, "reader-1")
        return_book(self.conn, first)
        second = borrow_book(self.conn, self.book_id, "reader-2")
        self.assertNotEqual(first, second)
        self.assertEqual(self._loan_count(), 2)
        self.assertEqual(self._available(), 0)

    def test_borrow_rolls_back_when_book_update_fails(self) -> None:
        """Сбой обновления книги откатывает вставку выдачи."""
        self.conn.execute(
            "CREATE TRIGGER fail_borrow_update "
            "BEFORE UPDATE ON books "
            "WHEN NEW.available = 0 "
            "BEGIN SELECT RAISE(ABORT, 'update blocked'); END"
        )
        with self.assertRaises(sqlite3.DatabaseError):
            borrow_book(self.conn, self.book_id, "reader-1")
        self.assertEqual(self._loan_count(), 0)
        self.assertEqual(self._available(), 1)

    def test_return_rolls_back_when_book_update_fails(self) -> None:
        """Сбой обновления книги откатывает отметку возврата."""
        loan_id = borrow_book(self.conn, self.book_id, "reader-1")
        self.conn.execute(
            "CREATE TRIGGER fail_return_update "
            "BEFORE UPDATE ON books "
            "WHEN NEW.available = 1 "
            "BEGIN SELECT RAISE(ABORT, 'update blocked'); END"
        )
        with self.assertRaises(sqlite3.DatabaseError):
            return_book(self.conn, loan_id)
        row = self.conn.execute(
            "SELECT returned_at FROM loans WHERE id = ?",
            (loan_id,),
        ).fetchone()
        self.assertIsNone(row["returned_at"])
        self.assertEqual(self._available(), 0)

    def _available(self) -> int:
        """Вернуть флаг доступности тестовой книги."""
        row = self.conn.execute(
            "SELECT available FROM books WHERE id = ?",
            (self.book_id,),
        ).fetchone()
        return int(row["available"])

    def _loan_count(self) -> int:
        """Вернуть число выдач в базе."""
        return int(
            self.conn.execute(
                "SELECT COUNT(*) FROM loans"
            ).fetchone()[0]
        )


if __name__ == "__main__":
    unittest.main()
