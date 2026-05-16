---
title: WhatsApp AI & pAIsa Trading
emoji: 📈
colorFrom: blue
colorTo: green
sdk: docker
dockerfile: Dockerfile.upstox
app_port: 8000
pinned: false
---

# Enterprise AI Chatbot for WhatsApp

**The Easiest, Most Powerful Way to Deploy AI on WhatsApp.**

Turn your WhatsApp business number into a 24/7 intelligent agent. Whether you are a developer looking for a robust foundation or a business owner wanting a "done-for-you" solution, this project delivers an enterprise-grade experience instantly.

## 🚀 Why This Chatbot?

*   **Zero-Friction Setup**: The database initializes automatically on the first run. No complex migrations or SQL scripts needed.
*   **Human-Like Intelligence**: Powered by Google's **Gemini 2.5 Flash**, it understands context, nuance, and intent better than traditional rule-based bots.
*   **Beautiful Responses**: Sends perfectly formatted messages with bold text, lists, and tables that look professional on mobile and desktop.
*   **PDF Document Analysis**: Send any PDF to the bot, and it will instantly read, understand, and answer questions based on its content.
*   **Real-Time Web Search**: Autonomously searches the internet via Tavily when it needs up-to-date information.
*   **Long-Term Memory**: Permanently remembers user-specific facts across conversations using PostgreSQL-backed memory extraction.
*   **Smart Conversation Management**: Automatically summarizes long conversations to maintain infinite context without losing history.
*   **Reliable**: Built on FastAPI, a modern, high-concurrency framework.

---

## 🌩️ Hosted Service (No Coding Required)

**Don't want to manage servers, Docker, or API keys?**

We offer a fully managed **Premium Cloud Tier** for business owners and non-tech users.

*   **We Host Everything**: You just scan a QR code or provide your number.
*   **No Technical Headache**: We handle the technical setup; you handle your customers.
*   **Cost**: **~$25 USD / month** (Base Hosting).
*   **Custom Integrations**: Connecting the bot to *your* specific database, calendar, or CRM is available as a **premium customization service**.

**[Contact us](#)** to get started with the Hosted Tier today.

---

## 🛠️ For Developers (Self-Hosted)

If you prefer to run it yourself, this codebase is open-source and developer-friendly.

### Tech Stack
*   **Framework**: FastAPI (High-performance Python web framework)
*   **AI Model**: Google Gemini 2.5 Flash (via LangChain)
*   **Orchestration**: LangGraph (Stateful agent with tool routing, memory, and summarization)
*   **Database**: PostgreSQL (Conversation checkpoints, long-term memory store)
*   **Vector Store**: ChromaDB (Persistent PDF embeddings on disk)
*   **Web Search**: Tavily (Real-time internet search)
*   **WhatsApp Integration**: PyWa (Verified WhatsApp Business APIs)
*   **Package Manager**: uv
*   **Containerization**: Docker & Docker Compose

### Key Features

#### 📄 PDF Document Analysis
- Upload any PDF to the bot
- Automatic text extraction and vectorization using ChromaDB
- Persistent storage: Ask unlimited questions about the same document
- Smart routing: LLM decides when to query the PDF vs. general chat
- MMR-based retrieval for diverse, relevant results

#### 🌐 Real-Time Web Search
- Integrated Tavily search engine for live internet access
- AI agent autonomously decides when to search the web for current events or missing knowledge
- Extracts, summarizes, and formats answers directly from live sources
- Powered by LangGraph's dynamic ToolNode routing mechanism

#### 🧠 Intelligent Memory Management
- **Conversation Summarization**: After 10+ messages, old messages are summarized and compressed
- **Infinite Context**: Never lose conversation history, even in long chats
- **Thread-based Memory**: Each user has isolated conversation threads
- **Long-Term Memory (LTM)**: Uses `PostgresStore` to extract and permanently save factual details about the user (identity, preferences, goals), routed dynamically via WhatsApp's native `msg.id`
- **Customizable Personas**: All system prompts (core Gentleman AI persona, Memory Extractor, PDF Analyst) are fully decoupled into an easy-to-edit `prompts.json` file

#### 🎯 Production-Ready
- PostgreSQL for reliable state management
- Automatic database and checkpoint table initialization
- Docker Compose for one-command deployment
- Message deduplication to prevent duplicate responses

### Architecture

![LangGraph Architecture](assets/langgraph_architecture.png)

### Fast Setup

**1. Prerequisites**
*   Git
*   Python 3.13+ & [uv](https://docs.astral.sh/uv/)
*   Docker (Optional, but recommended)
*   A Meta Developer Account & WhatsApp Business API credentials

**2. Get Credentials**
You need to fill the `.env` file with secrets from Meta, Google, and Tavily.

*   **Meta/Facebook Developers**:
    1.  Go to [Meta Developers](https://developers.facebook.com/).
    2.  Create an App -> Select **Other** -> **Business** -> **WhatsApp**.
    3.  **API Setup**: In the sidebar, go to **WhatsApp > API Setup**.
        *   Copy **Phone Number ID** (`PHONE_ID`).
        *   **Permanent Access Token**: Go to **Business Settings -> System Users**. Create a System User (Admin role). Click **Add Assets** and assign both your **App** (Full Control) and your **WhatsApp Account** (Full Control). Click **Generate Token**, select your App, and check `whatsapp_business_messaging` and `whatsapp_business_management`. Copy this permanent string (`WHATSAPP_TOKEN`).
    4.  **App Basic Settings**: Go to **App Settings > Basic**.
        *   Copy **App ID** (`APP_ID`) and **App Secret** (`APP_SECRET`).
    5.  **Webhook**: Go to **WhatsApp > Configuration**.
        *   Edit Webhook.
        *   **Callback URL**: Your ngrok URL + `/webhook/meta` (e.g., `https://xyz.ngrok-free.app/webhook/meta`).
        *   **Verify Token**: Create a random string (e.g., `xyzxyz`). This goes into `VERIFY_TOKEN`.
    
*   **Google AI**:
    1.  Get your API Key from [Google AI Studio](https://aistudio.google.com/).
    2.  This goes into `GOOGLE_API_KEY`.

*   **Tavily**:
    1.  Get your API Key from [Tavily](https://tavily.com/).
    2.  This goes into `TAVILY_API_KEY`.

**3. Clone & Configure**
```bash
git clone https://github.com/Vedant-Kaushik/WhatsApp_Chatbot.git
cd Whatsapp_chatbot
```

Create a `.env` file (do not use quotes):
```env
# WhatsApp / Meta
PHONE_ID=your_phone_id
WHATSAPP_TOKEN=your_token
CALLBACK_URL=https://your-domain.com
VERIFY_TOKEN=your_verify_token
APP_ID=your_app_id
APP_SECRET=your_app_secret
WABA_ID=your_whatsapp_business_account_id

# AI & Search
GOOGLE_API_KEY=your_google_ai_key
TAVILY_API_KEY=your_tavily_api_key

# Database (only needed for local dev without Docker)
DB_URI=postgresql://postgres:postgres@localhost:5432/postgres
```

**4. Run with Docker Compose (Recommended)**
```bash
# Start PostgreSQL + WhatsApp Bot
docker-compose up --build

# In a separate terminal, start ngrok
ngrok http 5173
```
> **Note**: Docker Compose automatically:
> - Starts PostgreSQL database
> - Waits for PostgreSQL to be ready (health check)
> - Initializes LangGraph checkpoint tables
> - Mounts `vector_stores/` and `temp_downloads/` for persistence

**5. Run Locally (No Docker)**
If you have Python and PostgreSQL installed:

```bash
# 1. Start PostgreSQL (if not running)
# macOS: brew services start postgresql@16
# Linux: sudo systemctl start postgresql

# 2. Create database
psql -U postgres -c "CREATE DATABASE postgres;"

# 3. Install dependencies
uv sync

# 4. Run the server
uv run uvicorn main:app --host 0.0.0.0 --port 5173

# 5. In a separate terminal, start ngrok
ngrok http 5173
```
> **Note**: Update `DB_URI` in your `.env` if your PostgreSQL credentials differ from the default.

---

## 📈 AI Investment Analyst (pAIsa)

A dedicated stock analysis dashboard that provides AI-powered insights for the Indian Market.

**[👉 Read the full pAIsa Documentation here](./trading_pAIsa/README.md)**

> ⚠️ **Note for Safari Users:** Safari does not support WebM video playback. If the video below appears blank, please view this page in **Chrome, Edge, or Firefox**.

<p align="center">
  <!-- TODO: DRAG AND DROP YOUR paisa_video.webm FILE HERE USING THE GITHUB WEB EDITOR -->
</p>

**How it works:**
1.  **Personalized Account**: Register to save your default investment budget and time horizon.
2.  **Smart Analysis**: Scans the **Nifty 50** and filters based on your budget and liquidity.
3.  **Deep-Dive Analysis**: Fetches historical candle data and calculates technical indicators.
4.  **AI Verdict**: Gemini 2.5 Flash analyzes the chart patterns and gives a clear **Buy/Hold/Avoid** verdict.

**Run the pAIsa Dashboard:**
```bash
uv run uvicorn trading_pAIsa.main:app --host 0.0.0.0 --port 8000
```

**Additional `.env` variables for Upstox:**
```env
UPSTOX_API_KEY=your_upstox_api_key
UPSTOX_API_SECRET=your_upstox_api_secret
UPSTOX_REDIRECT_URI=your_redirect_uri
UPSTOX_ACCESS_TOKEN=your_access_token
```

---

## 🔌 API Reference

### `POST /clear`
Resets the conversation memory for a specific user.

**Payload:**
```json
{
  "user_id": "wa_phone_number"
}
```

### WhatsApp Commands
| Command | Description |
|---------|-------------|
| `clear` | Reset conversation history, PDF memory, and long-term memory |
| Send a PDF | Bot analyzes the document and answers questions about it |
| Any text | Normal conversation with the AI assistant |

---

## Future Roadmap

1.  **Omnichannel Support**: Bringing the same intelligent experience to Telegram and other chat platforms.
2.  **Cloud & Scalability**: Investigating cloud-native deployments with distributed queues for background task processing.
3.  **Upstox WhatsApp Integration**: Bringing the investment analyst directly into WhatsApp conversations.
4.  **Integrate Trader with Chatter**: Merge the automated Upstox trading system with the WhatsApp chatting interface, allowing trade execution directly via chat.

---
