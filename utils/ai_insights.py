import os
import re
import logging
import time

logger = logging.getLogger(__name__)

_insight_cache = {}
_INSIGHT_CACHE_TTL = 600

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.info("groq package not installed. AI insights disabled.")

MODEL_CHAIN = ["qwen/qwen3-32b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]


def strip_think_tags(text):
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'\[think\].*?\[/think\]', '', text, flags=re.DOTALL)
    text = re.sub(r'\[ reasoning.*?\]', '', text, flags=re.DOTALL)
    text = re.sub(r' dom.*?(?=\.)', '', text, flags=re.DOTALL)
    return text.strip()


def generate_ai_summary(token_data, score_data=None):
    if not GROQ_AVAILABLE:
        return _generate_rule_summary(token_data, score_data)

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return _generate_rule_summary(token_data, score_data)

    address = token_data.get("address", "")
    if address in _insight_cache:
        entry = _insight_cache[address]
        if time.time() - entry["ts"] < _INSIGHT_CACHE_TTL:
            return entry["data"]

    client = Groq(api_key=api_key)

    symbol = token_data.get("symbol", "???")
    name = token_data.get("name", "Unknown")
    score = token_data.get("score", 0)
    verdict = token_data.get("verdict", "UNKNOWN")
    liq = token_data.get("liquidity", 0)
    mint_rev = token_data.get("mint_authority_revoked", False)
    freeze_rev = token_data.get("freeze_authority_revoked", False)
    top10 = token_data.get("top_10_holders_pct", 0)
    price_chg = token_data.get("price_change_24h", 0)

    prompt = (
        f"Analyze Solana token '{name}' ({symbol}) in 1 sentence max. "
        f"Score: {score}/100 ({verdict}). "
        f"Liquidity: ${liq:,.0f}. "
        f"Mint revoked: {mint_rev}. Freeze revoked: {freeze_rev}. "
        f"Top 10 holders: {top10:.1f}%. "
        f"24h price change: {price_chg:+.1f}%. "
        f"Start with the main risk. End with recommendation. NO emojis."
    )

    last_err = None
    for model in MODEL_CHAIN:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a concise crypto risk analyst. Give 1-2 sentence risk assessments. Never give financial advice. Do NOT use think tags."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=60,
                temperature=0.3,
            )

            insight = response.choices[0].message.content.strip()
            insight = strip_think_tags(insight)
            insight = re.sub(r'\*+', '', insight)
            if not insight or len(insight) < 10:
                logger.warning(f"Model {model} returned empty/short insight after stripping think tags, trying next")
                continue
            result = {"insight": insight, "source": "groq", "model": model, "available": True}

            _insight_cache[address] = {"data": result, "ts": time.time()}
            return result

        except Exception as e:
            last_err = e
            logger.warning(f"Groq model {model} failed: {e}. Trying next fallback...")

    logger.error(f"All Groq models failed. Last error: {last_err}")
    return {"insight": "AI insights temporarily unavailable", "source": "unavailable", "available": False}


def _generate_rule_summary(token_data, score_data=None):
    score = token_data.get("score", 0)
    verdict = token_data.get("verdict", "UNKNOWN")
    mint_rev = token_data.get("mint_authority_revoked", False)
    freeze_rev = token_data.get("freeze_authority_revoked", False)
    liq = token_data.get("liquidity", 0)
    top10 = token_data.get("top_10_holders_pct", 0)
    price_chg = token_data.get("price_change_24h", 0)
    symbol = token_data.get("symbol", "???")

    parts = []

    if not mint_rev and not freeze_rev:
        parts.append(f"{symbol} has both mint and freeze authority active — classic rug pull setup.")
    elif not mint_rev:
        parts.append(f"{symbol} has active mint authority — supply can be inflated at any time.")
    elif not freeze_rev:
        parts.append(f"{symbol} has active freeze authority — dev can lock token transfers.")

    if liq < 1000:
        parts.append("Near-zero liquidity makes exiting nearly impossible.")
    elif liq < 5000:
        parts.append("Very low liquidity limits sell options.")

    if top10 > 70:
        parts.append(f"Top 10 holders control {top10:.0f}% — extreme whale dump risk.")
    elif top10 > 50:
        parts.append(f"Top 10 holders at {top10:.0f}% — concentrated holdings.")

    if price_chg > 500:
        parts.append(f"Price surged {price_chg:.0f}% in 24h — typical pump-and-drop pattern.")
    elif price_chg > 200:
        parts.append(f"Large {price_chg:.0f}% price jump — high volatility expected.")

    if not parts:
        if score >= 70:
            parts.append(f"{symbol} shows solid fundamentals with revoked authorities and reasonable distribution.")
        elif score >= 50:
            parts.append(f"{symbol} has mixed signals — proceed with caution and small positions only.")
        else:
            parts.append(f"{symbol} shows multiple red flags — high probability of loss.")

    insight = " ".join(parts[:2])

    return {"insight": insight, "source": "rules", "available": True}
