"""Exploratory data summary for the home dashboard.

Reads the training dataset once and returns lightweight, chart-ready aggregates
(target balance, risk-class mix, categorical breakdowns, a few numeric
histograms). Result is cached in-memory so the dataset is only scanned once.
"""

from functools import lru_cache
from typing import Any

import numpy as np
import pandas as pd

from app.config import settings


def _value_counts(series: pd.Series, top: int | None = None) -> list[dict[str, Any]]:
    counts = series.dropna().value_counts()
    if top is not None:
        counts = counts.head(top)
    return [{"label": str(idx), "count": int(val)} for idx, val in counts.items()]


def _histogram(series: pd.Series, bins: int = 12) -> dict[str, Any]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return {"edges": [], "counts": []}
    # trim extreme tail so the chart stays readable on skewed money columns
    hi = float(clean.quantile(0.97))
    lo = float(clean.min())
    if hi <= lo:
        hi = float(clean.max()) or lo + 1
    counts, edges = np.histogram(clean.clip(lo, hi), bins=bins, range=(lo, hi))
    return {
        "edges": [round(float(e), 2) for e in edges],
        "counts": [int(c) for c in counts],
    }


@lru_cache(maxsize=1)
def compute_eda() -> dict[str, Any]:
    path = settings.dataset_path
    if not path.exists():
        return {"available": False, "reason": f"Dataset not found at {path}"}

    df = pd.read_csv(path)
    n_rows, n_cols = df.shape

    target = df["default_flag"] if "default_flag" in df.columns else pd.Series(dtype=float)
    default_rate = float(target.mean()) if not target.empty else None

    missing_cells = int(df.isna().sum().sum())
    total_cells = int(n_rows * n_cols)
    completeness = round(1 - missing_cells / total_cells, 4) if total_cells else None

    def cat(col: str, top: int | None = None) -> list[dict[str, Any]]:
        return _value_counts(df[col], top) if col in df.columns else []

    return {
        "available": True,
        "summary": {
            "rows": int(n_rows),
            "features": int(n_cols),
            "default_rate": round(default_rate, 4) if default_rate is not None else None,
            "default_count": int(target.sum()) if not target.empty else None,
            "non_default_count": int((target == 0).sum()) if not target.empty else None,
            "completeness": completeness,
            "missing_cells": missing_cells,
            "n_sectors": int(df["secteur_activite"].nunique()) if "secteur_activite" in df.columns else None,
        },
        "target": [
            {"label": "Default", "count": int(target.sum()) if not target.empty else 0},
            {"label": "Non-Default", "count": int((target == 0).sum()) if not target.empty else 0},
        ],
        "risk_class": cat("risk_class"),
        "sector": cat("secteur_activite"),
        "classification": cat("classification_pme"),
        "region": cat("region_localisation"),
        "scenario": cat("scenario_economique"),
        "loan_hist": _histogram(df["montant_pret"]) if "montant_pret" in df.columns else {"edges": [], "counts": []},
    }


def clear_eda_cache() -> None:
    compute_eda.cache_clear()
