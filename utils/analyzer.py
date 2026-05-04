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
from utils.cache import get_cached, set_cached, get_cache_count, clear_cache
from utils.ai_insights import generate_ai_summary
from utils.simulation import simulate_investment
from utils.pattern_matching import run_all_patterns
from utils.comparative import generate_comparative

logger = logging.getLogger(__name__)

BASE_URL = "https://public-api.birdeye.so"

api_call_counter = 0
counter_lock = Lock()


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
    recommendation = get_recommendation(analysis["overall_score"], analysis)
    verdict_class = get_verdict_class(analysis["verdict"])

    age_hours, is_new = format_contract_age(token_data, security_data)
    if is_new and age_hours > 0:
        warnings.insert(0, {"level": "warning", "text": f"Contract <24h old ({age_hours:.0f}h) - High volatility"})

    price = float(price_data.get("value", 0) or 0)
    liquidity = analysis.get("liquidity", 0)
    fdv = float(overview_data.get("fdv", 0) or 0) or float(token_data.get("fdv", 0) or 0)
    logo_uri = token_data.get("logoURI", "") or overview_data.get("logoURI", "") or ""

    result = {
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
        "top_holder_pct": analysis.get("top_holder_pct", 0),
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

    ai_data = {
        "address": result["address"],
        "name": result["name"],
        "symbol": result["symbol"],
        "score": result["score"],
        "verdict": result["verdict"],
        "liquidity": result["liquidity"],
        "mint_authority_revoked": result["mint_authority_revoked"],
        "freeze_authority_revoked": result["freeze_authority_revoked"],
        "top_10_holders_pct": result["top_10_holders_pct"],
        "price_change_24h": result["price_change_24h"],
    }

    try:
        ai_result = generate_ai_summary(ai_data)
        result["ai_insight"] = ai_result.get("insight", "AI analysis failed to generate text")
        result["ai_source"] = ai_result.get("source", "unavailable")
        result["ai_available"] = ai_result.get("available", False)
        if ai_result.get("model"):
            result["ai_model"] = ai_result["model"]
    except Exception as e:
        logger.error(f"AI summary generation failed: {e}")
        result["ai_insight"] = f"AI insight generation error: {str(e)[:100]}"
        result["ai_source"] = "error"
        result["ai_available"] = False

    sim_result = simulate_investment(ai_data, investment_usd=100)
    result["simulation"] = sim_result

    pattern_result = run_all_patterns(ai_data)
    result["patterns"] = pattern_result

    return result


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
            "top_holder_pct": 0,
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
        "ai_insight": "No security or price data available — unable to generate AI analysis.",
    "ai_source": "unavailable",
    "ai_available": False,
    "simulation": simulate_investment({"price": 0, "liquidity": 0, "score": 0}),
    "patterns": run_all_patterns({"score": 0}),
    "from_cache": False,
}


def _error_token_result(token, address, error):
    return {
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
        "top_holder_pct": 0,
        "price": 0,
        "price_formatted": "N/A",
        "fdv": 0,
        "fdv_formatted": "N/A",
        "price_change_24h": 0,
        "volume_24h": 0,
        "contract_age_hours": 0,
        "is_new": True,
        "warnings": [{"level": "critical", "text": f"Analysis error: {str(error)}"}],
        "recommendation": {"label": "AVOID", "text": "Analysis failed"},
        "ai_insight": "Analysis failed — unable to assess this token due to data retrieval error.",
        "ai_source": "unavailable",
        "ai_available": False,
            "simulation": simulate_investment({"price": 0, "liquidity": 0, "score": 0}),
            "patterns": run_all_patterns({"score": 0}),
            "from_cache": False,
        }


def scan_new_tokens(limit: int = 15) -> Dict[str, Any]:
    api_key = os.environ.get("BIRDEYE_API_KEY", "")
    if not api_key or api_key == "your_api_key_here":
        return {"error": "API key not configured. Set BIRDEYE_API_KEY in Vercel settings.", "tokens": []}

    scan_start = get_api_counter()

    seen_addresses = set()
    tokens_list = []

    new_listings = get_birdeye_data('/defi/v2/tokens/new_listing', {'limit': limit})
    new_tokens = extract_token_list(new_listings)
    for t in new_tokens:
        addr = t.get("address", "")
        if addr and addr not in seen_addresses:
            seen_addresses.add(addr)
            tokens_list.append(t)

    if len(tokens_list) < limit:
        logger.info(f"New listings returned {len(tokens_list)} tokens, fetching trending to fill up to {limit}")
        trending = get_birdeye_data('/defi/token_trending', {'sort_by': 'rank', 'limit': limit})
        trending_tokens = extract_token_list(trending)
        for t in trending_tokens:
            addr = t.get("address", "")
            if addr and addr not in seen_addresses:
                seen_addresses.add(addr)
                tokens_list.append(t)
            if len(tokens_list) >= limit:
                break

    if len(tokens_list) < limit:
        logger.info(f"Still only {len(tokens_list)} tokens, fetching top gainers as additional fallback")
        gainers = get_birdeye_data('/defi/token_trending', {'sort_by': 'rank', 'sort_by': '24hPercent', 'limit': limit})
        gainer_tokens = extract_token_list(gainers)
        for t in gainer_tokens:
            addr = t.get("address", "")
            if addr and addr not in seen_addresses:
                seen_addresses.add(addr)
                tokens_list.append(t)
            if len(tokens_list) >= limit:
                break

    if not tokens_list:
        return {"error": "No tokens found from Birdeye API. Rate limit may have been hit. Try again in a minute.", "tokens": []}

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
            logger.info(f"Score for {token.get('symbol')}: {result['score']} ({result['verdict']}) - AI: {result.get('ai_insight', 'MISSING')[:50]}")
        else:
            empty = _empty_token_result(token, address)
            results.append(empty)
            logger.info(f"Empty result for {token.get('symbol')} - no security/price data")
    except Exception as e:
        logger.error(f"Error processing {address}: {e}")
        results.append(_error_token_result(token, address, e))

    scan_end = get_api_counter()
    calls_this_scan = scan_end - scan_start

    comp_results = []
    for result in results:
        comp = generate_comparative(result, results)
        result["comparative"] = comp
        comp_results.append(result)

    logger.info(f"=== Scan complete. Total API calls: {api_call_counter}, this scan: {calls_this_scan} ===")

    return {
        "tokens": comp_results,
        "total_api_calls": api_call_counter,
        "calls_this_scan": calls_this_scan,
        "tokens_scanned": len(results),
        "batch_stats": generate_comparative(results[0] if results else {}, results).get("batch_stats", {}),
    }


def _empty_token_result(token, address):
    return {
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
        "top_holder_pct": 0,
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
        "ai_insight": "",
        "ai_source": "unavailable",
        "ai_available": False,
        "simulation": simulate_investment({"price": 0, "liquidity": 0, "score": 0}),
        "patterns": run_all_patterns({"score": 0}),
        "from_cache": False,
    }


def _error_token_result(token, address, error):
    return {
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
        "top_holder_pct": 0,
        "price": 0,
        "price_formatted": "N/A",
        "fdv": 0,
        "fdv_formatted": "N/A",
        "price_change_24h": 0,
        "volume_24h": 0,
        "contract_age_hours": 0,
        "is_new": True,
        "warnings": [{"level": "critical", "text": f"Analysis error: {str(error)}"}],
        "recommendation": {"label": "AVOID", "text": "Analysis failed"},
        "ai_insight": "",
        "ai_source": "unavailable",
        "ai_available": False,
        "simulation": simulate_investment({"price": 0, "liquidity": 0, "score": 0}),
        "patterns": run_all_patterns({"score": 0}),
        "from_cache": False,
    }
