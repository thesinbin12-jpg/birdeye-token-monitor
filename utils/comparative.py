import logging

logger = logging.getLogger(__name__)


def calculate_percentile(token_score, batch_scores):
    if not batch_scores:
        return 50

    sorted_scores = sorted(batch_scores)
    rank = 0
    for s in sorted_scores:
        if token_score >= s:
            rank += 1

    percentile = (rank / len(sorted_scores)) * 100
    return round(percentile, 1)


def get_percentile_label(percentile):
    if percentile >= 90:
        return "Top 10%"
    elif percentile >= 75:
        return "Top 25%"
    elif percentile >= 50:
        return "Above Average"
    elif percentile >= 25:
        return "Below Average"
    else:
        return "Bottom 25%"


def compute_batch_statistics(batch_tokens):
    if not batch_tokens:
        return {}

    scores = [t.get("score", 0) for t in batch_tokens]
    liquidities = [t.get("liquidity", 0) for t in batch_tokens]
    holders_pct = [t.get("top_10_holders_pct", 0) for t in batch_tokens]
    price_changes = [t.get("price_change_24h", 0) for t in batch_tokens]

    avg_score = sum(scores) / len(scores) if scores else 0
    avg_liq = sum(liquidities) / len(liquidities) if liquidities else 0
    avg_holders = sum(holders_pct) / len(holders_pct) if holders_pct else 0

    verdicts = {}
    for t in batch_tokens:
        v = t.get("verdict", "UNKNOWN")
        verdicts[v] = verdicts.get(v, 0) + 1

    safe_count = verdicts.get("STRONG BUY", 0) + verdicts.get("BUY", 0)
    risky_count = verdicts.get("AVOID", 0) + verdicts.get("STRONG AVOID", 0)

    mint_revoked_count = sum(1 for t in batch_tokens if t.get("mint_authority_revoked", False))
    freeze_revoked_count = sum(1 for t in batch_tokens if t.get("freeze_authority_revoked", False))

    return {
        "total_tokens": len(batch_tokens),
        "avg_score": round(avg_score, 1),
        "avg_liquidity": round(avg_liq, 0),
        "avg_top10_holders": round(avg_holders, 1),
        "verdicts": verdicts,
        "safe_count": safe_count,
        "risky_count": risky_count,
        "mint_revoked_pct": round(mint_revoked_count / len(batch_tokens) * 100, 0) if batch_tokens else 0,
        "freeze_revoked_pct": round(freeze_revoked_count / len(batch_tokens) * 100, 0) if batch_tokens else 0,
        "score_range": {
            "min": min(scores) if scores else 0,
            "max": max(scores) if scores else 0,
        },
    }


def generate_comparative(token_data, batch_tokens):
    batch_scores = [t.get("score", 0) for t in batch_tokens]
    percentile = calculate_percentile(token_data.get("score", 0), batch_scores)

    token_liq = token_data.get("liquidity", 0)
    batch_liqs = [t.get("liquidity", 0) for t in batch_tokens]
    liq_percentile = calculate_percentile(token_liq, batch_liqs)

    token_top10 = token_data.get("top_10_holders_pct", 0)
    batch_top10s = [t.get("top_10_holders_pct", 0) for t in batch_tokens]
    inv_top10s = [100 - t for t in batch_top10s]
    inv_token_top10 = 100 - token_top10
    holder_rank = calculate_percentile(inv_token_top10, inv_top10s)

    stats = compute_batch_statistics(batch_tokens)

    comparisons = []

    avg_score = stats.get("avg_score", 50)
    token_score = token_data.get("score", 0)
    diff = token_score - avg_score
    if diff > 10:
        comparisons.append(f"Score {diff:+.0f} above batch average — stronger fundamentals")
    elif diff < -10:
        comparisons.append(f"Score {diff:+.0f} below batch average — weaker than peers")
    else:
        comparisons.append("Score near batch average — typical for this batch")

    avg_liq = stats.get("avg_liquidity", 0)
    if token_liq > avg_liq * 2 and avg_liq > 0:
        comparisons.append("Liquidity significantly above batch average — easier to exit")
    elif token_liq < avg_liq * 0.5 and avg_liq > 0:
        comparisons.append("Liquidity well below batch average — harder to sell")

    mint_rev = token_data.get("mint_authority_revoked", False)
    mint_pct = stats.get("mint_revoked_pct", 0)
    if mint_rev and mint_pct < 50:
        comparisons.append("Mint revoked — safer than most tokens in this batch")
    elif not mint_rev and mint_pct > 50:
        comparisons.append("Mint still active — most other tokens have revoked it")

    return {
        "percentile": percentile,
        "percentile_label": get_percentile_label(percentile),
        "liquidity_percentile": liq_percentile,
        "holder_rank": holder_rank,
        "comparisons": comparisons,
        "batch_stats": stats,
    }
