import math
import logging

logger = logging.getLogger(__name__)


def simulate_investment(token_data, investment_usd=100):
    price = float(token_data.get("price", 0) or 0)
    liquidity = float(token_data.get("liquidity", 0) or 0)
    fdv = float(token_data.get("fdv", 0) or 0)
    score = int(token_data.get("score", 0))
    price_change = float(token_data.get("price_change_24h", 0) or 0)
    top10 = float(token_data.get("top_10_holders_pct", 0) or 0)
    mint_rev = token_data.get("mint_authority_revoked", True)
    freeze_rev = token_data.get("freeze_authority_revoked", True)

    if price <= 0:
        return {
            "investment_usd": investment_usd,
            "tokens_received": 0,
            "estimated_value_24h": 0,
            "estimated_roi_24h": 0,
            "exit_possible": False,
            "exit_impact_pct": 0,
            "risk_level": "EXTREME",
            "scenario": "Cannot calculate — no price data",
            "break_even_price": 0,
        }

    tokens_received = investment_usd / price

    exit_possible = liquidity >= investment_usd * 2
    exit_impact_pct = (investment_usd / liquidity * 100) if liquidity > 0 else 100

    if not mint_rev or not freeze_rev:
        prob_loss = 0.85
        prob_gain = 0.05
    elif liquidity < 1000:
        prob_loss = 0.8
        prob_gain = 0.05
    elif top10 > 70:
        prob_loss = 0.7
        prob_gain = 0.1
    elif score >= 70:
        prob_loss = 0.2
        prob_gain = 0.5
    elif score >= 50:
        prob_loss = 0.35
        prob_gain = 0.3
    else:
        prob_loss = 0.55
        prob_gain = 0.15

    if price_change > 500:
        prob_loss = min(prob_loss + 0.2, 0.95)
        prob_gain = max(prob_gain - 0.15, 0.01)
    elif price_change > 200:
        prob_loss = min(prob_loss + 0.1, 0.9)
        prob_gain = max(prob_gain - 0.1, 0.02)

    if score >= 70:
        expected_move = 0.05 + (score - 70) * 0.005
    elif score >= 50:
        expected_move = -0.05
    elif score >= 30:
        expected_move = -0.2
    else:
        expected_move = -0.5

    estimated_price_24h = price * (1 + expected_move)
    estimated_value_24h = tokens_received * estimated_price_24h
    estimated_roi_24h = ((estimated_value_24h / investment_usd) - 1) * 100

    best_case_roi = estimated_roi_24h + abs(estimated_roi_24h) * 0.5 + 10
    worst_case_roi = -95 if not mint_rev or not freeze_rev else max(estimated_roi_24h - 30, -90)

    if score >= 70:
        risk_level = "LOW"
    elif score >= 50:
        risk_level = "MODERATE"
    elif score >= 30:
        risk_level = "HIGH"
    else:
        risk_level = "EXTREME"

    if not mint_rev and not freeze_rev:
        scenario = "Rug pull likely — dev can mint + freeze. Expect total loss."
    elif not mint_rev:
        scenario = "Mint authority active — supply dilution probable."
    elif not freeze_rev:
        scenario = "Freeze authority active — tokens can be locked anytime."
    elif liquidity < 1000:
        scenario = "Cannot exit — no liquidity to sell into."
    elif top10 > 70:
        scenario = "Whale dump probable — top holders can crash price."
    elif estimated_roi_24h > 10:
        scenario = "Positive outlook based on current metrics."
    elif estimated_roi_24h > 0:
        scenario = "Slight positive drift expected, but uncertain."
    elif estimated_roi_24h > -20:
        scenario = "Minor decline expected. Consider small position only."
    else:
        scenario = "Significant decline expected. High risk of loss."

    break_even_price = price

    return {
        "investment_usd": investment_usd,
        "tokens_received": round(tokens_received, 2),
        "estimated_value_24h": round(estimated_value_24h, 2),
        "estimated_roi_24h": round(estimated_roi_24h, 1),
        "best_case_roi": round(best_case_roi, 1),
        "worst_case_roi": round(worst_case_roi, 1),
        "exit_possible": exit_possible,
        "exit_impact_pct": round(exit_impact_pct, 1),
        "risk_level": risk_level,
        "scenario": scenario,
        "break_even_price": break_even_price,
        "prob_loss": round(prob_loss * 100, 0),
        "prob_gain": round(prob_gain * 100, 0),
    }
