import os
import time
import logging
import requests
from threading import Lock
from typing import Dict, Any, Optional, List

from utils.scoring import (
    calculate_overall_score,
    generate_warnings,
    get_recommendation,
    get_verdict_class,
    format_contract_age,
    format_price,
    format_liquidity,
    format_fdv,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://public-api.birdeye.so"

api_call_counter = 0
counter_lock = Lock()

token_cache: Dict[str, Dict[str, Any]] = {}
cache_lock = Lock()

CACHE_TTL_SECONDS = 300


def increment_api_counter() -> int:
    global api_call_counter
    with counter_lock:
        api_call_counter += 1
        return api_call_counter


def get_api_counter() -> int:
    return api_call_counter


def reset_api_counter() -> int:
    global api_call_counter
    with counter_lock:
        old = api_call_counter
        api_call_counter = 0
        return old


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


def get_cache_count() -> int:
    with cache_lock:
        return len(token_cache)


def get_birdeye_data(endpoint: str, params: Dict = None, retries: int = 3) -> Dict[str, Any]:
    headers = {
        "accept": "application/json",
        "X-API-KEY": os.environ.get("BIRDEYE_API_KEY", ""),
        "x-chain": "solana",
    }
    url = f"{BASE_URL}{endpoint}"

    for attempt in range(retries):
        try:
            call_count = increment_api_counter()
            logger.info(f"API Call #{call_count}: {endpoint} params={params}")

            resp = requests.get(url, headers=headers, params=params, timeout=30)

            if resp.status_code == 429:
                wait = 2 ** attempt
                logger.warning(f"Rate limited on {endpoint}. Waiting {wait}s...")
                time.sleep(wait)
                continue

            if resp.status_code >= 500:
                wait = 2 ** attempt
                logger.warning(f"Server error {resp.status_code} on {endpoint}. Retry in {wait}s...")
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
            logger.error(f"Request failed for {endpoint}: {e}")
            if attempt == retries - 1:
                return {}

    return {}


def extract_token_list(api_response: Dict) -> List[Dict]:
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


def analyze_token(token_data: Dict, security_data: Dict, price_data: Dict, overview_data: Dict) -> Dict[str, Any]:
    analysis = calculate_overall_score(token_data, security_data, price_data, overview_data)
    warnings = generate_warnings(analysis)
    recommendation = get_recommendation(analysis["overall_score"])
    verdict_class = get_verdict_class(analysis["verdict"])

    age_hours, is_new = format_contract_age(token_data, security_data)
    if is_new and age_hours > 0:
        warnings.insert(0, {"level": "warning", "text": f"Contract <24h old ({age_hours:.0f}h) - High volatility"})

    price = float(price_data.get("value", 0) or 0)
    liquidity = analysis.get("liquidity", 0)
    fdv = float(overview_data.get("fdv", 0) or 0) or float(token_data.get("fdv", 0) or 0)
    logo_uri = token_data.get("logoURI", "") or overview_data.get("logoURI", "") or ""

    return {
        "address": token_data.get("address", ""),
        "name": token_data.get("name", "Unknown"),
        "symbol": token_data.get("symbol", "???"),
        "logo_uri": logo_uri,
        "score": analysis["overall_score"],
        "verdict": analysis["verdict"],
        "verdict_class": verdict_class,
        "security_score": analysis["security_score"],
        "distribution_score": analysis["distribution_score"],
        "liquidity_score": analysis["liquidity_score"],
        "momentum_score": analysis["momentum_score"],
        "mint_authority_revoked": analysis["mint_authority_revoked"],
        "freeze_authority_revoked": analysis["freeze_authority_revoked"],
        "liquidity": liquidity,
        "liquidity_formatted": format_liquidity(liquidity),
        "top_10_holders_pct": analysis["top_10_holders_pct"],
        "price": price,
        "price_formatted": format_price(price),
        "fdv": fdv,
        "fdv_formatted": format_fdv(fdv),
        "price_change_24h": analysis.get("price_change_24h", 0),
        "volume_24h": analysis.get("volume_24h", 0),
        "contract_age_hours": round(age_hours, 1),
        "is_new": is_new,
        "warnings": warnings,
        "recommendation": recommendation,
    }


def analyze_single_token(address: str) -> Dict[str, Any]:
    cached = get_cached(address)
    if cached:
        cached["from_cache"] = True
        return cached

    security_resp = get_birdeye_data('/defi/token_security', {"address": address})
    price_resp = get_birdeye_data('/defi/price', {"address": address, "include_liquidity": "true"})
    overview_resp = get_birdeye_data('/defi/token_overview', {"address": address})

    sec = security_resp.get("data", {}) if security_resp else {}
    pri = price_resp.get("data", {}) if price_resp else {}
    ovr = overview_resp.get("data", {}) if overview_resp else {}

    token_data = {
        "address": address,
        "name": sec.get("tokenMetadata", {}).get("name", "") or ovr.get("name", "Unknown"),
        "symbol": sec.get("tokenMetadata", {}).get("symbol", "") or ovr.get("symbol", "???"),
        "logoURI": ovr.get("logoURI", ""),
    }

    if sec or pri:
        result = analyze_token(token_data, sec, pri, ovr)
        set_cached(address, result)
        result["from_cache"] = False
        return result
    else:
        return {
            "address": address,
            "name": ovr.get("name", "Unknown"),
            "symbol": ovr.get("symbol", "???"),
            "logo_uri": ovr.get("logoURI", ""),
            "score": 0,
            "verdict": "UNKNOWN",
            "verdict_class": "risky",
            "security_score": 0,
            "distribution_score": 0,
            "liquidity_score": 0,
            "momentum_score": 0,
            "mint_authority_revoked": False,
            "freeze_authority_revoked": False,
            "liquidity": 0,
            "liquidity_formatted": "N/A",
            "top_10_holders_pct": 0,
            "price": 0,
            "price_formatted": "N/A",
            "fdv": 0,
            "fdv_formatted": "N/A",
            "price_change_24h": 0,
            "volume_24h": 0,
            "contract_age_hours": 0,
            "is_new": True,
            "warnings": [{"level": "warning", "text": "No security/price data available"}],
            "recommendation": {"label": "AVOID", "text": "Insufficient data to analyze"},
            "from_cache": False,
        }


def scan_new_tokens(limit: int = 15) -> Dict[str, Any]:
    api_key = os.environ.get("BIRDEYE_API_KEY", "")
    if not api_key or api_key == "your_api_key_here":
        return {"error": "API key not configured. Set BIRDEYE_API_KEY in Vercel settings.", "tokens": []}

    scan_start = get_api_counter()

    new_listings = get_birdeye_data('/defi/v2/tokens/new_listing', {'limit': limit})
    tokens_list = extract_token_list(new_listings)

    if not tokens_list:
        logger.warning("No new listings. Trying trending as fallback.")
        trending = get_birdeye_data('/defi/token_trending', {'sort_by': 'rank', 'limit': limit})
        tokens_list = extract_token_list(trending)

    if not tokens_list:
        return {"error": "No tokens found from Birdeye API. Try again later.", "tokens": []}

    raw_tokens = tokens_list[:limit]
    logger.info(f"Found {len(raw_tokens)} tokens to analyze")

    results = []
    for i, token in enumerate(raw_tokens):
        address = token.get("address", "")
        if not address:
            continue

        logger.info(f"Scanning {i+1}/{len(raw_tokens)}: {token.get('symbol', '???')}")

        cached = get_cached(address)
        if cached:
            cached["from_cache"] = True
            results.append(cached)
            continue

        security_resp = get_birdeye_data('/defi/token_security', {"address": address})
        price_resp = get_birdeye_data('/defi/price', {"address": address, "include_liquidity": "true"})
        overview_resp = get_birdeye_data('/defi/token_overview', {"address": address})

        try:
            sec = security_resp.get("data", {}) if security_resp else {}
            pri = price_resp.get("data", {}) if price_resp else {}
            ovr = overview_resp.get("data", {}) if overview_resp else {}

            if sec or pri:
                result = analyze_token(token, sec, pri, ovr)
                set_cached(address, result)
                result["from_cache"] = False
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
                    "verdict_class": "risky",
                    "security_score": 0,
                    "distribution_score": 0,
                    "liquidity_score": 0,
                    "momentum_score": 0,
                    "mint_authority_revoked": False,
                    "freeze_authority_revoked": False,
                    "liquidity": 0,
                    "liquidity_formatted": "N/A",
                    "top_10_holders_pct": 0,
                    "price": 0,
                    "price_formatted": "N/A",
                    "fdv": 0,
                    "fdv_formatted": "N/A",
                    "price_change_24h": 0,
                    "volume_24h": 0,
                    "contract_age_hours": 0,
                    "is_new": True,
                    "warnings": [{"level": "warning", "text": "No data available"}],
                    "recommendation": {"label": "AVOID", "text": "Insufficient data"},
                    "from_cache": False,
                })
        except Exception as e:
            logger.error(f"Error processing {address}: {e}")
            results.append({
                "address": address,
                "name": token.get("name", "Error"),
                "symbol": token.get("symbol", "???"),
                "logo_uri": token.get("logoURI", ""),
                "score": 0,
                "verdict": "ERROR",
                "verdict_class": "risky",
                "security_score": 0,
                "distribution_score": 0,
                "liquidity_score": 0,
                "momentum_score": 0,
                "mint_authority_revoked": False,
                "freeze_authority_revoked": False,
                "liquidity": 0,
                "liquidity_formatted": "N/A",
                "top_10_holders_pct": 0,
                "price": 0,
                "price_formatted": "N/A",
                "fdv": 0,
                "fdv_formatted": "N/A",
                "price_change_24h": 0,
                "volume_24h": 0,
                "contract_age_hours": 0,
                "is_new": True,
                "warnings": [{"level": "critical", "text": f"Analysis error: {str(e)}"}],
                "recommendation": {"label": "AVOID", "text": "Analysis failed"},
                "from_cache": False,
            })

    scan_end = get_api_counter()
    calls_this_scan = scan_end - scan_start

    logger.info(f"=== Scan complete. Total API calls: {api_call_counter}, this scan: {calls_this_scan} ===")

    return {
        "tokens": results,
        "total_api_calls": api_call_counter,
        "calls_this_scan": calls_this_scan,
        "tokens_scanned": len(results),
    }
