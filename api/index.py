import os
import sys
import re
import logging

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from utils import analyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    static_folder=os.path.join(PROJECT_ROOT, 'static'),
)
CORS(app)


@app.route('/')
def index():
    return send_from_directory(os.path.join(PROJECT_ROOT, 'static'), 'index.html')


@app.route('/api/health')
def health():
    return jsonify({
        "status": "ok",
        "api_calls_made": analyzer.get_api_counter(),
        "cache_entries": analyzer.get_cache_count(),
        "groq_configured": bool(os.environ.get("GROQ_API_KEY", "")),
    })


@app.route('/api/test-connection')
def test_connection():
    api_key = os.environ.get("BIRDEYE_API_KEY", "")
    if not api_key or api_key == "your_api_key_here":
        return jsonify({"connected": False, "error": "API key not configured"})
    resp = analyzer.get_birdeye_data('/defi/token_trending', {'sort_by': 'rank', 'limit': 1})
    if resp and resp.get("success"):
        return jsonify({"connected": True, "api_calls_made": analyzer.get_api_counter()})
    return jsonify({"connected": False, "error": "API returned error", "api_calls_made": analyzer.get_api_counter()})


@app.route('/api/scan-new-tokens', methods=['POST', 'GET'])
def scan_new_tokens():
    try:
        result = analyzer.scan_new_tokens(limit=15)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Scan endpoint crashed: {e}")
        return jsonify({
            "error": f"Server error: {str(e)}",
            "tokens": [],
            "total_api_calls": analyzer.get_api_counter(),
        })


@app.route('/api/analyze-token/<path:address>', methods=['GET'])
def analyze_single_token(address):
    try:
        if not address or len(address) < 32 or len(address) > 44:
            return jsonify({
                "error": "Invalid token address. Must be 32-44 characters.",
                "tokens": [],
            }), 400

        if not re.match(r'^[1-9A-HJ-NP-Za-km-z]+$', address):
            return jsonify({
                "error": "Invalid token address. Contains invalid characters.",
                "tokens": [],
            }), 400

        scan_start = analyzer.get_api_counter()
        result = analyzer.analyze_single_token(address)
        scan_end = analyzer.get_api_counter()

        return jsonify({
            "tokens": [result],
            "total_api_calls": analyzer.get_api_counter(),
            "calls_this_scan": scan_end - scan_start,
            "tokens_scanned": 1,
        })
    except Exception as e:
        logger.error(f"Single token analysis crashed: {e}")
        return jsonify({
            "error": f"Server error: {str(e)}",
            "tokens": [],
            "total_api_calls": analyzer.get_api_counter(),
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
