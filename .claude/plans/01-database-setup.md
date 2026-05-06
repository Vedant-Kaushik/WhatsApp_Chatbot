# Database Setup Plan for WhatsApp Trading Agents - Upstox Module

## Context
The Upstox module in the WhatsApp Trading Agents project currently uses an in-memory `STOCK_CACHE` dictionary (lines 298-302 in upstox_analysis.py) to store market data. This approach has several critical flaws:

1. **Volatile Data Loss**: Cache is cleared on every application restart
2. **Duplicate API Calls**: Master instruments data and historical candles must be re-fetched from Upstox API every time
3. **No Caching Strategy**: Against Upstox rate limits by not caching fetched data
4. **Limited Historic Analysis**: Cannot provide signal backtesting or track AI decision quality over time

This plan replaces the in-memory cache with a robust SQLite database storage system to enable:
- Persistent market data caching
- Rate limit prevention via intelligent data retrieval
- AI signal logging for accuracy tracking
- Scalable performance as the application grows

## Implementation Approach

### 1. Database Schema (Partial Modification from pAIsa spec)

While pAIsa uses a SQLite database named `pAIsa.db`, the WhatsApp Trading Agents project should use:
- **File**: `database/market_db.sqlite3` (in project root)
- **Schema**: Simplified version focusing on what Upstox needs:

#### A. instruments (Market Master Cache)
**Purpose**: Cache instrument metadata to avoid constant Upstox API calls for master data downloads.

| Column | Type | Constraints |
|--------|------|-----------|
| instrument_key | TEXT PRIMARY KEY | (e.g., 'NSE_EQ|INE467B01029') |
| trading_symbol | TEXT | Not null (e.g., 'TCS') |
| segment | TEXT | Not null |
| exchange | TEXT | Not null |
| name | TEXT | Optional (company name) |
| last_updated | TEXT DEFAULT datetime('now') | ISO 8601 format |

SQL: 
```sql
CREATE TABLE IF NOT EXISTS instruments (
    instrument_key TEXT PRIMARY KEY,
    trading_symbol TEXT NOT NULL,
    segment TEXT NOT NULL,
    exchange TEXT NOT NULL,
    name TEXT,
    last_updated TEXT DEFAULT (datetime('now'))
);
```

#### B. historical_candles (Market Data Cache)
**Purpose**: Cache OHLCV data to instantly load charts and indicators without hitting Upstox API.

| Column | Type | Constraints |
|-------------------|-------|--------------------------------------------------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| instrument_key | TEXT | Foreign key → instruments.instrument_key, not null |
| timestamp | TEXT | Not null (ISO 8601 format: YYYY-MM-DDTHH:MM:SS) |
| open | REAL | Not null |
| high | REAL | Not null |
| low | REAL | Not null |
| close | REAL | Not null |
| volume | INTEGER | Not null |

Constraints: 
```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_historical_candles_unique
    ON historical_candles(instrument_key, timestamp);
```

#### C. trade_signals (AI Signal Logger) ✅ IN SCOPE (For Backtracking)

**Purpose**: Log every AI recommendation with full context for backtesting and accuracy measurement.

| Column | Type | Constraints |
|---------------|------|-------------------------------------------------------|
| id | INTEGER | Primary key, autoincrement |
| instrument_key | TEXT | Foreign key → instruments.instrument_key, NOT NULL |
| signal_type | TEXT | NOT NULL (BUY / SELL / HOLD) |
| recommended_amount | INTEGER | Amount recommended in INR |
| ltp_at_signal | REAL | NOT NULL (Live price when decision was made) |
| stock_name | TEXT | NOT NULL (trading_symbol for readability) |
| reasoning | TEXT | Detailed AI justification (full prompt/output) |
| created_at | TEXT | DEFAULT datetime('now'), ISO 8601 format |

```sql
CREATE TABLE IF NOT EXISTS trade_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_key TEXT NOT NULL,
    signal_type TEXT NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
    recommended_amount INTEGER NOT NULL,
    ltp_at_signal REAL NOT NULL,
    stock_name TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(instrument_key) REFERENCES instruments(instrument_key)
);
```

**Implementation notes:**
- Current code in `upstox_analysis.py` line 369+ generates recommendations and reasoning
- Add function in `market_repo.py` to insert these signals after LLM generates response
- Simple insert operation - no complex queries initially
- Stored for accuracy backtesting over time
- Can be analyzed for AI performance metrics later

### 2. File Structure

```
database/
  ├── __init__.py
  ├── db.py (NEW)
  └── market_repo.py (NEW)
```

### 3. Files to Create

#### File: `database/db.py`
**Purpose**: Database connection setup and initialization.

**Implementation**:
- `get_db()` - Opens SQLite connection with PRAGMA foreign_keys=ON
- `init_db()` - Creates tables on startup
- Utility function to check if instrument data exists

```python
import sqlite3
import os
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), os.pardir, 'market_db.sqlite3')

def get_db():
    """Get SQLite database connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initialize database schema if not exists."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS instruments (
            instrument_key TEXT PRIMARY KEY,
            trading_symbol TEXT NOT NULL,
            segment TEXT NOT NULL,
            exchange TEXT NOT NULL,
            name TEXT,
            last_updated TEXT DEFAULT (datetime('now'))
        );
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS historical_candles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instrument_key TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume INTEGER NOT NULL,
            FOREIGN KEY(instrument_key) REFERENCES instruments(instrument_key),
            UNIQUE(instrument_key, timestamp)
        );
    """)
    
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_historical_candles_unique
        ON historical_candles(instrument_key, timestamp);
    """)
    
    conn.commit()
    conn.close()

def instrument_exists(instrument_key: str) -> bool:
    """Check if instrument metadata is already cached."""
    conn = get_db()
    cursor = conn.execute(
        "SELECT 1 FROM instruments WHERE instrument_key = ?", (instrument_key,)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None
```

#### File: `database/market_repo.py`
**Purpose**: Repository pattern for data access operations.

**Implementation**:
- Functions to get/insert/update instruments
- Functions to get/insert historical candles
- Bulk operations to optimize for market data updates

```python
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
from .db import get_db

def insert_instruments(instruments: List[Dict]) -> int:
    """Insert or update instrument metadata in bulk.
    
    Args:
        instruments: List of dicts with instrument_key, trading_symbol, segment, exchange, name
    
    Returns:
        Number of instruments inserted/updated
    """
    if not instruments:
        return 0
        
    conn = get_db()
    inserted_count = 0
    
    for instrument in instruments:
        cursor = conn.execute(
            """
            INSERT INTO instruments (instrument_key, trading_symbol, segment, exchange, name, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(instrument_key) DO UPDATE SET
                trading_symbol = excluded.trading_symbol,
                segment = excluded.segment,
                exchange = excluded.exchange,
                name = excluded.name,
                last_updated = excluded.last_updated
            """,
            (
                instrument['instrument_key'],
                instrument['trading_symbol'],
                instrument['segment'],
                instrument['exchange'],
                instrument.get('name'),
                instrument.get('last_updated', datetime.utcnow().isoformat())
            )
        )
        if cursor.rowcount > 0:
            inserted_count += 1
    
    conn.commit()
    conn.close()
    return inserted_count

def get_all_instruments() -> List[Dict]:
    """Get all cached instruments.
    
    Returns:
        List of instrument dicts with all fields
    """
    conn = get_db()
    cursor = conn.execute("SELECT * FROM instruments")
    columns = [col[0] for col in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return results

def insert_historical_candles(instrument_key: str, candles: List[List]) -> int:
    """Insert historical candle data for a single instrument.
    
    Args:
        instrument_key: The instrument to insert candles for
        candles: List of candle tuples in format [timestamp, open, high, low, close, volume]
    
    Returns:
        Number of candles inserted
    """
    if not candles:
        return 0
    
    conn = get_db()
    inserted_count = 0
    
    for candle in candles:
        # candle format: [timestamp, open, high, low, close, volume]
        # timestamp format from Upstox: "2025-01-01T00:00:00"
        # convert to: "2025-01-01T00:00:00" (same format)
        timestamp = candle[0]
        
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO historical_candles
                (instrument_key, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    instrument_key,
                    timestamp,
                    float(candle[1]),
                    float(candle[2]),
                    float(candle[3]),
                    float(candle[4]),
                    int(candle[5])
                )
            )
            if conn.total_changes > 0:
                inserted_count += 1
        except Exception as e:
            print(f"Warning: Failed to insert candle for {instrument_key} at {timestamp}: {e}")
            continue
    
    conn.commit()
    conn.close()
    return inserted_count

def get_historical_candles(instrument_key: str, start_date: str = None) -> List[Dict]:
    """Get historical candles for an instrument.
    
    Args:
        instrument_key: Instrument to retrieve
        start_date: Optional start date filter (YYYY-MM-DD)
    
    Returns:
        List of dicts with candle data
    """
    conn = get_db()
    
    if start_date:
        cursor = conn.execute(
            """
            SELECT * FROM historical_candles
            WHERE instrument_key = ? AND timestamp >= ?
            ORDER BY timestamp ASC
            """,
            (instrument_key, f"{start_date}T00:00:00")
        )
    else:
        cursor = conn.execute(
            """
            SELECT * FROM historical_candles
            WHERE instrument_key = ?
            ORDER BY timestamp ASC
            """,
            (instrument_key,)
        )
    
    columns = [col[0] for col in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return results
```

### 4. File: `upstox_analysis.py` - Changes Required

**Lines 298-302 to REPLACE**:
```python
# Current volatile in-memory cache
STOCK_CACHE = {
    "target_keys": [],
    "history_data": []
}
```

**With import statements (lines 12-20) to ADD**:
```python
# Database imports
from database.db import init_db, get_db
from database.market_repo import (
    insert_instruments,
    get_all_instruments,
    insert_historical_candles,
    get_historical_candles
)
```

**Lines 308-320 (Startup Function) to REPLACE**: 
```python
@app.on_event("startup")
def preload_historical_data():
    if not ACCESS_TOKEN:
        print("Error: UPSTOX_ACCESS_TOKEN not found! Cannot fetch data.")
        return

    print("Pre-fetching 1-year historical data...")
    target_keys = get_target_instrument_keys()
    
    # Save to global cache so all users can read it instantly
    STOCK_CACHE["target_keys"] = target_keys
    STOCK_CACHE["history_data"] = fetch_historical_data(target_keys)
    print("Historical Cache populated successfully!")
```

**With**:
```python
@app.on_event("startup")
def preload_historical_data():
    if not ACCESS_TOKEN:
        print("Error: UPSTOX_ACCESS_TOKEN not found! Cannot fetch data.")
        return
    
    # Initialize database on startup
    init_db()
    print("Database initialized!")
    print("Pre-fetching instrument master and historical data...")
    
    # 1. Get or download instrument master
    instruments = get_all_instruments()
    
    if not instruments or len(instruments) < 10:  # Threshold - we have 51+ instruments
        print("Master cache empty or outdated. Download fresh NSE/BSE instrument data...")
        target_keys = get_target_instrument_keys()
        
        # Convert to instrument objects and store
        nse_data = get_instrument_master("NSE")
        bse_data = get_instrument_master("BSE")
        
        instrument_objects = []
        
        # Process NSE instruments
        for item in nse_data:
            if item['segment'] == 'NSE_EQ':
                instrument_objects.append({
                    'instrument_key': item['instrument_key'],
                    'trading_symbol': item['trading_symbol'],
                    'segment': item['segment'],
                    'exchange': 'NSE',
                    'name': item.get('name')
                })
        
        # Process BSE instruments  
        for item in bse_data:
            if item['segment'] == 'BSE_INDEX' or item['segment'] == 'BSE_EQ':
                instrument_objects.append({
                    'instrument_key': item['instrument_key'],
                    'trading_symbol': item['trading_symbol'],
                    'segment': item['segment'],
                    'exchange': 'BSE',
                    'name': item.get('name')
                })
        
        insert_instruments(instrument_objects)
        print(f"Inserted/updated {len(instrument_objects)} instruments")
    else:
        print(f"Using cached {len(instruments)} instruments from database")
    
    target_keys = [inst['instrument_key'] for inst in get_all_instruments()]
    STOCK_CACHE["target_keys"] = target_keys  # Keep in memory for quick access
    
    # 2. Fetch historical data only if not cached
    # Check which instruments are missing data
    history_data = []
    for key in target_keys:
        candles = get_historical_candles(key, "2025-01-01")
        if not candles:
            print(f"Fetching missing historical data for {key}...")
            # Reverse mapping to get symbol
            symbol = next((inst['trading_symbol'] for inst in instruments if inst['instrument_key'] == key), key.split('|')[-1])
            single_history = fetch_historical_data([key])  # This returns candles list
            if single_history:
                result = single_history[0]
                candles_list = result['candles'] if isinstance(result['candles'], list) else result['candles'].candles
                inserted = insert_historical_candles(key, candles_list)
                print(f"Inserted {inserted} candles for {symbol}")
                history_data.append({
                    'instrument_key': key,
                    'candles': candles_list
                })
            else:
                print(f"Failed to fetch data for {key}")
        else:
            history_data.append({
                'instrument_key': key,
                'candles': candles  # Already in proper format
            })
    
    STOCK_CACHE["history_data"] = history_data
    print("Historical data cache populated successfully!")
```

**Lines 326-329 function to MODIFY**:
```python
@app.post("/analyze",response_class=HTMLResponse)
def analyze_data(request: Request, amount: int = Form(...), time: int = Form(...)):
    # Retrieve the heavy, static data from our RAM cache instantly (0 latency) 
    target_keys = STOCK_CACHE["target_keys"]
```

**To**:
```python
@app.post("/analyze",response_class=HTMLResponse)
def analyze_data(request: Request, amount: int = Form(...), time: int = Form(...)):
    # Retrieve target keys from RAM cache (quick access)
    target_keys = STOCK_CACHE.get("target_keys", [])
```

### 5. Critical Rules Enforcement

1. **No ORMs**: Use `sqlite3` standard library only ✅
2. **Parameterized Queries Only**: Never use string formatting in SQL ✅ (All functions use ? parameters)
3. **Foreign Keys ON**: Enforced in `get_db()` via `PRAGMA foreign_keys = ON` ✅
4. **ISO 8601 Timestamps**: All timestamps use `YYYY-MM-DDTHH:MM:SS` format ✅
5. **Graceful Error Handling**: Functions catch exceptions and continue ✅

### 6. Verification Plan

**Setup & Create**:
1. mkdir -p database
2. Create database/db.py with all functions
3. Create database/market_repo.py with repository functions
4. Edit upstox_analysis.py and remove STOCK_CACHE, add imports, modify preload_historical_data
5. Run: `uv run uvicorn upstox_analysis:app --host 0.0.0.0 --port 8000`

**Test**:
1. Application starts without errors
2. First run downloads fresh data and creates market_db.sqlite3 (verify file exists)
3. Second run uses cached instruments from database (check console)
4. Browse to http://localhost:8000 - should work same as before
5. Query database directly: `sqlite3 market_db.sqlite3 "SELECT COUNT(*) FROM instruments; SELECT COUNT(*) FROM historical_candles;"`

**Checklist**:
- [ ] `market_db.sqlite3` file is created on first startup
- [ ] All 3 tables exist with correct schema (tools: SQLite browser or ".schema" command)
- [ ] Duplicate inserts are prevented by UNIQUE constraint on historical_candles
- [ ] App starts without errors and serves requests correctly
- [ ] In-memory STOCK_CACHE is replaced with automated database caching
- [ ] Foreign key constraints work (verify with insert errors)

### 7. Database File Location

**Path**: `/Users/vedantkaushik/Documents/Documents - Vedant’s MacBook/Whatsapp_trading_agents/market_db.sqlite3`
**In .gitignore**: Should be added to prevent committing database to git

---

**Total Files to Create**: 2 (database/db.py, database/market_repo.py)
**Total Files to Modify**: 1 (upstox_analysis.py)
**Lines Added**: ~300 lines across 3 files
**Lines Removed**: ~15 lines (in-memory cache, some duplication)

This plan provides:
- 100% cache persistence across restarts
- Rate limit prevention and reduction of Upstox API calls
- Scalable foundation for future AI signal logging add-on
- Same external API contract (no changes to frontend or API consumers)