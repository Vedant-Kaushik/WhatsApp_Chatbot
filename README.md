# AI-Powered WhatsApp Chatbot

An intelligent, conversational WhatsApp chatbot built with **FastAPI**, **LangGraph**, and **Google Gemini 2.0 Flash**. This project leverages modern AI agent architectures to maintain context-aware conversations and serve as a foundation for advanced future capabilities.

## 🚀 Features

- **Advanced LLM Integration:** Powered by Google's **Gemini 2.0 Flash** for fast, high-quality responses.
- **Stateful Conversations:** Utilizes **LangGraph** to manage conversation state and message history, ensuring the bot remembers context.
- **Persistent Memory:** Uses **SQLite** checkpoints to save conversation history across sessions (stored in `conversation.db`).
- **Robust Webhook Handling:** Built on **FastAPI** and **PyWa** for reliable real-time message processing with Meta's WhatsApp Cloud API.
- **Session Management:** Includes basic session handling (reset context via `clear` command).

## 🛠️ Tech Stack

- **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
- **WhatsApp Client:** [PyWa](https://github.com/david-lev/pywa)
- **LLM Orchestration:** [LangGraph](https://langchain-ai.github.io/langgraph/) & [LangChain](https://www.langchain.com/)
- **State Management:** SQLite (LangGraph Checkpointer)
- **Model:** Google Gemini 2.0 Flash (`gemini-2.0-flash`)
- **Environment Management:** [python-dotenv](https://pypi.org/project/python-dotenv/)
- **Deployment:** Docker (containerized), ngrok (local tunneling)

## ⚙️ Setup & Installation

### **Prerequisites**

1. Clone the repository:
   ```bash
   git clone https://github.com/Vedant-Kaushik/WhatsApp_Chatbot.git
   cd Whatsapp_chatbot
   ```

2. Create a `.env` file with your credentials:
   ```env
   PHONE_ID=your_whatsapp_phone_id
   WHATSAPP_TOKEN=your_meta_access_token
   CALLBACK_URL=https://your-tunnel-url.ngrok-free.app
   VERIFY_TOKEN=your_custom_verify_token
   APP_ID=your_meta_app_id
   APP_SECRET=your_meta_app_secret
   GOOGLE_API_KEY=your_google_gemini_api_key
   ```
   > [!IMPORTANT]
   > Do NOT use quotes around the values in `.env`

### **Option A: Local Development**

1. Install dependencies with uv:
   ```bash
   pip install uv
   uv sync
   ```

2. Run the server:
   ```bash
   uvicorn main:app --reload --port 5173
   ```

3. Expose via ngrok:
   ```bash
   ngrok http 5173
   ```

4. Update `CALLBACK_URL` in `.env` with the ngrok URL.

### **Option B: Docker (Recommended)**

1. Build the Docker image:
   ```bash
   docker build -t whatsapp_chatbot_v1 .
   ```

2. Run the container:
   ```bash
   docker run -p 5173:5173 --env-file .env whatsapp_chatbot_v1
   ```

3. In a separate terminal, expose via ngrok:
   ```bash
   ngrok http 5173
   ```

4. Update `CALLBACK_URL` in `.env` and restart the container.

##  Future Roadmap

This project is evolving into a fully autonomous WhatsApp agentic system. Planned enhancements include:

-   [ ] **Multi-Modal Capabilities:** Support for image and PDF analysis via Gemini's vision capabilities.
-   [ ] **Tool Use (MCP):** Integration of **Model Context Protocol (MCP)** tools to allow the bot to perform external actions (searching the web, querying databases, etc.).
-   [ ] **User Experience:** Typing indicators and rich media responses.
-   [ ] **Production Deployment:** Migration from local tunneling to a public cloud host (AWS/GCP/Vercel).

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
