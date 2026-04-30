"""
Константы для новой архитектуры (совместимость со старой)
"""

# Максимальное количество книг для поиска
MAX_BOOKS_SEARCH = 2000
MAX_AUTHORS_SEARCH = 200
MAX_SERIES_SEARCH = 200

# Константы для популярного/новинок (из старой архитектуры)
SHOW_POPULAR_ALL_TIME = 'show_pop_999'
SHOW_POPULAR_30_DAYS = 'show_pop_30'
SHOW_POPULAR_7_DAYS = 'show_pop_7'
SHOW_NOVELTY = 'show_pop_0'

HEADING_POP = {
    SHOW_POPULAR_ALL_TIME: 'популярных за всё время',
    SHOW_POPULAR_30_DAYS: 'популярных за 30 дней',
    SHOW_POPULAR_7_DAYS: 'популярных за 7 дней',
    SHOW_NOVELTY: 'новинок'
}

# Константы для типов настроек
SETTING_MAX_BOOKS = 'max_books'
SETTING_LANG_SEARCH = 'lang_search'
SETTING_SIZE_LIMIT = 'size_limit'
SETTING_BOOK_FORMAT = 'book_format'
SETTING_SEARCH_TYPE = 'search_type'
SETTING_RATING_FILTER = 'rating_filter'
SETTING_SEARCH_AREA = 'aux_search'

# Области поиска
SETTING_SEARCH_AREA_B = 'b'  # Поиск по основной информации
SETTING_SEARCH_AREA_BA = 'ba'  # Поиск по аннотации книг
SETTING_SEARCH_AREA_AA = 'aa'  # Поиск по аннотации авторов

# Типы поиска
SEARCH_TYPE_BOOKS = 'books'
SEARCH_TYPE_SERIES = 'series'
SEARCH_TYPE_AUTHORS = 'authors'

# Форматы книг
BOOK_FORMAT_FB2 = 'fb2'
BOOK_FORMAT_MOBI = 'mobi'
BOOK_FORMAT_EPUB = 'epub'
DEFAULT_BOOK_FORMAT = BOOK_FORMAT_FB2

# Рейтинги книг с эмодзи
BOOK_RATINGS = {
    0: ("⚪️", "Без рейтинга (0)"),
    1: ("🔴", "Нечитаемо (1)"),
    2: ("🟠", "Плохо (2)"),
    3: ("🟡", "Неплохо (3)"),
    4: ("🟢", "Хорошо (4)"),
    5: ("🔵", "Отлично (5)")
}

# Словарь соответствия setting_type -> заголовок
SETTING_TITLES = {
    SETTING_MAX_BOOKS: 'Постраничный вывод',
    SETTING_LANG_SEARCH: 'Язык книг',
    SETTING_SIZE_LIMIT: 'Ограничение на размер книг',
    SETTING_RATING_FILTER: 'Фильтр по рейтингу',
    SETTING_BOOK_FORMAT: 'Формат скачивания книг',
    SETTING_SEARCH_TYPE: 'Вывод результатов',
    SETTING_SEARCH_AREA: 'Область поиска'
}

# Словарь опций для настроек
SETTING_OPTIONS = {
    SETTING_MAX_BOOKS: [
        (20, '20'),
        (40, '40')
    ],
    SETTING_SIZE_LIMIT: [
        ('less800', '<800K'),
        ('more800', '>800K'),
        ('', 'Сбросить')
    ],
    SETTING_BOOK_FORMAT: [
        (BOOK_FORMAT_FB2, 'FB2'),
        (BOOK_FORMAT_MOBI, 'MOBI'),
        (BOOK_FORMAT_EPUB, 'EPUB')
    ],
    SETTING_SEARCH_TYPE: [
        (SEARCH_TYPE_BOOKS, 'по книгам'),
        (SEARCH_TYPE_SERIES, 'по сериям'),
        (SEARCH_TYPE_AUTHORS, 'по авторам')
    ],
    SETTING_RATING_FILTER: [
        (key, f"{value[0]} {value[1]}") for key, value in BOOK_RATINGS.items()
    ],
    SETTING_SEARCH_AREA: [
        (SETTING_SEARCH_AREA_B, 'по основным данным книг'),
        "__NEWLINE__",
        (SETTING_SEARCH_AREA_BA, 'по аннотации книг'),
        (SETTING_SEARCH_AREA_AA, 'по аннотации авторов')
    ]
}