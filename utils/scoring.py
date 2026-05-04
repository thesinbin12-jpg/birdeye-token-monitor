import time
from datetime import datetime


def calculate_security_score(security_data, price_data, age_hours=0):
    score = 0
    details = {}

    mint_val = security_data.get("mintAuthority", "")
    mint_revoked = not mint_val or str(mint_val).lower() in ("null", "", "none")
    if mint_revoked:
        score += 10
    else:
        score -= 40
    details["mint_revoked"] = mint_revoked

    freeze_val = security_data.get("freezeAuthority", "")
    freeze_revoked = not freeze_val or str(freeze_val).lower() in ("null", "", "none")
    if freeze_revoked:
        score += 10
    else:
        score -= 35
    details["freeze_revoked"] = freeze_revoked

    liquidity = float(price_data.get("liquidity", 0) or 0)
    details["liquidity"] = liquidity

    if liquidity >= 50000:
        score += 10
    elif liquidity >= 10000:
        score += 5
    elif liquidity < 1000:
        score -= 35
    elif liquidity < 5000:
        score -= 25
    else:
        score -= 15

    if age_hours < 1 and age_hours > 0:
        score -= 25
    elif age_hours < 24 and age_hours > 0:
        score -= 15

    score = max(0, min(40, score + 20))
    return score, details


def calculate_distribution_score(security_data):
    score = 0
    details = {}

    holder_data = security_data.get("holder", {}) or {}
    top_10_pct = float(holder_data.get("top10HolderPercent", 0) or 0)

    if top_10_pct < 20:
        score += 25
    elif top_10_pct < 40:
        score += 15
    elif top_10_pct < 60:
        score += 5
    else:
        score -= 25

    details["top_10_holders_pct"] = top_10_pct

    top_holder_pct = 0
    holders_list = holder_data.get("topHolders", []) or []
    if holders_list and len(holders_list) > 0:
        try:
            top_holder_pct = float(holders_list[0].get("pct", 0) or 0)
        except (ValueError, TypeError, IndexError):
            top_holder_pct = 0
    if top_holder_pct > 20:
        score -= 10
    details["top_holder_pct"] = top_holder_pct

    score = max(0, min(25, score + 5))
    return score, details


def calculate_liquidity_score(price_data):
    score = 0
    details = {}

    liquidity = float(price_data.get("liquidity", 0) or 0)

    if liquidity >= 100000:
        score = 20
    elif liquidity >= 50000:
        score = 15
    elif liquidity >= 10000:
        score = 10
    elif liquidity >= 5000:
        score = 5
    elif liquidity < 1000:
        score = -30
    else:
        score = -15

    details["liquidity"] = liquidity
    score = max(0, min(20, score))
    return score, details


def calculate_momentum_score(token_data, overview_data):
    score = 0
    details = {}

    price_change = float(overview_data.get("priceChange24h", 0) or 0)
    if -50 <= price_change <= 200:
        score += 10
    elif 200 < price_change <= 500:
        score += 5
    elif price_change > 500:
        score -= 15

    volume = float(overview_data.get("volume24h", 0) or 0)
    if volume > 10000:
        score += 5
    elif volume > 0:
        score += 2

    details["price_change_24h"] = price_change
    details["volume_24h"] = volume
    score = max(0, min(15, score + 3))
    return score, details


def apply_critical_multipliers(total_score, sec_details, liq_details, age_hours):
    if not sec_details.get("mint_revoked", True) and not sec_details.get("freeze_revoked", True):
        total_score = min(total_score, 25)

    liq = liq_details.get("liquidity", 0)
    if liq < 1000:
        total_score = min(total_score, 35)

    return total_score


def calculate_overall_score(token_data, security_data, price_data, overview_data, age_hours=0):
    sec_score, sec_details = calculate_security_score(security_data, price_data, age_hours)
    dist_score, dist_details = calculate_distribution_score(security_data)
    liq_score, liq_details = calculate_liquidity_score(price_data)
    mom_score, mom_details = calculate_momentum_score(token_data, overview_data)

    total = sec_score + dist_score + liq_score + mom_score

    total = apply_critical_multipliers(total, sec_details, liq_details, age_hours)

    total = max(0, min(100, total))

    if total >= 85:
        verdict = "STRONG BUY"
    elif total >= 70:
        verdict = "BUY"
    elif total >= 50:
        verdict = "HOLD"
    elif total >= 30:
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
        "top_holder_pct": dist_details.get("top_holder_pct", 0),
        "price_change_24h": mom_details.get("price_change_24h", 0),
        "volume_24h": mom_details.get("volume_24h", 0),
    }


def generate_warnings(analysis):
    warnings = []

    if not analysis.get("mint_authority_revoked", True):
        warnings.append({"level": "critical", "text": "Mint NOT revoked - Infinite mint risk"})
    if not analysis.get("freeze_authority_revoked", True):
        warnings.append({"level": "critical", "text": "Freeze NOT revoked - Dev can freeze transfers"})

    if not analysis.get("mint_authority_revoked", True) and not analysis.get("freeze_authority_revoked", True):
        warnings.append({"level": "critical", "text": "Mint + Freeze both active - Classic rug setup"})

    liq = analysis.get("liquidity", 0)
    if liq < 1000:
        warnings.append({"level": "critical", "text": f"Liquidity ${liq:.0f} - Exit nearly impossible"})
    elif liq < 5000:
        warnings.append({"level": "critical", "text": f"Liquidity ${liq:.0f} - Very low, hard to sell"})
    elif liq < 10000:
        warnings.append({"level": "warning", "text": f"Liquidity ${liq:.0f} - Low, limited exit"})

    top10 = analysis.get("top_10_holders_pct", 0)
    if top10 > 80:
        warnings.append({"level": "critical", "text": f"Top 10 holders {top10:.0f}% - Whale dump risk"})
    elif top10 > 60:
        warnings.append({"level": "critical", "text": f"Top 10 holders {top10:.0f}% - High concentration"})
    elif top10 > 40:
        warnings.append({"level": "warning", "text": f"Top 10 holders {top10:.0f}% - Moderate concentration"})

    price_change = analysis.get("price_change_24h", 0)
    if price_change > 500:
        warnings.append({"level": "critical", "text": f"Price +{price_change:.0f}% in 24h - Pump & dump risk"})
    elif price_change > 200:
        warnings.append({"level": "warning", "text": f"Price +{price_change:.0f}% in 24h - Volatile"})

    if analysis.get("mint_authority_revoked") and analysis.get("freeze_authority_revoked"):
        warnings.append({"level": "success", "text": "Mint & Freeze both revoked - Safe"})

    if liq >= 50000:
        warnings.append({"level": "success", "text": f"Strong liquidity ${liq/1000:.0f}K"})

    if top10 < 30:
        warnings.append({"level": "success", "text": f"Fair distribution - Top 10 < {top10:.0f}%"})

    if -50 <= price_change <= 200 and price_change != 0:
        warnings.append({"level": "success", "text": f"Stable price movement ({price_change:+.0f}%)"})

    return warnings


def get_recommendation(score, analysis=None):
    if score >= 85:
        text = "Excellent fundamentals across all categories."
    elif score >= 70:
        text = "Solid project. Monitor for dips."
    elif score >= 50:
        text = "Mixed signals. Small positions only."
    elif score >= 30:
        text = "High risk. Multiple red flags present."
    else:
        text = "Likely rug pull. Do not invest."

    if analysis:
        if not analysis.get("mint_authority_revoked", True):
            text = "Mint authority active. Dangerous."
        elif not analysis.get("freeze_authority_revoked", True):
            text = "Freeze authority active. Can lock your tokens."
        elif analysis.get("liquidity", 0) < 1000:
            text = "Near-zero liquidity. Cannot exit position."
        elif analysis.get("top_10_holders_pct", 0) > 70:
            text = "Whale-dominated. Dump risk extreme."

    if score >= 85:
        label = "STRONG BUY"
    elif score >= 70:
        label = "BUY"
    elif score >= 50:
        label = "HOLD"
    elif score >= 30:
        label = "AVOID"
    else:
        label = "STRONG AVOID"

    return {"label": label, "text": text}


def get_verdict_class(verdict):
    v = (verdict or "").upper()
    if v in ("STRONG BUY", "BUY"):
        return "safe"
    elif v in ("HOLD",):
        return "caution"
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
