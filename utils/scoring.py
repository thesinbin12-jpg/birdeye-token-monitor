import time
from datetime import datetime


def calculate_security_score(security_data, price_data):
    score = 0
    details = {}

    mint_val = security_data.get("mintAuthority", "")
    if mint_val and str(mint_val).lower() not in ("null", "", "none"):
        score -= 40
        details["mint_revoked"] = False
    else:
        score += 15
        details["mint_revoked"] = True

    freeze_val = security_data.get("freezeAuthority", "")
    if freeze_val and str(freeze_val).lower() not in ("null", "", "none"):
        score -= 35
        details["freeze_revoked"] = False
    else:
        score += 15
        details["freeze_revoked"] = True

    liquidity = float(price_data.get("liquidity", 0) or 0)
    if liquidity >= 50000:
        score += 10
    elif liquidity >= 10000:
        score += 5
    elif liquidity < 1000:
        score -= 30
    else:
        score -= 15
    details["liquidity"] = liquidity

    score = max(0, min(40, score + 20))
    return score, details


def calculate_distribution_score(security_data):
    score = 0
    details = {}

    holder_data = security_data.get("holder", {}) or {}
    top_10_pct = float(holder_data.get("top10HolderPercent", 0) or 0)

    if top_10_pct < 30:
        score += 25
    elif top_10_pct < 50:
        score += 15
    elif top_10_pct < 70:
        score -= 10
    else:
        score -= 25

    details["top_10_holders_pct"] = top_10_pct
    score = max(0, min(25, score + 5))
    return score, details


def calculate_liquidity_score(price_data):
    score = 0
    details = {}

    liquidity = float(price_data.get("liquidity", 0) or 0)

    if liquidity >= 50000:
        score = 20
    elif liquidity >= 10000:
        score = 15
    elif liquidity >= 5000:
        score = 10
    elif liquidity < 1000:
        score = -20
    else:
        score = 0

    details["liquidity"] = liquidity
    score = max(0, min(20, score))
    return score, details


def calculate_momentum_score(token_data, overview_data):
    score = 0
    details = {}

    price_change = float(overview_data.get("priceChange24h", 0) or 0)
    if -50 <= price_change <= 200:
        score += 10
    elif price_change > 500:
        score -= 15
    else:
        score += 0

    volume = float(overview_data.get("volume24h", 0) or 0)
    if volume > 10000:
        score += 5

    details["price_change_24h"] = price_change
    details["volume_24h"] = volume
    score = max(0, min(15, score + 5))
    return score, details


def calculate_overall_score(token_data, security_data, price_data, overview_data):
    sec_score, sec_details = calculate_security_score(security_data, price_data)
    dist_score, dist_details = calculate_distribution_score(security_data)
    liq_score, liq_details = calculate_liquidity_score(price_data)
    mom_score, mom_details = calculate_momentum_score(token_data, overview_data)

    total = sec_score + dist_score + liq_score + mom_score
    total = max(0, min(100, total))

    if total >= 85:
        verdict = "STRONG BUY"
    elif total >= 70:
        verdict = "BUY"
    elif total >= 55:
        verdict = "HOLD"
    elif total >= 40:
        verdict = "CAUTION"
    elif total >= 20:
        verdict = "AVOID"
    else:
        verdict = "STRONG AVOID"

    return {
        "overall_score": total,
        "verdict": verdict,
        "security_score": sec_score,
        "distribution_score": dist_score,
        "liquidity_score": liq_score,
        "momentum_score": mom_score,
        "mint_authority_revoked": sec_details.get("mint_revoked", False),
        "freeze_authority_revoked": sec_details.get("freeze_revoked", False),
        "liquidity": liq_details.get("liquidity", sec_details.get("liquidity", 0)),
        "top_10_holders_pct": dist_details.get("top_10_holders_pct", 0),
        "price_change_24h": mom_details.get("price_change_24h", 0),
        "volume_24h": mom_details.get("volume_24h", 0),
    }


def generate_warnings(analysis):
    warnings = []

    if not analysis.get("mint_authority_revoked", True):
        warnings.append({"level": "critical", "text": "Mint NOT revoked - Infinite mint risk"})

    if not analysis.get("freeze_authority_revoked", True):
        warnings.append({"level": "critical", "text": "Freeze NOT revoked - Dev can freeze transfers"})

    liq = analysis.get("liquidity", 0)
    if liq < 1000:
        warnings.append({"level": "critical", "text": f"Liquidity ${liq:.0f} - Extremely low, hard to sell"})
    elif liq < 5000:
        warnings.append({"level": "warning", "text": f"Liquidity ${liq:.0f} - Low, limited exit"})

    top10 = analysis.get("top_10_holders_pct", 0)
    if top10 > 70:
        warnings.append({"level": "critical", "text": f"Top 10 holders {top10:.0f}% - Can dump anytime"})
    elif top10 > 50:
        warnings.append({"level": "warning", "text": f"Top 10 holders {top10:.0f}% - Whale concentration risk"})

    if analysis.get("mint_authority_revoked") and analysis.get("freeze_authority_revoked"):
        warnings.append({"level": "success", "text": "Mint & Freeze both revoked"})

    if liq >= 50000:
        warnings.append({"level": "success", "text": f"Strong liquidity ${liq/1000:.0f}K"})

    if top10 < 30:
        warnings.append({"level": "success", "text": f"Fair distribution - Top 10 < {top10:.0f}%"})

    return warnings


def get_recommendation(score):
    if score >= 85:
        return {"label": "STRONG BUY", "text": "Excellent fundamentals. Low risk."}
    elif score >= 70:
        return {"label": "BUY", "text": "Solid project. Monitor for dips."}
    elif score >= 55:
        return {"label": "HOLD", "text": "Mixed signals. Wait for clarity."}
    elif score >= 40:
        return {"label": "CAUTION", "text": "Elevated risk. Small positions only."}
    elif score >= 20:
        return {"label": "AVOID", "text": "High risk. Multiple red flags."}
    else:
        return {"label": "STRONG AVOID", "text": "Likely rug pull. Do not invest."}


def get_verdict_class(verdict):
    v = (verdict or "").upper()
    if v in ("STRONG BUY", "BUY"):
        return "safe"
    elif v in ("HOLD", "CAUTION"):
        return "caution"
    elif v in ("AVOID", "STRONG AVOID"):
        return "risky"
    return "risky"


def format_contract_age(token_data, security_data):
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
                try:
                    dt = datetime.fromisoformat(creation_ts.replace('Z', '+00:00'))
                    creation_ts = dt.timestamp() * 1000
                except Exception:
                    creation_ts = 0
            if creation_ts > 0:
                age_hours = (time.time() * 1000 - creation_ts) / 3600000
    except Exception:
        age_hours = 0

    if age_hours < 24:
        return age_hours, True
    return age_hours, False


def format_price(price):
    if not price or price <= 0:
        return "N/A"
    if price < 0.001:
        return f"${price:.8f}"
    elif price < 1:
        return f"${price:.6f}"
    else:
        return f"${price:.4f}"


def format_liquidity(liquidity):
    if not liquidity or liquidity <= 0:
        return "$0"
    if liquidity >= 1000000:
        return f"${liquidity/1000000:.2f}M"
    elif liquidity >= 1000:
        return f"${liquidity/1000:.2f}K"
    return f"${liquidity:.2f}"


def format_fdv(fdv):
    if not fdv or fdv <= 0:
        return "N/A"
    if fdv >= 1e9:
        return f"${fdv/1e9:.2f}B"
    elif fdv >= 1e6:
        return f"${fdv/1e6:.2f}M"
    elif fdv >= 1e3:
        return f"${fdv/1e3:.2f}K"
    return f"${fdv:.2f}"
