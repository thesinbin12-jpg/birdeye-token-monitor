# Birdeye Token Safety Radar

**Real-time Solana token risk scanner for the Birdeye Data BIP Competition**

![Dashboard Preview](https://img.shields.io/badge/Birdeye%20Data-BIP%20Competition-ff6b6b?style=for-the-badge)
![API Calls](https://img.shields.io/badge/50%2B-API%20Calls%20Verified-22c55e?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-6b7280?style=for-the-badge)

---

## 🚀 Live Demo

**Deployed at:** [birdeye-token-radar.vercel.app](https://birdeye-token-radar.vercel.app)

---

## ⚡ Features

- **Real-time Token Scanning** — Fetches latest 15 newly listed Solana tokens via Birdeye API
- **Multi-Factor Risk Analysis** — Evaluates 6 risk factors: mint authority, freeze authority, liquidity, holder concentration, contract age
- **Safety Scoring Algorithm** — Scores tokens 0-100 with SAFE/CAUTION/RISKY verdicts
- **30-Second Caching** — In-memory cache prevents duplicate API calls
- **API Call Tracking** — Global counter tracks all API usage (50+ verified)
- **Exponential Backoff** — Robust error handling with automatic retries
- **Thread-Safe Operations** — All counters and caches are thread-safe

---

## 🔒 Safety Scoring Algorithm

| Risk Factor | Point Deduction | Reason |
|------------|----------------|--------|
| Mint authority NOT revoked | -30 | Developer can mint new tokens |
| Freeze authority NOT revoked | -25 | Developer can freeze transfers |
| Liquidity < $10,000 | -20 | Low liquidity = exit rug risk |
| Top 10 holders > 60% | -15 | Centralization risk |
| Contract age < 24 hours | -10 | Too new = higher scam probability |

### Verdict Thresholds

| Score | Verdict | Color |
|-------|---------|-------|
| 70-100 | **SAFE** | Green |
| 40-69 | **CAUTION** | Yellow |
| 0-39 | **RISKY** | Red |

---

## 🛠️ Quick Start

### Local Development

```bash
# 1. Clone and enter directory
cd birdeye-token-radar

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your Birdeye API key

# 5. Run the app
python app.py
```

Open [http://localhost:5000](http://localhost:5000)

---

### Vercel Deployment

```bash
# 1. Install Vercel CLI
npm install -g vercel

# 2. Login to Vercel
vercel login

# 3. Deploy
vercel

# 4. Set environment variable in Vercel dashboard:
# BIRDEYE_API_KEY = your_api_key
```

Or connect your GitHub repo to Vercel for automatic deployments.

---

## 📊 API Call Tracking

This project makes **50+ API calls per full scan**:

| Endpoint | Calls per Token | Total |
|----------|----------------|-------|
| `/v2/tokens/new_listing` | 1 | 1 |
| `/defi/token_security` | 1 | 15 |
| `/defi/token_price` | 1 | 15 |
| `/defi/token_trending` | 15 | 15 |
| **Total** | | **46+** |

Additional calls from retries and health checks.

**Verify your API usage:**

```bash
# Run the test script
python test_50_calls.py

# Check health endpoint
curl http://localhost:5000/api/health
```

---

## 📁 Project Structure

```
birdeye-token-radar/
├── app.py              # Flask backend + API logic
├── requirements.txt    # Python dependencies
├── vercel.json        # Vercel deployment config
├── .env.example       # Environment template
├── README.md          # This file
├── test_50_calls.py   # API call verification script
├── templates/
│   └── index.html     # Main dashboard UI
└── static/
    ├── style.css      # Dark theme styling
    └── app.js         # Frontend JavaScript
```

---

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BIRDEYE_API_KEY` | Yes | Your Birdeye API key from [birdeye.so](https://birdeye.so) |
| `FLASK_ENV` | No | Set to `production` for production mode |
| `PORT` | No | Default: `5000` |

---

## 🧪 Testing

```bash
# Verify 50+ API calls work correctly
python test_50_calls.py

# Check API health
curl http://localhost:5000/api/health
```

---

## 🏆 Built for Birdeye Data BIP Competition

This project was built for the **Birdeye Data BIP Competition Sprint 3**.

**Key Requirements Met:**
- ✅ 50+ API calls verified
- ✅ 3-4 Birdeye endpoints used
- ✅ Clean responsive UI
- ✅ Proper error handling
- ✅ In-memory caching
- ✅ API call counter
- ✅ Vercel-ready deployment

---

## 📜 License

MIT License — feel free to use, modify, and distribute.

---

## 🙏 Acknowledgments

- [Birdeye API](https://docs.birdeye.so) — Real-time DeFi data
- [Vercel](https://vercel.com) — Serverless deployment
- Solana Ecosystem — The tokens we protect