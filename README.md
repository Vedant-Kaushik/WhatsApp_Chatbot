# Enterprise AI Chatbot for WhatsApp

**The Easiest, Most Powerful Way to Deploy AI on WhatsApp.**

Turn your WhatsApp business number into a 24/7 intelligent agent. Whether you are a developer looking for a robust foundation or a business owner wanting a "done-for-you" solution, this project delivers an enterprise-grade experience instantly.

## 🚀 Why This Chatbot?

*   **Zero-Friction Setup**: The database initializes automatically on the first run. No complex migrations or SQL scripts needed.
*   **Human-Like Intelligence**: Powered by a State-of-the-Art Large Language Model (LLM), it understands context, nuance, and intent better than traditional rule-based bots.
*   **Beautiful Responses**: Sends perfectly formatted messages with bold text, lists, and tables that look professional on mobile and desktop.
*   **PDF Document Analysis**: Send any PDF to the bot, and it will instantly read, understand, and answer questions based on its content.
*   **Smart Memory**: Remembers conversation history for seamless follow-ups. Reset memory instantly with our simpler commands.
*   **Reliable**: Built on a modern, high-concurrency framework.

---

## 🌩️ Hosted Service (No Coding Required)

**Don't want to manage servers, Docker, or API keys?**

We offer a fully managed **Premium Cloud Tier** for business owners and non-tech users.

*   **We Host Everything**: You just scan a QR code or provide your number.
*   **No Technical Headache**: We handle the technical setup; you handle your customers.
*   **Cost**: **~$25 USD / month** (Base Hosting).
*   **Custom Integrations**: connecting the bot to *your* specific database, calendar, or CRM is available as a **premium customization service**.


**[Contact us](#)** to get started with the Hosted Tier today.

---

## 🛠️ For Developers (Self-Hosted)

If you prefer to run it yourself, this codebase is open-source and developer-friendly.

### Tech Stack
*   **Framework**: FastAPI (High-performance Python web framework)
*   **AI Engine**: Advanced LLM (Abstracted via LangChain/LangGraph)
*   **Database**: PostgreSQL (Stores conversation history, user threads, and memory checkpoints)
*   **Vector Store**: ChromaDB (Persistent PDF embeddings on disk)
*   **Integration**: PyWa (Verified WhatsApp APIs)
*   **Containerization**: Docker & Docker Compose

### Key Features

#### 📄 **PDF Document Analysis**
- Upload any PDF to the bot
- Automatic text extraction and vectorization
- Persistent storage: Ask unlimited questions about the same document
- Smart routing: LLM decides when to query the PDF vs. general chat

#### 🧠 **Intelligent Memory Management**
- **Conversation Summarization**: After 10+ messages, old messages are summarized and compressed
- **Infinite Context**: Never lose conversation history, even in long chats
- **Thread-based Memory**: Each user has isolated conversation threads

#### 🎯 **Production-Ready**
- PostgreSQL for reliable state management
- Automatic database initialization
- Docker Compose for one-command deployment

### Fast Setup

**1. Prerequisites**
*   Git
*   Docker (Optional, but recommended)
*   A Meta Developer Account & WhatsApp Business API credentials

**2. Get Credentials**
You need to fill the `.env` file with secrets from Meta and Google.

*   **Meta/Facebook Developers**:
    1.  Go to [Meta Developers](https://developers.facebook.com/).
    2.  Create an App -> Select **Other** -> **Business** -> **WhatsApp**.
    3.  **API Setup**: In the sidebar, go to **WhatsApp > API Setup**.
        *   Copy **Phone Number ID** (`PHONE_ID`).
        *   Copy **Temporary Access Token** (or configure a System User for permanent access) (`WHATSAPP_TOKEN`).
    4.  **App Basic Settings**: Go to **App Settings > Basic**.
        *   Copy **App ID** (`APP_ID`) and **App Secret** (`APP_SECRET`).
    5.  **Webhook**: Go to **WhatsApp > Configuration**.
        *   Edit Webhook.
        *   **Callback URL**: Your ngrok URL + `/webhook/meta` (e.g., `https://xyz.ngrok-free.app/webhook/meta`).
        *   **Verify Token**: Create a random string (e.g., `xyzxyz`). This goes into `VERIFY_TOKEN`.
    
*   **Google AI**:
    1.  Get your API Key from [Google AI Studio](https://aistudio.google.com/).
    2.  This goes into `GOOGLE_API_KEY`.

**3. Clone & Configure**
```bash
git clone https://github.com/Vedant-Kaushik/WhatsApp_Chatbot.git
cd Whatsapp_chatbot
```

Create a `.env` file (do not use quotes):
```env
PHONE_ID=your_phone_id
WHATSAPP_TOKEN=your_token
CALLBACK_URL=https://your-domain.com
VERIFY_TOKEN=your_verify_token
APP_ID=your_app_id
APP_SECRET=your_app_secret
GOOGLE_API_KEY=your_ai_api_key
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
pip install -r requirements.txt

# 4. Run the server (Port 5173)
uvicorn main:app --reload --port 5173

# 5. In a separate terminal, start ngrok
ngrok http 5173
```
> **Note**: Update `DB_URI` in `main.py` if your PostgreSQL credentials differ from the default.

---

## 🔌 API Documentation

### `POST /clear`
**Description**: Resets the conversation memory for a specific user.
**Usage**: Useful for testing or when a user wants to start a fresh topic.
**Payload**:
```json
{
  "user_id": "wa_phone_number"
}
```

---

##  Future Scope & Roadmap

We are constantly learning and exploring new system architectures to make this bot even better.

1.  **Omnichannel Support**:
    *   Bringing this same intelligent experience to Telegram and other chat apps, keeping WhatsApp as the primary interface.

2.  **Cloud & Scalability Exploration**:
    *   Investigating Cloud-Native deployments to support more users efficiently.
    *   Learning system design concepts like distributed queues for handling complex tasks in the background.

    *   Allowing the bot to perform real-world actions (web search, data lookup) to be more helpful.
    
4.  **📈 Coming Soon: AI Investment Analyst (Upstox)**
    We are building a powerful **Investment Advice Engine** directly into WhatsApp.
    
    **The Logic (Already Designed):**
    1.  **Smart Filter**: Scans the **Nifty 500** (Top 500 Indian companies) instead of random junk stocks.
    2.  **Affordability Check**: You type "Invest ₹50k". The bot instantly filters out stocks way above your budget (like MRF).
    3.  **Liquidity Sort**: Picks the Top 5 most liquid/active stocks to ensure safety.
    4.  **Deep-Dive Analysis**: Fetches **6 Months of Daily Candles** (History) for the shortlisted stocks.
    5.  **LLM Verdict**: The AI analyzes the chart patterns and gives you a clear **Buy/Hold/Avoid** rating with reasons.
    
    *Goal: To give you a Hedge Fund Analyst in your pocket.*

---
