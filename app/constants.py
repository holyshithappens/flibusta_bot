# Пути к базам данных и файлам
PREFIX_FILE_PATH = "./data"
PREFIX_TMP_PATH = "./tmp"  # путь для временных файлов и резервных копий
FLIBUSTA_LOG_PATH = './logs'

#FLIBUSTA_DB_BOOKS_PATH = f"{PREFIX_FILE_PATH}/Flibusta_FB2_local.hlc2"
FLIBUSTA_DB_SETTINGS_PATH = f"{PREFIX_FILE_PATH}/FlibustaSettings.sqlite"
FLIBUSTA_DB_LOGS_PATH = f"{PREFIX_FILE_PATH}/FlibustaLogs.sqlite"

# пути для резервных копий
BACKUP_TMP_PATH = PREFIX_TMP_PATH
BACKUP_DB_FILES = [
    FLIBUSTA_DB_SETTINGS_PATH,
    FLIBUSTA_DB_LOGS_PATH
]
BACKUP_LOG_PATTERN = f"{FLIBUSTA_LOG_PATH}/*log*"

# Максимальное количество книг для поиска
MAX_BOOKS_SEARCH = 2000
# Максимальное количество авторов для поиска
MAX_AUTHORS_SEARCH = 200
# Максимальное количество серий для поиска
MAX_SERIES_SEARCH = 200

#WEB
FLIBUSTA_BASE_URL = "https://www.flibusta.is"

BOOK_FORMAT_FB2 = 'fb2'
BOOK_FORMAT_MOBI = 'mobi'
BOOK_FORMAT_EPUB = 'epub'
DEFAULT_BOOK_FORMAT = BOOK_FORMAT_FB2  # По умолчанию формат не установлен

# Интервалы мониторинга загрузки и очистки ресурсов
# MONITORING_INTERVAL=1800 # каждые полчаса мониторим потребление памяти
CLEANUP_INTERVAL=3600 # каждый час очищаем старые сохранённые контексты поисков

# Константы для типов настроек
SETTING_MAX_BOOKS = 'max_books'
SETTING_LANG_SEARCH = 'lang_search'
# SETTING_SORT_ORDER = 'sort_order'
SETTING_SIZE_LIMIT = 'size_limit'
SETTING_BOOK_FORMAT = 'book_format'
SETTING_SEARCH_TYPE = 'search_type'
# Константа для типа настройки рейтинга
SETTING_RATING_FILTER = 'rating_filter'
SETTING_SEARCH_AREA = 'search_area' #'aux_search'
SETTING_SEARCH_AREA_B = 'b' # Поиск по основной информации
SETTING_SEARCH_AREA_BA = 'ba' # Поиск по аннотации книг
SETTING_SEARCH_AREA_AA = 'aa' # Поиск по аннотации авторов
SETTING_LOCALE = 'locale'  # User interface language

# SETTING_SORT_ORDER_ASC = 'asc'
# SETTING_SORT_ORDER_DESC = 'desc'

# Словарь соответствия setting_type -> заголовок
SETTING_TITLES = {
    SETTING_MAX_BOOKS: 'settings.menu.max_books',
    SETTING_LANG_SEARCH: 'settings.menu.lang_search',
    SETTING_SIZE_LIMIT: 'settings.menu.size_limit',
    SETTING_RATING_FILTER: 'settings.menu.rating_filter',
    SETTING_BOOK_FORMAT: 'settings.menu.book_format',
    SETTING_SEARCH_TYPE: 'settings.menu.search_type',
    SETTING_SEARCH_AREA: 'settings.menu.search_area',
    SETTING_LOCALE: 'settings.menu.locale'
}

SEARCH_TYPE_BOOKS = 'books'
SEARCH_TYPE_SERIES = 'series'
SEARCH_TYPE_AUTHORS = 'authors'

# Рейтинги книг с эмодзи
BOOK_RATINGS = {
    "0": ("⚪️", "common.ratings.0"),
    "1": ("🔴", "common.ratings.1"),
    "2": ("🟠", "common.ratings.2"),
    "3": ("🟡", "common.ratings.3"),
    "4": ("🟢", "common.ratings.4"),
    "5": ("🔵", "common.ratings.5")
}

UI_SEPARATOR = "__NEWLINE__"

# Словарь опций для настроек
SETTING_OPTIONS = {
    SETTING_MAX_BOOKS: [
        (20, '20'),
        (40, '40')
    ],
    SETTING_SIZE_LIMIT: [
        ('less800', 'common.size_limits.less800'),
        ('more800', 'common.size_limits.more800'),
        ('', 'common.reset')
    ],
    SETTING_BOOK_FORMAT: [
        (BOOK_FORMAT_FB2, 'common.formats.fb2'),
        (BOOK_FORMAT_MOBI, 'common.formats.mobi'),
        (BOOK_FORMAT_EPUB, 'common.formats.epub')
    ],
    SETTING_SEARCH_TYPE: [
        (SEARCH_TYPE_BOOKS, 'common.search_types.books'),
        (SEARCH_TYPE_SERIES, 'common.search_types.series'),
        (SEARCH_TYPE_AUTHORS, 'common.search_types.authors')
    ],
    SETTING_RATING_FILTER: [
        (key, f"{value[1]}") for key, value in BOOK_RATINGS.items()
    ],
    SETTING_SEARCH_AREA: [
        (SETTING_SEARCH_AREA_B, 'common.search_areas.main'),
        UI_SEPARATOR,
        (SETTING_SEARCH_AREA_BA, 'common.search_areas.book_annotations'),
        (SETTING_SEARCH_AREA_AA, 'common.search_areas.author_annotations')
    ],
    SETTING_LOCALE: [
        ('ru', 'common.locale_select.ru'),
        ('en', 'common.locale_select.en')
    ]
}

SHOW_POPULAR_ALL_TIME = 'show_pop_999'
SHOW_POPULAR_30_DAYS = 'show_pop_30'
SHOW_POPULAR_7_DAYS = 'show_pop_7'
SHOW_NOVELTY = 'show_pop_0'

# ============================================================
# POPULARITY WEIGHTS CONFIGURATION
# ============================================================
# Weights for calculating book popularity score
# Formula: (rate_count * W_RATE) + (recs_count * W_RECS) + (reviews_count * W_REVIEWS)
# These weights can be adjusted to change the relative importance of each source

POPULARITY_WEIGHT_RATE = 1.0   # Weight for ratings count (cb_librate)
POPULARITY_WEIGHT_RECS = 1.5   # Weight for recommendations count (cb_librecs)
POPULARITY_WEIGHT_REVIEWS = 2.0  # Weight for reviews count (cb_libreviews)

HEADING_POP = {
    SHOW_POPULAR_ALL_TIME: 'popular.headings.all_time',
    SHOW_POPULAR_30_DAYS: 'popular.headings.days_30',
    SHOW_POPULAR_7_DAYS: 'popular.headings.days_7',
    SHOW_NOVELTY: 'popular.headings.novelty'
}

# # Путь к файлу с новостями (теперь Python файл)
# BOT_NEWS_FILE_PATH = "./data/bot_news.py"

