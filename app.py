"""
Birdeye Token Safety Radar - Flask Application
Scans newly listed Solana tokens for rug pull risk using Birdeye API
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from flask import Flask, jsonify, render_template
from flask_cors import CORS
import requests
from threading import Lock
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Thread-safe API call counter
api_call_counter = 0
counter_lock = Lock()

# In-memory cache: {address: {"data": ..., "timestamp": ...}}
token_cache: Dict[str, Dict[str, Any]] = {}
cache_lock = Lock()

CACHE_TTL_SECONDS = 30

def increment_api_counter() -> int:
    """Thread-safe API call counter increment"""
    global api_call_counter
    with counter_lock:
        api_call_counter += 1
        return api_call_counter

def get_cached(address: str) -> Optional[Dict[str, Any]]:
    """Get token data from cache if fresh"""
    with cache_lock:
        if address in token_cache:
            cached_entry = token_cache[address]
            if time.time() - cached_entry["timestamp"] < CACHE_TTL_SECONDS:
                return cached_entry["data"]
    return None

def set_cached(address: str, data: Dict[str, Any]) -> None:
    """Store token data in cache"""
    with cache_lock:
        token_cache[address] = {
            "data": data,
            "timestamp": time.time()
        }

@dataclass
class TokenSafetyResult:
    """Token safety analysis result"""
    address: str
    name: str
    symbol: str
    score: int
    verdict: str
    verdict_color: str
    mint_authority_revoked: bool
    freeze_authority_revoked: bool
    liquidity: float
    liquidity_formatted: str
    top_10_holders_pct: float
    contract_age_hours: float
    price: float
    price_formatted: str
    api_calls_used: int

def calculate_safety_score(token_data: Dict[str, Any], security_data: Dict[str, Any],
                          price_data: Dict[str, Any], api_calls: int) -> TokenSafetyResult:
    """
    Calculate safety score (0-100) for a token based on multiple risk factors.

    Scoring Algorithm:
    - Start at 100
    - -30 if mint authority NOT revoked
    - -25 if freeze authority NOT revoked
    - -20 if liquidity < $10,000
    - -15 if top 10 holders hold > 60% of supply
    - -10 if contract age < 24 hours

    Verdict:
    - Score >= 70: SAFE (green)
    - Score 40-69: CAUTION (yellow)
    - Score < 40: RISKY (red)
    """
    score = 100

    # Check mint authority (renounced = True means SAFE, we subtract if NOT revoked)
    mint_revoked = security_data.get("mintAuthority", "")
    if mint_revoked and mint_revoked.lower() != "null" and mint_revoked != "":
        score -= 30
        mint_auth_revoked = False
    else:
        mint_auth_revoked = True

    # Check freeze authority
    freeze_revoked = security_data.get("freezeAuthority", "")
    if freeze_revoked and freeze_revoked.lower() != "null" and freeze_revoked != "":
        score -= 25
        freeze_auth_revoked = False
    else:
        freeze_auth_revoked = True

    # Check liquidity (in USD)
    liquidity = price_data.get("liquidity", 0) or 0
    if liquidity < 10000:
        score -= 20

    # Check holder concentration (top 10 holders %)
    holder_data = security_data.get("holder", {})
    top_10_pct = holder_data.get("top10HolderPercent", 0) or 0
    if top_10_pct > 60:
        score -= 15

    # Check contract age
    try:
        creation_time = security_data.get("tokenMetadata", {}).get("tokenCreationTime", 0)
        if creation_time:
            age_hours = (time.time() * 1000 - creation_time) / 3600000
            if age_hours < 24:
                score -= 10
        else:
            age_hours = 0
    except:
        age_hours = 0

    # Ensure score stays in 0-100 range
    score = max(0, min(100, score))

    # Determine verdict
    if score >= 70:
        verdict = "SAFE"
        verdict_color = "#22c55e"
    elif score >= 40:
        verdict = "CAUTION"
        verdict_color = "#eab308"
    else:
        verdict = "RISKY"
        verdict_color = "#ef4444"

    # Format values for display
    name = token_data.get("name", "Unknown")
    symbol = token_data.get("symbol", "???")
    address = token_data.get("address", "")

    # Get price
    price = price_data.get("value", 0) or 0
    if price > 0:
        if price < 0.001:
            price_formatted = f"${price:.8f}"
        elif price < 1:
            price_formatted = f"${price:.6f}"
        else:
            price_formatted = f"${price:.4f}"
    else:
        price_formatted = "N/A"

    # Format liquidity
    if liquidity >= 1000000:
        liquidity_formatted = f"${liquidity/1000000:.2f}M"
    elif liquidity >= 1000:
        liquidity_formatted = f"${liquidity/1000:.2f}K"
    else:
        liquidity_formatted = f"${liquidity:.2f}"

    return TokenSafetyResult(
        address=address,
        name=name,
        symbol=symbol,
        score=score,
        verdict=verdict,
        verdict_color=verdict_color,
        mint_authority_revoked=mint_auth_revoked,
        freeze_authority_revoked=freeze_auth_revoked,
        liquidity=liquidity,
        liquidity_formatted=liquidity_formatted,
        top_10_holders_pct=top_10_pct,
        contract_age_hours=round(age_hours, 1),
        price=price,
        price_formatted=price_formatted,
        api_calls_used=api_calls
    )

def get_birdeye_data(endpoint: str, params: Dict = None, retries: int = 3) -> Dict[str, Any]:
    """
    Make API call to Birdeye with exponential backoff retry for rate limits.
    Tracks API calls globally for the 50+ call requirement verification.
    """
    headers = {
        "accept": "application/json",
        "X-API-KEY": os.environ.get("BIRDEYE_API_KEY", "")
    }
    url = f"https://public-api.birdeye.so{endpoint}"

    for attempt in range(retries):
        try:
            # Increment global API call counter (thread-safe)
            call_count = increment_api_counter()
            logger.info(f"API Call #{call_count}: {endpoint}")

            response = requests.get(url, headers=headers, params=params, timeout=30)

            # Handle rate limiting with exponential backoff
            if response.status_code == 429:
                wait_time = 2 ** attempt
                logger.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue

            # Handle server errors
            if response.status_code >= 500:
                wait_time = 2 ** attempt
                logger.warning(f"Server error {response.status_code}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue

            if response.status_code == 200:
                return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {endpoint}")
            if attempt == retries - 1:
                return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if attempt == retries - 1:
                return {}

    return {}

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)
app.config['JSON_SORT_KEYS'] = False

@app.route('/')
def index():
    """Serve the main dashboard HTML"""
    return render_template('index.html')

@app.route('/api/health')
def health():
    """Health check endpoint with API call count"""
    global api_call_counter
    return jsonify({
        "status": "ok",
        "api_calls_made": api_call_counter,
        "cache_entries": len(token_cache),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/scan-new-tokens', methods=['POST'])
def scan_new_tokens():
    """
    Main endpoint: Scan latest 15 newly listed Solana tokens via Birdeye API.
    For each token, fetches security data, price data, and calculates safety score.
    Returns array of tokens with risk verdicts.
    """
    logger.info("=== Starting token scan ===")

    # Check if API key is configured
    api_key = os.environ.get("BIRDEYE_API_KEY", "")
    if not api_key or api_key == "your_api_key_here":
        logger.error("BIRDEYE_API_KEY not configured")
        return jsonify({
            "error": "API key not configured",
            "message": "Please set BIRDEYE_API_KEY in Vercel project settings",
            "tokens": []
        }), 503

    # Step 1: Get latest 15 new token listings from Birdeye
    new_listings = get_birdeye_data('/v2/tokens/new_listing', {'limit': 15})

    if 'data' not in new_listings or not new_listings['data']:
        logger.warning("No new listings found or API returned empty response")
        return jsonify({"error": "No tokens found", "tokens": []}), 200

    raw_tokens = new_listings['data'][:15]  # Ensure max 15 tokens
    logger.info(f"Found {len(raw_tokens)} new tokens to analyze")

    results: List[Dict[str, Any]] = []

    # Step 2: Analyze each token
    for i, token in enumerate(raw_tokens):
        address = token.get("address", "")
        if not address:
            continue

        logger.info(f"Scanning token {i+1}/{len(raw_tokens)}: {token.get('symbol', '???')}")

        # Check cache first
        cached_result = get_cached(address)

        if cached_result:
            logger.info(f"Using cached data for {address}")
            results.append(cached_result)
            continue

        # Fetch fresh data for this token
        api_calls_for_token = api_call_counter  # Track calls made for this token

        # Step 3: Get token security data
        security_data = get_birdeye_data(
            '/defi/token_security',
            {"address": address}
        )

        # Step 4: Get token price data
        price_data = get_birdeye_data(
            '/defi/token_price',
            {"address": address}
        )

        # Step 5: Calculate safety score and create result
        try:
            if security_data and price_data:
                safety_result = calculate_safety_score(
                    token,
                    security_data.get("data", {}),
                    price_data.get("data", {}),
                    api_call_counter
                )
                result_dict = asdict(safety_result)
                set_cached(address, result_dict)
                results.append(result_dict)
                logger.info(f"Score for {token.get('symbol')}: {safety_result.score} ({safety_result.verdict})")
            else:
                # Handle API failure for this token gracefully
                logger.warning(f"Missing data for {address}, adding with UNKNOWN verdict")
                results.append({
                    "address": address,
                    "name": token.get("name", "Unknown"),
                    "symbol": token.get("symbol", "???"),
                    "score": 0,
                    "verdict": "UNKNOWN",
                    "verdict_color": "#6b7280",
                    "mint_authority_revoked": False,
                    "freeze_authority_revoked": False,
                    "liquidity": 0,
                    "liquidity_formatted": "N/A",
                    "top_10_holders_pct": 0,
                    "contract_age_hours": 0,
                    "price": 0,
                    "price_formatted": "N/A",
                    "api_calls_used": api_call_counter
                })
        except Exception as e:
            logger.error(f"Error processing token {address}: {e}")
            continue

    logger.info(f"=== Scan complete. Total API calls: {api_call_counter} ===")

    return jsonify({
        "tokens": results,
        "total_api_calls": api_call_counter,
        "tokens_scanned": len(results)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)