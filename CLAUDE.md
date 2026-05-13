# CLAUDE.md
This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Core Development Commands

- **Install Dependencies**: `uv sync`
  - Installs all project dependencies using uv package manager

- **Install pre-commit hooks** (if project uses git hooks):
  ```bash
  pre-commit install
  ```

### Running the WhatsApp Chatbot (Local Development)

```bash
# 1. Start PostgreSQL (if not running via Docker)
# macOS: brew services start postgresql@16
# Linux: sudo systemctl start postgresql

# 2. Set up environment variables in .env file
# See README.md section on Meta/Facebook and Google AI credentials

# 3. Install dependencies
uv sync

# 4. Run the FastAPI server
uv run uvicorn main:app --host 0.0.0.0 --port 5173

# 5. In a separate terminal, start ngrok for webhook tunneling
ngrok http 5173
```

> **Note**: Update the Meta Developer console with your ngrok webhook URL (`https://<subdomain>.ngrok-free.app/webhook/meta`) and verifier token.

### Running pAIsa Trading Dashboard (Local Development)

```bash
# Ensure UPSTOX_ACCESS_TOKEN is in .env or environment
# Recommended Upstox access tokens are long-lived development tokens

# Run the pAIsa dashboard
uv run uvicorn trading_pAIsa.main:app --host 0.0.0.0 --port 8000
```

Access at: `http://localhost:8000`

### Running via Docker (Recommended for Production-Style Testing)

This starts both PostgreSQL and the WhatsApp bot:
```bash
docker-compose up --build
```
- Docker Compose automatically initializes the PostgreSQL database
- Waits for PostgreSQL to be ready (health check)
- Initializes LangGraph checkpoint tables automatically
- Mounts `vector_stores/` and `temp_downloads/` directories for persistence

### Database Operations

```bash
# pAIsa SQLite Database (local)
# File: trading_pAIsa/database/market_db.sqlite3
# No migrations needed - schema is created automatically on first run
# Table schema is defined in trading_pAIsa/database/db.py:init_db()

# WhatsApp PostgreSQL Database (if used)
# Connection string: postgresql://postgres:postgres@localhost:5432/postgres
# Tables initialized by LangGraph automatically
```

### Running Tests / Experimentation

- The project uses Jupyter Notebooks for testing and experimentation
- Example notebooks:
  - `test_upstox.ipynb` - Tests pAIsa analysis capabilities
  - `upstox_clean.ipynb` - Upstox API testing
  - `tavily.ipynb` - Tavily search API testing

Run notebooks with:
```bash
uv run jupyter notebook notebook_name.ipynb
```

---

## High-Level Code Architecture


### 1. WhatsApp Chatbot Core (`main.py`)

The main WhatsApp chatbot entry point using LangGraph for stateful, memory-aware AI:

- **Framework**: FastAPI (asynchronous web framework)
- **AI Orchestration**: LangGraph (state management, tool routing, memory, summarization)
- **AI Model**: Google Gemini 2.5 Flash via LangChain
- **State & Memory**: PostgreSQL-backed
  - `PostgresSaver`: Short-term state via LangGraph thread checkpoints
  - `PostgresStore`: Long-term user memory (extracts factual details across conversations)
- **Capabilities**:
  - PDF document analysis (Chroma vector store)
  - Real-time web search (TavilySearch tool)
  - Message formatting optimized for WhatsApp (custom formatting agents)
  - Memory extraction and persistent user context
- **Entry Point**: `uv run uvicorn main:app --host 0.0.0.0 --port 5173`

### 2. pAIsa: The Upstox Investment Analyst (`trading_pAIsa/`)

a dedicated stock analysis dashboard extracted into its own module:

- **Framework**: FastAPI
- **AI Model**: Google Gemini 2.5 Flash (for recommendation generation)
- **Market Data**: Upstox API V3
- **Database**: SQLite (local, high-performance cache)
- **Caching Architecture**:
  - Instrument master cache prevents repeated API calls
  - Historical candles cache (monthly data from Jan 2025 onwards)
  - Prevents rate limiting while enabling instant dashboard loading
- **Data Flow**:
  1. Startup: Downloads instrument master (NSE, BSE) and caches historical candles
  2. User analysis: Loads from cache, fetches only live prices (fast LTP calls)
  3. AI analysis: Generates strategically-filtered recommendation
  4. Signal logging: Persists every recommendation in `trade_signals` table for backtesting
- **Technical Analysis**: Python-based calculations (SMA, ATR, trend analysis, support/resistance)
- **Charting**: Plotly.js (professional candlestick charts with indicators)
- **Frontend**: Jinja2 templates (plain HTML/CSS/JS for maximum performance)
- **User Management**: Registration/login with preferences storage (default investment amount/time horizon)

#### pAIsa Module Structure
```
trading_pAIsa/
├── main.py                    # FastAPI application entry
├── database/
│   ├── db.py                  # SQLite database initialization & helpers
│   ├── market_repo.py         # Repository: instruments, candles, trade signals
│   └── market_db.sqlite3      # Local SQLite database file (~350MB cached data)
├── upstox_core/
│   ├── __init__.py
│   └── ...                   # (May contain additional core logic)
└── README.md                 # Detailed module-specific documentation
```

### 3. Prompt Configuration (`prompts.json`)

All system prompts decoupled for easy editing:
- `system_prompt`: Core WhatsApp assistant persona and formatting rules
- `pdf_prompt`: Document analysis instructions with strict context adherence
- `memory_prompt`: User memory extraction and management for long-term context retention

Formatting follows WhatsApp native format (asterisks for bold, underscores for italics) rather than Markdown.

---

## Database Design

### pAIsa SQLite (Trading Analyst)

Three core tables in `trading_pAIsa/database/market_db.sqlite3`:

1. **instruments** - Market master cache
   - `instrument_key`, `trading_symbol`, `segment`, `exchange`, `last_updated`
   - Purpose: Cache NSE and BSE instrument metadata to avoid repeated API calls

2. **historical_candles** - OHLCV data cache
   - `instrument_key`, `timestamp`, `open`, `high`, `low`, `close`, `volume`
   - Purpose: Cache monthly candle data from Jan 2025 onwards (300K++ rows)
   - Foreign key to instruments

3. **trade_signals** - AI recommendation logging
   - `id`, `instrument_key`, `signal_type`, `recommended_amount`, `ltp_at_signal`, 
     `stock_name`, `reasoning`, `created_at`
   - Purpose: Persistent logging for post-trade analysis and backtesting

Database initialization is automatic and idempotent - safe to call on every startup.

---

## Key Features by Module

### WhatsApp Bot Core Features

1. **Conversational Memory**: 
   - Infinite context via LangGraph thread checkpoints
   - Automatic summarization after 10+ messages
   - Long-term memory extraction via `PostgresStore` (permanent storage of user facts)

2. **Document Analysis**:
   - PDF upload → Chroma vectorization → persistent storage
   - Multi-query context retrieval with MMR (Maximal Marginal Relevance)
   - Answer questions about uploaded documents

3. **Real-Time Search**:
   - Tavily AI web search integration
   - Automatic query routing when seeking current information
   - Response formatting optimized for WhatsApp

4. **User Commands**:
   - `/clear` - Reset conversation history and memory
   - PDF upload - Analyze document
   - Direct text - Normal conversation

### pAIsa Dashboard Features

1. **Registration & Preferences**:
   - User accounts with default investment amount/time horizon storage
   - Browser cookie-based authentication (simple, no session db required)
   - Personalized analysis based on saved defaults

2. **Smart Candidate Selection**:
   - Filters Nifty 50 stocks only
   - Retrieves instrument master (NSE + BSE cached)
   - Loads historical candles from cache (15+ months by default)

3. **Real-Time Analysis**:
   - Strategy-based filtering: 6 months → select lowest ATR (volatility), 12+ months → highest return
   - Live price fetch via Upstox API (fast LTP calls)
   - Technical indicators: SMA, ATR, trend analysis, support/resistance

4. **Professional Visualization**:
   - Plotly.js candlestick chart
   - Volume overlaid below
   - 3-month SMA indicator line
   - Horizontal support/resistance levels
   - Professional dark theme

5. **AI Recommendations**:
   - Google Gemini 2.5 Flash recommendation generation
   - Personalized 3-4 sentence analysis explaining fit for user's amount/time horizon
   - Persistent logging in trade_signals table for backtesting
6. **Caching Architecture**:
   - Instrument master: Persistent across sessions
   - Historical candles: Persistent across sessions (full year+)
   - Live pricing: Quick LTP calls, minimal API usage
   - Database auto-initialization prevents cold starts

---

## Technical Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **Backend** | FastAPI | High-performance Python web framework |
| **AI Model** | Google Gemini 2.5 Flash | Via LangChain |
| **Orchestration** | LangGraph | Stateful agents, memory, tool routing |
| **WhatsApp** | PyWa / Meta WhatsApp API | Official Business API |
| **Memory** | PostgreSQL | Long-term user memory storage |
| **State** | PostgreSQL | LangGraph checkpoints via `PostgresSaver` |
| **Vector Store** | ChromaDB | PDF document embeddings on disk |
| **Search** | Tavily AI | Real-time web search integration |
| **pAIsa Database** | SQLite | Local high-performance cache |
| **Caching** | Local caching | Market master + historical data |
| **Charts** | Plotly.js | Professional technical analysis charts |
| **Frontend** | Jinja2 + Vanilla HTML5/CSS3/JS | Fast, simple, no build step |
| **Market Data** | Upstox API V3 | Indian market data provider |
| **Package Manager** | uv | Python package and dependency manager |
| **Container** | Docker | Recommended deployment |
| **AI Prompts** | JSON (prompts.json) | Decoupled, easy to edit |

---

## Environment Variables

### WhatsApp Bot (Required)
```
# Meta/Facebook Developer Settings
PHONE_ID=
WHATSAPP_TOKEN=
CALLBACK_URL=
VERIFY_TOKEN=
APP_ID=
APP_SECRET=
WABA_ID=

# AI & Search
GOOGLE_API_KEY=
TAVILY_API_KEY=

# Database (non-Docker only)
DB_URI=postgresql://postgres:postgres@localhost:5432/postgres
```

### pAIsa Dashboard (Required)
```
UPSTOX_API_KEY=
UPSTOX_API_SECRET=
UPSTOX_REDIRECT_URI=
UPSTOX_ACCESS_TOKEN=
GOOGLE_API_KEY=
```

> **Note**: Semi-automated Onboarding: Ensure `ACCESS_TOKEN` is set in environment for pAIsa; the Chatbot uses separate API keys.

---

## Project Structure Summary

```
.
├── main.py                          # WhatsApp bot entry (FastAPI + LangGraph)
├── trading_pAIsa/                   # pAIsa investment analyst (FastAPI)
│   ├── main.py                       # pAIsa FastAPI app entry
│   ├── database/
│   │   ├── db.py                      # SQLite setup: instruments, candles, trade_signals
│   │   ├── market_repo.py             # CRUD operations for market data
│   │   └── market_db.sqlite3          # Cached market data (~350MB)
│   ├── upstox_core/                 # Upstox integrations
│   └── README.md                    # pAIsa-specific docs
├── prompts.json                      # WhatsApp system prompts
├── templates/                       # Jinja2 HTML templates
│   ├── frontend_upstox.html
│   ├── login.html
│   └── signup.html
├── docker-compose.yml               # Docker multi-service setup
├── pyproject.toml                   # uv project configuration
├── uv.lock                         # uv dependency lock
└── .env                            # Environment variables
```