import logging

logger = logging.getLogger(__name__)

RUG_PULL_SIGNALS = [
    ("mint_active", "mint_authority_revoked", False, 30, "Mint authority still active — dev can inflate supply"),
    ("freeze_active", "freeze_authority_revoked", False, 30, "Freeze authority active — dev can lock all transfers"),
    ("low_liquidity", "liquidity", lambda v: v < 1000, 25, "Liquidity under $1K — likely rug or dead token"),
    ("whale_concentrated", "top_10_holders_pct", lambda v: v > 70, 20, "Top 10 holders >70% — coordinated dump risk"),
]

HONEYPOT_SIGNALS = [
    ("no_liquidity", "liquidity", lambda v: v < 500, 40, "Near-zero liquidity — cannot sell"),
    ("freeze_active", "freeze_authority_revoked", False, 35, "Freeze authority — dev can block selling"),
    ("single_whale", "top_holder_pct", lambda v: v > 30, 25, "Single holder >30% — likely honeypot creator"),
]

PUMP_DUMP_SIGNALS = [
    ("price_spike", "price_change_24h", lambda v: v > 500, 35, "500%+ price surge — classic pump signal"),
    ("moderate_spike", "price_change_24h", lambda v: v > 200, 20, "200%+ surge — pump-and-drop pattern"),
    ("whale_setup", "top_10_holders_pct", lambda v: v > 60, 20, "Whale concentration + price spike = dump setup"),
    ("low_liq_spike", "liquidity", lambda v: v < 5000, 15, "Low liquidity + spike = easy manipulation"),
]


def _check_signals(token_data, signals):
    detected = []
    total_weight = 0

    for signal_id, field, condition, weight, description in signals:
        value = token_data.get(field)
        if value is None:
            continue

        triggered = False
        if callable(condition):
            try:
                triggered = condition(value)
            except (TypeError, ValueError):
                triggered = False
        else:
            triggered = (value == condition)

        if triggered:
            detected.append({
                "signal": signal_id,
                "weight": weight,
                "description": description,
                "field": field,
                "value": value,
            })
            total_weight += weight

    return detected, total_weight


def detect_rug_pull(token_data):
    signals, weight = _check_signals(token_data, RUG_PULL_SIGNALS)

    if weight >= 50:
        risk = "HIGH"
    elif weight >= 25:
        risk = "MODERATE"
    elif weight > 0:
        risk = "LOW"
    else:
        risk = "NONE"

    return {
        "pattern": "rug_pull",
        "risk": risk,
        "confidence": min(weight, 100),
        "signals": signals,
        "description": "Potential rug pull: dev retains control to drain liquidity or inflate supply" if risk != "NONE" else "No rug pull indicators detected",
    }


def detect_honeypot(token_data):
    signals, weight = _check_signals(token_data, HONEYPOT_SIGNALS)

    if weight >= 50:
        risk = "HIGH"
    elif weight >= 25:
        risk = "MODERATE"
    elif weight > 0:
        risk = "LOW"
    else:
        risk = "NONE"

    return {
        "pattern": "honeypot",
        "risk": risk,
        "confidence": min(weight, 100),
        "signals": signals,
        "description": "Likely honeypot: you can buy but probably cannot sell" if risk != "NONE" else "No honeypot indicators detected",
    }


def detect_pump_dump(token_data):
    signals, weight = _check_signals(token_data, PUMP_DUMP_SIGNALS)

    price_change = float(token_data.get("price_change_24h", 0) or 0)
    top10 = float(token_data.get("top_10_holders_pct", 0) or 0)
    if price_change > 200 and top10 > 50:
        extra = {
            "signal": "spike_whale_combo",
            "weight": 25,
            "description": "Price spike + whale concentration — pump-and-dump in progress",
            "field": "combo",
            "value": f"price={price_change:.0f}%, top10={top10:.0f}%",
        }
        signals.append(extra)
        weight += 25

    if weight >= 50:
        risk = "HIGH"
    elif weight >= 25:
        risk = "MODERATE"
    elif weight > 0:
        risk = "LOW"
    else:
        risk = "NONE"

    return {
        "pattern": "pump_dump",
        "risk": risk,
        "confidence": min(weight, 100),
        "signals": signals,
        "description": "Pump-and-dump pattern: artificial price inflation before whale exit" if risk != "NONE" else "No pump-and-dump indicators detected",
    }


def run_all_patterns(token_data):
    rug = detect_rug_pull(token_data)
    honeypot = detect_honeypot(token_data)
    pump = detect_pump_dump(token_data)

    all_signals = []
    for pattern in [rug, honeypot, pump]:
        all_signals.extend(pattern.get("signals", []))

    high_risk_count = sum(1 for p in [rug, honeypot, pump] if p["risk"] == "HIGH")
    moderate_risk_count = sum(1 for p in [rug, honeypot, pump] if p["risk"] == "MODERATE")

    if high_risk_count >= 2:
        overall = "DANGEROUS"
        summary = "Multiple high-risk patterns detected — extremely likely scam"
    elif high_risk_count >= 1:
        overall = "HIGH_RISK"
        summary = "At least one high-risk pattern — proceed with extreme caution"
    elif moderate_risk_count >= 2:
        overall = "SUSPICIOUS"
        summary = "Multiple moderate-risk signals — careful investigation needed"
    elif moderate_risk_count >= 1:
        overall = "CAUTION"
        summary = "Some risk signals present — monitor closely"
    elif all_signals:
        overall = "LOW_RISK"
        summary = "Minor signals only — relatively safe but stay alert"
    else:
        overall = "SAFE"
        summary = "No concerning patterns detected"

    return {
        "rug_pull": rug,
        "honeypot": honeypot,
        "pump_dump": pump,
        "overall_risk": overall,
        "overall_summary": summary,
        "total_signals": len(all_signals),
        "high_risk_patterns": high_risk_count,
    }
