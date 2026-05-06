## 1. Overview

Replace the volatile in-memory `STOCK_CACHE` with a robust SQLite database for **pAIsa**.

This step establishes the **data layer foundation** for pAIsa. Moving to a persistent database is required to:

1. Cache Upstox market data and prevent API rate-limiting.
2. Store AI trade signals to measure the bot's accuracy over time.

---

## 2. Depends on

Nothing — this is the first architectural step to upgrade pAIsa from a prototype to a reliable application.

---

## 3. Database Schema

### A. instruments (Market Master Cache)

*Stores the target keys so we don't have to download the massive JSON from Upstox constantly.*

| Column         | Type | Constraints                                |
| -------------- | ---- | ------------------------------------------ |
| instrument_key | TEXT | Primary key (e.g., 'NSE_EQ\|INE467B01029') |
| trading_symbol | TEXT | Not null (e.g., 'TCS')                     |
| segment        | TEXT | Not null                                   |
| exchange       | TEXT | Not null                                   |
| last_updated   | TEXT | Default datetime('now')                    |

---

### B. historical_candles (Market Data Cache)

*Stores OHLCV (Open, High, Low, Close, Volume) data to instantly load charts and indicators without hitting Upstox.*

| Column               | Type    | Constraints                                           |
| -------------------- | ------- | ----------------------------------------------------- |
| id                   | INTEGER | Primary key, autoincrement                            |
| instrument_key       | TEXT    | Foreign key → instruments.instrument_key, not null   |
| timestamp            | TEXT    | Not null (ISO 8601 format)                            |
| open                 | REAL    | Not null                                              |
| high                 | REAL    | Not null                                              |
| low                  | REAL    | Not null                                              |
| close                | REAL    | Not null                                              |
| volume               | INTEGER | Not null                                              |
| **Constraint** | UNIQUE  | `(instrument_key, timestamp)` to prevent duplicates |

---

### C. trade_signals (AI Prediction Log)

*Logs exactly what pAIsa recommended and why, allowing you to backtest if the AI is actually profitable.*

| Column         | Type    | Constraints                                         |
| -------------- | ------- | --------------------------------------------------- |
| id             | INTEGER | Primary key, autoincrement                          |
| instrument_key | TEXT    | Foreign key → instruments.instrument_key, not null |
| signal_type    | TEXT    | Not null (BUY / SELL / HOLD)                        |
| ltp_at_signal  | REAL    | Not null (The price when AI made the decision)      |
| reasoning      | TEXT    | Not null (The LLM's justification)                  |
| created_at     | TEXT    | Default datetime('now')                             |

---

## 4. Functions to Implement (`database/db.py`)

### A. `get_db()`

- Opens connection to `pAIsa.db` in the project root.
- Sets:
  - `row_factory = sqlite3.Row`
  - `PRAGMA foreign_keys = ON`
- Returns the connection.

### B. `init_db()`

- Creates all 3 tables using `CREATE TABLE IF NOT EXISTS`.
- Safe to call multiple times.
- Ensures schema is ready before app usage.

---

## 5. Changes to Application Flow

- **Startup:** Call `init_db()` when the FastAPI app starts.
- **Data Fetching:** Modify `preload_historical_data` to *first* check the `instruments` and `historical_candles` tables. Only fetch missing dates from Upstox API, then save the new data to the DB.

---

## 6. Files to Create / Change

- **[NEW]** `database/db.py` → Connection and schema setup.
- **[NEW]** `database/market_repo.py` → Helper functions to insert/read candles and instruments safely.
- **[MODIFY]** `upstox_analysis.py` → Remove `STOCK_CACHE` and import database functions.

---

## 7. Rules for Implementation

- **No ORMs:** Use standard library `sqlite3` (no SQLAlchemy).
- **Parameterized Queries Only:** Never use string formatting in SQL (prevents SQL injection).
- **Foreign Keys:** Enable `PRAGMA foreign_keys = ON` on every connection.
- **Timestamps:** Dates must follow strictly **ISO 8601 format** (YYYY-MM-DDTHH:MM:SS) for easy sorting.

---

## 8. Definition of Done

- [ ] `pAIsa.db` file is generated automatically on app startup.
- [ ] All 3 tables exist with correct schema and constraints.
- [ ] Attempting to insert duplicate candles for the same timestamp fails gracefully.
- [ ] App starts without errors and the in-memory dictionary is completely removed.
