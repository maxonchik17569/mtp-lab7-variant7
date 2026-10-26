"""Тесты параметризованных запросов к библиотеке."""

import sqlite3
import unittest

from lab7.db import connect, init_schema
from lab7.queries import (
    add_author,
    add_book,
    all_books,
    available_books,
    books_by_author,
)


class QueryTests(unittest.TestCase):
    """Проверки модуля ``lab7.queries``."""

    def setUp(self) -> None:
        """Создать схему и двух авторов."""
        self.conn = connect()
        init_schema(self.conn)
        self.alice = add_author(self.conn, "alice")
        self.bob = add_author(self.conn, "bob")

    def tearDown(self) -> None:
        """Закрыть соединение."""
        self.conn.close()

    def test_add_author_returns_identifier(self) -> None:
        """Вставка автора возвращает целочисленный id."""
        author_id = add_author(self.conn, "carol")
        self.assertIsInstance(author_id, int)
        row = self.conn.execute(
            "SELECT name FROM authors WHERE id = ?", (author_id,)
        ).fetchone()
        self.assertEqual(row["name"], "carol")

    def test_add_author_rejects_duplicate(self) -> None:
        """Повторное имя автора нарушает UNIQUE."""
        with self.assertRaises(sqlite3.IntegrityError):
            add_author(self.conn, "alice")

    def test_add_book_uses_defaults(self) -> None:
        """Книга получает год NULL, один экземпляр и доступность."""
        book_id = add_book(self.conn, "Dune", self.alice)
        books = all_books(self.conn)
        self.assertEqual(len(books), 1)
        self.assertEqual(
            books[0],
            {
                "id": book_id,
                "title": "Dune",
                "author_id": self.alice,
                "year": None,
                "total_copies": 1,
                "available": True,
            },
        )

    def test_all_books_keeps_insertion_order(self) -> None:
        """Список всех книг упорядочен по идентификатору."""
        first = add_book(self.conn, "Dune", self.alice)
        second = add_book(self.conn, "Solaris", self.bob)
        self.assertEqual(
            [book["id"] for book in all_books(self.conn)],
            [first, second],
        )

    def test_books_by_author_filters_rows(self) -> None:
        """Выборка по автору не содержит чужих книг."""
        first = add_book(self.conn, "Dune", self.alice)
        add_book(self.conn, "Solaris", self.bob)
        third = add_book(self.conn, "Emma", self.alice, year=1815)
        books = books_by_author(self.conn, self.alice)
        self.assertEqual(
            [book["id"] for book in books],
            [first, third],
        )
        self.assertTrue(
            all(book["author_id"] == self.alice for book in books)
        )

    def test_books_by_unknown_author_is_empty(self) -> None:
        """Неизвестный автор даёт пустой список."""
        self.assertEqual(books_by_author(self.conn, 999), [])

    def test_available_books_excludes_borrowed(self) -> None:
        """Выборка доступных книг учитывает флаг available."""
        available = add_book(self.conn, "Dune", self.alice)
        add_book(
            self.conn,
            "Solaris",
            self.bob,
            available=False,
        )
        self.assertEqual(
            [book["id"] for book in available_books(self.conn)],
            [available],
        )

    def test_available_books_are_sorted_by_title(self) -> None:
        """Доступные книги сортируются по названию."""
        add_book(self.conn, "Solaris", self.bob)
        add_book(self.conn, "Dune", self.alice)
        self.assertEqual(
            [book["title"] for book in available_books(self.conn)],
            ["Dune", "Solaris"],
        )

    def test_quoted_values_are_stored_literally(self) -> None:
        """Кавычки и SQL-фрагменты остаются данными, а не кодом."""
        title = "Robert'); DROP TABLE books; --"
        author = add_author(self.conn, "O'Brien")
        book_id = add_book(self.conn, title, author)
        books = all_books(self.conn)
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0]["id"], book_id)
        self.assertEqual(books[0]["title"], title)
        names = self.conn.execute(
            "SELECT name FROM authors WHERE id = ?", (author,)
        ).fetchone()
        self.assertEqual(names["name"], "O'Brien")

    def test_add_book_with_unknown_author_raises(self) -> None:
        """Внешний ключ не даёт вставить книгу без автора."""
        with self.assertRaises(sqlite3.IntegrityError):
            add_book(self.conn, "Ghost book", 999)
        self.assertEqual(all_books(self.conn), [])

    def test_unavailable_flag_is_boolean(self) -> None:
        """Флаг доступности возвращается как bool."""
        add_book(
            self.conn,
            "Dune",
            self.alice,
            available=False,
        )
        self.assertIs(all_books(self.conn)[0]["available"], False)


if __name__ == "__main__":
    unittest.main()
