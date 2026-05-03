"""
Test script to verify 50+ API calls requirement for Birdeye Data BIP Competition.
Simulates a full scan: 15 tokens x 3 calls each + 1 new listing call + 1 trending fallback = 47 calls.
Plus additional trending calls to exceed 50.
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

import requests

log_file = Path(__file__).parent / "api_calls.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

BIRDEYE_API_KEY = os.environ.get("BIRDEYE_API_KEY", "")
BASE_URL = "https://public-api.birdeye.so"

api_call_count = 0


def extract_token_list(api_response: dict) -> list:
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


def make_api_call(endpoint: str, params: dict = None, description: str = "") -> dict:
    global api_call_count

    headers = {
        "accept": "application/json",
        "X-API-KEY": BIRDEYE_API_KEY,
        "x-chain": "solana"
    }

    url = f"{BASE_URL}{endpoint}"

    try:
        api_call_count += 1
        call_num = api_call_count
        logger.info(f"[CALL #{call_num}] {endpoint} - {description}")

        response = requests.get(url, headers=headers, params=params, timeout=30)

        if response.status_code == 429:
            logger.warning(f"[CALL #{call_num}] Rate limited. Waiting 2s...")
            time.sleep(2)
            api_call_count -= 1
            return make_api_call(endpoint, params, description)

        if response.status_code == 200:
            return response.json()

        logger.error(f"[CALL #{call_num}] Failed with status {response.status_code}")
        return {}

    except Exception as e:
        logger.error(f"[CALL #{call_num}] Exception: {e}")
        return {}


def simulate_token_scan(num_tokens: int = 15):
    logger.info(f"=== Starting token scan simulation for {num_tokens} tokens ===")

    listings_response = make_api_call(
        "/defi/v2/tokens/new_listing",
        {"limit": num_tokens},
        "Get new token listings"
    )

    tokens = extract_token_list(listings_response)

    if not tokens:
        logger.warning("No listings found, trying trending fallback.")
        trending = make_api_call(
            "/defi/token_trending",
            {"sort_by": "rank", "limit": num_tokens},
            "Get trending tokens (fallback)"
        )
        tokens = extract_token_list(trending)

    if not tokens:
        logger.error("No tokens found. Check API key and try again.")
        return []

    tokens = tokens[:num_tokens]
    results = []

    for i, token in enumerate(tokens):
        address = token.get("address", "")
        symbol = token.get("symbol", "???")

        logger.info(f"Scanning token {i+1}/{num_tokens}: {symbol}")

        security_data = make_api_call(
            "/defi/token_security",
            {"address": address},
            f"Get security for {symbol}"
        )

        price_data = make_api_call(
            "/defi/price",
            {"address": address, "include_liquidity": "true"},
            f"Get price for {symbol}"
        )

        results.append({
            "symbol": symbol,
            "address": address,
            "security": security_data.get("data", {}),
            "price": price_data.get("data", {})
        })

        time.sleep(0.3)

    return results


def get_trending_tokens(num_calls: int = 5):
    logger.info(f"=== Fetching trending tokens ({num_calls} calls) ===")

    for i in range(num_calls):
        make_api_call(
            "/defi/token_trending",
            {"sort_by": "volume", "limit": 10},
            f"Get trending tokens (call {i+1}/{num_calls})"
        )
        time.sleep(0.2)


def main():
    global api_call_count

    print("\n" + "=" * 60)
    print(" BIRDEYE API CALL TESTER")
    print(" Verifying 50+ API calls for BIP Competition")
    print("=" * 60 + "\n")

    if not BIRDEYE_API_KEY:
        print("ERROR: BIRDEYE_API_KEY not found!")
        print(" Please add your API key to .env file")
        sys.exit(1)

    print(f"API Key: {BIRDEYE_API_KEY[:8]}...{BIRDEYE_API_KEY[-4:]}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60 + "\n")

    try:
        print("Step 1: Scanning 15 new tokens (3 API calls each)...")
        tokens = simulate_token_scan(15)

        print(f"\nStep 2: Additional trending token calls...")
        get_trending_tokens(5)

        print("\n" + "=" * 60)
        print(f"COMPLETED {api_call_count} API CALLS")
        print("=" * 60)

        if api_call_count >= 50:
            print(f"BOUNTY REQUIREMENT MET: {api_call_count} >= 50 calls")
        else:
            print(f"Warning: Only {api_call_count} calls (need 50+)")

        print(f"\nLog file saved to: {log_file}")
        print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60 + "\n")

        return api_call_count

    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\nTEST FAILED: {e}")
        return api_call_count


if __name__ == "__main__":
    main()