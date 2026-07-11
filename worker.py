"""worker.py
Background daemon for SupplyRadar.
Fetches news, scores against user watchlists, saves to Firestore, and sends Telegram alerts.
Run this via cron or as a long-running process: python worker.py
"""
import time
import logging
from config.settings import settings
from core.ingestion import fetch_all_sources
from core.processor import process_batch
from core.risk_engine import score_batch
from core.firebase_db import get_all_users, save_articles
from core.alerts import dispatch_alerts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# In-memory set of sent alerts to prevent duplicate Telegram messages across worker loops
sent_history = set()

def job():
    log.info("Starting worker job...")
    if not settings.has_firebase:
        log.warning("Firebase not configured. Worker cannot save to DB. Exiting.")
        return

    # 1. Fetch live news
    log.info("Fetching raw news from APIs...")
    raw_articles = fetch_all_sources()
    log.info(f"Fetched {len(raw_articles)} articles.")

    # 2. Process NLP (Clean, VADER, ML, Categories, Impact)
    log.info("Running NLP pipeline...")
    processed_articles = process_batch(raw_articles)

    # 3. Fetch all user watchlists from DB
    users = get_all_users()
    log.info(f"Found {len(users)} registered users.")

    # We save the articles to the DB. We score them with an empty watchlist first 
    # to get the global baseline risk, then save.
    baseline_scored = score_batch(processed_articles, {})
    saved_count = save_articles(baseline_scored)
    log.info(f"Saved {saved_count} new articles to Firestore.")

    # 4. Check if we need to send Telegram alerts (based on individual user watchlists)
    if settings.telegram_bot_token and settings.telegram_chat_id:
        total_alerts = 0
        for u in users:
            wl = u.get("watchlist", {})
            # Re-score against this specific user's watchlist
            user_scored = score_batch(processed_articles, wl)
            # Dispatch alerts (will only send if it's HIGH risk AND a watchlist hit)
            sent = dispatch_alerts(
                user_scored, 
                sent_history, 
                settings.telegram_bot_token, 
                settings.telegram_chat_id
            )
            total_alerts += sent
        log.info(f"Dispatched {total_alerts} Telegram alerts.")

if __name__ == "__main__":
    log.info("Starting SupplyRadar Worker Daemon.")
    while True:
        try:
            job()
        except Exception as e:
            log.error(f"Job failed: {e}")
        
        sleep_sec = settings.fetch_interval_minutes * 60
        log.info(f"Sleeping for {settings.fetch_interval_minutes} minutes...")
        time.sleep(sleep_sec)
