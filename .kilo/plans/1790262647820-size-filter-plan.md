# Book Size Filter Implementation Plan

## Overview
Replace the current two-option size limit (`less800` / `more800`, single-select) with a 10-bin percentile-based size filter, modeled exactly on the year filter. Users can select multiple size intervals as filter buttons. Selected intervals are stored in user settings and applied to all search types.

## Critical Design Decisions

### 1. Volatile Bins — Store Actual Byte Ranges, Not Computed Bin Keys
Size bins are recalculated when the DB updates. If a user selects "90915-313961" and the DB changes, the boundary shifts.

**Solution:** When a user selects a bin, store the **actual byte range** as the filter identifier. The identifier encodes the SQL condition directly:
- `"0-90915"` → `b.FileSize >= 0 AND b.FileSize < 90915`
- `"90915-313961"` → `b.FileSize >= 90915 AND b.FileSize < 313961`
- `">5786432"` → `b.FileSize >= 5786432` (last bin, inclusive lower bound to avoid a coverage gap)

This makes the saved filter **self-contained and stable** regardless of how bins are currently calculated.

**Interval scheme (no gaps, no overlaps):** all range bins use half-open intervals `[lower, upper)`; the last bin uses `[upper, ∞)` i.e. `>= upper`. The last bin is *displayed* as `>{size}` (matching the "more than" phrasing) but its SQL lower bound is inclusive — the only practical difference is a single book whose `FileSize` equals the boundary exactly.

**Handling bin disappearance:** a stored range like `"90915-313961"` still generates valid SQL (`>= 90915 AND < 313961`) even when it no longer matches a current computed bin. Orphaned stored filters are still shown as selected (✔) in the keyboard.

### 2. Repurpose `BookSize` (do NOT add a parallel column)
The existing `UserSettings.BookSize` column currently holds `less800`/`more800`. It is repurposed to hold comma-separated size bin ids (e.g. `"0-90915,>5786432"`). This keeps one field and one menu item ("Book size limit") and requires **no schema migration**.

**Legacy value safety:** `build_size_filter_condition()` only recognizes bin ids matching `N-M` (range) or `>N` (last bin). Any other value (e.g. a stored `less800`) is **skipped**, so legacy values become no-ops rather than SQL errors. In the keyboard they appear as orphaned buttons (toggleable off); the "Clear all sizes" button resets them. An optional one-time startup migration can blank legacy `less800`/`more800` values (see Implementation Order step 13).

### 3. SQL Integration — Inner Query (like year filter)
`build_sql_where_ft()` produces a WHERE applied **outside** the subquery, where the `b` table alias is not available. The size condition needs `b.FileSize`, so it is injected into the **inner** queries via `_build_size_sql()` — exactly like `_build_year_sql()`. The existing `BookSizeCat = '{size_limit}'` line in `build_sql_where_ft()` is removed.

`search_pop_books()` builds its own conditions on real columns (`b.FileSize`), so it appends `build_size_filter_condition()` output directly (replacing the hardcoded `less800`/`more800` block).

### 4. Global Cache Like Year Bins
Size bins are computed from the DB and cached globally in `DatabaseBooks`, invalidated on DB update, and preloaded at startup — same as `_class_cached_year_bins`.

### 5. Display Derived From `bin_id` via `format_size()`
No display text is stored. `get_size_bin_display(bin_id, context)` derives the button label from the bin id using `format_size()` from `app/tools.py`:
- first bin (`lower == 0`): `<{format_size(upper)}` → e.g. `<88.8K`
- middle bins: `{format_size(lower)}-{format_size(upper)}` → e.g. `88.8K-306.6K`
- last bin: `>{format_size(upper)}` → e.g. `>5.5M`

`format_size()` returns one decimal (e.g. `88.8K`). If integer labels (`90K`) are preferred, adjust `format_size()` — out of scope here.

## ⚠ Risk: `PERCENTILE_CONT` on MariaDB 12.0
The DB is **MariaDB 12.0** (`docker-compose.db.yml`). MariaDB does **not** support `PERCENTILE_CONT ... WITHIN GROUP ... OVER ()` (that is MySQL 8.0.2+ / SQL standard). The user-supplied boundary query may therefore fail at runtime.

**Verification step 1 (mandatory):** run the supplied `PERCENTILE_CONT` query against the actual MariaDB 12.0 instance.
- If it works → use the two-query approach below (boundary query + count query).
- If it errors → use the **MariaDB-compatible `NTILE(10)` fallback** (single query, returns boundaries AND counts, produces equivalent equal-count bins):

```sql
WITH ranked AS (
    SELECT COALESCE(FileSize, 0) AS FileSize,
           NTILE(10) OVER (ORDER BY COALESCE(FileSize, 0)) AS tile
    FROM cb_libbook
    WHERE deleted = 0
)
SELECT
    tile,
    MIN(FileSize) AS min_size,
    MAX(FileSize) AS max_size,
    COUNT(*) AS books_in_bin
FROM ranked
GROUP BY tile
ORDER BY tile
```

`NTILE` is supported since MariaDB 10.2. With `NTILE(10)`, each tile holds ~10% of books — the same equal-count binning the percentile boundaries produce.

## Data Flow
```
DB query (size bins) → Cached in DatabaseBooks → Settings menu buttons
→ User selection → UserSettings.BookSize (comma-separated bin ids)
→ build_size_filter_condition() → SQL WHERE conditions → All search methods
```

## Size Bin Definition
10 bins from the 10 percentile boundaries `p0..p90` (current values: `0, 90915, 313961, 545716, 763015, 986668, 1286355, 1778877, 2773901, 5786432`):

| bin_id | SQL condition | button label |
|---|---|---|
| `0-90915` | `FileSize >= 0 AND FileSize < 90915` | `<88.8K` |
| `90915-313961` | `FileSize >= 90915 AND FileSize < 313961` | `88.8K-306.6K` |
| `313961-545716` | `...` | `306.6K-532.9K` |
| `545716-763015` | `...` | `532.9K-745.1K` |
| `763015-986668` | `...` | `745.1K-963.5K` |
| `986668-1286355` | `...` | `963.5K-1.3M` |
| `1286355-1778877` | `...` | `1.3M-1.7M` |
| `1778877-2773901` | `...` | `1.7M-2.6M` |
| `2773901-5786432` | `FileSize >= 2773901 AND FileSize < 5786432` | `2.6M-5.5M` |
| `>5786432` | `FileSize >= 5786432` | `>5.5M` |

The `bin_id` is the stable identifier stored in user settings. No special "unknown/negative" categories (unlike year) — `FileSize` is a non-negative byte count; `FileSize = 0` books fall in the first bin.

## Files to Modify

### 1. `app/database.py`
- Add `_class_cached_size_bins = None` class variable to `DatabaseBooks`.
- Add `get_size_bins()` method:
  - Returns cached bins if available.
  - Otherwise runs the boundary query (PERCENTILE_CONT, or NTILE fallback) to get 10 boundaries, then a count query (or the single NTILE query) to get per-bin counts.
  - Builds `bin_id` per bin: `f"{min_size}-{max_size}"` for range bins, `f">{max_size}"` for the last bin.
  - Returns `list[tuple[str, int]]` — `(bin_id, books_count)`.
  - Merges duplicates by `bin_id` (sum counts) so each bin renders once.
  - Caches in `_class_cached_size_bins`.
- Add `build_size_filter_condition(size_filter: str) -> str` static method (parses comma-separated bin ids → OR-joined `b.FileSize` conditions; skips unrecognized/legacy values):
  ```python
  @staticmethod
  def build_size_filter_condition(size_filter: str) -> str:
      parts = []
      for bin_id in size_filter.split(','):
          bin_id = bin_id.strip()
          if not bin_id:
              continue
          if bin_id.startswith('>'):
              try:
                  upper = int(bin_id[1:])
              except ValueError:
                  continue
              parts.append(f"b.FileSize >= {upper}")
          elif '-' in bin_id:
              start, end = bin_id.split('-', 1)
              try:
                  start, end = int(start), int(end)
              except ValueError:
                  continue
              parts.append(f"b.FileSize >= {start} AND b.FileSize < {end}")
          # else: legacy/unrecognized (e.g. 'less800') — skip
      return ' OR '.join(parts)
  ```
- Add `_build_size_sql(size_filter: str) -> str` static method (wraps condition in `AND (...)` for inner-query injection), mirroring `_build_year_sql`.
- Add `size_filter=None` parameter to the three inner-query lambdas `SQL_QUERY_BOOKS`, `SQL_QUERY_ABOOKS`, `SQL_QUERY_AAUTHORS`, each including `{DatabaseBooks._build_size_sql(size_filter)}`.
- Add `size_filter=None` parameter to `build_sql_query_books()` and pass it to the lambda: `SELECT_SQL_QUERY.get(search_area)(locale, is_empty, genre_filter, year_filter, size_filter)`.
- `search_books()`: pass `size_filter=size_limit` to `build_sql_query_books()`.
- `search_series()` and `search_authors()`: pass `size_limit` to the lambda call: `SELECT_SQL_QUERY.get(search_area)(locale, False, genre_filter, year_filter, size_limit)`.
- `search_pop_books()`: replace the `less800`/`more800` block with:
  ```python
  if size_limit and size_limit.strip():
      size_conditions = DatabaseBooks.build_size_filter_condition(size_limit)
      if size_conditions:
          conditions.append(f"({size_conditions})")
  ```
- `build_sql_where_ft()`: **remove** the `if size_limit: conditions.append(f"BookSizeCat = '{size_limit}'")` block. Keep the `size_limit` parameter for signature compatibility with a comment that size is now handled in the inner query.
- Clear `_class_cached_size_bins = None` in `invalidate_db_cache()` (alongside `_class_cached_year_bins`).
- Add `invalidate_size_bins_cache()` (optional, mirrors `invalidate_year_bins_cache`).

### 2. `app/constants.py`
- Remove the `SETTING_SIZE_LIMIT` entry from `SETTING_OPTIONS` (no longer used — the keyboard is now DB-driven). Keep `SETTING_SIZE_LIMIT` and its `SETTING_TITLES` mapping.

### 3. `app/handlers_settings.py`
- Import `format_size` from `.tools`.
- Rewrite `handle_set_size_limit()` to the multi-select pattern (mirror `handle_set_year_filter`): fetch `DB_BOOKS.get_size_bins()`, parse `user_params.BookSize` into a selected set, build `all_bin_ids` including orphaned stored ids, call `create_size_filter_keyboard()`.
- Add `handle_toggle_size()` (mirror `handle_toggle_year`): toggle bin_id in `BookSize`, `update_user_params(context, BookSize=new_filter)`, refresh keyboard, log via `structured_logger.log_settings_change`.
- Add `handle_clear_all_sizes()` (mirror `handle_clear_all_years`): set `BookSize=''`, refresh keyboard, log.
- Add `get_size_bin_display(bin_id: str, context) -> str`:
  ```python
  def get_size_bin_display(bin_id: str, context) -> str:
      if bin_id.startswith('>'):
          return f">{format_size(int(bin_id[1:]))}"
      if '-' in bin_id:
          lower, upper = bin_id.split('-', 1)
          lower, upper = int(lower), int(upper)
          if lower == 0:
              return f"<{format_size(upper)}"
          return f"{format_size(lower)}-{format_size(upper)}"
      return bin_id  # legacy/unrecognized
  ```
- Add `create_size_filter_keyboard(size_bins, selected_bins, all_bin_ids, context)` (mirror `create_year_filter_keyboard`): two buttons per row, ✔ for selected, book counts, dedupe via a `rendered` set, orphaned stored filters section, "Clear all sizes" button when selections exist, back button. Callback data: `toggle_size:{bin_id}`, `clear_all_sizes`.
- Update `create_settings_menu()` `SETTING_SIZE_LIMIT` branch (currently iterates `SETTING_OPTIONS`) to a count badge like genre/year filter:
  ```python
  elif setting_type == SETTING_SIZE_LIMIT:
      current_value = user_params.BookSize
      if current_value:
          size_count = len([s for s in current_value.split(',') if s])
          current_display = f"({size_count})" if size_count else ""
  ```

### 4. `app/handlers_callback.py`
- Import `handle_toggle_size`, `handle_clear_all_sizes` (and the rewritten `handle_set_size_limit`).
- `f'set_{SETTING_SIZE_LIMIT}': handle_set_size_limit` already registered — now points to the rewritten handler.
- Add `if action == 'toggle_size':` → `handle_toggle_size(...)`.
- Add `if action == 'clear_all_sizes':` → `handle_clear_all_sizes(...)`.

### 5. `app/handlers_search.py`
- No change needed: `user_params.BookSize` is already passed as `size_limit` to all search methods. The field's *content* changes from `less800`/`more800` to bin ids, but the plumbing is identical.

### 6. `app/i18n/translations/en.yaml` and `ru.yaml`
- Add under `common:`:
  - en: `clear_all_sizes: "🗑️ Clear all sizes"`
  - ru: `clear_all_sizes: "🗑️ Очистить все размеры"`
- Size bin labels are derived from `format_size()`, so no per-bin i18n keys are needed. `settings.menu.size_limit` already exists.

### 7. `app/main.py`
- Preload size bins at startup (alongside year bins): `DB_BOOKS.get_size_bins()` in a try/except with a `structured_logger.log_system(...)` call.

### 8. `db_init/zz_sqlite_init_user_settings.sql`
- No change — `BookSize` column already exists; it is repurposed.

## SQL Queries for `get_size_bins()`

**Primary (if PERCENTILE_CONT works on the target DB) — two queries:**

Query 1 — boundaries (user-supplied):
```sql
WITH pct AS (
    SELECT DISTINCT
        PERCENTILE_CONT(0.0) WITHIN GROUP (ORDER BY FileSize) OVER () AS p0,
        PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY FileSize) OVER () AS p10,
        PERCENTILE_CONT(0.2) WITHIN GROUP (ORDER BY FileSize) OVER () AS p20,
        PERCENTILE_CONT(0.3) WITHIN GROUP (ORDER BY FileSize) OVER () AS p30,
        PERCENTILE_CONT(0.4) WITHIN GROUP (ORDER BY FileSize) OVER () AS p40,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY FileSize) OVER () AS p50,
        PERCENTILE_CONT(0.6) WITHIN GROUP (ORDER BY FileSize) OVER () AS p60,
        PERCENTILE_CONT(0.7) WITHIN GROUP (ORDER BY FileSize) OVER () AS p70,
        PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY FileSize) OVER () AS p80,
        PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY FileSize) OVER () AS p90
    FROM cb_libbook
    WHERE deleted = 0
)
SELECT p0, p10, p20, p30, p40, p50, p60, p70, p80, p90 FROM pct
```

Query 2 — per-bin counts (build the CASE from the 10 boundaries `b0..b9`):
```sql
SELECT
    CASE
        WHEN COALESCE(FileSize,0) < {b1} THEN '{b0}-{b1}'
        WHEN COALESCE(FileSize,0) < {b2} THEN '{b1}-{b2}'
        WHEN COALESCE(FileSize,0) < {b3} THEN '{b2}-{b3}'
        WHEN COALESCE(FileSize,0) < {b4} THEN '{b3}-{b4}'
        WHEN COALESCE(FileSize,0) < {b5} THEN '{b4}-{b5}'
        WHEN COALESCE(FileSize,0) < {b6} THEN '{b5}-{b6}'
        WHEN COALESCE(FileSize,0) < {b7} THEN '{b6}-{b7}'
        WHEN COALESCE(FileSize,0) < {b8} THEN '{b7}-{b8}'
        WHEN COALESCE(FileSize,0) < {b9} THEN '{b8}-{b9}'
        ELSE '>{b9}'
    END AS bin_id,
    COUNT(*) AS books_count
FROM cb_libbook
WHERE deleted = 0
GROUP BY bin_id
```

**Fallback (MariaDB-safe) — single NTILE query:** see the Risk section above. Convert each tile row to `(bin_id, books_count)` where `bin_id = f"{min_size}-{max_size}"` for tiles 1..9 and `f">{max_size}"` for tile 10.

## Implementation Order
1. **Verify** the PERCENTILE_CONT boundary query runs on the actual MariaDB 12.0 instance; choose primary vs NTILE fallback.
2. Add `_class_cached_size_bins` and `get_size_bins()` to `DatabaseBooks`.
3. Add `build_size_filter_condition()` and `_build_size_sql()` static methods.
4. Add `size_filter` to the three inner-query lambdas and `{DatabaseBooks._build_size_sql(size_filter)}` to each.
5. Add `size_filter` to `build_sql_query_books()`; thread `size_limit` through `search_books`, `search_series`, `search_authors`.
6. Replace the `less800`/`more800` block in `search_pop_books()` with `build_size_filter_condition()`.
7. Remove the `BookSizeCat` condition from `build_sql_where_ft()`.
8. Clear `_class_cached_size_bins` in `invalidate_db_cache()`.
9. Remove `SETTING_OPTIONS[SETTING_SIZE_LIMIT]` from `constants.py`.
10. Add `common.clear_all_sizes` to both YAML files.
11. Add handlers in `handlers_settings.py`: `handle_set_size_limit` (rewrite), `handle_toggle_size`, `handle_clear_all_sizes`, `get_size_bin_display`, `create_size_filter_keyboard`; update `create_settings_menu()` count badge.
12. Register `toggle_size` / `clear_all_sizes` in `handlers_callback.py`.
13. (Optional) Add a one-time startup migration in `DatabaseSettings` to blank legacy `BookSize` values of `less800`/`more800` (pattern: the commented-out `_ensure_year_filter_column`).
14. Preload size bins in `main.py` startup.

## Verification
- Settings menu shows "Book size limit (N)" with count of selected intervals.
- Clicking opens a keyboard with 10 size bins showing book counts, labels like `<88.8K`, `88.8K-306.6K`, …, `>5.5M`.
- Selected bins show ✔; two buttons per row.
- "Clear all sizes" button appears when selections exist; back button returns to settings.
- Selected size filter is applied to book, series, author, and popular searches.
- Multiple intervals can be selected simultaneously (OR between bins, AND with other filters).
- Filter persists across sessions (stored in `UserSettings.BookSize`).
- After a DB update, previously saved ranges still work (stored bin ids generate direct `b.FileSize` conditions regardless of current bin calculation); orphaned filters still display as selected.
- Legacy `less800`/`more800` values do not break searches (skipped by the condition builder).
- Size bins are cached, invalidated on DB update, and preloaded at startup.
- Confirm no SQL error when `BookSize` contains an unrecognized value.

## Open Questions / Notes
- **PERCENTILE_CONT compatibility** is the top risk — resolve via Verification step 1; NTILE(10) fallback is ready.
- Bins are fixed at 10 (matching the supplied query). If a configurable bin count is wanted later, the boundary query must be regenerated for `N` percentiles.
- `format_size()` yields one-decimal labels (`88.8K`). Integer labels (`90K`) would require a `format_size()` change — out of scope.
- Consider a separate "0 (unknown)" bin if `FileSize = 0` books are numerous and semantically distinct; not requested, so all `FileSize = 0` books currently fall in the first bin.
