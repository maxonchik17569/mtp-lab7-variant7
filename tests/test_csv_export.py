"""Тесты экспорта данных в CSV."""

import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path

from lab7.csv_export import export_books, export_query
from lab7.db import connect, init_schema
from lab7.queries import add_author, add_book


class CsvExportTests(unittest.TestCase):
    """Проверки модуля ``lab7.csv_export``."""

    def setUp(self) -> None:
        """Создать временный каталог, схему и данные."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.conn = connect()
        self.addCleanup(self.conn.close)
        init_schema(self.conn)
        self.author_id = add_author(self.conn, "alice")
        add_book(self.conn, "Dune", self.author_id, year=1965)
        add_book(self.conn, "Solaris", self.author_id, year=1961)

    def test_export_query_writes_header_and_rows(self) -> None:
        """CSV содержит заголовки и все выбранные строки."""
        target = self.path / "titles.csv"
        count = export_query(
            self.conn,
            "SELECT id, title FROM books ORDER BY id",
            (),
            target,
        )
        self.assertEqual(count, 2)
        with target.open(
            encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.reader(handle))
        self.assertEqual(rows[0], ["id", "title"])
        self.assertEqual(
            rows[1:],
            [["1", "Dune"], ["2", "Solaris"]],
        )

    def test_export_query_escapes_special_characters(self) -> None:
        """Запятые, кавычки и переводы строк экранируются."""
        title = 'Dune, "Special"\nEdition'
        add_book(self.conn, title, self.author_id)
        target = self.path / "special.csv"
        export_query(
            self.conn,
            "SELECT title FROM books WHERE title = ?",
            (title,),
            target,
        )
        raw = target.read_text(encoding="utf-8")
        self.assertIn('"Dune, ""Special""', raw)
        with target.open(
            encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.reader(handle))
        self.assertEqual(rows[1], [title])

    def test_export_query_writes_utf8(self) -> None:
        """Кириллица сохраняется в кодировке UTF-8."""
        target = self.path / "utf8.csv"
        export_query(
            self.conn,
            "SELECT 'Война и мир' AS title",
            (),
            target,
        )
        payload = target.read_bytes()
        self.assertIn("Война и мир".encode("utf-8"), payload)
        with target.open(
            encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.reader(handle))
        self.assertEqual(rows[0], ["title"])
        self.assertEqual(rows[1], ["Война и мир"])

    def test_export_query_accepts_named_parameters(self) -> None:
        """Именованные параметры передаются без изменений."""
        target = self.path / "named.csv"
        count = export_query(
            self.conn,
            "SELECT title FROM books WHERE year = :year",
            {"year": 1961},
            target,
        )
        self.assertEqual(count, 1)
        with target.open(
            encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.reader(handle))
        self.assertEqual(rows[1], ["Solaris"])

    def test_export_query_empty_result_keeps_header(self) -> None:
        """Пустая выборка оставляет только строку заголовков."""
        target = self.path / "empty.csv"
        count = export_query(
            self.conn,
            "SELECT id, title FROM books WHERE id < 0",
            (),
            target,
        )
        self.assertEqual(count, 0)
        with target.open(
            encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.reader(handle))
        self.assertEqual(rows, [["id", "title"]])

    def test_export_query_invalid_sql_creates_no_file(self) -> None:
        """Ошибка SQL возникает до создания файла."""
        target = self.path / "missing.csv"
        with self.assertRaises(sqlite3.OperationalError):
            export_query(
                self.conn,
                "SELECT * FROM missing_table",
                (),
                target,
            )
        self.assertFalse(target.exists())

    def test_export_books_returns_rows_and_columns(self) -> None:
        """Экспорт книг выгружает все столбцы таблицы books."""
        target = self.path / "books.csv"
        count = export_books(self.conn, target)
        self.assertEqual(count, 2)
        with target.open(
            encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.reader(handle))
        self.assertEqual(
            rows[0],
            [
                "id",
                "title",
                "author_id",
                "year",
                "available",
            ],
        )
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1][1], "Dune")
        self.assertEqual(rows[1][3], "1965")

    def test_export_books_creates_file_in_new_directory(self) -> None:
        """Каталог назначения создаётся автоматически."""
        target = self.path / "nested" / "books.csv"
        count = export_books(self.conn, target)
        self.assertEqual(count, 2)
        self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()
