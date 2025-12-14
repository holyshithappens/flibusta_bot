# План рефакторинга проекта Flibusta Bot

## 📊 АНАЛИЗ ПРОБЛЕМ И ПРИОРИТЕТЫ

### Матрица приоритетов

| Проблема | Сложность | Влияние | Приоритет | Оценка |
|----------|-----------|---------|-----------|--------|
| 5. Git flow и версионирование | 🟢 Низкая | 🔴 Высокое | **P0** | 2-4 часа |
| 1. Типизация | 🟡 Средняя | 🔴 Высокое | **P1** | 8-12 часов |
| 4. Структурированное логирование | 🟢 Низкая | 🟡 Среднее | **P2** | 4-6 часов |
| 3. Рефакторинг в классы | 🔴 Высокая | 🔴 Высокое | **P3** | 16-24 часа |
| 2. Оптимизация SQL | 🔴 Высокая | 🟡 Среднее | **P4** | 12-16 часов |

**Итого**: ~42-62 часа работы (5-8 рабочих дней)

---

## 🎯 СТРАТЕГИЯ РЕФАКТОРИНГА

### Подход: Инкрементальный (постепенный)

**Почему не "большой взрыв"?**
- ✅ Проект работает в production
- ✅ Нужна стабильность
- ✅ Поэтапное тестирование безопаснее
- ✅ Можно откатиться на любом этапе

**Принципы**:
1. **Backward compatibility** - старый код работает с новым
2. **Feature flags** - возможность отключить новое
3. **Тестирование на каждом этапе**
4. **Отдельные ветки для каждой задачи**

---

## 📋 ДЕТАЛЬНЫЙ ПЛАН ДЕЙСТВИЙ

## ЭТАП 0: Подготовка инфраструктуры (День 0)

### 0.1 Git Flow и версионирование ⏱️ 2-4 часа

#### Задачи:
```bash
1. Создать структуру веток
   └── main (production, защищённая)
   └── develop (разработка)
   └── feature/* (фичи)
   └── hotfix/* (срочные исправления)
   └── release/* (подготовка релизов)

2. Настроить GitHub
   └── Branch protection rules для main
   └── PR templates
   └── Issue templates
   └── GitHub Actions (CI/CD)

3. Версионирование (Semantic Versioning)
   └── Текущая версия: v1.0.0
   └── Формат: MAJOR.MINOR.PATCH
   └── Теги для релизов
```

#### Файлы для создания:

**`.github/workflows/ci.yml`** - автотесты
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python -m pytest tests/
```

**`.github/pull_request_template.md`**
```markdown
## Описание изменений
<!-- Что изменено и зачем -->

## Тип изменений
- [ ] Bugfix
- [ ] Feature
- [ ] Refactoring
- [ ] Documentation

## Чеклист
- [ ] Код протестирован
- [ ] Добавлены type hints
- [ ] Обновлена документация
- [ ] Нет breaking changes
```

**`VERSION.py`**
```python
__version__ = "1.0.0"
__version_info__ = (1, 0, 0)
```

**`CHANGELOG.md`**
```markdown
# Changelog

## [Unreleased]

## [1.0.0] - 2025-01-15
### Added
- Полнотекстовый поиск MariaDB
- Поиск по аннотациям
- Групповые чаты

### Changed
- Миграция с SQLite на MariaDB

### Fixed
- Скачивание книг на всех языках
```

#### Инструкции по работе:
```bash
# 1. Создание новой фичи
git checkout develop
git pull origin develop
git checkout -b feature/add-typing

# 2. Работа и коммиты
git add .
git commit -m "feat: добавлена типизация для handlers"
git push origin feature/add-typing

# 3. Pull Request
# Создать PR: feature/add-typing -> develop
# После ревью и тестов -> merge

# 4. Релиз
git checkout -b release/1.1.0 develop
# Обновить VERSION.py и CHANGELOG.md
git commit -m "chore: release 1.1.0"
git checkout main
git merge --no-ff release/1.1.0
git tag -a v1.1.0 -m "Release 1.1.0"
git push origin main --tags

# 5. Hotfix
git checkout -b hotfix/critical-bug main
# Исправления
git checkout main
git merge --no-ff hotfix/critical-bug
git tag -a v1.0.1 -m "Hotfix 1.0.1"
```

#### Обновление деплой скриптов:
```bash
# deploy.sh - добавить выбор ветки/тега
read -p "Deploy from [branch/tag] (main): " deploy_ref
deploy_ref=${deploy_ref:-"main"}
git clone $GITHUB_REPO --branch $deploy_ref --single-branch temp_build
```

---

## ЭТАП 1: Типизация (Дни 1-2)

### 1.1 Установка инструментов ⏱️ 30 мин

```bash
# requirements-dev.txt
mypy==1.8.0
pytest==7.4.3
black==23.12.0
isort==5.13.2
pylint==3.0.3

pip install -r requirements-dev.txt
```

**`pyproject.toml`** - конфигурация
```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
ignore_missing_imports = true

[tool.black]
line-length = 120
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 120
```

### 1.2 Создание type definitions ⏱️ 2 часа

**`app/types.py`** - новый файл
```python
from typing import TypedDict, Optional, List, Tuple, NamedTuple
from dataclasses import dataclass
from enum import Enum

# ===== ENUMS =====
class SearchType(Enum):
    BOOKS = "books"
    SERIES = "series"
    AUTHORS = "authors"

class SearchArea(Enum):
    BASIC = "b"
    BOOK_ANNOTATIONS = "ba"
    AUTHOR_ANNOTATIONS = "aa"

class BookFormat(Enum):
    FB2 = "fb2"
    EPUB = "epub"
    MOBI = "mobi"

# ===== SETTINGS =====
@dataclass
class UserSettings:
    user_id: int
    max_books: int = 20
    lang: str = ""
    book_format: BookFormat = BookFormat.FB2
    search_type: SearchType = SearchType.BOOKS
    rating: str = ""
    book_size: str = ""
    search_area: SearchArea = SearchArea.BASIC
    is_blocked: bool = False
    last_news_date: str = "2000-01-01"

# ===== BOOK DATA =====
@dataclass
class BookInfo:
    file_name: str
    title: str
    last_name: Optional[str]
    first_name: Optional[str]
    middle_name: Optional[str]
    genre: Optional[str]
    book_size: int
    search_year: int
    lib_rate: float
    series_title: Optional[str]
    relevance: float

@dataclass
class BookDetails:
    bookid: int
    title: str
    year: Optional[int]
    series: Optional[str]
    seqid: Optional[int]
    genres: str  # comma-separated "id,name,id,name"
    authors: str  # comma-separated "id,lastname firstname,id,lastname firstname"
    cover_url: Optional[str]
    size: int
    pages: Optional[int]
    lang: str
    rate: Optional[float]

@dataclass
class AuthorInfo:
    author_id: int
    name: str
    photo_url: Optional[str]
    title: Optional[str]
    biography: Optional[str]

# ===== SEARCH RESULTS =====
class SearchResults(TypedDict):
    books: List[BookInfo]
    total_count: int
    pages: List[List[BookInfo]]

class SeriesResult(TypedDict):
    series_name: str
    series_id: int
    book_count: int

class AuthorResult(TypedDict):
    author_name: str
    author_id: int
    book_count: int

# ===== CONTEXT DATA =====
class UserContext(TypedDict, total=False):
    settings: UserSettings
    last_activity: str
    pages_of_books: List[List[BookInfo]]
    found_books_count: int
    current_series_name: Optional[str]
    current_author_id: Optional[int]
    last_search_query: str
```

### 1.3 Рефакторинг по модулям ⏱️ 6-8 часов

**Приоритет модулей для типизации:**

1. **database.py** (2 часа)
```python
from typing import List, Optional, Dict, Any
from types import BookInfo, BookDetails, AuthorInfo, UserSettings

class DatabaseBooks:
    def search_books(
        self,
        query: str,
        lang: str,
        size_limit: str,
        rating_filter: Optional[str] = None,
        search_area: str = "b",
        series_id: int = 0,
        author_id: int = 0
    ) -> List[BookInfo]:
        ...

    async def get_book_info(self, book_id: int) -> Optional[BookDetails]:
        ...

    async def get_author_info(self, author_id: int) -> Optional[AuthorInfo]:
        ...
```

2. **context.py** (1 час)
```python
from typing import Optional, Any
from telegram.ext import CallbackContext
from types import UserSettings, UserContext

class ContextManager:
    @classmethod
    def get(
        cls,
        context: CallbackContext,
        key: str,
        default: Optional[Any] = None
    ) -> Any:
        ...

    @classmethod
    def set(
        cls,
        context: CallbackContext,
        key: str,
        value: Any
    ) -> None:
        ...
```

3. **handlers_*.py** (3-4 часа)
```python
from telegram import Update
from telegram.ext import CallbackContext

async def start_cmd(update: Update, context: CallbackContext) -> None:
    ...

async def handle_search_books(update: Update, context: CallbackContext) -> None:
    ...
```

4. **utils.py** (1 час)
```python
from typing import Optional, Tuple, List

def format_size(size_in_bytes: int) -> str:
    ...

def clean_html_tags(text: str) -> str:
    ...

def format_links_from_flat_string(
    url_routine: Callable[[int], str],
    flat_str: str,
    max_num_elem: int
) -> Tuple[str, bool]:
    ...
```

### 1.4 Проверка типизации ⏱️ 1 час

```bash
# Запуск mypy
mypy app/

# Ожидаемый результат (первая итерация)
# Found 150 errors in 12 files

# Постепенное исправление
# Goal: 0 errors
```

---

## ЭТАП 2: Структурированное логирование (День 3)

### 2.1 Дизайн новой системы логирования ⏱️ 1 час

**Структура событий:**
```python
# app/logging_schema.py
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

class EventType(Enum):
    # User actions
    BOT_START = "bot.start"
    SEARCH_BOOKS = "search.books"
    SEARCH_SERIES = "search.series"
    SEARCH_AUTHORS = "search.authors"
    BOOK_DOWNLOAD = "book.download"
    BOOK_INFO_VIEW = "book.info.view"
    AUTHOR_INFO_VIEW = "author.info.view"
    SETTINGS_CHANGE = "settings.change"
    
    # Admin actions
    ADMIN_LOGIN = "admin.login"
    ADMIN_USER_BLOCK = "admin.user.block"
    ADMIN_STATS_VIEW = "admin.stats.view"
    
    # System events
    SYSTEM_ERROR = "system.error"
    PAYMENT_RECEIVED = "payment.received"

@dataclass
class LogEvent:
    timestamp: datetime
    event_type: EventType
    user_id: int
    username: Optional[str]
    
    # Context
    chat_type: str  # private/group
    chat_id: Optional[int]
    
    # Event specific data
    data: Dict[str, Any]
    
    # Metadata
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), default=str)

# Примеры событий
@dataclass
class SearchEvent:
    query: str
    search_type: str
    search_area: str
    results_count: int
    filters: Dict[str, Any]

@dataclass
class DownloadEvent:
    book_id: int
    book_title: str
    format: str
    file_size: int
    success: bool

@dataclass
class SettingsChangeEvent:
    setting_name: str
    old_value: Any
    new_value: Any
```

### 2.2 Реализация логгера ⏱️ 2 часа

**`app/structured_logger.py`** - новый файл
```python
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from logging_schema import LogEvent, EventType
from database import DatabaseLogs

class StructuredLogger:
    def __init__(self, db: DatabaseLogs):
        self.db = db
        self.logger = logging.getLogger('structured_logger')
    
    def log_event(self, event: LogEvent) -> None:
        """Логирует структурированное событие"""
        # 1. Файловое логирование (JSON)
        self.logger.info(event.to_json())
        
        # 2. Базовое логирование в БД
        self.db.write_structured_log(
            timestamp=event.timestamp.isoformat(),
            event_type=event.event_type.value,
            user_id=event.user_id,
            username=event.username,
            chat_type=event.chat_type,
            data_json=json.dumps(event.data),
            duration_ms=event.duration_ms,
            error=event.error
        )
    
    # Удобные методы для частых событий
    def log_search(
        self,
        user_id: int,
        username: str,
        query: str,
        search_type: str,
        results_count: int,
        duration_ms: int,
        **filters
    ) -> None:
        event = LogEvent(
            timestamp=datetime.now(),
            event_type=EventType.SEARCH_BOOKS,
            user_id=user_id,
            username=username,
            chat_type="private",
            chat_id=user_id,
            data={
                "query": query,
                "search_type": search_type,
                "results_count": results_count,
                "filters": filters
            },
            duration_ms=duration_ms
        )
        self.log_event(event)
    
    def log_download(
        self,
        user_id: int,
        username: str,
        book_id: int,
        book_title: str,
        format: str,
        success: bool
    ) -> None:
        event = LogEvent(
            timestamp=datetime.now(),
            event_type=EventType.BOOK_DOWNLOAD,
            user_id=user_id,
            username=username,
            chat_type="private",
            chat_id=user_id,
            data={
                "book_id": book_id,
                "book_title": book_title,
                "format": format,
                "success": success
            }
        )
        self.log_event(event)
```

### 2.3 Обновление схемы БД ⏱️ 1 час

**`db_init/zz_init_structured_logs.sql`**
```sql
CREATE TABLE IF NOT EXISTS StructuredLog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    user_id INTEGER NOT NULL,
    username VARCHAR(100),
    chat_type VARCHAR(20),
    chat_id INTEGER,
    data_json TEXT,
    duration_ms INTEGER,
    error TEXT,
    
    INDEX idx_timestamp (timestamp),
    INDEX idx_user_id (user_id),
    INDEX idx_event_type (event_type)
);

-- Представления для аналитики
CREATE VIEW v_search_stats AS
SELECT 
    DATE(timestamp) as date,
    json_extract(data_json, '$.search_type') as search_type,
    COUNT(*) as search_count,
    AVG(duration_ms) as avg_duration_ms,
    COUNT(DISTINCT user_id) as unique_users
FROM StructuredLog
WHERE event_type = 'search.books'
GROUP BY DATE(timestamp), json_extract(data_json, '$.search_type');

CREATE VIEW v_download_stats AS
SELECT
    DATE(timestamp) as date,
    json_extract(data_json, '$.format') as format,
    COUNT(*) as download_count,
    SUM(CASE WHEN json_extract(data_json, '$.success') = 1 THEN 1 ELSE 0 END) as successful_downloads
FROM StructuredLog  
WHERE event_type = 'book.download'
GROUP BY DATE(timestamp), json_extract(data_json, '$.format');
```

### 2.4 Интеграция в handlers ⏱️ 1 час

```python
# app/handlers_search.py
from structured_logger import StructuredLogger
from time import time

structured_logger = StructuredLogger(DB_LOGS)

async def async_search_books(...):
    start_time = time()
    
    # Поиск
    books = DB_BOOKS.search_books(...)
    
    duration_ms = int((time() - start_time) * 1000)
    
    # Структурированное логирование
    structured_logger.log_search(
        user_id=user.id,
        username=user.username,
        query=query_text,
        search_type=user_params.SearchType,
        results_count=len(books),
        duration_ms=duration_ms,
        lang=user_params.Lang,
        rating_filter=user_params.Rating,
        search_area=user_params.SearchArea
    )
```

---

## ЭТАП 3: Рефакторинг в классы (Дни 4-6)

### 3.1 Архитектура новых классов ⏱️ 2 часа

**Структура:**
```
app/
├── services/           # Бизнес-логика
│   ├── __init__.py
│   ├── search_service.py
│   ├── book_service.py
│   ├── user_service.py
│   └── admin_service.py
├── repositories/       # Работа с БД
│   ├── __init__.py
│   ├── book_repository.py
│   ├── user_repository.py
│   └── log_repository.py
├── handlers/          # Telegram handlers
│   ├── __init__.py
│   ├── command_handlers.py
│   ├── search_handlers.py
│   ├── callback_handlers.py
│   └── admin_handlers.py
├── core/              # Core компоненты
│   ├── __init__.py
│   ├── context_manager.py
│   ├── logger.py
│   └── config.py
└── utils/             # Утилиты
    ├── __init__.py
    ├── formatters.py
    └── validators.py
```

### 3.2 Service Layer ⏱️ 6 часов

**`app/services/search_service.py`**
```python
from typing import List, Optional
from dataclasses import dataclass
from repositories.book_repository import BookRepository
from types import BookInfo, UserSettings, SearchResults

@dataclass
class SearchParams:
    query: str
    settings: UserSettings
    series_id: Optional[int] = None
    author_id: Optional[int] = None

class SearchService:
    def __init__(self, book_repo: BookRepository):
        self.book_repo = book_repo
    
    async def search_books(self, params: SearchParams) -> SearchResults:
        """Поиск книг с применением фильтров"""
        books = await self.book_repo.search(
            query=params.query,
            lang=params.settings.lang,
            size_limit=params.settings.book_size,
            rating_filter=params.settings.rating,
            search_area=params.settings.search_area.value,
            series_id=params.series_id or 0,
            author_id=params.author_id or 0
        )
        
        pages = self._paginate(books, params.settings.max_books)
        
        return SearchResults(
            books=books,
            total_count=len(books),
            pages=pages
        )
    
    def _paginate(
        self,
        items: List[BookInfo],
        page_size: int
    ) -> List[List[BookInfo]]:
        """Разбивает список на страницы"""
        return [
            items[i:i + page_size]
            for i in range(0, len(items), page_size)
        ]
    
    async def get_popular_books(
        self,
        settings: UserSettings,
        days_back: int
    ) -> SearchResults:
        """Получение популярных книг"""
        books = await self.book_repo.get_popular(
            lang=settings.lang,
            size_limit=settings.book_size,
            rating_filter=settings.rating,
            days_back=days_back
        )
        
        pages = self._paginate(books, settings.max_books)
        
        return SearchResults(
            books=books,
            total_count=len(books),
            pages=pages
        )
```

**`app/services/book_service.py`**
```python
from typing import Optional
from repositories.book_repository import BookRepository
from types import BookDetails, AuthorInfo
from flibusta_client import FlibustaClient

class BookService:
    def __init__(
        self,
        book_repo: BookRepository,
        flibusta_client: FlibustaClient
    ):
        self.book_repo = book_repo
        self.client = flibusta_client
    
    async def get_book_details(self, book_id: int) -> Optional[BookDetails]:
        """Получает полную информацию о книге"""
        return await self.book_repo.get_book_info(book_id)
    
    async def download_book(
        self,
        book_id: int,
        format: str,
        try_auth: bool = True
    ) -> Optional[tuple[bytes, str]]:
        """Скачивает книгу"""
        # Попытка без авторизации
        book_data, filename = await self.client.download_book(
            book_id, format, auth=False
        )
        
        # С авторизацией если нужно
        if not book_data and try_auth:
            book_data, filename = await self.client.download_book(
                book_id, format, auth=True
            )
        
        return (book_data, filename) if book_data else None
```

### 3.3 Repository Layer ⏱️ 4 часа

**`app/repositories/book_repository.py`**
```python
from typing import List, Optional
from types import BookInfo, BookDetails
import mysql.connector

class BookRepository:
    def __init__(self, db_config: dict):
        self.db_config = db_config
    
    async def search(
        self,
        query: str,
        lang: str = "",
        size_limit: str = "",
        rating_filter: Optional[str] = None,
        search_area: str = "b",
        series_id: int = 0,
        author_id: int = 0
    ) -> List[BookInfo]:
        """Поиск книг"""
        sql_query = self._build_search_query(
            search_area, lang, size_limit, rating_filter, series_id, author_id
        )
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql_query, (query, query))
            rows = cursor.fetchall()
        
        return [BookInfo(*row) for row in rows]
    
    async def get_book_info(self, book_id: int) -> Optional[BookDetails]:
        """Получает информацию о книге"""
        sql = """
            SELECT b.BookID, b.Title, b.Year, ...
            FROM libbook b
            LEFT JOIN ...
            WHERE b.BookID = %s
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (book_id,))
            row = cursor.fetchone()
        
        return BookDetails(*row) if row else None
    
    def _build_search_query(self, ...):
        """Строит SQL запрос"""
        # Вынесенная логика построения SQL
        ...
    
    def _get_connection(self):
        """Контекстный менеджер для подключения"""
        return mysql.connector.connect(**self.db_config)
```

### 3.4 Handler Layer ⏱️ 4 часа

**`app/handlers/search_handlers.py`**
```python
from telegram import Update
from telegram.ext import CallbackContext
from services.search_service import SearchService, SearchParams
from core.context_manager import ContextManager
from structured_logger import StructuredLogger

class SearchHandlers:
    def __init__(
        self,
        search_service: SearchService,
        logger: StructuredLogger
    ):
        self.search_service = search_service
        self.logger = logger
    
    async def handle_search(
        self,
        update: Update,
        context: CallbackContext
    ) -> None:
        """Обработчик поиска"""
        message = update.message
        user = message.from_user
        query_text = message.text
        
        # Получаем настройки
        settings = ContextManager.get_user_settings(context)
        
        # Показываем процесс
        processing_msg = await message.reply_text("⏰ Ищу книги...")
        
        # Выполняем поиск
        params = SearchParams(query=query_text, settings=settings)
        results = await self.search_service.search_books(params)
        
        # Сохраняем в контекст
        ContextManager.set_search_results(context, results)
        
        # Формируем ответ
        keyboard = self._create_results_keyboard(results, page=0)
        header = self._format_results_header(results, page=0)
        
        await processing_msg.edit_text(header, reply_markup=keyboard)
        
        # Логируем
        self.logger.log_search(
            user_id=user.id,
            username=user.username,
            query=query_text,
            search_type=settings.search_type.value,
            results_count=results.total_count
        )
    
    def _create_results_keyboard(self, results, page):
        """Создаёт клавиатуру с результатами"""
        ...
    
    def _format_results_header(self, results, page):
        """Форматирует заголовок"""
        ...
```

---

## ЭТАП 4: Оптимизация SQL (Дни 7-8)

### 4.1 Анализ текущих запросов ⏱️ 2 часа

```python
# app/sql_analyzer.py
class SQLAnalyzer:
    """Инструмент для анализа производительности SQL"""
    
    def explain_query(self, query: str) -> dict:
        """Выполняет EXPLAIN для запроса"""
        ...
    
    def benchmark_query(self, query: str, iterations: int = 10) -> dict:
        """Замеряет время выполнения"""
        ...
```

### 4.2 Оптимизированные запросы ⏱️ 6-8 часов

**Новый подход - Query Builder:**

```python
# app/repositories/query_builder.py
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class QueryCondition:
    field: str
    operator: str
    value: any

class SearchQueryBuilder:
    """Строитель SQL запросов для поиска"""
    
    def __init__(self):
        self.base_fields = """
            b.BookID as FileName,
            UPPER(b.Lang) as SearchLang,
            b.Title,
            b.FileSize as BookSize,
            b.Year as SearchYear,
            CASE 
                WHEN b.FileSize <= 800 * 1024 THEN 'less800'
                WHEN b.FileSize > 800 * 1024 THEN 'more800'
            END as BookSizeCat,
            an.LastName,
            an.FirstName, 
            an.MiddleName,
            an.AvtorId as AuthorID,
            gl.GenreDesc AS Genre,
            sn.SeqName as SeriesTitle, 
            sn.SeqId as SeriesID, 
            ROUND(COALESCE(r.LibRate, 0)) as LibRate
        """
        
        self.base_joins = """
            LEFT JOIN libavtor a ON a.BookID = b.BookID
            LEFT JOIN libavtorname an ON an.AvtorID = a.AvtorID
            LEFT JOIN (
                SELECT bookid, MIN(genreid) as genreid 
                FROM libgenre 
                GROUP BY bookid
            ) g ON g.BookID = b.BookID
            LEFT JOIN libgenrelist gl ON gl.GenreID = g.GenreID
            LEFT JOIN libseq s ON s.BookID = b.BookID
            LEFT JOIN libseqname sn ON sn.SeqID = s.SeqID
            LEFT JOIN (
                SELECT BookId, AVG(CAST(Rate AS SIGNED)) as LibRate
                FROM librate 
                GROUP BY BookId
            ) r ON r.BookId = b.BookId
        """
        
        self.conditions: List[QueryCondition] = []
    
    def for_fulltext_search(self, search_area: str) -> 'SearchQueryBuilder':
        """Добавляет полнотекстовый поиск"""
        if search_area == 'b':
            self.search_table = "libbook_fts fts"
            self.search_join = "JOIN libbook b ON b.BookID = fts.BookID"
            self.match_field = "fts.FT"
        elif search_area == 'ba':
            self.search_table = "libbannotations ba"
            self.search_join = "JOIN libbook b ON b.BookID = ba.BookID"
            self.match_field = "ba.Body"
        elif search_area == 'aa':
            self.search_table = "libaannotations aa"
            self.search_join = """
                JOIN libavtor ab ON ab.AvtorId = aa.AvtorId
                JOIN libbook b ON b.BookID = ab.BookID
            """
            self.match_field = "aa.Body"
        return self
    
    def where_lang(self, lang: str) -> 'SearchQueryBuilder':
        """Фильтр по языку"""
        if lang:
            self.conditions.append(
                QueryCondition('SearchLang', '=', f"'{lang.upper()}'")
            )
        return self
    
    def where_size(self, size_limit: str) -> 'SearchQueryBuilder':
        """Фильтр по размеру"""
        if size_limit:
            self.conditions.append(
                QueryCondition('BookSizeCat', '=', f"'{size_limit}'")
            )
        return self
    
    def where_rating(self, rating_filter: Optional[str]) -> 'SearchQueryBuilder':
        """Фильтр по рейтингу"""
        if rating_filter:
            self.conditions.append(
                QueryCondition('LibRate', 'IN', f"({rating_filter})")
            )
        return self
    
    def where_series(self, series_id: int) -> 'SearchQueryBuilder':
        """Фильтр по серии"""
        if series_id != 0:
            self.conditions.append(
                QueryCondition('SeriesID', '=', str(series_id))
            )
        return self
    
    def where_author(self, author_id: int) -> 'SearchQueryBuilder':
        """Фильтр по автору"""
        if author_id != 0:
            self.conditions.append(
                QueryCondition('AuthorID', '=', str(author_id))
            )
        return self
    
    def build_for_books(self, limit: int = 2000) -> str:
        """Строит запрос для поиска книг"""
        where_clause = self._build_where_clause()
        
        return f"""
            SELECT * FROM (
                SELECT 
                    {self.base_fields},
                    MATCH({self.match_field}) AGAINST(%s IN BOOLEAN MODE) as Relevance,
                    ROW_NUMBER() OVER (PARTITION BY FileName ORDER BY FileName) AS rn
                FROM {self.search_table}
                {self.search_join}
                {self.base_joins}
                WHERE b.Deleted = '0'
                  AND MATCH({self.match_field}) AGAINST(%s IN BOOLEAN MODE)
            ) as ranked
            {where_clause}
              AND rn = 1
            ORDER BY Relevance DESC, FileName DESC
            LIMIT {limit}
        """
    
    def build_for_series(self, limit: int = 200) -> str:
        """Строит запрос для группировки по сериям"""
        inner_query = f"""
            SELECT 
                {self.base_fields},
                MATCH({self.match_field}) AGAINST(%s IN BOOLEAN MODE) as Relevance
            FROM {self.search_table}
            {self.search_join}
            {self.base_joins}
            WHERE b.Deleted = '0'
              AND MATCH({self.match_field}) AGAINST(%s IN BOOLEAN MODE)
            ORDER BY Relevance DESC
        """
        
        where_clause = self._build_where_clause()
        
        return f"""
            SELECT 
                SeriesTitle, 
                SeriesID,
                COUNT(DISTINCT FileName) as book_count
            FROM ({inner_query}) as subquery
            {where_clause}
              AND SeriesTitle IS NOT NULL
            GROUP BY SeriesTitle, SeriesID 
            ORDER BY book_count DESC, SeriesTitle
            LIMIT {limit}
        """
    
    def build_for_authors(self, limit: int = 200) -> str:
        """Строит запрос для группировки по авторам"""
        inner_query = f"""
            SELECT 
                {self.base_fields},
                MATCH({self.match_field}) AGAINST(%s IN BOOLEAN MODE) as Relevance
            FROM {self.search_table}
            {self.search_join}
            {self.base_joins}
            WHERE b.Deleted = '0'
              AND MATCH({self.match_field}) AGAINST(%s IN BOOLEAN MODE)
        """
        
        where_clause = self._build_where_clause()
        
        return f"""
            SELECT 
                CONCAT(COALESCE(LastName, ''), ' ', 
                       COALESCE(FirstName, ''), ' ', 
                       COALESCE(MiddleName, '')) as AuthorName,
                COUNT(DISTINCT FileName) as book_count,
                AuthorID
            FROM ({inner_query}) as subquery
            {where_clause}
              AND (LastName <> '' OR FirstName <> '' OR MiddleName <> '')
            GROUP BY AuthorName, AuthorID
            ORDER BY book_count DESC, AuthorName
            LIMIT {limit}
        """
    
    def _build_where_clause(self) -> str:
        """Строит WHERE условие из накопленных условий"""
        if not self.conditions:
            return "WHERE 1=1"
        
        conditions_sql = " AND ".join([
            f"{cond.field} {cond.operator} {cond.value}"
            for cond in self.conditions
        ])
        
        return f"WHERE {conditions_sql}"


# Использование:
class BookRepository:
    def search_books(self, query: str, lang: str, size_limit: str, 
                     rating_filter: str, search_area: str, 
                     series_id: int, author_id: int) -> List[BookInfo]:
        
        builder = SearchQueryBuilder()
        sql = (builder
               .for_fulltext_search(search_area)
               .where_lang(lang)
               .where_size(size_limit)
               .where_rating(rating_filter)
               .where_series(series_id)
               .where_author(author_id)
               .build_for_books(limit=2000))
        
        # Выполнение запроса
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (query, query))
            return [BookInfo(*row) for row in cursor.fetchall()]
```

### 4.3 Оптимизация индексов ⏱️ 2 часа

**`db_init/zz_optimize_indexes.sql`**
```sql
-- Анализ текущих индексов
SHOW INDEX FROM libbook;
SHOW INDEX FROM libavtor;

-- Добавление составных индексов
CREATE INDEX idx_book_deleted_lang ON libbook(Deleted, Lang);
CREATE INDEX idx_book_deleted_size ON libbook(Deleted, FileSize);

-- Оптимизация JOIN'ов
CREATE INDEX idx_avtor_bookid ON libavtor(BookID);
CREATE INDEX idx_seq_bookid ON libseq(BookID);
CREATE INDEX idx_genre_bookid ON libgenre(BookID);

-- Анализ планов выполнения
EXPLAIN SELECT ... FROM libbook WHERE ...;

-- Обновление статистики
ANALYZE TABLE libbook;
ANALYZE TABLE libavtor;
ANALYZE TABLE libavtorname;
```

### 4.4 Кеширование результатов ⏱️ 2 часа

```python
# app/core/cache.py
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import json

class SimpleCache:
    """Простой in-memory кеш с TTL"""
    
    def __init__(self):
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._ttl = timedelta(minutes=5)
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кеша"""
        if key in self._cache:
            value, expires_at = self._cache[key]
            if datetime.now() < expires_at:
                return value
            else:
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> None:
        """Сохранить значение в кеш"""
        expires_at = datetime.now() + (ttl or self._ttl)
        self._cache[key] = (value, expires_at)
    
    def clear(self) -> None:
        """Очистить кеш"""
        self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """Удалить просроченные записи"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, expires_at) in self._cache.items()
            if now >= expires_at
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)

# Использование в репозитории
class BookRepository:
    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.cache = SimpleCache()
    
    async def get_book_info(self, book_id: int) -> Optional[BookDetails]:
        # Проверяем кеш
        cache_key = f"book_info:{book_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Запрос к БД
        book_info = await self._fetch_book_info(book_id)
        
        # Сохраняем в кеш
        if book_info:
            self.cache.set(cache_key, book_info, ttl=timedelta(hours=1))
        
        return book_info
```

---

## ЭТАП 5: Тестирование и документация (День 9)

### 5.1 Unit тесты ⏱️ 4 часа

**`tests/test_search_service.py`**
```python
import pytest
from unittest.mock import Mock, AsyncMock
from services.search_service import SearchService, SearchParams
from types import UserSettings, SearchType, SearchArea, BookFormat

@pytest.fixture
def mock_book_repo():
    repo = Mock()
    repo.search = AsyncMock(return_value=[
        # Моковые данные книг
    ])
    return repo

@pytest.fixture
def search_service(mock_book_repo):
    return SearchService(mock_book_repo)

@pytest.mark.asyncio
async def test_search_books_basic(search_service, mock_book_repo):
    """Тест базового поиска"""
    settings = UserSettings(
        user_id=123,
        max_books=20,
        search_type=SearchType.BOOKS
    )
    params = SearchParams(query="фантастика", settings=settings)
    
    results = await search_service.search_books(params)
    
    assert results.total_count > 0
    assert len(results.pages) > 0
    mock_book_repo.search.assert_called_once()

@pytest.mark.asyncio
async def test_search_with_filters(search_service):
    """Тест поиска с фильтрами"""
    settings = UserSettings(
        user_id=123,
        max_books=20,
        lang="ru",
        rating="45"
    )
    params = SearchParams(query="Толстой", settings=settings)
    
    results = await search_service.search_books(params)
    
    # Проверяем что фильтры применены
    assert results is not None

def test_pagination(search_service):
    """Тест пагинации"""
    items = list(range(100))
    pages = search_service._paginate(items, page_size=20)
    
    assert len(pages) == 5
    assert len(pages[0]) == 20
    assert pages[0][0] == 0
    assert pages[-1][-1] == 99
```

**`tests/test_query_builder.py`**
```python
import pytest
from repositories.query_builder import SearchQueryBuilder

def test_query_builder_basic():
    """Тест базового построения запроса"""
    builder = SearchQueryBuilder()
    sql = (builder
           .for_fulltext_search('b')
           .where_lang('ru')
           .build_for_books())
    
    assert "MATCH" in sql
    assert "SearchLang = 'RU'" in sql
    assert "LIMIT 2000" in sql

def test_query_builder_all_filters():
    """Тест запроса со всеми фильтрами"""
    builder = SearchQueryBuilder()
    sql = (builder
           .for_fulltext_search('b')
           .where_lang('en')
           .where_size('less800')
           .where_rating('45')
           .where_series(123)
           .build_for_books())
    
    assert "SearchLang = 'EN'" in sql
    assert "BookSizeCat = 'less800'" in sql
    assert "LibRate IN (45)" in sql
    assert "SeriesID = 123" in sql
```

### 5.2 Интеграционные тесты ⏱️ 2 часа

**`tests/integration/test_database.py`**
```python
import pytest
from repositories.book_repository import BookRepository

@pytest.fixture
def book_repo():
    config = {
        'host': 'localhost',
        'database': 'flibusta_test',
        'user': 'test',
        'password': 'test'
    }
    return BookRepository(config)

@pytest.mark.integration
async def test_real_search(book_repo):
    """Тест реального поиска в БД"""
    books = await book_repo.search(
        query="Пушкин",
        lang="ru",
        size_limit="",
        rating_filter=None,
        search_area="b"
    )
    
    assert len(books) > 0
    assert all(book.SearchLang == "RU" for book in books)
```

### 5.3 Обновление документации ⏱️ 2 часа

**`docs/ARCHITECTURE.md`**
```markdown
# Архитектура проекта

## Слои приложения

### Service Layer
Бизнес-логика приложения. Координирует работу между handlers и repositories.

### Repository Layer
Доступ к данным. Инкапсулирует работу с БД.

### Handler Layer
Обработка событий Telegram. Тонкий слой между Telegram API и сервисами.

## Диаграммы
[Вставить диаграммы классов]
```

**`docs/DEVELOPMENT.md`**
```markdown
# Руководство разработчика

## Настройка окружения
## Запуск тестов
## Git workflow
## Code style
## Deployment
```

---

## 📅 ДЕТАЛЬНЫЙ ГРАФИК РАБОТ

### Неделя 1: Фундамент

| День | Задача | Часы | Ответственный |
|------|--------|------|---------------|
| **День 0** | **Подготовка** | **4ч** | |
| | Git flow настройка | 2ч | Dev |
| | CI/CD pipeline | 2ч | Dev |
| **День 1** | **Типизация (часть 1)** | **6ч** | |
| | Установка mypy, black, isort | 0.5ч | Dev |
| | Создание types.py | 2ч | Dev |
| | Типизация database.py | 2ч | Dev |
| | Типизация context.py | 1.5ч | Dev |
| **День 2** | **Типизация (часть 2)** | **6ч** | |
| | Типизация handlers | 4ч | Dev |
| | Типизация utils | 1ч | Dev |
| | Проверка mypy, исправления | 1ч | Dev |
| **День 3** | **Логирование** | **5ч** | |
| | Дизайн схемы событий | 1ч | Dev |
| | Реализация StructuredLogger | 2ч | Dev |
| | Обновление БД схемы | 1ч | Dev |
| | Интеграция в handlers | 1ч | Dev |

### Неделя 2: Рефакторинг

| День | Задача | Часы | Ответственный |
|------|--------|------|---------------|
| **День 4** | **Service Layer** | **8ч** | |
| | Архитектура сервисов | 2ч | Dev |
| | SearchService | 3ч | Dev |
| | BookService | 2ч | Dev |
| | UserService | 1ч | Dev |
| **День 5** | **Repository Layer** | **7ч** | |
| | BookRepository | 4ч | Dev |
| | UserRepository | 2ч | Dev |
| | LogRepository | 1ч | Dev |
| **День 6** | **Handler Layer** | **6ч** | |
| | Рефакторинг search_handlers | 2ч | Dev |
| | Рефакторинг command_handlers | 2ч | Dev |
| | Рефакторинг callback_handlers | 2ч | Dev |

### Неделя 3: Оптимизация и тесты

| День | Задача | Часы | Ответственный |
|------|--------|------|---------------|
| **День 7** | **SQL оптимизация (1)** | **8ч** | |
| | Анализ текущих запросов | 2ч | Dev |
| | Query Builder реализация | 4ч | Dev |
| | Тестирование производительности | 2ч | Dev |
| **День 8** | **SQL оптимизация (2)** | **6ч** | |
| | Оптимизация индексов | 2ч | Dev |
| | Реализация кеширования | 2ч | Dev |
| | Интеграция в репозитории | 2ч | Dev |
| **День 9** | **Тесты и документация** | **8ч** | |
| | Unit тесты | 4ч | Dev |
| | Интеграционные тесты | 2ч | Dev |
| | Обновление документации | 2ч | Dev |

---

## 🔄 ПРОЦЕСС РАБОТЫ ПО КАЖДОЙ ЗАДАЧЕ

### Шаблон для каждой задачи:

```
1. Создать feature ветку
   git checkout develop
   git checkout -b feature/task-name

2. Разработка
   - Написать код
   - Добавить type hints
   - Написать тесты
   - Запустить mypy/pytest

3. Commit
   git add .
   git commit -m "feat: описание изменений"

4. Push и PR
   git push origin feature/task-name
   # Создать PR в develop

5. Review и merge
   # После одобрения
   git checkout develop
   git merge --no-ff feature/task-name
   git push origin develop

6. Тестирование на staging
   # Деплой develop ветки на тестовый сервер
   ./deploy.sh -u --branch develop

7. Release
   # Когда готов набор фич
   git checkout -b release/1.1.0 develop
   # Обновить VERSION.py, CHANGELOG.md
   git checkout main
   git merge --no-ff release/1.1.0
   git tag -a v1.1.0 -m "Release 1.1.0"
   git push origin main --tags
```

---

## ✅ ACCEPTANCE CRITERIA (Критерии приёмки)

### Этап 0: Git Flow
- [ ] Созданы ветки main, develop
- [ ] Настроены branch protection rules
- [ ] GitHub Actions работает
- [ ] Есть PR и issue templates
- [ ] deploy.sh поддерживает выбор ветки

### Этап 1: Типизация
- [ ] Все публичные функции имеют type hints
- [ ] mypy проходит без ошибок
- [ ] Созданы type definitions в types.py
- [ ] IDE показывает автодополнение
- [ ] Нет breaking changes

### Этап 2: Логирование
- [ ] Все действия логируются структурированно
- [ ] БД содержит StructuredLog таблицу
- [ ] Есть views для аналитики
- [ ] Логи в JSON формате
- [ ] Можно построить отчёты

### Этап 3: Классы
- [ ] Код организован в Service/Repository/Handler слои
- [ ] Нет дублирования кода
- [ ] Классы следуют SOLID принципам
- [ ] Улучшена читаемость
- [ ] Упрощено тестирование

### Этап 4: SQL
- [ ] Query Builder работает
- [ ] Производительность не ухудшилась
- [ ] Логика дубликатов сохранена
- [ ] Добавлены индексы
- [ ] Есть кеширование

### Этап 5: Тесты
- [ ] Unit test coverage > 70%
- [ ] Есть интеграционные тесты
- [ ] CI запускает тесты автоматически
- [ ] Обновлена документация
- [ ] Есть руководство разработчика

---

## 🚨 РИСКИ И МИТИГАЦИЯ

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Breaking changes в production | Средняя | Высокое | Тщательное тестирование, фича флаги |
| Падение производительности | Низкая | Высокое | Бенчмарки до/после, откат возможен |
| Увеличение сложности | Средняя | Среднее | Документация, code review |
| Потеря данных при миграции БД | Низкая | Критическое | Бэкапы перед изменениями |
| Нехватка времени | Средняя | Среднее | Приоритизация, можно разбить на 2 итерации |

---

## 📊 МЕТРИКИ УСПЕХА

### Технические метрики
- **Type coverage**: 0% → 95%+
- **Test coverage**: 0% → 70%+
- **Cyclomatic complexity**: уменьшение на 40%
- **Code duplication**: уменьшение на 60%
- **SQL query time**: без ухудшения
- **Memory usage**: стабильное или лучше

### Качественные метрики
- **Readability**: легче понимать код
- **Maintainability**: проще добавлять фичи
- **Debugging**: проще находить баги
- **Onboarding**: новый разработчик входит быстрее

---

## 🎯 ПОСТ-РЕФАКТОРИНГ

### Что делать после завершения:

1. **Мониторинг production**
   - Следить за метриками 2 недели
   - Быстро реагировать на проблемы

2. **Сбор обратной связи**
   - От пользователей
   - От команды разработки

3. **Итерация 2 (опционально)**
   - Дальнейшая оптимизация
   - Дополнительные фичи

4. **Knowledge sharing**
   - Документировать lessons learned
   - Обновить onboarding материалы

---

## 💡 КАК Я МОГУ ПОМОЧЬ

### На каждом этапе я могу:

1. **Генерировать код**
   - Написать полную реализацию классов
   - Создать тесты
   - Написать SQL запросы

2. **Code review**
   - Проверить на ошибки
   - Предложить улучшения
   - Найти edge cases

3. **Документация**
   - Написать docstrings
   - Создать README
   - Нарисовать диаграммы

4. **Отладка**
   - Найти баги
   - Оптимизировать производительность
   - Исправить type errors

### Формат работы:

```
Вы: "Начинаем Этап 1, Задача 1.2 - создание types.py"

Я: [Генерирую полный файл types.py с type definitions]

Вы: "Добавь тип для review"

Я: [Добавляю BookReview dataclass]

Вы: "Теперь типизируй database.py"

Я: [Добавляю type hints в методы DatabaseBooks]
```

---

## 🚀 ГОТОВЫ НАЧАТЬ?

**Предлагаемый порядок действий:**

1. **Сначала**: Этап 0 (Git Flow) - быстро и важно
2. **Потом**: Этап 1 (Типизация) - фундамент для остального
3. **Далее**: Этапы 2-4 можно идти параллельно если есть ресурсы

**С чего начнём?** 

Предлагаю начать с **Этапа 0: Git Flow** - это займёт 2-4 часа и даст нам безопасную основу для всех последующих изменений.

Я могу:
- ✅ Создать все конфиг файлы (workflows, templates)
- ✅ Написать обновлённые deploy скрипты
- ✅ Создать CHANGELOG.md и VERSION.py
- ✅ Дать инструкции по настройке GitHub

**Готовы начать?** 🎯