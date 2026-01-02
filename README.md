# AI-Powered WhatsApp Chatbot

An intelligent, conversational WhatsApp chatbot built with **FastAPI**, **LangGraph**, and **Google Gemini 2.0 Flash**. This project leverages modern AI agent architectures to maintain context-aware conversations and serve as a foundation for advanced future capabilities.

## 🚀 Features

- **Advanced LLM Integration:** Powered by Google's **Gemini 2.0 Flash** for fast, high-quality responses.
- **Stateful Conversations:** Utilizes **LangGraph** to manage conversation state and message history, ensuring the bot remembers context.
- **Robust Webhook Handling:** Built on **FastAPI** and **PyWa** for reliable real-time message processing with Meta's WhatsApp Cloud API.
- **Session Management:** Includes basic session handling (reset context via `/clear` command).

## 🛠️ Tech Stack

- **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
- **WhatsApp Client:** [PyWa](https://github.com/david-lev/pywa)
- **LLM Orchestration:** [LangGraph](https://langchain-ai.github.io/langgraph/) & [LangChain](https://www.langchain.com/)
- **Model:** Google Gemini 2.0 Flash (`gemini-2.0-flash`)
- **Environment Management:** [python-dotenv](https://pypi.org/project/python-dotenv/)

## ⚙️ Setup & Installation

> [!NOTE]
> **Current Status:** This setup guide is for **local development** using tunneling (ngrok).
> **Future Update:** Docker support and public hosting instructions are currently in development. Please wait for the upcoming Docker update for a containerized deployment guide.

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/Vedant-Kaushik/WhatsApp_Chatbot.git
    cd Whatsapp_chatbot
    ```

2.  **Install Dependencies**
    Ensure you created a virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```
    *(Note: Ensure `uv` or `pip` is used to install `fastapi`, `uvicorn`, `pywa`, `langchain-google-genai`, `langgraph`, `python-dotenv`)*

3.  **Environment Configuration**
    Create a `.env` file in the root directory with the following credentials:
    ```env
    PHONE_ID="your_whatsapp_phone_id"
    WHATSAPP_TOKEN="your_meta_access_token"
    CALLBACK_URL="https://your-tunnel-url.ngrok-free.app"
    VERIFY_TOKEN="your_custom_verify_token"
    APP_ID="your_meta_app_id"
    APP_SECRET="your_meta_app_secret"
    GOOGLE_API_KEY="your_google_gemini_api_key"
    ```

4.  **Run the Server**
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 5173 --reload
    ```

5.  **Expose Localhost**
    ```bash
    ngrok http 5173
    ```
    Update your `CALLBACK_URL` in `.env` and the Meta App Dashboard with the new ngrok URL.

## 🔮 Future Roadmap

This project is evolving into a fully autonomous agentic system. Planned enhancements include:

-   [ ] **Multi-Modal Capabilities:** Support for image and PDF analysis via Gemini's vision capabilities.
-   [ ] **Persistent Memory:** Integration with **SQLite/PostgreSQL** for long-term user history storage.
-   [ ] **Tool Use (MCP):** Integration of **Model Context Protocol (MCP)** tools to allow the bot to perform external actions (searching the web, querying databases, etc.).
-   [ ] **User Experience:** Typing indicators and rich media responses.
-   [ ] **Docker Support:** Containerization for consistent deployment environments (Coming soon).
-   [ ] **Production Deployment:** Migration from local tunneling to a public cloud host (AWS/GCP/Vercel).

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.