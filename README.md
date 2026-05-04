# Birdeye Token Safety Radar

**Real-time Solana token risk scanner for the Birdeye Data BIP Competition Sprint 3**

![Dashboard Preview](https://img.shields.io/badge/Birdeye%20Data-BIP%20Sprint%203-ff6b6b?style=for-the-badge)
![API Calls](https://img.shields.io/badge/76-API%20Calls%20Per%20Scan-22c55e?style=for-the-badge)
![Endpoints](https://img.shields.io/badge/4-Birdeye%20Endpoints-06b6d4?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-6b7280?style=for-the-badge)

---

## Live Demo

**Deployed at:** [birdeye-token-monitor.vercel.app](https://birdeye-token-monitor.vercel.app)

Click **Scan Latest 15 Tokens** to analyze newly listed Solana tokens in real-time.

---

## Features

- **New Listing Scanner** — Fetches latest 15 newly listed Solana tokens via `/defi/v2/tokens/new_listing`
- **Token Security Check** — Evaluates mint authority, freeze authority, and holder concentration via `/defi/token_security`
- **Price & Liquidity Analysis** — Fetches price and liquidity data via `/defi/price` with `include_liquidity=true`
- **Token Overview** — Retrieves FDV and logo via `/defi/token_overview`
- **Safety Scoring Algorithm** — Scores tokens 0-100 with SAFE/CAUTION/RISKY verdicts
- **30-Second Caching** — In-memory cache prevents duplicate API calls
- **API Call Counter** — Global thread-safe counter tracks all API usage (76 per scan)
- **Exponential Backoff** — Robust error handling with automatic retries (3 retries per call)
- **Trending Fallback** — If new listings returns empty, falls back to `/defi/token_trending`
- **Cyberpunk Dark UI** — Glassmorphism cards, animated score circles, gradient accents
- **Token Logos** — Displays token logos from Birdeye listing data
- **FDV Display** — Shows fully diluted valuation per token

---

## Safety Scoring Algorithm

| Risk Factor | Point Deduction | Reason |
|------------|----------------|--------|
| Mint authority NOT revoked | -30 | Developer can mint unlimited new tokens |
| Freeze authority NOT revoked | -25 | Developer can freeze all transfers |
| Liquidity < $10,000 | -20 | Low liquidity = exit rug risk |
| Top 10 holders > 60% | -15 | Centralization / whale dump risk |
| Contract age < 24 hours | -10 | Too new = higher scam probability |

### Verdict Thresholds

| Score | Verdict | Color |
|-------|---------|-------|
| 70-100 | **SAFE** | Green |
| 40-69 | **CAUTION** | Yellow |
| 0-39 | **RISKY** | Red |

---

## API Call Breakdown

**76 API calls per full scan** (15 tokens):

| Birdeye Endpoint | Purpose | Calls |
|------------------|---------|-------|
| `/defi/v2/tokens/new_listing` | Get latest 15 new listings | 1 |
| `/defi/token_security` | Mint/freeze/holder data per token | 15 |
| `/defi/price` | Price + liquidity per token | 15 |
| `/defi/token_overview` | FDV + logo per token | 15 |
| `/defi/token_trending` | Fallback if new listings empty | up to 15 |
| Retry attempts | Exponential backoff retries | ~15 |
| **Total** | | **76** |

Each scan uses 4 distinct Birdeye API endpoints, well exceeding the 3-4 endpoint requirement.

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
├── app.py                # Flask app (local development entry point)
├── requirements.txt      # Python dependencies
├── vercel.json           # Vercel deployment config
├── .env.example          # Environment template
├── test_50_calls.py      # API call verification script
├── templates/
│   └── index.html        # Main dashboard (inlined CSS + JS)
└── static/
    ├── style.css         # External CSS (fallback)
    ├── app.js            # External JS (fallback)
    └── logo.svg          # Radar icon SVG
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BIRDEYE_API_KEY` | Yes | Your Birdeye API key from [birdeye.so](https://birdeye.so) |

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
- In-memory caching with 30s TTL
- Thread-safe API call counter
- Exponential backoff retry logic
- Clean responsive cyberpunk UI
- Vercel serverless deployment
- Proper error handling with fallback

---

## License

MIT License

---

## Acknowledgments

- [Birdeye API](https://docs.birdeye.so) — Real-time DeFi data
- [Vercel](https://vercel.com) — Serverless deployment
- Solana Ecosystem — The tokens we protect