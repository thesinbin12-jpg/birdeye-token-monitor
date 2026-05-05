# 🛡️ Birdeye Token Safety Radar

[![Vercel Deployment](https://img.shields.io/badge/Deployment-Vercel-black?style=for-the-badge&logo=vercel)](https://birdeye-token-monitor.vercel.app)
[![Python](https://img.shields.io/badge/Language-Python-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Solana](https://img.shields.io/badge/Network-Solana-purple?style=for-the-badge&logo=solana)](https://solana.com/)
[![AI Powered](https://img.shields.io/badge/AI-Groq%20%26%20Rules-orange?style=for-the-badge)](https://groq.com/)

**The ultimate risk-assessment engine for Solana tokens.** 

Built for the [Birdeye Data BIP Competition Sprint 3](https://birdeye.so), this tool transforms raw on-chain data into actionable, AI-augmented intelligence. It doesn't just fetch data; it interprets it.

👉 **[LAUNCH LIVE DASHBOARD](https://birdeye-token-monitor.vercel.app)**

---

## ✨ Key Features

### 🧠 AI-Augmented Intelligence
- **Groq-Powered Analysis:** Leverages a sophisticated 3-model fallback chain (`qwen-32b` → `llama-3.3-70b` → `llama-3.1-8b`) for rapid, human-like risk assessments.
- **Hybrid Reasoning:** Combly AI intelligence with deterministic rule-based logic to ensure accuracy and speed.
- **Smart Caching:** 10-minute intelligence cache reduces API latency and costs.

### 📊 Calibrated Risk Scoring (0-100)
A multi-factor scoring engine that accounts for the volatile nature of Solana tokens:
- **Security (40%):** Mint/Freeze authority revocation and contract age.
- **Distribution (25%):** Whale concentration and holder distribution.
- **Liquidity (20%):** Real-world exit capacity.
- **Momentum (15%):** 24h price volatility and volume trends.
- **💥 Critical Multipliers:** Automated score caps for high-risk profiles (e.g., active mint/freeze authority or critically low liquidity).

### ⚡ High-Performance Engine
- **Concurrent Processing:** Uses Python `ThreadPoolExecutor` to parallelize API calls, enabling rapid batch scans of 15+ tokens without hitting serverless timeouts.
- **Pattern Intelligence:** Automatic detection of **Rug Pulls**, **Honeypots**, and **Pump & Dumps**.
- **Investment Simulation:** Predictive modeling of $100 investments based on score-weighted probability.

---

## 📸 Dashboard Preview

> *[📸 PRO-TIP: Replace these placeholders with your high-quality mobile and desktop screenshots for the competition submission!]*

| Mobile View (High Impact) | Desktop View (Detailed) |
| :--- | :--- |
| `![Mobile Screenshot](https://via.placeholder.com/300x600?text=Mobile+View)` | `![Desktop Screenshot](https://via.placeholder.com/600x400?text=Desktop+Dashboard)` |

---

## 🛠️ Tech Stack

- **Frontend:** Vanilla HTML5, CSS3 (Mobile-First), JavaScript (ES6+)
- **Backend:** Python 3.12, Flask, Vercel Serverless Functions
- **AI Engine:** Groq Cloud API
- **Data Source:** Birdeye Public API v2
- **Infrastructure:** Vercel

---

## 🏗️ Architecture

```text
birdeye-token-radar/
├── api/
│   └── index.py          # Vercel serverless entry & Flask routing
├── utils/
│   ├── analyzer.py       # Orchestrates scanning, scoring, and AI
│   ├── scoring.py        # Weighted math & critical multipliers
│   ├── ai_insights.py    # Groq fallback chain & regex cleaning
│   ├── simulation.py     # Investment ROI modeling
│   ├── pattern_matching.py # Rug/Honeypot/Pump & Dump logic
│   ├── comparative.py    # Batch percentile rankings
│   └── cache.py          # Thread-safe TTL caching
├── static/
│   ├── app.js            # Frontend logic & API orchestration
│   └── style.css         # Cyberpunk-inspired responsive styles
├── templates/
│   └── index.html        # Dashboard UI
└── vercel.json           # Deployment & concurrency configuration
```

---

## 🚀 Getting Started (Local Development)

### Prerequisites
- Python 3.9+
- [Birdeye API Key](https://birdeye.so)
- [Groq API Key](https://console.groq.com) (Optional)

### Setup
```bash
# 1. Clone the repository
git clone https://github.com/thesinbin12-jpg/birdeye-token-monitor.git
cd birdeye-token-monitor

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env with your BIRDEYE_API_KEY and GROQ_API_KEY

# 4. Launch the app
python -m flask --app api/index.py run --port 5000
```

### Deployment
The project is configured for one-click deployment on Vercel.
```bash
vercel deploy
```

---

## ⚖️ Scoring Methodology

| Category | Weight | Primary Indicators |
| :--- | :--- | :--- |
| **Security** | 40% | Mint/Freeze Revocation, Contract Age |
| **Distribution** | 25% | Top 10 Holders %, Whale Concentration |
| **Liquidity** | 20% | USD Liquidity, Exit Capacity |
| **Momentum** | 15% | 24h Volume, Price Volatility |

**⚠️ Safety Caps:**
- **Authority Risk:** If Mint OR Freeze authority is still active, the overall score is capped at **25**.
- **Liquidity Risk:** If liquidity is < $1,000, the score is capped at **35**.
- **Age Risk:** Penalties applied for contracts < 24 hours old.

---

## ⚠️ Disclaimer

**This tool is for informational purposes only and does not constitute financial advice.** Token scores are based on on-chain metrics and should not be the sole factor in investment decisions. Always DYOR (Do Your Own Research). The developers are not responsible for any financial losses.

---

## 📄 License

Distributed under the **Apache 2.0 License**. See `LICENSE` for more information.
