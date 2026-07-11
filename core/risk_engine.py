"""core/risk_engine.py
Hybrid risk scorer + watchlist personalisation.
The core business logic: score articles, match against user watchlist,
output human-readable risk assessments.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from pathlib import Path

import yaml

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_thresholds() -> dict:
    path = Path(__file__).parent.parent / "config" / "thresholds.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Recency factor ────────────────────────────────────────────────────────────

def compute_recency(published_at: str) -> float:
    """
    Exponential decay based on article age.
    Fresh (< 1h) → ~1.0. After 24h → min_factor.
    """
    cfg = _load_thresholds().get("recency", {})
    decay_hours = cfg.get("decay_hours", 24)
    min_factor = cfg.get("min_factor", 0.5)

    try:
        if published_at.endswith("Z"):
            published_at = published_at[:-1] + "+00:00"
        pub = datetime.fromisoformat(published_at)
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - pub).total_seconds() / 3600
        factor = max(min_factor, 1.0 - (age_hours / decay_hours) * (1 - min_factor))
        return round(factor, 4)
    except Exception:
        return 0.8


# ── Watchlist matching ────────────────────────────────────────────────────────

def match_watchlist(text: str, watchlist: dict) -> dict:
    """
    Check if the article mentions any watchlist item.

    Args:
        text: Raw article text
        watchlist: dict with keys companies, ports, commodities, countries

    Returns:
        dict with matched items and boost score
    """
    text_lower = text.lower()
    matched: list[dict] = []

    for category, items in watchlist.items():
        for item in (items or []):
            if item.lower() in text_lower:
                matched.append({"item": item, "category": category})

    thresholds = _load_thresholds()
    max_boost = thresholds.get("weights", {}).get("watchlist_boost_max", 0.20)
    # Each match contributes; cap at max_boost
    boost = min(max_boost, len(matched) * 0.07)

    return {
        "matched": matched,
        "boost": round(boost, 4),
        "is_watchlist_hit": len(matched) > 0,
        "match_count": len(matched),
    }


# ── Hybrid scoring ────────────────────────────────────────────────────────────

def compute_hybrid_score(
    vader_score: float,
    ml_high_prob: float,
    watchlist_boost: float,
    recency_factor: float,
) -> float:
    cfg = _load_thresholds().get("weights", {})
    w_vader = cfg.get("vader", 0.35)
    w_ml = cfg.get("ml_classifier", 0.45)
    # Remaining weight goes to watchlist (already capped separately)
    base = (w_vader * vader_score + w_ml * ml_high_prob)
    score = (base + watchlist_boost) * recency_factor
    return round(min(1.0, max(0.0, score)), 4)


def classify_risk(hybrid_score: float) -> str:
    thresholds = _load_thresholds()
    if hybrid_score >= thresholds.get("high_risk_threshold", 0.60):
        return "High"
    elif hybrid_score >= thresholds.get("medium_risk_threshold", 0.30):
        return "Medium"
    return "Low"


# ── Impact description (human-readable) ───────────────────────────────────────

def format_impact_badge(impact: dict, risk_level: str) -> str:
    if risk_level == "Low":
        return "⚪ Minimal impact expected"
    days_min = impact.get("days_min", 3)
    days_max = impact.get("days_max", 10)
    if risk_level == "High":
        return f"🔴 Est. {days_min}–{days_max} day supply delay"
    return f"🟡 Est. {days_min}–{days_max} day supply delay"


# ── Full scoring pipeline ─────────────────────────────────────────────────────

def score_article(processed_article: dict, watchlist: dict) -> dict:
    """
    Score a fully processed article against a user watchlist.
    Returns enriched article dict with risk scoring fields.
    """
    from core.processor import estimate_impact

    vader = processed_article.get("vader_score", 0.5)
    ml = processed_article.get("ml_high_prob", 0.5)
    published_at = processed_article.get("published_at", datetime.now(timezone.utc).isoformat())

    recency = compute_recency(published_at)
    wl_result = match_watchlist(processed_article.get("raw_text", ""), watchlist)
    hybrid = compute_hybrid_score(vader, ml, wl_result["boost"], recency)
    risk_level = classify_risk(hybrid)
    impact = estimate_impact(processed_article.get("raw_text", ""), risk_level)

    return {
        **processed_article,
        "vader_score": vader,
        "ml_high_prob": ml,
        "recency_factor": recency,
        "watchlist_match": wl_result,
        "hybrid_score": hybrid,
        "risk_level": risk_level,
        "risk_color": {"High": "#FF4B4B", "Medium": "#FFD600", "Low": "#00C853"}.get(risk_level, "#78909C"),
        "risk_icon": {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(risk_level, "⚪"),
        "impact": impact,
        "impact_badge": format_impact_badge(impact, risk_level),
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }


def score_batch(processed_articles: list[dict], watchlist: dict) -> list[dict]:
    """Score a batch of articles. Returns sorted by hybrid_score descending."""
    scored = [score_article(a, watchlist) for a in processed_articles]
    scored.sort(key=lambda x: (
        {"High": 2, "Medium": 1, "Low": 0}.get(x.get("risk_level", "Low"), 0),
        x.get("hybrid_score", 0)
    ), reverse=True)
    return scored


# ── Dashboard summary stats ───────────────────────────────────────────────────

def compute_summary_stats(scored_articles: list[dict]) -> dict:
    high = sum(1 for a in scored_articles if a.get("risk_level") == "High")
    medium = sum(1 for a in scored_articles if a.get("risk_level") == "Medium")
    low = sum(1 for a in scored_articles if a.get("risk_level") == "Low")
    watchlist_hits = sum(1 for a in scored_articles if a.get("watchlist_match", {}).get("is_watchlist_hit"))
    avg_score = (
        sum(a.get("hybrid_score", 0) for a in scored_articles) / len(scored_articles)
        if scored_articles else 0.0
    )
    return {
        "total": len(scored_articles),
        "high": high,
        "medium": medium,
        "low": low,
        "watchlist_hits": watchlist_hits,
        "avg_score": round(avg_score, 3),
    }
