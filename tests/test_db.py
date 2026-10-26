"""Тесты подключения и схемы базы данных."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from lab7.db import connect, init_schema, table_names


class DatabaseTests(unittest.TestCase):
    """Проверки модуля ``lab7.db``."""

    def setUp(self) -> None:
        """Создать пустую in-memory базу и схему."""
        self.conn = connect()
        init_schema(self.conn)

    def tearDown(self) -> None:
        """Закрыть соединение."""
        self.conn.close()

    def test_connect_uses_row_factory(self) -> None:
        """Строки доступны и по индексу, и по имени столбца."""
        row = self.conn.execute("SELECT 1 AS value").fetchone()
        self.assertIsInstance(row, sqlite3.Row)
        self.assertEqual(row["value"], 1)

    def test_foreign_keys_are_enabled(self) -> None:
        """PRAGMA foreign_keys включён для каждого соединения."""
        value = self.conn.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0]
        self.assertEqual(value, 1)

    def test_schema_contains_required_tables(self) -> None:
        """Схема содержит авторов, книги и выдачи."""
        self.assertEqual(
            table_names(self.conn),
            ["authors", "books", "loans"],
        )

    def test_init_schema_is_idempotent(self) -> None:
        """Повторная инициализация не разрушает данные."""
        self.conn.execute(
            "INSERT INTO authors (name) VALUES (?)", ("alice",)
        )
        init_schema(self.conn)
        count = self.conn.execute(
            "SELECT COUNT(*) FROM authors"
        ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_author_name_is_unique(self) -> None:
        """UNIQUE не позволяет завести двух авторов с одним именем."""
        self.conn.execute(
            "INSERT INTO authors (name) VALUES (?)", ("alice",)
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO authors (name) VALUES (?)", ("alice",)
            )

    def test_book_title_is_unique_per_author(self) -> None:
        """UNIQUE(title, author_id) запрещает дубль у одного автора."""
        author_id = self._insert_author("alice")
        self._insert_book(author_id, "Dune")
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_book(author_id, "Dune")
        other_author = self._insert_author("bob")
        self._insert_book(other_author, "Dune")

    def test_book_requires_author(self) -> None:
        """Внешний ключ запрещает книгу без существующего автора."""
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_book(999, "Ghost book")

    def test_book_title_is_not_null(self) -> None:
        """NOT NULL защищает обязательные поля книги."""
        author_id = self._insert_author("alice")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO books (title, author_id) VALUES (?, ?)",
                (None, author_id),
            )

    def test_loan_reader_is_not_null(self) -> None:
        """NOT NULL защищает имя читателя в выдаче."""
        author_id = self._insert_author("alice")
        book_id = self._insert_book(author_id, "Dune")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO loans (book_id, reader) VALUES (?, ?)",
                (book_id, None),
            )

    def test_file_database_persists_schema(self) -> None:
        """Файловая база сохраняет схему между соединениями."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "library.sqlite3"
            first = connect(path)
            try:
                init_schema(first)
                first.execute(
                    "INSERT INTO authors (name) VALUES (?)",
                    ("alice",),
                )
            finally:
                first.close()
            second = connect(path)
            try:
                self.assertEqual(
                    table_names(second),
                    ["authors", "books", "loans"],
                )
                count = second.execute(
                    "SELECT COUNT(*) FROM authors"
                ).fetchone()[0]
                self.assertEqual(count, 1)
            finally:
                second.close()

    def test_table_names_hides_sqlite_sequence(self) -> None:
        """Служебные таблицы SQLite не попадают в результат."""
        names = table_names(self.conn)
        self.assertNotIn("sqlite_sequence", names)

    def _insert_author(self, name: str) -> int:
        """Вставить автора и вернуть его идентификатор."""
        cursor = self.conn.execute(
            "INSERT INTO authors (name) VALUES (?)", (name,)
        )
        return int(cursor.lastrowid)

    def _insert_book(self, author_id: int, title: str) -> int:
        """Вставить книгу и вернуть её идентификатор."""
        cursor = self.conn.execute(
            "INSERT INTO books (title, author_id) VALUES (?, ?)",
            (title, author_id),
        )
        return int(cursor.lastrowid)


if __name__ == "__main__":
    unittest.main()
