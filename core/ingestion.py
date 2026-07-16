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


import xml.etree.ElementTree as ET
import urllib.parse

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def _fetch_google_news_rss(query: str, days_back: int = 1) -> list[dict]:
    """Fetch from Google News RSS (Free, no API key required)."""
    # Google News RSS format: https://news.google.com/rss/search?q={query}+when:{days_back}d
    encoded_query = urllib.parse.quote(f"{query} when:{days_back}d")
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        log.error("Failed to parse Google News RSS XML: %s", e)
        return []

    results = []
    # Items are inside the <channel> tag
    for item in root.findall('./channel/item'):
        title = (item.findtext('title') or "").strip()
        if not title:
            continue
            
        link = item.findtext('link') or ""
        pub_date_str = item.findtext('pubDate') or ""
        
        # Parse pubDate (e.g., "Wed, 16 Jul 2026 10:00:00 GMT")
        try:
            pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            pub_date = datetime.now(timezone.utc).isoformat()
            
        results.append({
            "id": make_hash(title),
            "source": "GoogleNewsRSS",
            "source_name": item.findtext('source') or "Google News",
            "raw_text": title,
            "description": "", # RSS descriptions are usually just HTML snippets of the title
            "url": link,
            "published_at": pub_date,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        })
        
        if len(results) >= settings.max_articles_per_source:
            break
            
    log.info("Google News RSS returned %d articles", len(results))
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
        all_articles.extend(_fetch_google_news_rss(query, days_back))
    except Exception as e:
        log.warning("Google News RSS fetch failed: %s", e)

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
