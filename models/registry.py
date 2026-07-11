"""
models/registry.py
───────────────────
Model version registry — loads model artifacts by version string.

Reads the metadata.json in each versioned model directory to build a
registry of available models with their metrics and training provenance.

Interviewers love this: "How do you manage model versions?"
  Answer: Each version has a metadata.json logging training date, data hash,
  and evaluation metrics. Promotion from staging to production is a single
  env var change (MODEL_VERSION=v2).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    """
    Metadata for a single model version.

    Attributes:
        version:       Version string, e.g. 'v1'.
        trained_at:    ISO-8601 training timestamp.
        data_hash:     SHA-256 of the training CSV for reproducibility.
        accuracy:      Accuracy on the hold-out validation set.
        precision:     Macro-averaged precision.
        recall:        Macro-averaged recall.
        f1_score:      Macro-averaged F1.
        model_type:    Human-readable model name, e.g. 'TF-IDF + Logistic Regression'.
        notes:         Free-text notes (e.g. "Baseline model — VADER weak labels").
    """

    version: str
    trained_at: str
    data_hash: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    model_type: str
    notes: str = ""

    @classmethod
    def from_dict(cls, version: str, data: dict) -> "ModelMetadata":
        return cls(
            version=version,
            trained_at=data.get("trained_at", "unknown"),
            data_hash=data.get("data_hash", "unknown"),
            accuracy=float(data.get("accuracy", 0.0)),
            precision=float(data.get("precision", 0.0)),
            recall=float(data.get("recall", 0.0)),
            f1_score=float(data.get("f1_score", 0.0)),
            model_type=data.get("model_type", "unknown"),
            notes=data.get("notes", ""),
        )


class ModelRegistry:
    """
    Discovers and indexes all versioned models under ``models_base_path``.

    Each model version must have a directory ``models/<version>/`` containing:
      - ``metadata.json``  (required — defines the version's metrics)
      - ``logistic_model.pkl``
      - ``tfidf_vectorizer.pkl``

    Usage:
        registry = ModelRegistry()
        meta = registry.get("v1")
        print(meta.f1_score)

        for v, m in registry.list_all().items():
            print(f"{v}: F1={m.f1_score:.3f}  ({m.model_type})")
    """

    def __init__(self, models_base_path: Optional[Path] = None) -> None:
        if models_base_path is None:
            from config.settings import settings
            models_base_path = settings.model_base_path

        self._base = models_base_path
        self._registry: dict[str, ModelMetadata] = {}
        self._scan()

    def _scan(self) -> None:
        """Walk the models directory and load all valid metadata.json files."""
        if not self._base.exists():
            log.warning("Models directory not found: %s", self._base)
            return

        for version_dir in sorted(self._base.iterdir()):
            if not version_dir.is_dir():
                continue
            meta_file = version_dir / "metadata.json"
            if not meta_file.exists():
                continue
            try:
                with open(meta_file, encoding="utf-8") as f:
                    data = json.load(f)
                meta = ModelMetadata.from_dict(version_dir.name, data)
                self._registry[version_dir.name] = meta
                log.debug("Registered model version '%s' (F1=%.3f)", version_dir.name, meta.f1_score)
            except Exception as exc:
                log.warning("Failed to load metadata from %s: %s", meta_file, exc)

        log.info("Model registry: %d version(s) found.", len(self._registry))

    def get(self, version: str) -> ModelMetadata:
        """
        Return metadata for a specific model version.

        Raises:
            KeyError: If the version is not in the registry.
        """
        if version not in self._registry:
            raise KeyError(
                f"Model version '{version}' not found. "
                f"Available: {list(self._registry.keys())}"
            )
        return self._registry[version]

    def list_all(self) -> dict[str, ModelMetadata]:
        """Return all registered model versions sorted by version string."""
        return dict(sorted(self._registry.items()))

    def best(self, metric: str = "f1_score") -> Optional[ModelMetadata]:
        """
        Return the model version with the highest value for ``metric``.

        Args:
            metric: One of 'accuracy', 'f1_score', 'precision', 'recall'.
        """
        if not self._registry:
            return None
        return max(self._registry.values(), key=lambda m: getattr(m, metric, 0.0))
