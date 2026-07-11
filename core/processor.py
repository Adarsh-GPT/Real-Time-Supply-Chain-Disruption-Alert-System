"""core/processor.py
NLP pipeline: clean → sentiment → classify → categorize → impact estimate.
Uses existing model/logistic_model.pkl to avoid retraining.
"""
from __future__ import annotations

import re
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

import nltk
import yaml

from config.settings import settings

log = logging.getLogger(__name__)

# ── NLTK bootstrap (idempotent) ───────────────────────────────────────────────
for _r in ["stopwords", "punkt", "punkt_tab", "wordnet", "vader_lexicon"]:
    nltk.download(_r, quiet=True)

from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_STOPWORDS = set(stopwords.words("english"))
_LEMMATIZER = WordNetLemmatizer()
_VADER = SentimentIntensityAnalyzer()
_URL_RE = re.compile(r"http\S+|www\.\S+", re.IGNORECASE)
_PUNCT_RE = re.compile(r"[^a-zA-Z\s]")
_SPACE_RE = re.compile(r"\s+")

# ── Load thresholds for categories ───────────────────────────────────────────
@lru_cache(maxsize=1)
def _load_thresholds() -> dict:
    path = Path(__file__).parent.parent / "config" / "thresholds.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Load ML model (lazy, cached) ─────────────────────────────────────────────
_model = None
_vectorizer = None

def _load_model():
    global _model, _vectorizer
    if _model is not None:
        return _model, _vectorizer
    try:
        import joblib
        model_dir = settings.model_path
        _model = joblib.load(model_dir / "logistic_model.pkl")
        _vectorizer = joblib.load(model_dir / "tfidf_vectorizer.pkl")
        log.info("Loaded ML model from %s", model_dir)
    except Exception as e:
        log.warning("Could not load ML model (%s). Falling back to VADER-only scoring.", e)
        _model = None
        _vectorizer = None
    return _model, _vectorizer


# ── Text cleaning ─────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    text = str(text)
    text = _URL_RE.sub(" ", text)
    text = _PUNCT_RE.sub(" ", text)
    text = text.lower()
    text = _SPACE_RE.sub(" ", text).strip()
    return text


def preprocess_text(text: str) -> str:
    cleaned = clean_text(text)
    tokens = word_tokenize(cleaned)
    tokens = [
        _LEMMATIZER.lemmatize(t)
        for t in tokens
        if t.isalpha() and t not in _STOPWORDS and len(t) > 2
    ]
    return " ".join(tokens)


# ── Sentiment scoring ─────────────────────────────────────────────────────────

def get_vader_score(text: str) -> tuple[float, str]:
    """
    Returns (normalised_score [0,1], label).
    VADER compound is [-1, 1]; we map to [0, 1] for 'negativity' (risk proxy).
    """
    compound = _VADER.polarity_scores(text)["compound"]
    # Negative compound → higher risk
    normalised = max(0.0, min(1.0, (-compound + 1) / 2))
    if compound <= -0.05:
        label = "negative"
    elif compound >= 0.05:
        label = "positive"
    else:
        label = "neutral"
    return normalised, label


# ── ML Classification ─────────────────────────────────────────────────────────

def get_ml_risk_prob(processed_text: str) -> float:
    """Returns probability of 'High' risk class. Falls back to 0.5 if no model."""
    model, vectorizer = _load_model()
    if model is None or not processed_text.strip():
        return 0.5
    try:
        vec = vectorizer.transform([processed_text])
        classes = list(model.classes_)
        proba = model.predict_proba(vec)[0]
        high_idx = classes.index("High") if "High" in classes else 0
        return float(proba[high_idx])
    except Exception as e:
        log.debug("ML prediction failed: %s", e)
        return 0.5


# ── Disruption category detection ─────────────────────────────────────────────

def detect_category(text: str) -> dict:
    """
    Returns the best-matching disruption category.
    Falls back to 'general' if nothing matches.
    """
    thresholds = _load_thresholds()
    categories = thresholds.get("categories", {})
    text_lower = text.lower()

    best_cat = "general"
    best_count = 0
    for cat_id, cat_data in categories.items():
        count = sum(1 for kw in cat_data.get("keywords", []) if kw in text_lower)
        if count > best_count:
            best_count = count
            best_cat = cat_id

    if best_cat == "general":
        return {"id": "general", "icon": "📰", "color": "#78909C", "label": "General"}

    cat = categories[best_cat]
    return {
        "id": best_cat,
        "icon": cat.get("icon", "📰"),
        "color": cat.get("color", "#78909C"),
        "label": best_cat.replace("_", " ").title(),
    }


# ── Impact estimation ─────────────────────────────────────────────────────────

def estimate_impact(text: str, risk_level: str) -> dict:
    """
    Rule-based lead time impact estimator.
    Returns a dict with days_min, days_max, description.
    """
    if risk_level == "Low":
        return {"days_min": 0, "days_max": 2, "description": "Minimal expected disruption"}

    thresholds = _load_thresholds()
    impact_rules = thresholds.get("impact_rules", {})
    text_lower = text.lower()

    for rule_id, rule in impact_rules.items():
        if any(kw in text_lower for kw in rule.get("keywords", [])):
            days_min = rule["days_min"]
            days_max = rule["days_max"]
            if risk_level == "Medium":
                days_min = max(1, days_min // 2)
                days_max = max(2, days_max // 2)
            return {
                "days_min": days_min,
                "days_max": days_max,
                "description": f"Estimated {days_min}–{days_max} day supply delay",
                "rule_matched": rule_id,
            }

    default = thresholds.get("default_impact", {"days_min": 3, "days_max": 10})
    return {
        "days_min": default["days_min"],
        "days_max": default["days_max"],
        "description": f"Estimated {default['days_min']}–{default['days_max']} day delay",
        "rule_matched": None,
    }


# ── Full pipeline ─────────────────────────────────────────────────────────────

def process_article(article: dict) -> dict:
    """
    Run the full NLP pipeline on a raw article dict.
    Adds: cleaned_text, processed_text, vader_score, sentiment_label,
          ml_high_prob, category.
    """
    raw = article.get("raw_text", "")
    cleaned = clean_text(raw)
    processed = preprocess_text(raw)
    vader_score, sentiment_label = get_vader_score(raw)
    ml_prob = get_ml_risk_prob(processed)
    category = detect_category(raw)

    return {
        **article,
        "cleaned_text": cleaned,
        "processed_text": processed,
        "vader_score": round(vader_score, 4),
        "sentiment_label": sentiment_label,
        "ml_high_prob": round(ml_prob, 4),
        "category": category,
    }


def process_batch(articles: list[dict]) -> list[dict]:
    """Process a list of articles through the full pipeline."""
    return [process_article(a) for a in articles]
