# Enterprise AI Chatbot for WhatsApp

**The Easiest, Most Powerful Way to Deploy AI on WhatsApp.**

Turn your WhatsApp business number into a 24/7 intelligent agent. Whether you are a developer looking for a robust foundation or a business owner wanting a "done-for-you" solution, this project delivers an enterprise-grade experience instantly.

## 🚀 Why This Chatbot?

*   **Zero-Friction Setup**: The database initializes automatically on the first run. No complex migrations or SQL scripts needed.
*   **Human-Like Intelligence**: Powered by a State-of-the-Art Large Language Model (LLM), it understands context, nuance, and intent better than traditional rule-based bots.
*   **Beautiful Responses**: Sends perfectly formatted messages with bold text, lists, and tables that look professional on mobile and desktop.
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
*   **Database**: SQLite (Auto-created), easily swappable for PostgreSQL
*   **Integration**: PyWa (Verified WhatsApp APIs)
*   **Containerization**: Docker & Docker Compose

### Fast Setup

**1. Prerequisites**
*   Git
*   Docker (Optional, but recommended)
*   A Meta Developer Account & WhatsApp Business API credentials

**2. Clone & Configure**
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

**3. Run via Docker**
```bash
docker build -t whatsapp-bot .
docker run -p 5173:5173 --env-file .env whatsapp-bot
```
> **Note**: On the first run, the system will **automatically create and initialize the database**. You will see a "Database initialized" message in the logs.

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

## 🔮 Future Scope & Roadmap

We are constantly learning and exploring new system architectures to make this bot even better.

1.  **Omnichannel Support**:
    *   Bringing this same intelligent experience to Telegram and other chat apps, keeping WhatsApp as the primary interface.

2.  **Cloud & Scalability Exploration**:
    *   Investigating Cloud-Native deployments to support more users efficiently.
    *   Learning system design concepts like distributed queues for handling complex tasks in the background.

3.  **Agentic Capabilities**:
    *   Allowing the bot to perform real-world actions (web search, data lookup) to be more helpful.

---
