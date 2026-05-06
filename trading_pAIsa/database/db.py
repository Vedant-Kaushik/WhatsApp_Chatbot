"""Database connection and initialization for pAIsa trading system.

Provides:
- Database connection with foreign keys enabled
- Schema initialization for all 3 tables
- Helper functions for validation
"""
import sqlite3
import os
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), 'market_db.sqlite3')

def get_db():
    """Get SQLite database connection with foreign keys enabled.

    Returns:
        sqlite3.Connection: Connection object with row_factory
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return dictionaries from queries
    conn.execute("PRAGMA foreign_keys = ON")  # Enforce foreign key constraints
    return conn

def init_db():
    """Initialize database schema if not exists.

    Creates all 3 tables:
    1. instruments - Market master cache
    2. historical_candles - OHLCV data cache
    3. trade_signals - AI recommendation logging

    Safe to call multiple times.
    """
    conn = get_db()

    # 1. instruments table
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

    # 2. historical_candles table with foreign key and unique constraint
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
            FOREIGN KEY(instrument_key) REFERENCES instruments(instrument_key)
        );
    """)

    # 3. trade_signals table - FOR BACKTRACKING AI RECOMMENDATIONS
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trade_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instrument_key TEXT NOT NULL,
            signal_type TEXT NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
            recommended_amount INTEGER NOT NULL,
            ltp_at_signal REAL NOT NULL,
            stock_name TEXT NOT NULL,
            reasoning TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)

    # Create indexes for performance
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_historical_candles_unique
        ON historical_candles(instrument_key, timestamp);
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_trade_signals_date
        ON trade_signals(created_at);
    """)

    conn.commit()
    conn.close()

    print(f"Trading database initialized at: {DB_PATH}")

def instrument_exists(instrument_key: str) -> bool:
    """Check if instrument metadata is already cached in database.

    Args:
        instrument_key: e.g., 'NSE_EQ|INE467B01029'

    Returns:
        bool: True if exists
    """
    conn = get_db()
    cursor = conn.execute(
        "SELECT 1 FROM instruments WHERE instrument_key = ?",
        (instrument_key,)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None

# Test database on import - quick validation
if __name__ == "__main__":
    init_db()
    print(" Database setup validated successfully")