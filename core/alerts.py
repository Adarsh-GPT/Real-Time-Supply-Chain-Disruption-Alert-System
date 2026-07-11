"""core/alerts.py
Handles sending push notifications to Telegram.
Only sends alerts for HIGH risk items that match the user's watchlist.
"""
from __future__ import annotations

import logging
import requests

from config.settings import settings

log = logging.getLogger(__name__)


def send_telegram_message(token: str, chat_id: str, message: str) -> bool:
    """Send a plain or HTML message via Telegram Bot API."""
    if not token or not chat_id:
        return False
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        log.error("Telegram send failed: %s", e)
        return False


def format_alert_message(article: dict) -> str:
    """Format an article into a readable Telegram HTML message."""
    headline = article.get("raw_text", "Unknown Event")
    url = article.get("url", "")
    impact = article.get("impact", {}).get("description", "Unknown impact")
    wl_match = article.get("watchlist_match", {})
    matched_items = ", ".join([m["item"] for m in wl_match.get("matched", [])])
    
    msg = (
        f"🚨 <b>SUPPLY CHAIN ALERT</b>\n\n"
        f"<b>Event:</b> {headline}\n"
        f"<b>Watchlist Hit:</b> {matched_items}\n"
        f"<b>Estimated Impact:</b> {impact}\n\n"
    )
    if url:
        msg += f"<a href='{url}'>Read Source Article</a>"
        
    return msg


def dispatch_alerts(articles: list[dict], sent_history: set[str], token: str, chat_id: str) -> int:
    """
    Check articles and send Telegram alerts for new HIGH risk watchlist hits.
    Returns the number of alerts successfully sent.
    """
    if not token or not chat_id:
        return 0

    sent_count = 0
    for a in articles:
        # We only alert on HIGH risk events that actually hit the user's watchlist
        if a.get("risk_level") == "High" and a.get("watchlist_match", {}).get("is_watchlist_hit"):
            article_id = a.get("id")
            
            # Prevent spam: check if we already sent this
            if article_id and article_id not in sent_history:
                msg = format_alert_message(a)
                success = send_telegram_message(token, chat_id, msg)
                if success:
                    sent_history.add(article_id)
                    sent_count += 1
                    
    return sent_count
