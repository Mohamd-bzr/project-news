# MOHMD NEWS — Financial Market Intelligence & Terminal

[![CI](https://github.com/Mohamd-bzr/project-news/actions/workflows/ci.yml/badge.svg)](https://github.com/Mohamd-bzr/project-news/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PWA Ready](https://img.shields.io/badge/PWA-offline--first-orange.svg)](web/sw.js)
[![Tests Passing](https://img.shields.io/badge/tests-324%20passed-brightgreen.svg)](tests/)

A high-performance, real-time financial market intelligence terminal and news aggregator engineered for Persian (RTL) financial desks. Built with a zero-cloud-dependency philosophy, running entirely locally or self-hosted with multi-threaded parallel scraping, algorithmic credibility scoring, technical market analytics, and autonomous multi-platform distribution.

---

## ⚡ Key Highlights

- **194+ Multi-Asset Sources**: Parallel scraping across Macroeconomics, Forex, Commodities, Energy, Industrial Metals, and Cryptocurrency.
- **Autonomous Multi-Channel Dispatch**: Built-in broadcast pipelines for **Telegram** and **Bale** messengers with channel monitoring, reaction filtering, and dedicated bot integration.
- **Next-Gen AI & LLM Engine**: Unified AI interface supporting direct **OpenAI** (`gpt-4o-mini`, `gpt-4o`) and **OpenRouter** (`sk-or-...`) with instant access to **Claude 3.5 Sonnet**, **DeepSeek V3 / R1**, **Google Gemini 2.0 Flash**, and **Llama 3.3**.
- **Real-Time Technical Indicators**: Instant computation of RSI, MACD, Bollinger Bands, ATR, and EMA overlays coupled with Yahoo Finance v8 candlestick charts.
- **Deterministic Persian Translation**: High-throughput automated translation pipeline featuring domain-specific entity preservation, Persian numeral normalization, and Zero-Width Non-Joiner (ZWNJ) orthography.
- **PWA & Offline First**: Standalone Progressive Web App with Service Worker caching, IndexedDB storage engine, Server-Sent Events (SSE) streaming, and low-latency dark theme UI.

---

## 🧠 AI & LLM Architecture

The terminal features an integrated AI subsystem ([`ai_features.py`](file:///e:/freebuff/ai_features.py)) that bridges automated market ingestion with advanced generative analysis:

### 1. Multi-Provider LLM Integration
- **OpenAI Native**: Plug-and-play with OpenAI API keys (`gpt-4o-mini`, `gpt-4o`).
- **OpenRouter Gateway**: Seamlessly routes requests through OpenRouter by supplying an API key (`sk-or-...`) or custom endpoint. This unlocks access to state-of-the-art reasoning models:
  - **Anthropic Claude 3.5 Sonnet**: In-depth institutional macroeconomic reports.
  - **DeepSeek V3 & DeepSeek R1**: Advanced quantitative reasoning and analytical breakdowns.
  - **Google Gemini 1.5 / 2.0 Flash**: Ultra-fast latency news summarization.
  - **Meta Llama 3.3 70B**: High-fidelity open-weights intelligence.

### 2. Intelligent Use Cases
- **Executive Summaries**: Synthesizes dozens of fragmented news articles into structured market briefs.
- **"Ask the News" RAG Engine**: Interactive retrieval-augmented question answering over the latest 72-hour news corpus.
- **Anomaly & Sentiment Corroboration**: Pairs local statistical anomaly detection with LLM validation.
- **Content Studio Generator**: Composes publish-ready Persian market posts tailored for social networks and channel subscribers.

---

## 📊 Tracked Assets & Market Coverage

The system tracks and computes technical metrics for a broad spectrum of global symbols:

| Category | Assets & Symbols |
|---|---|
| **Forex** | EUR/USD, GBP/USD, AUD/USD, USD/CHF, USD/JPY, USDCAD |
| **Energy** | WTI Crude Oil (`CL=F`), Brent Crude (`BZ=F`), RBOB Gasoline (`RB=F`), Natural Gas (`NG=F`), Heating Oil / Gasoil (`HO=F`) |
| **Precious Metals** | Gold (`XAU`), Silver (`XAG`), Platinum (`PL=F`) |
| **Industrial Metals** | Copper (`HG=F`), Nickel (`P4Y.F`), Lead (`LL1=F`), Aluminum (`ALI=F`), Tin (`FTIN.L`) |
| **Major Indices** | S&P 500 (`^GSPC`), Dow Jones (`^DJI`), Nasdaq (`^IXIC`), Dollar Index (`DXY`), Volatility Index (`^VIX`), FTSE 100, DAX, CAC 40, IBEX 35, Euro Stoxx 50, Nikkei 225 |
| **Cryptocurrency** | Bitcoin (BTC), Ethereum (ETH), Solana (SOL), Ripple (XRP), Cardano (ADA), Binance Coin (BNB), Dogecoin (DOGE) |

---

## 🔄 Automated Pipeline Workflow

Every **30 minutes**, the system autonomously executes its end-to-end processing loop:

```
[ 194+ RSS / Web / Social Sources ]
                │
                ▼
   [ Parallel Ingestion & Deduplication ] ──► (Filters stories outside 72h window)
                │
                ▼
   [ Algorithmic Quality & Credibility ] ──► (Scores 0–100%, strips clickbait & ads)
                │
                ▼
  [ Deterministic Persian Translation ] ──► (Disk-cached, ZWNJ & Persian digits)
                │
                ▼
    [ Real-Time Market Data Engine ]    ──► (Yahoo Finance OHLC + Technical Indicators)
                │
                ▼
  [ Multi-Channel Autonomous Dispatch ] ──► (Telegram Channels, Bale News, Content Studio)
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- Git

### One-Click Launch (Windows)
Double-click `start.bat` in the repository root. It will automatically initialize the virtual environment, install requirements, and spin up the production server.

### Manual Setup

1. **Clone the repository:**
   ```bash
   git clone git@github.com:Mohamd-bzr/project-news.git
   cd project-news
   ```

2. **Set up the virtual environment:**
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Run the server:**
   ```bash
   python app.py --port 5055
   ```

5. Open your browser and navigate to:
   ```
   http://localhost:5055
   ```

---

## 🛠 Architecture & Technology Stack

- **Backend**: Python / Flask running on **Waitress WSGI** (32 concurrent worker threads) with zero cloud requirements.
- **Persistence**: High-reliability SQLite database (`.mohmd_news.db`) with zero data loss across restarts.
- **High-Speed Serialization & Compression**: Native `orjson` parser with fallback and `Flask-Compress` (Brotli / Gzip) reducing payloads by up to 5x over the wire.
- **Frontend SPA**: Lightweight vanilla JS architecture divided into clean fragments (`web/fragments/`), fully accessible, offline-capable, and optimized for RTL Persian typography (Vazirmatn).
- **Public API**: RESTful endpoints (`/api/v1/*`) with API key authorization, rate limiting, and interactive OpenAPI documentation at `/api/docs`.

---

## 🧪 Testing & Quality Gates

The codebase enforces strict test invariants to guarantee stability:

```bash
# Run the full hermetic test suite (324+ tests, offline, no network required):
pytest tests/ -q

# Validate all inline JavaScript and fragment syntax:
python tools/check_dashboard_js.py

# Verify diff boundaries and change safety:
python tools/guard_diff.py --allow app.py,tests/conftest.py
```

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
