# Отчёт по лабораторной работе №7

Ким Максим Сергеевич, группа 221341, вариант 7.

Тема: работа с СУБД в Python — `sqlite3`, SQLAlchemy 2.0, FastAPI
и транзакции.

## Схема базы данных

Схема создаётся в `lab7/db.py` функцией `init_schema`. Используются
три таблицы и два индекса.

| Таблица   | Столбцы                                                        |
| --------- | -------------------------------------------------------------- |
| `authors` | `id` PK, `name` NOT NULL UNIQUE                                |
| `books`   | `id` PK, `title` NOT NULL, `author_id` FK, `year`,             |
|           | `total_copies` NOT NULL, `available` NOT NULL                  |
| `loans`   | `id` PK, `book_id` FK, `reader` NOT NULL, `borrowed_at`,       |
|           | `returned_at`                                                  |

Ограничения:

- `books.author_id` ссылается на `authors.id` с `ON DELETE RESTRICT`;
- `loans.book_id` ссылается на `books.id` с `ON DELETE RESTRICT`;
- `UNIQUE (title, author_id)` запрещает дубликат книги у одного автора;
- `CHECK (total_copies >= 1)` и `CHECK (available IN (0, 1))`
  защищают числовые поля;
- `connect` включает `PRAGMA foreign_keys = ON` для каждого соединения
  и задаёт `row_factory = sqlite3.Row`.

`init_schema` использует `CREATE TABLE IF NOT EXISTS`, поэтому повторный
вызов не удаляет данные. `table_names` возвращает только пользовательские
таблицы, отфильтровывая `sqlite_%`.

## Средняя сложность

### №7 — создание нескольких таблиц

Реализация: `lab7/db.py`.

Создаются `authors`, `books` и `loans` со связями «автор — книги» и
«книга — выдачи». Первичные ключи автоинкрементные, обязательные поля
помечены `NOT NULL`, уникальность автора и пары «название, автор»
закреплена на уровне схемы. Внешние ключи включены на уровне соединения,
а не только объявлены в DDL, поэтому SQLite действительно проверяет
ссылочную целостность.

### №3 — выборка данных из таблицы

Реализация: `lab7/queries.py`.

- `add_author` и `add_book` вставляют строки и возвращают `lastrowid`;
- `all_books` выбирает все книги в порядке `id`;
- `books_by_author` фильтрует по `author_id`;
- `available_books` оставляет только `available = 1` и сортирует по
  названию.

Все значения передаются через заполнители `?`; SQL-строка не собирается
из пользовательских данных. Строки `sqlite3.Row` преобразуются в
словари, а `available` — в `bool`. Тест с названием
`Robert'); DROP TABLE books; --` подтверждает, что кавычки остаются
данными.

### №9 — экспорт данных в CSV

Реализация: `lab7/csv_export.py`.

`export_query` выполняет произвольный SELECT, берёт заголовки из
`cursor.description`, затем пишет файл через `csv.writer` с
`encoding="utf-8"` и `newline=""`. Экранирование запятых, кавычек и
переводов строк выполняет модуль `csv`; вручную строки не склеиваются.
Файл создаётся только после успешного выполнения запроса, а каталог
назначения при необходимости создаётся. `export_books` — обёртка над
`export_query` для таблицы `books`, возвращает число строк.

## Повышенная сложность

### №7 — FastAPI + SQLAlchemy (REST)

Реализация: `lab7/api.py`.

Модель `Book` описана в стиле SQLAlchemy 2.0: `DeclarativeBase`,
`Mapped`, `mapped_column`. Схемы Pydantic `BookCreate` и `BookRead`
валидируют длину строк и диапазон года `0..2100`.

`create_app(session_factory)` собирает приложение и сохраняет фабрику
сессий в `app.state`. Зависимость `get_session` открывает сессию на
время запроса и закрывает её в `finally`; в тестах она переопределяется
через `dependency_overrides`. Маршруты:

| Метод  | Путь          | Результат                                  |
| ------ | ------------- | ------------------------------------------ |
| GET    | `/books`      | 200, список книг по возрастанию `id`       |
| GET    | `/books/{id}` | 200 или 404 `Book not found`               |
| POST   | `/books`      | 201, созданная книга                       |
| DELETE | `/books/{id}` | 204 без тела или 404                       |

Модульный `app` использует файл `lab7_api.db` (переопределяется
переменной `LAB7_API_DB`) и создаёт таблицы в lifespan при старте.
Запуск: `uvicorn lab7.api:app`.

### №5 — транзакции

Реализация: `lab7/loans.py`.

`borrow_book` начинает `BEGIN IMMEDIATE`, проверяет флаг доступности,
вставляет запись в `loans` и выставляет `books.available = 0`. Только
после обеих операций выполняется `COMMIT`. Если книга не найдена или
занята, возбуждается собственное исключение `BookUnavailable`, а
`ROLLBACK` возвращает базу в исходное состояние.

`return_book` в такой же транзакции находит выдачу, проверяет, что она
ещё открыта, записывает `returned_at = CURRENT_TIMESTAMP` и возвращает
`available = 1`. Для неизвестной выдачи используется `LoanNotFound`,
для повторного возврата — `LoanAlreadyReturned`.

Откат проверяется искусственным сбоем: тест создаёт SQLite-триггер,
который запрещает `UPDATE books`, и убеждается, что после исключения
нет ни новой выдачи, ни изменения доступности. Аналогичный тест для
возврата проверяет, что `returned_at` остаётся `NULL`.

## Проверки

Все команды выполнялись из корня репозитория на Python 3.13.

### Демонстрация

```text
$ uv run --with sqlalchemy --with fastapi --with httpx python -m lab7
Medium task 7: schema
  tables -> ['authors', 'books', 'loans']
Medium task 3: selection
  all_books -> ['Dune', 'Emma', 'Solaris']
  books_by_author(alice) -> ['Dune', 'Emma']
  available_books -> ['Dune', 'Emma', 'Solaris']
Medium task 9: CSV export
  exported rows -> 3
  header -> id,title,author_id,year,available
  first data row -> 1,Dune,1,1965,1
Advanced task 5: transactions
  borrowed loan_id -> 1
  second borrow rejected -> book 1 is unavailable
  returned -> available again
  second return rejected -> loan 1 is closed
Advanced task 7: FastAPI + SQLAlchemy
  POST /books -> 201
  GET /books -> [{'title': 'Dune', 'author': 'Frank Herbert', 'year': 1965, 'available': True, 'id': 1}]
  DELETE /books/1 -> 204
```

### Тесты

```text
$ uv run --with sqlalchemy --with fastapi --with httpx --with flake8 \
    python -m unittest discover -s tests -v
...
----------------------------------------------------------------------
Ran 50 tests in 0.168s

OK
```

Распределение тестов:

| Модуль                | Тестов |
| --------------------- | ------ |
| `tests/test_api.py`   | 10     |
| `tests/test_csv_export.py` | 8 |
| `tests/test_db.py`    | 11     |
| `tests/test_loans.py` | 10     |
| `tests/test_queries.py` | 11   |

Временные файлы создаются через `tempfile.TemporaryDirectory` и
удаляются автоматически; файловых баз в репозитории не остаётся.

### Стиль кода

```text
$ uv run --with flake8 flake8 lab7 tests
```

Вывод пуст, код возврата `0`: flake8 с `max-line-length = 79` из
`setup.cfg` нарушений не нашёл.

### CI

`.github/workflows/python-checks.yml` на Python 3.13 устанавливает
`requirements-dev.txt`, запускает `flake8 lab7 tests`,
`python -m compileall -q lab7 tests` и
`python -m unittest discover -s tests -v`.
