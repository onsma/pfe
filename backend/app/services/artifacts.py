import json
import __main__
from functools import lru_cache
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

from app.config import settings


class Winsorizer(BaseEstimator, TransformerMixin):
    """Compatibility class for artifacts pickled from training script __main__."""

    def __init__(self, lower_quantile: float = 0.01, upper_quantile: float = 0.99):
        self.lower_quantile = lower_quantile
        self.upper_quantile = upper_quantile
        self.lower_bounds_ = None
        self.upper_bounds_ = None

    def fit(self, X, y=None):
        x_df = pd.DataFrame(X)
        self.lower_bounds_ = x_df.quantile(self.lower_quantile)
        self.upper_bounds_ = x_df.quantile(self.upper_quantile)
        return self

    def transform(self, X):
        x_df = pd.DataFrame(X).copy()
        return x_df.clip(self.lower_bounds_, self.upper_bounds_, axis=1).values

    def get_feature_names_out(self, input_features=None):
        if input_features is not None:
            return np.asarray(input_features, dtype=object)
        if hasattr(self, "feature_names_in_"):
            return self.feature_names_in_
        n = len(self.lower_bounds_) if self.lower_bounds_ is not None else 0
        return np.array([f"x{i}" for i in range(n)], dtype=object)


def _register_pickle_compat() -> None:
    # Training script saved Winsorizer as __main__.Winsorizer.
    if not hasattr(__main__, "Winsorizer"):
        setattr(__main__, "Winsorizer", Winsorizer)


@lru_cache(maxsize=1)
def load_artifact() -> dict[str, Any]:
    _register_pickle_compat()
    artifact = joblib.load(settings.model_artifact_path)
    if not {"preprocessor", "model", "allowed_columns"}.issubset(artifact.keys()):
        raise ValueError("Model artifact must include preprocessor, model, and allowed_columns.")
    return artifact


def clear_artifact_cache() -> None:
    load_artifact.cache_clear()
    load_metrics.cache_clear()


def reload_artifact() -> dict[str, Any]:
    clear_artifact_cache()
    return load_artifact()


@lru_cache(maxsize=1)
def load_metrics() -> dict[str, Any]:
    if not settings.model_metrics_path.exists():
        return {}
    return json.loads(settings.model_metrics_path.read_text(encoding="utf-8"))

