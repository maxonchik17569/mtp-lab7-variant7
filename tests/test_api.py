"""Тесты REST-интерфейса на FastAPI и SQLAlchemy."""

import unittest
from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from lab7.api import Base, create_app, get_session


class ApiTests(unittest.TestCase):
    """Проверки модуля ``lab7.api``."""

    def setUp(self) -> None:
        """Создать общую in-memory базу и тестовый клиент."""
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )
        self.app = create_app(self.session_factory)

        def override_session() -> Iterator[Session]:
            """Выдать сессию, привязанную к тестовой базе."""
            session = self.session_factory()
            try:
                yield session
            finally:
                session.close()

        self.app.dependency_overrides[get_session] = override_session
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        """Закрыть клиент и освободить движок."""
        self.client.close()
        self.engine.dispose()

    def test_empty_catalogue_returns_empty_list(self) -> None:
        """Без книг GET /books возвращает пустой массив."""
        response = self.client.get("/books")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_create_book_returns_201_and_location(self) -> None:
        """POST /books сохраняет книгу и возвращает её представление."""
        response = self.client.post(
            "/books",
            json={
                "title": "Dune",
                "author": "Frank Herbert",
                "year": 1965,
            },
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertIsInstance(body["id"], int)
        self.assertEqual(body["title"], "Dune")
        self.assertEqual(body["author"], "Frank Herbert")
        self.assertEqual(body["year"], 1965)
        self.assertIs(body["available"], True)
        self.assertEqual(len(self.client.get("/books").json()), 1)

    def test_get_book_by_id(self) -> None:
        """Созданная книга доступна по идентификатору."""
        created = self.client.post(
            "/books",
            json={"title": "Solaris", "author": "Stanislaw Lem"},
        ).json()
        response = self.client.get(f"/books/{created['id']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), created)

    def test_get_unknown_book_returns_404(self) -> None:
        """Неизвестный идентификатор даёт 404."""
        response = self.client.get("/books/999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Book not found")

    def test_list_books_is_sorted_by_id(self) -> None:
        """Список книг упорядочен по возрастанию идентификатора."""
        for title in ("Dune", "Solaris", "Emma"):
            self.client.post(
                "/books",
                json={"title": title, "author": "author"},
            )
        titles = [
            book["title"] for book in self.client.get("/books").json()
        ]
        self.assertEqual(titles, ["Dune", "Solaris", "Emma"])

    def test_create_book_validates_payload(self) -> None:
        """Пустые поля и неверный год отклоняются Pydantic."""
        response = self.client.post(
            "/books",
            json={"title": "", "author": "", "year": 3000},
        )
        self.assertEqual(response.status_code, 422)

    def test_create_unavailable_book(self) -> None:
        """Флаг available можно задать при создании."""
        response = self.client.post(
            "/books",
            json={
                "title": "Rare book",
                "author": "collector",
                "available": False,
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertIs(response.json()["available"], False)

    def test_delete_book_returns_204(self) -> None:
        """DELETE удаляет книгу и не возвращает тело."""
        created = self.client.post(
            "/books",
            json={"title": "Dune", "author": "Frank Herbert"},
        ).json()
        response = self.client.delete(f"/books/{created['id']}")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(self.client.get("/books").json(), [])

    def test_delete_unknown_book_returns_404(self) -> None:
        """Удаление неизвестной книги даёт 404."""
        response = self.client.delete("/books/999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Book not found")

    def test_data_survives_between_requests(self) -> None:
        """StaticPool сохраняет данные между сессиями зависимостей."""
        self.client.post(
            "/books",
            json={"title": "Dune", "author": "Frank Herbert"},
        )
        first = self.client.get("/books").json()
        second = self.client.get("/books").json()
        self.assertEqual(first, second)
        self.assertEqual(len(second), 1)


if __name__ == "__main__":
    unittest.main()
