# Birdeye Token Safety Radar

Real-time Solana token safety scanner with AI-powered insights, investment simulation, and pattern detection. Built for the [Birdeye Data BIP Competition Sprint 3](https://birdeye.so).

**Live Demo:** [birdeye-token-monitor.vercel.app](https://birdeye-token-monitor.vercel.app)

---

## Features

### Core Safety Analysis
- **Calibrated Scoring (0-100):** Security (40pts), Distribution (25pts), Liquidity (20pts), Momentum (15pts)
- **Critical Multipliers:** Mint+freeze both active → score caps at 25; liquidity <$1k → caps at 35; age <1h → -25
- **5-Tier Verdicts:** STRONG AVOID → AVOID → HOLD → BUY → STRONG BUY
- **50+ API Calls Per Scan:** Honest counting with per-scan tracking

### AI-Powered Insights
- **Groq Integration:** 3-model fallback chain (qwen/qwen3-32b → llama-3.3-70b-versatile → llama-3.1-8b-instant)
- **Rule-Based Fallback:** When Groq is unavailable, generates insights from scoring data
- **10-Minute Insight Cache:** Avoids redundant AI calls for same tokens

### $100 Investment Simulation
- **Tokens Received:** Based on current price from Birdeye
- **Estimated 24h Value & ROI:** Probability-weighted using score, patterns, and liquidity
- **Best/Worst Case Scenarios:** With probability estimates
- **Exit Liquidity Assessment:** Whether $100 can realistically exit

### Pattern Detection
- **Rug Pull Signals:** Mint authority active, freeze authority, whale concentration, low liquidity
- **Honeypot Signals:** Freeze authority, extreme holder concentration, zero liquidity
- **Pump & Dump Signals:** Price spikes, whale concentration, recent contract age
- **Combo Detection:** Spike + whale concentration triggers extra weight
- **Risk Classification:** DANGEROUS → HIGH_RISK → SUSPICIOUS → CAUTION → LOW_RISK → SAFE

### Batch Comparison
- **Percentile Ranking:** Each token ranked vs others in the same scan batch
- **Liquidity & Holder Ranks:** Position within batch
- **Verdict Distribution:** How many SAFE/CAUTION/RISKY tokens in the batch
- **Comparison Text:** Human-readable summary

### Share & Engagement
- **X/Twitter Share Button:** One-click sharing of token safety scores
- **Recent Search History:** Persisted in localStorage, one-click re-analysis

---

## Birdeye API Endpoints Used

| Endpoint | Purpose | Calls Per Scan |
|----------|---------|----------------|
| `/defi/v2/tokens/new_listing` | Fetch newly listed tokens | 1 |
| `/defi/token_security` | Security data (mint/freeze authority, holders) | 10 |
| `/defi/price` | Current price + liquidity info (`include_liquidity=true`) | 10 |
| `/defi/token_overview` | Logo, description, metadata | 10 |
| `/defi/token_trending` | Fallback when new listing returns empty | 1 (conditional) |

**Total per 10-token scan: ~31-51+ API calls** (with retries and trending fallback)

---

## Architecture

```
birdeye-token-radar/
├── api/
│   └── index.py          # Flask app (Vercel serverless entry)
├── utils/
│   ├── analyzer.py       # Core analysis engine
│   ├── scoring.py        # Calibrated scoring + multipliers
│   ├── ai_insights.py    # Groq 3-model fallback + rule-based
│   ├── simulation.py     # $100 investment simulation
│   ├── pattern_matching.py # Rug pull/honeypot/pump&dump
│   ├── comparative.py    # Batch percentile + rankings
│   └── cache.py          # Thread-safe TTL cache
├── templates/
│   └── index.html        # Dashboard HTML
├── static/
│   ├── style.css         # Mobile-first CSS
│   └── app.js            # Frontend logic
├── vercel.json           # Routes + 30s timeout
├── requirements.txt      # Python deps
├── .env.example          # Environment variable template
└── .gitignore
```

---

## Quick Start

### Prerequisites
- Python 3.9+
- [Birdeye API Key](https://birdeye.so) (required)
- [Groq API Key](https://console.groq.com) (optional, for AI insights)

### Local Development

```bash
# Clone
git clone https://github.com/thesinbin12-jpg/birdeye-token-monitor.git
cd birdeye-token-monitor

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Run locally
python -m flask --app api/index.py run --port 5000
```

### Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Set environment variables in Vercel dashboard:
# BIRDEYE_API_KEY=your_key
# GROQ_API_KEY=your_key (optional)
```

---

## API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/api/health` | GET | API health + call count |
| `/api/scan-new-tokens` | POST | Scan latest Solana tokens (batch) |
| `/api/analyze-token/<address>` | GET | Analyze a specific token by address |

---

## Scoring Methodology

### Security (40 points max)
| Factor | Points | Condition |
|--------|--------|-----------|
| Mint Authority Revoked | 20 | Yes = 20, No = 0 |
| Freeze Authority Revoked | 15 | Yes = 15, No = 0 |
| Contract Age Bonus | 5 | >24h = 5, >12h = 3, >1h = 1 |

### Distribution (25 points max)
| Top 10 Holders % | Points |
|-------------------|--------|
| < 10% | 25 |
| < 20% | 20 |
| < 30% | 15 |
| < 50% | 10 |
| < 70% | 5 |
| >= 70% | 0 |

### Liquidity (20 points max)
| Liquidity (USD) | Points |
|-----------------|--------|
| >= $100k | 20 |
| >= $50k | 16 |
| >= $10k | 12 |
| >= $5k | 8 |
| >= $1k | 4 |
| < $1k | 0 |

### Momentum (15 points max)
Based on price change over 24h with diminishing returns for extreme moves.

### Critical Multipliers
- **Mint + Freeze both active → score caps at 25** (both centralization risks present)
- **Liquidity < $1,000 → score caps at 35** (exit liquidity insufficient)
- **Contract age < 1 hour → -25 penalty**
- **Contract age < 24 hours → -15 penalty**

---

## Tech Stack

- **Backend:** Python, Flask, Vercel Serverless
- **Frontend:** Vanilla HTML/CSS/JS (no frameworks)
- **AI:** Groq (qwen/qwen3-32b, llama-3.3-70b-versatile, llama-3.1-8b-instant)
- **API:** Birdeye Public API v2
- **Deploy:** Vercel

---

## Disclaimer

**This tool is for informational purposes only and does not constitute financial advice.** Token scores are based on on-chain metrics and should not be the sole factor in investment decisions. Always DYOR (Do Your Own Research). The developers are not responsible for any financial losses.

---

## License

Apache License 2.0 — See [LICENSE](LICENSE) for details.

You may use, modify, and distribute this software provided you:
- Include the original copyright notice
- State significant changes made
- Include the LICENSE file in distributions

This license includes patent grant protections. No warranty is provided.
