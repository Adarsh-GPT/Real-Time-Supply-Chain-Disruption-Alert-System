"""
ml_training/train.py
──────────────────────
Full ML training pipeline: loads data, runs NLP pipeline, trains models,
saves versioned artifacts with metadata.json.

This script is run offline (not at API startup).
Usage:
    python ml_training/train.py [--data data/cleaned.csv] [--version v2]

Phase 2: Scaffold with existing TF-IDF + Logistic Regression.
Phase 5: Will add XGBoost + hand-labeled eval set + real metrics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path so imports work when running as script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def compute_file_hash(filepath: Path) -> str:
    """SHA-256 hash of the training data file for reproducibility."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def train(data_path: Path, version: str) -> None:
    """
    Train the TF-IDF + Logistic Regression model and save artifacts.

    Args:
        data_path: Path to the cleaned + labeled CSV file.
        version:   Model version string (e.g. 'v2').
    """
    import pandas as pd
    import joblib
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report, accuracy_score, f1_score
    from sklearn.model_selection import train_test_split

    from processing.cleaner import clean_dataframe
    from processing.preprocessor import preprocess_series
    from processing.sentiment import score_batch

    print(f"[train] Loading data from {data_path}...")
    df = pd.read_csv(data_path, encoding="latin1")
    print(f"[train] Loaded {len(df)} rows.")

    # ── Cleaning ──────────────────────────────────────────────────────────────
    print("[train] Cleaning headlines...")
    df = clean_dataframe(df, text_column="headline", output_column="headline_clean")
    df = df.dropna(subset=["headline_clean"])
    df = df[df["headline_clean"].str.strip().str.len() > 0]

    # ── Preprocessing ─────────────────────────────────────────────────────────
    print("[train] Lemmatising...")
    df["headline_processed"] = preprocess_series(df["headline_clean"].tolist())
    df = df[df["headline_processed"].str.strip().str.len() > 0]

    # ── Labels: use VADER if no 'risk_level' column exists ───────────────────
    if "risk_level" not in df.columns:
        print("[train] No 'risk_level' column found — generating VADER labels (WEAK SUPERVISION).")
        print("[train] ⚠️  These labels are NOT defensible. Phase 5 will use hand-labeled data.")
        results = score_batch(df["headline"].tolist())
        from risk_engine.risk_scorer import HybridRiskScorer, RiskLevel

        def vader_to_risk(compound: float) -> str:
            if compound <= -0.05:
                return "High"
            elif compound >= 0.05:
                return "Low"
            else:
                return "Medium"

        df["risk_level"] = [vader_to_risk(r.compound) for r in results]

    print(f"[train] Class distribution:\n{df['risk_level'].value_counts()}")

    # ── Train/test split ──────────────────────────────────────────────────────
    X = df["headline_processed"]
    y = df["risk_level"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # ── Model training ────────────────────────────────────────────────────────
    print("[train] Training TF-IDF vectoriser...")
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=20_000,
        sublinear_tf=True,
    )
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    print("[train] Training Logistic Regression...")
    model = LogisticRegression(
        C=1.0,
        max_iter=1000,
        class_weight="balanced",
        random_state=42,
    )
    model.fit(X_train_vec, y_train)

    # ── Evaluation ────────────────────────────────────────────────────────────
    y_pred = model.predict(X_test_vec)
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)

    print("\n[train] Evaluation Report:")
    print(classification_report(y_test, y_pred, zero_division=0))

    # ── Save artifacts ────────────────────────────────────────────────────────
    model_dir = PROJECT_ROOT / "models" / version
    model_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, model_dir / "logistic_model.pkl")
    joblib.dump(vectorizer, model_dir / "tfidf_vectorizer.pkl")

    data_hash = compute_file_hash(data_path)
    metadata = {
        "version": version,
        "model_type": "TF-IDF (unigrams+bigrams, max_features=20000) + Logistic Regression (balanced)",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "data_path": str(data_path),
        "data_hash": data_hash,
        "training_rows": len(X_train),
        "eval_rows": len(X_test),
        "eval_set": "VADER-auto-labeled (weak supervision)" if "risk_level" not in pd.read_csv(data_path, nrows=1).columns else "Column 'risk_level' from input data",
        "accuracy": round(acc, 4),
        "precision": 0.0,  # Placeholder — Phase 5 computes per-class
        "recall": 0.0,
        "f1_score": round(f1, 4),
        "artifacts": {
            "model_file": "logistic_model.pkl",
            "vectorizer_file": "tfidf_vectorizer.pkl",
        },
        "notes": "Trained by ml_training/train.py. Phase 5 will add XGBoost and hand-labeled eval set.",
    }

    with open(model_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n[train] ✅ Model artifacts saved to {model_dir}")
    print(f"[train]    Accuracy: {acc:.4f} | Macro F1: {f1:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the supply chain risk classifier.")
    parser.add_argument(
        "--data",
        type=Path,
        default=PROJECT_ROOT / "data" / "cleaned.csv",
        help="Path to cleaned training data CSV (must have 'headline' column).",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="v1",
        help="Model version string (e.g. 'v2').",
    )
    args = parser.parse_args()

    if not args.data.exists():
        print(f"Error: Data file not found: {args.data}")
        print("Place your cleaned CSV at data/cleaned.csv or specify --data <path>")
        sys.exit(1)

    train(data_path=args.data, version=args.version)
