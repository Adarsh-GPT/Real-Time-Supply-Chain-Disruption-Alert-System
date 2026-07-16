import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

DEMO_DB_PATH = Path("data/demo_users.json")

def _init_db():
    DEMO_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DEMO_DB_PATH.exists():
        with open(DEMO_DB_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)

def save_demo_user(email: str, profile: dict, watchlist: dict) -> None:
    """Save a user's profile and watchlist to the local JSON database."""
    _init_db()
    try:
        with open(DEMO_DB_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
            
        db[email] = {
            "profile": profile,
            "watchlist": watchlist
        }
        
        with open(DEMO_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
    except Exception as e:
        log.error("Failed to save demo user: %s", e)

def get_demo_user(email: str) -> dict | None:
    """Retrieve a user's data from the local JSON database."""
    if not DEMO_DB_PATH.exists():
        return None
    try:
        with open(DEMO_DB_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
            return db.get(email)
    except Exception as e:
        log.error("Failed to get demo user: %s", e)
        return None
