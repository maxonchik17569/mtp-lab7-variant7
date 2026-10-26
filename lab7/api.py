"""REST-интерфейс библиотеки на FastAPI и SQLAlchemy 2.0."""

import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Engine, String, create_engine, select
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)


class Base(DeclarativeBase):
    """Базовый класс декларативных моделей SQLAlchemy."""


class Book(Base):
    """Книга в каталоге REST-сервиса."""

    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    author: Mapped[str] = mapped_column(String(200), nullable=False)
    year: Mapped[int | None] = mapped_column(nullable=True)
    available: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )


class BookCreate(BaseModel):
    """Тело запроса на создание книги."""

    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=200)
    year: int | None = Field(default=None, ge=0, le=2100)
    available: bool = True


class BookRead(BookCreate):
    """Представление книги в ответах API."""

    id: int

    model_config = ConfigDict(from_attributes=True)


def get_session(request: Request) -> Iterator[Session]:
    """Открыть сессию из фабрики, сохранённой в состоянии приложения."""
    factory: sessionmaker[Session] = request.app.state.session_factory
    session = factory()
    try:
        yield session
    finally:
        session.close()


def create_app(
    session_factory: sessionmaker[Session],
    *,
    engine: Engine | None = None,
) -> FastAPI:
    """Собрать приложение с переданной фабрикой сессий."""

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        """Создать таблицы при старте приложения с файловой базой."""
        if engine is not None:
            Base.metadata.create_all(engine)
        yield

    app = FastAPI(
        title="Library API",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.session_factory = session_factory

    @app.get("/books", response_model=list[BookRead])
    def list_books(
        session: Annotated[Session, Depends(get_session)],
    ) -> list[Book]:
        """Вернуть все книги в порядке идентификатора."""
        statement = select(Book).order_by(Book.id)
        return list(session.scalars(statement))

    @app.get("/books/{book_id}", response_model=BookRead)
    def get_book(
        book_id: int,
        session: Annotated[Session, Depends(get_session)],
    ) -> Book:
        """Вернуть книгу по идентификатору или 404."""
        book = session.get(Book, book_id)
        if book is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )
        return book

    @app.post(
        "/books",
        response_model=BookRead,
        status_code=status.HTTP_201_CREATED,
    )
    def create_book(
        payload: BookCreate,
        session: Annotated[Session, Depends(get_session)],
    ) -> Book:
        """Создать книгу после валидации тела запроса."""
        book = Book(**payload.model_dump())
        session.add(book)
        session.commit()
        session.refresh(book)
        return book

    @app.delete(
        "/books/{book_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_book(
        book_id: int,
        session: Annotated[Session, Depends(get_session)],
    ) -> Response:
        """Удалить книгу или вернуть 404."""
        book = session.get(Book, book_id)
        if book is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )
        session.delete(book)
        session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


_DB_PATH = os.environ.get("LAB7_API_DB", "lab7_api.db")
_ENGINE = create_engine(
    f"sqlite+pysqlite:///{_DB_PATH}",
    connect_args={"check_same_thread": False},
)
_SESSION_FACTORY = sessionmaker(
    bind=_ENGINE,
    expire_on_commit=False,
)
app = create_app(_SESSION_FACTORY, engine=_ENGINE)
