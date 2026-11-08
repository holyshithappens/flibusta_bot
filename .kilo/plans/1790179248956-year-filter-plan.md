# Publication Year Filter Implementation Plan

## Overview
Add a publication year filter to the user settings menu, modeled after the existing genre filter pattern. Users can select multiple year intervals (including invalid year categories) as filter buttons. Selected intervals are stored in user settings and applied to all search types.

## Critical Design Decisions

### 1. Volatile Bins — Store Actual Year Ranges, Not Computed Bin Keys
The year bins are recalculated every time the DB updates. If a user selects "1992-1993" and the DB changes, the bin boundaries shift and "1992-1993" may no longer exist as a computed bin.

**Solution:** When a user selects a bin, store the **actual year range** as the filter identifier, not the computed bin key. The identifier encodes the SQL condition directly:
- `"1750-1922"` → `b.Year BETWEEN 1750 AND 1922`
- `"2000"` → `b.Year = 2000`
- `"0"` → `b.Year = 0`
- `"negative"` → `b.Year < 0`
- `"ancient"` → `b.Year > 0 AND b.Year < 1750`
- `"future"` → `b.Year > {current_year}` (resolved dynamically)

This makes the saved filter **self-contained and stable** regardless of how bins are currently calculated. The filter works by direct SQL condition, not by matching to current bin boundaries.

**Handling bin disappearance:** When a stored filter like "2002-2003" no longer matches any current bin after recalculation, the filter still works in SQL (`BETWEEN 2002 AND 2003`). When displaying the keyboard, stored filters that don't match current bins are still shown as selected (✔) with their original display text, ensuring the user's selection is preserved.

**Handling "future" threshold:** The "future" bin_id is a keyword, not a year range. When applying the filter, resolve it dynamically using `datetime.now().year`. When displaying, show "Future (>{current_year})" with the current year.

### 2. Global Cache Like Genres
Year bins are computed from the database and should be cached globally in `DatabaseBooks`, invalidated on DB update, and preloaded at startup — exactly like `_class_cached_parent_genres` and `_class_cached_genres`.

**Implementation:**
- Add `_class_cached_year_bins = None` class variable to `DatabaseBooks`
- Add `get_year_bins()` method: returns cached bins or computes + caches them
- Clear `_class_cached_year_bins` in `invalidate_db_cache()`
- Preload year bins in `main.py` startup (like genre caches)
- The `get_year_bins()` method returns a list of `(bin_id, display_text, book_count)` tuples where `bin_id` is the stable identifier described above

### 3. Storage and WHERE Clause Conversion
`YearFilter` in `UserSettings` stores comma-separated bin identifiers (e.g., `"1750-1922,2000,negative"`). Each identifier is parsed to generate the corresponding SQL condition.

**Parsing logic:**
```python
import datetime
current_year = datetime.now().year

def build_year_filter_condition(year_filter: str) -> str:
    """Convert comma-separated bin IDs to SQL WHERE conditions."""
    parts = []
    for bin_id in year_filter.split(','):
        bin_id = bin_id.strip()
        if bin_id == 'negative':
            parts.append("b.Year < 0")
        elif bin_id == 'ancient':
            parts.append("b.Year > 0 AND b.Year < 1750")
        elif bin_id == 'future':
            parts.append(f"b.Year > {current_year}")
        elif bin_id == '0':
            parts.append("b.Year = 0")
        elif '-' in bin_id:
            start, end = bin_id.split('-', 1)
            parts.append(f"b.Year BETWEEN {start} AND {end}")
        else:
            parts.append(f"b.Year = {bin_id}")
    return ' OR '.join(parts)
```

The generated conditions are joined with `OR` and added to the SQL WHERE clause.

## Data Flow
```
DB query (year bins) → Cached in DatabaseBooks → Settings menu buttons
→ User selection → UserSettings.YearFilter (comma-separated bin IDs)
→ parse_year_filter() → SQL WHERE conditions → All search methods
```

## Year Bin Definition
Based on the provided SQL queries, the year filter buttons are:

**Invalid categories (stable, don't change with DB updates):**
- `0` → "0 (unknown)" (173642 books)
- `negative` → "Negative" (1 book)
- `ancient` → "Ancient (<1750)" (772 books)
- `future` → `Future (>{current_year})` — threshold is dynamic, resolved at display and filter time using `datetime.now().year`

**Valid year intervals (60 bins, volatile — recalculated on DB update):**
- Single year: `"2000 (5815)"`, `"2001 (6568)"`, etc.
- Range: `"1992-1993 (8073)"`, `"2002-2003 (14446)"`, etc.

The `bin_id` for valid years is the actual year range string (e.g., `"1750-1922"`, `"2000"`, `"2025-2026"`). This is the stable identifier stored in user settings.

**Key insight:** The `bin_id` is the stable identifier. Even when bins are recalculated and "2002-2003" disappears as a computed bin, the stored `bin_id="2002-2003"` still generates valid SQL (`BETWEEN 2002 AND 2003`). The filter works independently of the current bin calculation.

## Files to Modify

### 1. `app/constants.py`
- Add `SETTING_YEAR_FILTER = 'year_filter'` constant
- Add `SETTING_YEAR_FILTER` to `SETTING_TITLES` dict with key `'settings.menu.year_filter'`

### 2. `app/database.py`
- Add `YearFilter` field to `UserSettingsType` namedtuple: `YearFilter` (default `''`)
- Add `_class_cached_year_bins = None` class variable to `DatabaseBooks`
- Add `get_year_bins()` method to `DatabaseBooks`:
  - Returns cached bins if available
  - Otherwise executes both SQL queries (invalid categories + 60-bin CTE), combines results
  - Enriches "future" display_text with current year: `f"Future (>{datetime.now().year})"`
  - Returns `list[tuple[str, str, int]]` — `(bin_id, display_text, book_count)`
  - Caches result in `_class_cached_year_bins`
  - The returned bins are used for display only; stored filters use bin_ids directly in SQL
- Add `invalidate_year_bins_cache()` or clear `_class_cached_year_bins` in existing `invalidate_db_cache()`
- Add `year_filter` parameter to `search_books()`, `search_series()`, `search_authors()`, `search_pop_books()` methods
- Add `build_year_filter_condition(year_filter: str)` static method that parses the comma-separated bin IDs and returns a SQL WHERE condition string joined with `OR`
- Integrate year filter condition into `build_sql_where_ft()` — add year_filter parameter and append the parsed conditions

### 3. `app/handlers_settings.py`
- Add `handle_set_year_filter()` async function:
  - Fetches year bins via `DB_BOOKS.get_year_bins()`
  - Gets current `YearFilter` from user params
  - Builds keyboard with checkmarks for selected intervals
  - Shows book count on each button
- Add `handle_toggle_year()` async function:
  - Parses `action` to get `bin_id`
  - Toggles bin_id in current `YearFilter`
  - Updates user params
  - Refreshes keyboard
- Add `handle_clear_all_years()` async function:
  - Clears `YearFilter` to `''`
  - Refreshes keyboard
- Update `create_settings_menu()` to show year filter count badge (like genre filter)
- Update `handle_set_actions()` to handle `set_year_filter` action
- Add `create_year_filter_keyboard()` function — builds the year bin selection keyboard with ✔ for selected, book counts, clear all button, back button

### 4. `app/handlers_callback.py`
- Add `'set_year_filter'` to `action_handlers` dict
- Add `'toggle_year'` handler (pattern: `toggle_year_{bin_id}`)
- Add `'clear_all_years'` handler
- Add `'back_to_year_filter'` handler (returns to year filter keyboard from child view if needed)

### 5. `app/handlers_search.py`
- Pass `year_filter` from `user_params.YearFilter` to all search methods:
  - `async_search_books()` → `DB_BOOKS.search_books(..., year_filter=user_params.YearFilter)`
  - `async_search_series()` → `DB_BOOKS.search_series(..., year_filter=user_params.YearFilter)`
  - `async_search_authors()` → `DB_BOOKS.search_authors(..., year_filter=user_params.YearFilter)`
  - `async_search_books()` (popular) → `DB_BOOKS.search_pop_books(..., year_filter=user_params.YearFilter)`

### 6. `app/i18n/translations/ru.yaml`
- Add `settings.menu.year_filter: "Фильтр по годам"` under `settings.menu`
- Add `common.clear_all_years: "🗑️ Очистить все годы"` under `common`

### 7. `app/i18n/translations/en.yaml`
- Add `settings.menu.year_filter: "Year filter"` under `settings.menu`
- Add `common.clear_all_years: "🗑️ Clear all years"` under `common`

### 8. `app/main.py`
- Preload year bins at startup (like genre caches): `DB_BOOKS.get_year_bins()`

## SQL Queries for `get_year_bins()`

The method executes two queries and combines results:

**Query 1 — Invalid categories:**
```sql
SELECT
    CASE
        WHEN Year = 0 THEN '0'
        WHEN Year < 0 THEN 'negative'
        WHEN Year = 32767 THEN 'future'
        WHEN Year < 1750 THEN 'ancient'
    END AS bin_id,
    CASE
        WHEN Year = 0 THEN '0 (unknown)'
        WHEN Year < 0 THEN 'Negative'
        WHEN Year = 32767 THEN 'Future'
        WHEN Year < 1750 THEN 'Ancient (<1750)'
    END AS display_text_base,
    COUNT(*) AS books_count
FROM cb_libbook
WHERE Deleted = 0
  AND (Year = 0 OR Year < 0 OR Year = 32767 OR Year < 1750)
GROUP BY bin_id, display_text_base
```

Note: The "future" display_text is computed in Python as `f"Future (>{datetime.now().year})"` since the threshold changes annually. The SQL returns "Future" as base text.

**Query 2 — 60-bin CTE (from user's provided query):**
The existing CTE query returns `(bin, min_year, max_year, books_in_bin)`. Convert each row to `(bin_id, display_text, books_count)` where:
- `bin_id = f"{min_year}-{max_year}"` if min_year != max_year, else `str(min_year)`
- `display_text = f"{min_year}-{max_year} ({books_in_bin})"` if range, else `f"{min_year} ({books_in_bin})"`

**Combined result:** Invalid categories first (sorted by count desc), then valid bins (sorted by bin order). The `get_year_bins()` method also enriches the "future" display_text with the current year.

## Year Filter SQL Integration Details

In `build_sql_where_ft()`, add `year_filter=None` parameter:
```python
@staticmethod
def build_sql_where_ft(lang, size_limit, rating_filter=None, series_id=0, author_id=0, person_type='author', genre_filter=None, year_filter=None):
    conditions = []
    # ... existing conditions ...
    
    # Year filter
    if year_filter and year_filter.strip():
        year_conditions = DatabaseBooks.build_year_filter_condition(year_filter)
        if year_conditions:
            conditions.append(f"({year_conditions})")
    
    sql_where = "WHERE " + " AND ".join(conditions) if conditions else "WHERE 1=1"
    return sql_where
```

The `build_year_filter_condition()` static method parses bin IDs and generates SQL. The "future" keyword is resolved dynamically using the current year:

```python
@staticmethod
def build_year_filter_condition(year_filter: str) -> str:
    import datetime
    current_year = datetime.now().year
    parts = []
    for bin_id in year_filter.split(','):
        bin_id = bin_id.strip()
        if bin_id == 'negative':
            parts.append("b.Year < 0")
        elif bin_id == 'ancient':
            parts.append("b.Year > 0 AND b.Year < 1750")
        elif bin_id == 'future':
            parts.append(f"b.Year > {current_year}")
        elif bin_id == '0':
            parts.append("b.Year = 0")
        elif '-' in bin_id:
            start, end = bin_id.split('-', 1)
            parts.append(f"b.Year BETWEEN {start} AND {end}")
        else:
            parts.append(f"b.Year = {bin_id}")
    return ' OR '.join(parts)
```

**Important:** The year filter uses `OR` between bins (selecting any matching bin) and `AND` with other filters (all filters must match). This matches the genre filter pattern where `g.GenreID IN (...)` is used.

### Keyboard Display — Handling Orphaned Filters
When building the year filter keyboard, the system must handle stored filters that no longer match any current bin:

1. Fetch current bins from `DB_BOOKS.get_year_bins()`
2. Parse current `YearFilter` from user settings
3. Build a merged list: current bins + any stored bin_ids not found in current bins
4. Mark each as selected (✔) if its bin_id is in the current `YearFilter`
5. For orphaned filters, display the original stored text (e.g., "2002-2003") with their original book count if available, or just the text without count
6. The "future" display text should use the current year: `f"Future (>{current_year})"`

This ensures:
- Previously saved filters remain visible and active even after bin recalculation
- The SQL filter still works correctly (uses stored year ranges directly)
- The user can toggle orphaned filters off just like any other

## Database Schema Note
No migration needed for the `UserSettings` table structure — it uses dynamic column updates via `UPDATE UserSettings SET ? = ?`. However, the `YearFilter` column must exist in the `UserSettings` table. If it doesn't exist yet, a migration is needed (similar to how `Locale` was added). Check the actual `UserSettings` table schema to confirm.

## Implementation Order
1. Check `UserSettings` table schema for `YearFilter` column existence; add migration if needed
2. Add `YearFilter` to `UserSettingsType` namedtuple in `database.py`
3. Add `_class_cached_year_bins` and `get_year_bins()` to `DatabaseBooks` (with dynamic "future" year enrichment)
4. Add `build_year_filter_condition()` static method (with dynamic year resolution for "future")
5. Add `year_filter` parameter to `build_sql_where_ft()` and all search methods
6. Add `SETTING_YEAR_FILTER` constant to `constants.py`
7. Add year filter SQL condition integration
8. Add handlers in `handlers_settings.py`:
   - `handle_set_year_filter()` with orphaned filter display logic
   - `handle_toggle_year()` with dynamic "future" display
   - `handle_clear_all_years()`
   - `create_year_filter_keyboard()` with merged current bins + orphaned stored filters
9. Add callback handlers in `handlers_callback.py`
10. Pass `year_filter` through in `handlers_search.py`
11. Add i18n translations (ru.yaml, en.yaml)
12. Update `create_settings_menu()` to display year filter count
13. Preload year bins in `main.py` startup
14. Clear year bins cache in `invalidate_db_cache()`

## Verification
- Settings menu shows "Фильтр по годам (N)" with count of selected intervals
- Clicking opens keyboard with all year bins showing book counts
- Selected bins show ✔ emoji
- "Clear all" button appears when selections exist
- Back button returns to settings menu
- Selected year filter is applied to search results
- Multiple intervals can be selected simultaneously
- Filter persists across sessions (stored in DB)
- After DB update, previously saved year filters still work correctly (stored bin_ids like "2002-2003" generate `BETWEEN 2002 AND 2003` SQL regardless of current bin calculation)
- Orphaned filters (no longer matching current bins) are still displayed as selected in the keyboard
- "Future" filter dynamically uses `datetime.now().year` for the threshold (e.g., >2026 in 2026, >2027 in 2027)
- Year bins are cached and invalidated properly on DB update
- Year bins are preloaded at startup and refreshed after DB update
