# Лабораторная работа №7

Ким Максим Сергеевич, группа 221341, вариант 7, лабораторная №7.

Тема работы: работа с СУБД в Python — стандартная библиотека `sqlite3`,
ORM SQLAlchemy 2.0, REST-интерфейс на FastAPI и транзакции.

## Задания варианта

**Средняя сложность:**

- №7 — создание нескольких таблиц (`lab7/db.py`)
- №9 — экспорт данных в CSV (`lab7/csv_export.py`)
- №3 — выборка данных из таблицы (`lab7/queries.py`)

**Повышенная сложность:**

- №7 — FastAPI + SQLAlchemy, REST (`lab7/api.py`)
- №5 — транзакции выдачи и возврата (`lab7/loans.py`)

## Клонирование

```bash
git clone https://github.com/maxonchik17569/mtp-lab7-variant7.git
cd mtp-lab7-variant7
```

## Запуск

Демонстрация всех заданий на in-memory базе данных, без сети и без
запуска uvicorn:

```bash
uv run --with sqlalchemy --with fastapi --with httpx python -m lab7
```

REST-сервис на файловой базе `lab7_api.db`:

```bash
uv run --with sqlalchemy --with fastapi --with uvicorn \
  uvicorn lab7.api:app --reload
```

## Проверки

```bash
uv run --with sqlalchemy --with fastapi --with httpx --with flake8 \
  python -m unittest discover -s tests -v
uv run --with flake8 flake8 lab7 tests
uv run --with sqlalchemy --with fastapi --with httpx python -m lab7
```

Зависимости для CI перечислены в `requirements-dev.txt`, настройки
стиля — в `setup.cfg`. Подробное описание выполнения — в
`docs/report.md`.

## Требования

- Python 3.13 или новее.
- [uv](https://docs.astral.sh/uv/) для запуска без ручной установки
  зависимостей.
- SQLAlchemy, FastAPI и httpx ставятся командами `uv run --with`.
- `flake8` ставится автоматически командой `uv run --with flake8`.
