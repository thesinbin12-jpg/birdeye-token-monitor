import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

import requests

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils import analyzer

log_file = PROJECT_ROOT / "api_calls.log"
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

if not BIRDEYE_API_KEY or BIRDEYE_API_KEY == "your_api_key_here":
    print("ERROR: BIRDEYE_API_KEY not found in .env file!")
    print("Please add your API key to .env")
    sys.exit(1)

print(f"\n{'=' * 60}")
print("  BIRDEYE API CALL TESTER")
print("  Verifying 50+ API calls for BIP Competition")
print(f"{'=' * 60}\n")
print(f"API Key: {BIRDEYE_API_KEY[:8]}...{BIRDEYE_API_KEY[-4:]}")
print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"API Calls at Start: {analyzer.get_api_counter()}")
print("-" * 60 + "\n")

print("Step 1: Scanning 15 new tokens (4 API calls each + 1 listing call)...")
result = analyzer.scan_new_tokens(15)

if result.get("error"):
    print(f"Error: {result['error']}")
    sys.exit(1)

print(f"\nTokens scanned: {result.get('tokens_scanned', 0)}")
print(f"API calls this scan: {result.get('calls_this_scan', 0)}")
print(f"Total API calls: {result.get('total_api_calls', 0)}")

print("\nStep 2: Analyzing a single token individually...")
sample_address = result['tokens'][0]['address'] if result.get('tokens') else None
if sample_address:
    before = analyzer.get_api_counter()
    analyzer.analyze_single_token(sample_address)
    after = analyzer.get_api_counter()
    print(f"Single token analysis: {after - before} API calls")

total = analyzer.get_api_counter()
print(f"\n{'=' * 60}")
print(f"COMPLETED {total} API CALLS")
print(f"{'=' * 60}")

if total >= 50:
    print(f"BOUNTY REQUIREMENT MET: {total} >= 50 calls")
else:
    print(f"Warning: Only {total} calls (need 50+)")

print(f"\nLog file saved to: {log_file}")
print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'=' * 60}\n")
