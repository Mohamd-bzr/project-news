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
- **Optional AI & LLM Add-on**: Optional generative intelligence interface supporting direct **OpenAI** (`gpt-4o-mini`, `gpt-4o`) and **OpenRouter** (`sk-or-...`) for on-demand summaries without altering the standalone, zero-cloud core.
- **Real-Time Technical Indicators**: Instant computation of RSI, MACD, Bollinger Bands, ATR, and EMA overlays coupled with Yahoo Finance v8 candlestick charts.
- **Deterministic Persian Translation**: High-throughput automated translation pipeline featuring domain-specific entity preservation, Persian numeral normalization, and Zero-Width Non-Joiner (ZWNJ) orthography.
- **PWA & Offline First**: Standalone Progressive Web App with Service Worker caching, IndexedDB storage engine, Server-Sent Events (SSE) streaming, and low-latency dark theme UI.

---

## 🧩 Optional AI / LLM Add-on (افزونه اختیاری هوش مصنوعی)

> [!NOTE]
> **Core Zero-Cloud Philosophy**: The entire news ingestion, quality ranking, Persian translation, indicator computation, and autonomous dispatch pipeline runs **100% locally and deterministically** using pure Python math, algorithms, and regex. The core system operates with complete autonomy and has **zero dependencies on external AI or cloud APIs**.

For users who wish to enable optional generative AI enhancements, the subsystem ([`ai_features.py`](file:///e:/freebuff/ai_features.py)) provides an on-demand bridge to external LLM providers when an API key is configured in settings:

### 1. Supported Providers (Optional)
- **OpenAI API**: Direct plug-and-play with OpenAI API keys (`gpt-4o-mini`, `gpt-4o`).
- **OpenRouter Gateway**: Connects via OpenRouter (`sk-or-...`) to access modern reasoning models on demand (such as Claude 3.5 Sonnet, DeepSeek V3 / R1, Gemini 2.0 Flash, or Llama 3.3).

### 2. Optional Capabilities (Requires User-Supplied API Key)
- **On-Demand Asset Summaries**: Generates a 3-bullet executive summary and sentiment snapshot for a specific symbol on demand.
- **"Ask the News" Q&A**: Interactive retrieval-augmented querying over the recent 72-hour news corpus.
- **Purely Optional & Graceful Fallback**: If no API key is supplied, this module remains inactive; all core terminal operations, charts, and auto-dispatches continue running smoothly using statistical calculations (Z-score volume anomaly detection and moving average momentum).

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
