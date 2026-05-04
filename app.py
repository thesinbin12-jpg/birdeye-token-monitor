"""
Birdeye Token Safety Radar - Flask Application
Scans newly listed Solana tokens for rug pull risk using Birdeye API
Deployed on Vercel Serverless Python
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from flask import Flask, jsonify, render_template, send_from_directory
from flask_cors import CORS
import requests
from threading import Lock
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_call_counter = 0
counter_lock = Lock()

token_cache: Dict[str, Dict[str, Any]] = {}
cache_lock = Lock()

CACHE_TTL_SECONDS = 30


def increment_api_counter() -> int:
    global api_call_counter
    with counter_lock:
        api_call_counter += 1
        return api_call_counter


def get_cached(address: str) -> Optional[Dict[str, Any]]:
    with cache_lock:
        if address in token_cache:
            entry = token_cache[address]
            if time.time() - entry["timestamp"] < CACHE_TTL_SECONDS:
                return entry["data"]
    return None


def set_cached(address: str, data: Dict[str, Any]) -> None:
    with cache_lock:
        token_cache[address] = {"data": data, "timestamp": time.time()}


def calculate_safety_score(token_data: Dict, security_data: Dict, price_data: Dict, overview_data: Dict, api_calls: int) -> Dict[str, Any]:
    """
    Safety scoring: start at 100
    -30 mint authority not revoked
    -25 freeze authority not revoked
    -20 liquidity < $10k
    -15 top 10 holders > 60%
    -10 contract age < 24h
    >=70 SAFE, 40-69 CAUTION, <40 RISKY
    """
    score = 100

    mint_val = security_data.get("mintAuthority", "")
    if mint_val and str(mint_val).lower() not in ("null", "", "none"):
        score -= 30
        mint_revoked = False
    else:
        mint_revoked = True

    freeze_val = security_data.get("freezeAuthority", "")
    if freeze_val and str(freeze_val).lower() not in ("null", "", "none"):
        score -= 25
        freeze_revoked = False
    else:
        freeze_revoked = True

    liquidity = float(price_data.get("liquidity", 0) or 0)
    if liquidity < 10000:
        score -= 20

    holder_data = security_data.get("holder", {}) or {}
    top_10_pct = float(holder_data.get("top10HolderPercent", 0) or 0)
    if top_10_pct > 60:
        score -= 15

    age_hours = 0
    try:
        creation_ts = 0
        for source in [security_data, token_data]:
            for key in ('tokenCreationTime', 'createTime', 'createdAt', 'liquidityAddedAt'):
                val = source.get(key, 0) or 0
                if val:
                    creation_ts = val
                    break
            meta = source.get("tokenMetadata", {}) or {}
            for key in ('tokenCreationTime', 'createTime', 'createdAt'):
                val = meta.get(key, 0) or 0
                if val:
                    creation_ts = val
                    break
            if creation_ts:
                break

        if creation_ts:
            if isinstance(creation_ts, str):
                from datetime import timezone
                try:
                    dt = datetime.fromisoformat(creation_ts.replace('Z', '+00:00'))
                    creation_ts = dt.timestamp() * 1000
                except Exception:
                    creation_ts = 0
            if creation_ts > 0:
                age_hours = (time.time() * 1000 - creation_ts) / 3600000
                if age_hours < 24:
                    score -= 10
    except Exception:
        age_hours = 0

    score = max(0, min(100, score))

    if score >= 70:
        verdict = "SAFE"
    elif score >= 40:
        verdict = "CAUTION"
    else:
        verdict = "RISKY"

    name = token_data.get("name", "Unknown")
    symbol = token_data.get("symbol", "???")
    address = token_data.get("address", "")
    logo_uri = token_data.get("logoURI", "") or overview_data.get("logoURI", "") or ""

    price = float(price_data.get("value", 0) or 0)
    if price > 0:
        if price < 0.001:
            price_fmt = f"${price:.8f}"
        elif price < 1:
            price_fmt = f"${price:.6f}"
        else:
            price_fmt = f"${price:.4f}"
    else:
        price_fmt = "N/A"

    if liquidity >= 1000000:
        liq_fmt = f"${liquidity/1000000:.2f}M"
    elif liquidity >= 1000:
        liq_fmt = f"${liquidity/1000:.2f}K"
    else:
        liq_fmt = f"${liquidity:.2f}"

    fdv = float(overview_data.get("fdv", 0) or 0) or float(token_data.get("fdv", 0) or 0)
    if fdv >= 1e9:
        fdv_fmt = f"${fdv/1e9:.2f}B"
    elif fdv >= 1e6:
        fdv_fmt = f"${fdv/1e6:.2f}M"
    elif fdv >= 1e3:
        fdv_fmt = f"${fdv/1e3:.2f}K"
    elif fdv > 0:
        fdv_fmt = f"${fdv:.2f}"
    else:
        fdv_fmt = "N/A"

    return {
        "address": address,
        "name": name,
        "symbol": symbol,
        "logo_uri": logo_uri,
        "score": score,
        "verdict": verdict,
        "mint_authority_revoked": mint_revoked,
        "freeze_authority_revoked": freeze_revoked,
        "liquidity": liquidity,
        "liquidity_formatted": liq_fmt,
        "top_10_holders_pct": top_10_pct,
        "contract_age_hours": round(age_hours, 1),
        "price": price,
        "price_formatted": price_fmt,
        "fdv": fdv,
        "fdv_formatted": fdv_fmt,
        "api_calls_used": api_calls
    }


def get_birdeye_data(endpoint: str, params: Dict = None, retries: int = 3) -> Dict[str, Any]:
    headers = {
        "accept": "application/json",
        "X-API-KEY": os.environ.get("BIRDEYE_API_KEY", ""),
        "x-chain": "solana"
    }
    url = f"https://public-api.birdeye.so{endpoint}"

    for attempt in range(retries):
        try:
            call_count = increment_api_counter()
            logger.info(f"API Call #{call_count}: {endpoint}")

            resp = requests.get(url, headers=headers, params=params, timeout=30)

            if resp.status_code == 429:
                wait = 2 ** attempt
                logger.warning(f"Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue

            if resp.status_code >= 500:
                wait = 2 ** attempt
                logger.warning(f"Server error {resp.status_code}. Retry in {wait}s...")
                time.sleep(wait)
                continue

            if resp.status_code == 200:
                return resp.json()

            logger.error(f"API {endpoint} returned {resp.status_code}: {resp.text[:200]}")
            return {}

        except requests.exceptions.Timeout:
            logger.error(f"Timeout for {endpoint}")
            if attempt == retries - 1:
                return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if attempt == retries - 1:
                return {}

    return {}


app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/health')
def health():
    return jsonify({
        "status": "ok",
        "api_calls_made": api_call_counter,
        "cache_entries": len(token_cache)
    })


def extract_token_list(api_response: Dict) -> List[Dict]:
    """Extract token list from Birdeye API response - handles multiple response formats."""
    if not api_response or 'data' not in api_response:
        return []

    data = api_response['data']

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ('items', 'tokens', 'data', 'list', 'results'):
            if key in data and isinstance(data[key], list):
                return data[key]

        if 'address' in data:
            return [data]

    return []


@app.route('/api/scan-new-tokens', methods=['POST', 'GET'])
def scan_new_tokens():
    try:
        logger.info("=== Starting token scan ===")

        api_key = os.environ.get("BIRDEYE_API_KEY", "")
        if not api_key or api_key == "your_api_key_here":
            logger.error("BIRDEYE_API_KEY not configured")
            return jsonify({
                "error": "API key not configured. Set BIRDEYE_API_KEY in Vercel settings.",
                "tokens": [],
                "total_api_calls": api_call_counter
            })

        new_listings = get_birdeye_data('/defi/v2/tokens/new_listing', {'limit': 15})
        logger.info(f"New listings response keys: {list(new_listings.keys()) if new_listings else 'EMPTY'}")

        tokens_list = extract_token_list(new_listings)

        if not tokens_list:
            logger.warning("No new listings. Trying trending as fallback.")
            trending = get_birdeye_data('/defi/token_trending', {'sort_by': 'rank', 'limit': 15})
            tokens_list = extract_token_list(trending)

        if not tokens_list:
            return jsonify({
                "error": "No tokens found from Birdeye API. Try again later.",
                "tokens": [],
                "total_api_calls": api_call_counter
            })

        raw_tokens = tokens_list[:15]
        logger.info(f"Found {len(raw_tokens)} tokens to analyze")

        results = []

        for i, token in enumerate(raw_tokens):
            address = token.get("address", "")
            if not address:
                continue

            logger.info(f"Scanning {i+1}/{len(raw_tokens)}: {token.get('symbol', '???')}")

            cached = get_cached(address)
            if cached:
                results.append(cached)
                continue

        security_data = get_birdeye_data('/defi/token_security', {"address": address})
        price_data = get_birdeye_data('/defi/price', {"address": address, "include_liquidity": "true"})
        overview_data = get_birdeye_data('/defi/token_overview', {"address": address})

        try:
            sec = security_data.get("data", {}) if security_data else {}
            pri = price_data.get("data", {}) if price_data else {}
            ovr = overview_data.get("data", {}) if overview_data else {}

            if sec or pri:
                result = calculate_safety_score(token, sec, pri, ovr, api_call_counter)
                set_cached(address, result)
                results.append(result)
                logger.info(f"Score for {token.get('symbol')}: {result['score']} ({result['verdict']})")
            else:
                results.append({
                    "address": address,
                    "name": token.get("name", "Unknown"),
                    "symbol": token.get("symbol", "???"),
                    "logo_uri": token.get("logoURI", ""),
                    "score": 0,
                    "verdict": "UNKNOWN",
                    "mint_authority_revoked": False,
                    "freeze_authority_revoked": False,
                    "liquidity": 0,
                    "liquidity_formatted": "N/A",
                    "top_10_holders_pct": 0,
                    "contract_age_hours": 0,
                    "price": 0,
                    "price_formatted": "N/A",
                    "fdv": 0,
                    "fdv_formatted": "N/A",
                    "api_calls_used": api_call_counter
                })
            except Exception as e:
                logger.error(f"Error processing {address}: {e}")
            results.append({
                "address": address,
                "name": token.get("name", "Error"),
                "symbol": token.get("symbol", "???"),
                "logo_uri": token.get("logoURI", ""),
                "score": 0,
                "verdict": "UNKNOWN",
                "mint_authority_revoked": False,
                "freeze_authority_revoked": False,
                "liquidity": 0,
                "liquidity_formatted": "N/A",
                "top_10_holders_pct": 0,
                "contract_age_hours": 0,
                "price": 0,
                "price_formatted": "N/A",
                "fdv": 0,
                "fdv_formatted": "N/A",
                "api_calls_used": api_call_counter
            })

        logger.info(f"=== Scan complete. Total API calls: {api_call_counter} ===")

        return jsonify({
            "tokens": results,
            "total_api_calls": api_call_counter,
            "tokens_scanned": len(results)
        })

    except Exception as e:
        logger.error(f"Scan endpoint crashed: {e}")
        return jsonify({
            "error": f"Server error: {str(e)}",
            "tokens": [],
            "total_api_calls": api_call_counter
        })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)