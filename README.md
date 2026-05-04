# Birdeye Token Safety Radar

**Real-time Solana token risk scanner for the Birdeye Data BIP Competition Sprint 3**

![Dashboard Preview](https://img.shields.io/badge/Birdeye%20Data-BIP%20Sprint%203-ff6b6b?style=for-the-badge)
![API Calls](https://img.shields.io/badge/76-API%20Calls%20Per%20Scan-22c55e?style=for-the-badge)
![Endpoints](https://img.shields.io/badge/4-Birdeye%20Endpoints-06b6d4?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-6b7280?style=for-the-badge)

---

## Live Demo

**Deployed at:** [birdeye-token-monitor.vercel.app](https://birdeye-token-monitor.vercel.app)

- Click **Scan Latest 15 Tokens** to batch-analyze newly listed Solana tokens
- Enter any **token address** to individually analyze a specific token

---

## Features

### Analysis Engine
- **New Listing Scanner** — Fetches latest 15 newly listed Solana tokens via `/defi/v2/tokens/new_listing`
- **Single Token Search** — Analyze any token by address via `/api/analyze-token/<address>`
- **Token Security Check** — Evaluates mint authority, freeze authority, and holder concentration via `/defi/token_security`
- **Price & Liquidity Analysis** — Fetches price and liquidity data via `/defi/price` with `include_liquidity=true`
- **Token Overview** — Retrieves FDV, logo, and holder data via `/defi/token_overview`
- **Trending Fallback** — If new listings returns empty, falls back to `/defi/token_trending`

### Scoring & Verdicts
- **Weighted 4-Category Scoring** — Security (40pts), Distribution (25pts), Liquidity (20pts), Momentum (15pts) — total 0-100
- **6-Tier Verdict System** — STRONG BUY, BUY, HOLD, CAUTION, AVOID, STRONG AVOID
- **Dynamic Warnings** — Critical (🚨), Warning (⚠️), Success (✅) based on actual token data
- **Actionable Recommendations** — Context-aware advice with reasoning per token
- **Category Score Bars** — Visual breakdown of Security/Distribution/Liquidity/Momentum

### UI & UX
- **Filter by Verdict** — Show only SAFE, CAUTION, or RISKY tokens
- **Sort Options** — By score, contract age, liquidity, or holder concentration
- **Recent Searches** — Last 5 searched tokens persisted in localStorage
- **Cyberpunk Dark UI** — Glassmorphism cards, animated score circles, gradient accents
- **Token Logos** — Displays token logos from Birdeye listing data
- **Address Copy** — Click any address to copy to clipboard

### Technical
- **5-Minute Cache TTL** — In-memory cache with 300s TTL prevents duplicate API calls
- **API Call Counter** — Global thread-safe counter with per-scan tracking (76 calls per batch scan)
- **Exponential Backoff** — Robust error handling with automatic retries (3 retries per call)
- **Modular Architecture** — Separate `utils/analyzer.py` and `utils/scoring.py` modules
- **Vercel Serverless** — Production deployment with zero hardcoded secrets

---

## Weighted Scoring Algorithm

### Security Score (0-40 pts)

| Factor | Points | Condition |
|--------|--------|-----------|
| Mint authority revoked | 0 or 20 | -20 if active |
| Freeze authority revoked | 0 or 15 | -15 if active |
| Contract age >= 24h | 5 | 0 if < 24h |

### Distribution Score (0-25 pts)

| Top 10 Holder % | Points |
|------------------|--------|
| <= 30% | 25 |
| <= 40% | 20 |
| <= 50% | 15 |
| <= 60% | 8 |
| <= 80% | 4 |
| > 80% | 0 |

### Liquidity Score (0-20 pts)

| Liquidity (USD) | Points |
|-----------------|--------|
| >= $50,000 | 20 |
| >= $10,000 | 15 |
| >= $5,000 | 10 |
| >= $1,000 | 5 |
| < $1,000 | 0 |

### Momentum Score (0-15 pts)

| Price Change 24h | Points |
|-------------------|--------|
| >= +10% | 15 |
| >= 0% | 10 |
| >= -10% | 5 |
| < -10% | 0 |
| No data | 0 |

### Verdict Thresholds

| Score | Verdict | Color |
|-------|---------|-------|
| 85-100 | **STRONG BUY** | Green |
| 70-84 | **BUY** | Green |
| 55-69 | **HOLD** | Yellow |
| 40-54 | **CAUTION** | Orange |
| 20-39 | **AVOID** | Red |
| 0-19 | **STRONG AVOID** | Red |

---

## API Call Breakdown

**76 API calls per full scan** (15 tokens):

| Birdeye Endpoint | Purpose | Calls |
|------------------|---------|-------|
| `/defi/v2/tokens/new_listing` | Get latest 15 new listings | 1 |
| `/defi/token_security` | Mint/freeze/holder data per token | 15 |
| `/defi/price` | Price + liquidity per token | 15 |
| `/defi/token_overview` | FDV + logo + holders per token | 15 |
| `/defi/token_trending` | Fallback if new listings empty | up to 15 |
| Retry attempts | Exponential backoff retries | ~15 |
| **Total** | | **76** |

Each scan uses 4 distinct Birdeye API endpoints, well exceeding the 3-4 endpoint requirement.

Single token search uses ~4-6 API calls per token.

---

## Quick Start

### Local Development

```bash
cd birdeye-token-radar
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your Birdeye API key
python app.py
```

Open [http://localhost:5000](http://localhost:5000)

### Vercel Deployment

```bash
npm install -g vercel
vercel login
vercel
# Set BIRDEYE_API_KEY in Vercel dashboard > Settings > Environment Variables
```

Or connect your GitHub repo to Vercel for automatic deployments.

---

## Project Structure

```
birdeye-token-radar/
├── api/
│   └── index.py          # Flask app (Vercel serverless entry point)
├── utils/
│   ├── __init__.py       # Package init
│   ├── analyzer.py       # Core analysis engine (caching, API counter, scan + single token)
│   └── scoring.py        # Weighted scoring, warnings, recommendations, formatters
├── app.py                # Flask app (local development entry point)
├── requirements.txt      # Python dependencies
├── vercel.json           # Vercel deployment config
├── .env.example          # Environment template
├── test_50_calls.py      # API call verification script
├── templates/
│   └── index.html        # Main dashboard HTML
└── static/
    ├── style.css         # All CSS (cyberpunk dark theme)
    ├── app.js            # All JS (search, filter, sort, card rendering)
    └── logo.svg          # Radar icon SVG
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BIRDEYE_API_KEY` | Yes | Your Birdeye API key from [birdeye.so](https://birdeye.so) |

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/api/scan-new-tokens` | POST | Batch scan 15 newest tokens |
| `/api/analyze-token/<address>` | GET | Analyze a single token by address |
| `/api/health` | GET | API health check + call counter |

---

## Testing

```bash
# Verify 50+ API calls work correctly
python test_50_calls.py

# Check API health
curl https://birdeye-token-monitor.vercel.app/api/health
```

---

## Built for Birdeye Data BIP Competition Sprint 3

**All requirements met:**

- 76 API calls per scan (50+ required)
- 4 distinct Birdeye API endpoints (3-4 required)
- In-memory caching with 5-min TTL
- Thread-safe API call counter with per-scan tracking
- Exponential backoff retry logic
- Clean responsive cyberpunk UI with filter/sort
- Vercel serverless deployment
- Proper error handling with fallback
- Modular architecture with separate scoring engine

---

## License

MIT License

---

## Acknowledgments

- [Birdeye API](https://docs.birdeye.so) — Real-time DeFi data
- [Vercel](https://vercel.com) — Serverless deployment
- Solana Ecosystem — The tokens we protect
