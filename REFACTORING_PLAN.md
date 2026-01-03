# План доработки Flibusta Bot - Миграция в новую архитектуру

**Обновлено:** 2025-12-29
**Статус:** В процессе (Этапы 1-3 завершены)

## 📋 Анализ текущего состояния

### ✅ Что уже есть в новой архитектуре (85%)

**Репозитории:**
- ✅ `BookRepository` - работа с MariaDB (книги, авторы, серии)
- ✅ `UserRepository` - работа с SQLite (настройки пользователей)
- ✅ `LogsRepository` - работа с SQLite (логи)

**Сервисы:**
- ✅ `SearchService` - поиск книг/серий/авторов
- ✅ `BookService` - работа с книгами (скачивание, информация)
- ✅ `UserService` - управление пользователями
- ✅ `AdminService` - админ-функции
- ✅ `FlibustaService` - работа с сайтом Flibusta (НОВЫЙ!)

**Обработчики:**
- ✅ `CommandHandlers` - команды (/start, /help, /about, /news, /genres, /pop, /set, /donate)
- ✅ `SearchHandlers` - текстовый поиск и пагинация
- ✅ `CallbackHandlers` - обработка inline callback'ов
- ✅ `InfoHandlers` - информационные команды
- ✅ `SettingsHandlers` - настройки пользователя
- ✅ `GroupHandlers` - работа в групповых чатах
- ✅ `PaymentHandlers` - обработка платежей
- ✅ `AdminHandlers` - админ-панель

**Инфраструктура:**
- ✅ `StructuredLogger` - структурированное логирование
- ✅ `SimpleCache` - кеширование с TTL
- ✅ `ContextManager` - управление состоянием
- ✅ Полная типизация (`custom_types.py`)

### ✅ Что уже сделано (Этапы 1-3 завершены)

**FlibustaService - новый сервис для работы с сайтом Flibusta:**
- ✅ Создан [`app/services/flibusta_service.py`](app/services/flibusta_service.py)
- ✅ Полная типизация всех методов
- ✅ Интеграция с StructuredLogger
- ✅ Управление сессиями (обычная и авторизованная)
- ✅ Fallback стратегия скачивания (сначала без авторизации, потом с авторизацией)
- ✅ Получение обложек книг
- ✅ Формирование URL для книг, авторов, серий, жанров
- ✅ Обработка ошибок с логированием
- ✅ Поддержка async context manager

**Интеграция в BookService:**
- ✅ BookService теперь использует FlibustaService вместо прямого доступа к FlibustaClient
- ✅ Упрощена логика скачивания книг
- ✅ Все методы получения URL делегируются FlibustaService
- ✅ Реализован метод `download_book_with_fallback` с обработкой таймаутов
- ✅ Добавлена поддержка загрузки больших файлов на tmpfiles.org

### ❌ Что еще отсутствует в новой архитектуре (10%)

**Из старой архитектуры не перенесено:**

1. **Полноценная работа с книгами:**
   - Скачивание и отправка файлов пользователю ✅ РЕАЛИЗОВАНО
   - Обработка таймаутов при скачивании ✅ РЕАЛИЗОВАНО
   - Загрузка на tmpfiles.org для больших файлов ✅ РЕАЛИЗОВАНО

2. **Callback обработчики для книг:** ✅ РЕАЛИЗОВАНЫ
   - `book_info` - информация о книге
   - `book_details` - аннотация
   - `book_reviews` - отзывы
   - `send_file` - скачивание книги
   - `author_info` - информация об авторе

4. **Групповые чаты (полная реализация):**
   - Обработка mention'ов бота
   - Извлечение запроса из сообщения
   - Поиск в контексте группы

5. **Админ-панель (полная реализация):**
   - Управление пользователями (блокировка/разблокировка)
   - Создание бэкапов БД
   - Статистика системы

---

## 🎯 План доработки (приоритетный порядок)

### Этап 1: Интеграция FlibustaClient (Высокий приоритет) ✅ ЗАВЕРШЕН

**Задачи:** ✅ ВСЕ ВЫПОЛНЕНО

1. **Создан FlibustaService** ✅
   - Файл: [`app/services/flibusta_service.py`](app/services/flibusta_service.py)
   - Полная типизация, интеграция с логгером
   - Все методы из старого FlibustaClient перенесены и улучшены
    
2. **Интегрирован в BookService** ✅
   - BookService теперь использует FlibustaService
   - Упрощена логика инициализации
   - Все методы получения URL делегируются FlibustaService
    
3. **Обновлен пакет services** ✅
   - Добавлен FlibustaService в [`app/services/__init__.py`](app/services/__init__.py)
   - Обеспечен удобный импорт из других модулей

### Этап 2: Создание утилит форматирования (Высокий приоритет)

**Задачи:**

1. **Создать модуль форматирования**
   ```python
   # app/utils/formatting.py
   """
   Утилиты форматирования для книг, авторов и отзывов
   Вынесены из старого utils.py для разделения ответственности
   """
   import html
   import re
   from typing import Optional, Tuple
   
   from ..services.flibusta_service import FlibustaService
   
   
   def format_book_info(book_info: dict, flibusta_service: FlibustaService) -> str:
       """Форматирует информацию о книге для сообщения"""
       text = f"📚 <b><a href='{flibusta_service.get_book_url(book_info['bookid'])}'>{book_info['title']}</a></b>\n"
       
       # Авторы
       author_links, is_truncated = format_links_from_flat_string(
           flibusta_service.get_author_url, book_info.get("authors", ""), 20
       )
       text += f"\n👤 <b>Автор(ы):</b> {(author_links + (',...' if is_truncated else '')) or 'Не указаны'}"
       
       # Жанры
       genre_links, is_truncated = format_links_from_flat_string(
           flibusta_service.get_genre_url, book_info.get("genres", ""), 10
       )
       if genre_links:
           text += f"\n📑 <b>Жанр(ы):</b> {(genre_links + (',...' if is_truncated else ''))}"
       
       # Серия
       if book_info.get("series"):
           text += f"\n📖 <b>Серия:</b> <a href='{flibusta_service.get_series_url(book_info['seqid'])}'>{book_info['series']}</a>"
       
       # Год
       if book_info.get("year") and book_info["year"] != 0:
           text += f"\n📅 <b>Год:</b> {book_info['year']}"
       
       # Язык
       if book_info.get("lang"):
           text += f"\n🗣️ <b>Язык:</b> {book_info['lang']}"
       
       # Страницы
       if book_info.get("pages"):
           text += f"\n📃 <b>Страниц:</b> {book_info['pages']}"
       
       # Размер
       text += f"\n📦 <b>Размер:</b> {format_size(book_info.get('size', 0))}"
       
       # Рейтинг
       if book_info.get("rate"):
           text += f"\n⭐ <b>Рейтинг:</b> {book_info['rate']:.1f}"
       
       return text
   
   
   def format_book_details(book_details: dict) -> str:
       """Форматирует детальную информацию о книге"""
       text = f"📖 <b>Аннотация:</b> {book_details.get('title', 'Неизвестно')}\n\n"
       
       if book_details.get("annotation"):
           clean_annotation = clean_html_tags(book_details["annotation"])
           text += clean_annotation
       
       return truncate_text(text, 4000, ".")
   
   
   def format_author_info(author_info: dict, flibusta_service: FlibustaService) -> str:
       """Форматирует информацию об авторе"""
       author_id = author_info.get('author_id', 0)
       author_name = author_info.get('name', 'Неизвестный автор')
       
       text = f"👤 <b>Об авторе:</b> <a href='{flibusta_service.get_author_url(author_id)}'>{author_name}</a>\n\n"
       
       if author_info.get("biography"):
           clean_bio = clean_html_tags(author_info["biography"])
           text += clean_bio
       
       return truncate_text(text, 4000, ".")
   
   
   def format_book_reviews(reviews: list) -> str:
       """Форматирует отзывы о книге"""
       text = "💬 <b>Отзывы о книге:</b>\n\n"
       
       for name, time, review_text in reviews[:50]:
           reviewer = f"👤 <b>{name}</b> ({time})\n"
           clean_review = clean_html_tags(review_text)
           clean_review_trunc = f"{clean_review[:1000]}" + ("..." if len(clean_review) > 1000 else "") + "\n"
           
           if len(text + reviewer + clean_review_trunc) > 4000:
               break
           
           text += reviewer + clean_review_trunc
       
       return text
   
   
   def clean_html_tags(text: str) -> str:
       """Удаляет HTML-теги и очищает текст"""
       clean_text = text
       clean_text = re.sub(r"<br\s*/?>", "\n", clean_text)
       clean_text = re.sub(r"</?p[^>]*>", "\n", clean_text)
       clean_text = re.sub(r"<[^<]+?>", "", clean_text)
       clean_text = re.sub(r"\[[^\]]*?\]", "", clean_text)
       clean_text = re.sub(r"\n\s*\n", "\n\n", clean_text)
       clean_text = html.escape(clean_text)
       return clean_text.strip()
   
   
   def format_links_from_flat_string(url_routine, flat_str: str, max_num_elem: int) -> Tuple[str, bool]:
       """Форматирует ссылки из плоской строки"""
       if not flat_str:
           return "", False
       
       parts = [part.strip() for part in flat_str.split(",") if part.strip()]
       orig_len = len(parts)
       parts = parts[:max_num_elem]
       
       # Если нечётное количество — отбрасываем последний непарный элемент
       if len(parts) % 2 != 0:
           parts = parts[:-1]
       
       links = []
       for i in range(0, len(parts), 2):
           try:
               elem_id = int(parts[i])
               elem_name = parts[i + 1]
               url = url_routine(elem_id)
               links.append(f"<a href='{url}'>{elem_name}</a>")
           except (ValueError, IndexError):
               continue
       
       return ", ".join(links), orig_len != len(parts)
   
   
   def format_size(size_in_bytes: int) -> str:
       """Форматирует размер файла"""
       units = ["B", "K", "M", "G", "T"]
       unit_index = 0
       while size_in_bytes >= 1024 and unit_index < len(units) - 1:
           size_in_bytes /= 1024
           unit_index += 1
       return f"{size_in_bytes:.1f}{units[unit_index]}"
   
   
   def truncate_text(text: str, max_len: int, stop_sep: str) -> str:
       """Обрезает текст до максимальной длины"""
       if len(text) <= max_len:
           return text
       
       truncated = text[:max_len]
       last_stop_char = truncated.rfind(stop_sep)
       
       if last_stop_char != -1:
           return truncated[:last_stop_char] + "..."
       else:
           return truncated + "..."
   ```

2. **Интегрировать форматирование в BookService**
   ```python
   # app/services/book_service.py (дополнить)
   from ..utils.formatting import (
       format_book_info,
       format_book_details, 
       format_author_info,
       format_book_reviews
   )
   
   class BookService:
       # ... существующий код ...
       
       async def get_book_info_formatted(self, book_id: int) -> str:
           """Получает и форматирует информацию о книге"""
           book_info = await self.book_repo.get_book_info(book_id)
           if not book_info:
               return "Книга не найдена"
           
           # Преобразуем в dict для совместимости
           book_dict = {
               'bookid': book_id,
               'title': book_info.title,
               'authors': book_info.authors,
               'genres': book_info.genres,
               'series': book_info.series,
               'seqid': book_info.seqid,
               'year': book_info.year,
               'lang': book_info.lang,
               'pages': book_info.pages,
               'size': book_info.size,
               'rate': book_info.rate
           }
           
           return format_book_info(book_dict, self.flibusta_service)
       
       async def get_book_details_formatted(self, book_id: int) -> str:
           """Получает и форматирует аннотацию книги"""
           details = await self.book_repo.get_book_details(book_id)
           if not details:
               return "Аннотация отсутствует"
           return format_book_details(details)
       
       async def get_author_info_formatted(self, author_id: int) -> str:
           """Получает и форматирует информацию об авторе"""
           author_info = await self.book_repo.get_author_info(author_id)
           if not author_info:
               return "Автор не найден"
           return format_author_info(author_info, self.flibusta_service)
   ```

### Этап 3: Реализация callback обработчиков для книг (Высокий приоритет) ✅ ЗАВЕРШЕН

**Задачи:** ✅ ВСЕ ВЫПОЛНЕНО

1. **Реализованы CallbackHandlers** ✅
   - [`_handle_book_info()`](app/handlers/callback_handlers.py:290) - информация о книге с кнопками
   - [`_handle_book_details()`](app/handlers/callback_handlers.py:355) - аннотация книги
   - [`_handle_book_reviews()`](app/handlers/callback_handlers.py:394) - отзывы о книге
   - [`_handle_send_file()`](app/handlers/callback_handlers.py:433) - скачивание с fallback стратегией
   - [`_handle_author_info()`](app/handlers/callback_handlers.py:501) - информация об авторе
   - [`_handle_close_info()`](app/handlers/callback_handlers.py:547) - закрытие информации
   - [`_handle_close_message()`](app/handlers/callback_handlers.py:560) - удаление сообщения

2. **Интегрированы утилиты форматирования** ✅
   - Используются функции из [`app/utils.py`](app/utils.py:231)
   - `format_book_info()` - форматирование карточки книги
   - `format_book_details()` - форматирование аннотации
   - `format_author_info()` - форматирование биографии автора
   - `format_book_reviews()` - форматирование отзывов

3. **Добавлены методы BookRepository** ✅
   - [`get_book_details()`](app/repositories/book_repository.py:262) - получение аннотации книги
   - [`get_book_reviews()`](app/repositories/book_repository.py:293) - получение отзывов
   - `get_author_info()` - уже существовал

### Этап 4: Доработка BookRepository (Средний приоритет)

**Задачи:**

1. **Добавить методы для получения детальной информации**
   ```python
   # app/repositories/book_repository.py
   async def get_book_details(self, book_id: int) -> dict:
       """Получение детальной информации о книге (аннотация)"""
       # Запрос к libbannotations
       query = """
           SELECT title, annotation
           FROM libbannotations
           WHERE book_id = %s
       """
       async with self.db.execute(query, (book_id,)) as cursor:
           row = await cursor.fetchone()
           if row:
               return {
                   'title': row[0],
                   'annotation': row[1]
               }
       return {}
   
   async def get_author_info(self, author_id: int) -> dict:
       """Получение информации об авторе"""
       # Запрос к libaannotations + libavtorname
       query = """
           SELECT 
               a.author_id,
               n.LastName,
               n.FirstName,
               n.MiddleName,
               a.title,
               a.biography
           FROM libaannotations a
           JOIN libavtorname n ON a.author_id = n.AvtorId
           WHERE a.author_id = %s
       """
       async with self.db.execute(query, (author_id,)) as cursor:
           row = await cursor.fetchone()
           if row:
               return {
                   'author_id': row[0],
                   'last_name': row[1],
                   'first_name': row[2],
                   'middle_name': row[3],
                   'title': row[4],
                   'biography': row[5]
               }
       return {}
   
   async def get_book_reviews(self, book_id: int) -> List[dict]:
       """Получение отзывов о книге"""
       # Запрос к libreviews
       query = """
           SELECT name, time, review
           FROM libreviews
           WHERE book_id = %s
           ORDER BY time DESC
           LIMIT 50
       """
       reviews = []
       async with self.db.execute(query, (book_id,)) as cursor:
           async for row in cursor:
               reviews.append({
                   'name': row[0],
                   'time': row[1],
                   'review': row[2]
               })
       return reviews
   ```

### Этап 5: Доработка GroupHandlers (Средний приоритет)

**Задачи:**

1. **Реализовать полноценную обработку групповых сообщений**
   ```python
   # app/handlers/group_handlers.py
   async def handle_group_message(self, update: Update, context: CallbackContext):
       """Обработка сообщений в групповых чатах"""
       message = update.effective_message
       user = update.effective_user
       
       # Извлечение запроса
       query = self._extract_clean_query(message.text, context.bot.username)
       
       if not query:
           return
       
       # Выполнение поиска
       settings = self.user_service.get_user_settings(user.id)
       params = SearchParams(query=query, settings=settings)
       result = await self.search_service.search_books(params)
       
       if not result.books:
           await message.reply_text(
               f"@{user.username}, по вашему запросу ничего не найдено.",
               parse_mode=ParseMode.HTML
           )
           return
       
       # Отправка первого результата с mention'ом пользователя
       book = result.books[0]
       text = f"@{user.username}\n\n" + self.book_service.format_book_info(book)
       
       keyboard = [
           [InlineKeyboardButton("📖 Подробнее", callback_data=f"book_info:{book.bookid}")]
       ]
       
       await message.reply_text(
           text,
           reply_markup=InlineKeyboardMarkup(keyboard),
           parse_mode=ParseMode.HTML
       )
   
   def _extract_clean_query(self, text: str, bot_username: str) -> str:
       """Извлекает и очищает запрос из сообщения"""
       if not text:
           return ""
       
       # Удаляем mention бота
       query = text.replace(f"@{bot_username}", "").strip()
       
       # Удаляем команды
       if query.startswith('/'):
           query = ""
       
       return query
   ```

### Этап 6: Доработка AdminHandlers (Низкий приоритет)

**Задачи:**

1. **Реализовать управление пользователями**
   ```python
   # app/handlers/admin_handlers.py
   async def admin_user_manage(self, update, context):
       query = update.callback_query
       
       if query.data == "admin_block":
           # Блокировка пользователя
           user_id = int(query.data.split(":")[1])
           self.user_service.block_user(user_id)
           await query.answer("Пользователь заблокирован")
           
       elif query.data == "admin_unblock":
           # Разблокировка пользователя
           user_id = int(query.data.split(":")[1])
           self.user_service.unblock_user(user_id)
           await query.answer("Пользователь разблокирован")
   ```

2. **Добавить создание бэкапов**
   ```python
   # app/services/admin_service.py
   async def create_backup(self) -> dict:
       """Создание zip-архива с базами данных"""
       import zipfile
       import datetime
       
       timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
       backup_file = f"backup_{timestamp}.zip"
       
       with zipfile.ZipFile(backup_file, 'w') as zipf:
           # Добавляем SQLite базы
           zipf.write('data/users.db')
           zipf.write('data/logs.db')
           
           # Экспортируем MariaDB
           # (нужно реализовать dump MariaDB)
       
       return {
           'filename': backup_file,
           'size': os.path.getsize(backup_file)
       }
   ```

### Этап 7: Тестирование и отладка (Высокий приоритет)

**Задачи:**

1. **Написать тесты для новой функциональности**
   ```python
   # app/test_new_arch.py добавить тесты:
   - test_book_download
   - test_book_info_formatting
   - test_author_info
   - test_group_chat_handling
   - test_admin_functions
   ```

2. **Проверить работу в production-окружении**
   - Запустить бота на VPS
   - Протестировать скачивание книг
   - Проверить логирование
   - Проверить работу в группах

---

## 📊 Оценка трудозатрат

| Этап | Задачи | Время | Приоритет |
|------|--------|-------|-----------|
| 1 | Интеграция FlibustaClient | ✅ ЗАВЕРШЕН | Высокий |
| 2 | Утилиты форматирования | ✅ ЗАВЕРШЕН | Высокий |
| 3 | Callback обработчики книг | ✅ ЗАВЕРШЕН | Высокий |
| 4 | Доработка BookRepository | ✅ ЗАВЕРШЕН | Средний |
| 5 | Доработка GroupHandlers | 3-4 часа | Средний |
| 6 | Доработка AdminHandlers | 4-6 часов | Низкий |
| 7 | Тестирование | 4-8 часов | Высокий |
| **Итого** | | **7-18 часов** | |

---

## 🎯 Критерии успешного завершения

1. ✅ Все книги скачиваются и отправляются пользователям
2. ✅ Информация о книгах и авторах форматируется корректно
3. ✅ Большие файлы загружаются на tmpfiles.org
4. ✅ Callback'и книг работают без ошибок
5. ✅ Групповые чаты обрабатывают запросы правильно
6. ✅ Админ-панель позволяет блокировать/разблокировать пользователей
7. ✅ Все ошибки логируются в структурированном виде
8. ✅ Бот работает стабильно на VPS

---

## 📝 Примечания

- **Важно**: При реализации скачивания книг необходимо учитывать лимит Telegram на размер файлов (50 MB)
- **Рекомендация**: Для больших файлов использовать загрузку на tmpfiles.org с отправкой ссылки
- **Безопасность**: Все операции с файлами должны быть обернуты в try-except с логированием ошибок
- **Производительность**: Использовать кеширование для часто запрашиваемых книг и обложек
- **Тестирование**: Перед деплоем на production обязательно протестировать на локальном окружении
- **Совместимость**: Старый код (FlibustaClient, старые обработчики) не удалять, оставить для обратной совместимости
