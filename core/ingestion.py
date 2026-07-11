"""core/ingestion.py
Real-time news ingestion from NewsAPI, The Guardian, and GNews.
Returns a unified list of article dicts regardless of source.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings

log = logging.getLogger(__name__)

SUPPLY_CHAIN_QUERY = (
    "supply chain disruption OR port closure OR shipping delay OR "
    "factory shutdown OR semiconductor shortage OR trade sanctions OR "
    "logistics disruption OR freight rate OR commodity shortage"
)


def make_hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()[:16]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def _fetch_newsapi(query: str, days_back: int = 1) -> list[dict]:
    """Fetch from NewsAPI (100 req/day on free plan)."""
    if not settings.newsapi_key:
        return []
    from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "from": from_date,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": settings.max_articles_per_source,
        "apiKey": settings.newsapi_key,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    articles = resp.json().get("articles", [])
    results = []
    for a in articles:
        title = (a.get("title") or "").strip()
        if not title or title == "[Removed]":
            continue
        results.append({
            "id": make_hash(title),
            "source": "NewsAPI",
            "source_name": (a.get("source") or {}).get("name", "Unknown"),
            "raw_text": title,
            "description": (a.get("description") or "")[:300],
            "url": a.get("url", ""),
            "published_at": a.get("publishedAt", datetime.now(timezone.utc).isoformat()),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        })
    log.info("NewsAPI returned %d articles", len(results))
    return results


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def _fetch_guardian(query: str, days_back: int = 1) -> list[dict]:
    """Fetch from The Guardian API (free, no daily limit for modest use)."""
    if not settings.guardian_key:
        return []
    from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    url = "https://content.guardianapis.com/search"
    params = {
        "q": query,
        "from-date": from_date,
        "order-by": "newest",
        "page-size": settings.max_articles_per_source,
        "show-fields": "headline,trailText,shortUrl",
        "api-key": settings.guardian_key,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    items = resp.json().get("response", {}).get("results", [])
    results = []
    for item in items:
        fields = item.get("fields", {})
        title = (fields.get("headline") or item.get("webTitle") or "").strip()
        if not title:
            continue
        results.append({
            "id": make_hash(title),
            "source": "TheGuardian",
            "source_name": "The Guardian",
            "raw_text": title,
            "description": (fields.get("trailText") or "")[:300],
            "url": fields.get("shortUrl") or item.get("webUrl", ""),
            "published_at": item.get("webPublicationDate", datetime.now(timezone.utc).isoformat()),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        })
    log.info("Guardian returned %d articles", len(results))
    return results


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def _fetch_gnews(query: str) -> list[dict]:
    """Fetch from GNews (free tier: 100 req/day, 10 articles/req)."""
    if not settings.gnews_key:
        return []
    url = "https://gnews.io/api/v4/search"
    params = {
        "q": query,
        "lang": "en",
        "max": 10,
        "token": settings.gnews_key,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    articles = resp.json().get("articles", [])
    results = []
    for a in articles:
        title = (a.get("title") or "").strip()
        if not title:
            continue
        results.append({
            "id": make_hash(title),
            "source": "GNews",
            "source_name": (a.get("source") or {}).get("name", "GNews"),
            "raw_text": title,
            "description": (a.get("description") or "")[:300],
            "url": a.get("url", ""),
            "published_at": a.get("publishedAt", datetime.now(timezone.utc).isoformat()),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        })
    log.info("GNews returned %d articles", len(results))
    return results


def fetch_all_sources(query: str = SUPPLY_CHAIN_QUERY, days_back: int = 1) -> list[dict]:
    """
    Fetch from all configured sources, deduplicate by content hash.
    Returns unified list sorted by published_at descending.
    """
    all_articles: list[dict] = []

    try:
        all_articles.extend(_fetch_newsapi(query, days_back))
    except Exception as e:
        log.warning("NewsAPI fetch failed: %s", e)

    try:
        all_articles.extend(_fetch_guardian(query, days_back))
    except Exception as e:
        log.warning("Guardian fetch failed: %s", e)

    try:
        all_articles.extend(_fetch_gnews(query))
    except Exception as e:
        log.warning("GNews fetch failed: %s", e)

    # Deduplicate by id (content hash)
    seen: set[str] = set()
    unique: list[dict] = []
    for article in all_articles:
        if article["id"] not in seen:
            seen.add(article["id"])
            unique.append(article)

    # Sort by published_at descending
    unique.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    log.info("Total unique articles fetched: %d", len(unique))
    return unique
