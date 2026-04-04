# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- **Install Dependencies**: `uv sync`
- **Run WhatsApp Bot (Local)**: `uv run uvicorn main:app --host 0.0.0.0 --port 5173`
  *(Note: You will typically need to run `ngrok http 5173` in a separate terminal and update the Meta developer console with the webhook).*
- **Run Upstox Module (Local)**: `uv run uvicorn upstox_analysis:app --host 0.0.0.0 --port 8000`
- **Run via Docker (Recommended)**: `docker-compose up --build`
  *(Starts the PostgreSQL database and the WhatsApp Bot).*
- **Database Setup (Local)**: Ensure PostgreSQL is running. By default, it expects `DB_URI=postgresql://postgres:postgres@localhost:5432/postgres`.

There is no formal testing suite (like pytest) currently set up; features are generally tested via Jupyter Notebooks like `test_upstox.ipynb`.

## High-Level Architecture

The project is an AI Chatbot for WhatsApp composed of two primary modules:

1.  **WhatsApp Chatbot Core (`main.py`)**:
    *   Uses **FastAPI** to receive Meta/WhatsApp webhooks via the `pywa` library.
    *   Driven by **LangGraph**, which orchestrates state, tool routing, memory, and summarization using Google's **Gemini 2.5 Flash**.
    *   **State & Memory Management**: Relies heavily on PostgreSQL. `PostgresSaver` is used for LangGraph thread checkpoints (short-term state/summarization), while `PostgresStore` acts as a Long-Term Memory (LTM) layer that extracts factual details about the user across conversations.
    *   **Tooling**: Supports real-time web search (via `TavilySearch`) and PDF document question-answering.
    *   **PDF Vectors**: `Chroma` is used for local vector storage. Uploaded PDFs are split and embedded locally into the `vector_stores/` directory.

2.  **Upstox Investment Analyst (`upstox_analysis.py`)**:
    *   A separate web interface using **FastAPI** and **Jinja2** (`templates/`).
    *   Uses the Upstox Python SDK to fetch master instruments (NSE/BSE), filter Nifty 50 stocks, check liquidity, and fetch historical candles.
    *   Analyzes the stock data via an LLM (Gemini 2.5 Flash) to generate Buy/Hold/Avoid recommendations.

3.  **Prompt Configuration (`prompts.json`)**:
    *   All system prompts, including the core persona, memory extractor, and PDF analyst instructions, are decoupled into this JSON file rather than being hardcoded in Python.