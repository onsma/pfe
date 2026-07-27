"""
Monte Carlo engine for credit-risk stress testing.

Given a base client and a set of feature shocks, it generates N perturbed
scenarios, runs the deployed model on all of them in a single vectorized batch
(one preprocessor.transform + one predict_proba), and summarizes the resulting
distribution of probability-of-default (PD): central tendency, dispersion,
percentiles, VaR / expected-shortfall, risk-class mix, a histogram, and the
most extreme scenarios.

Shocks are applied to the RAW input features, then feature engineering is
re-derived so ratios (loan_to_revenue, cash_to_debt, ...) stay consistent.
"""
from typing import Any

import numpy as np
import pandas as pd

from app.schemas import (
    MonteCarloExtreme,
    MonteCarloHistogram,
    MonteCarloResponse,
    MonteCarloShock,
)
from app.services.artifacts import load_artifact, load_metrics
from app.services.feature_engineering import apply_feature_engineering
from app.services.model_service import _risk_class

_PERCENTILES = [5, 10, 25, 50, 75, 90, 95]


def _build_sample_frame(
    base: dict[str, Any],
    active: list[MonteCarloShock],
    n: int,
    distribution: str,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    """Row 0 is the untouched baseline; rows 1..n are perturbed scenarios."""
    frame = pd.DataFrame([dict(base) for _ in range(n + 1)])
    sampled: dict[str, np.ndarray] = {}

    for shock in active:
        b = float(base[shock.field])
        if distribution == "normal":
            factors = rng.normal(1.0, shock.pct, n)
        else:  # uniform
            factors = rng.uniform(1.0 - shock.pct, 1.0 + shock.pct, n)
        values = b * factors
        # Financial magnitudes (base >= 0) must not flip negative; rates may.
        if b >= 0:
            values = np.clip(values, 0.0, None)
        frame.loc[1:, shock.field] = values
        sampled[shock.field] = values

    return frame, sampled


def run_monte_carlo(
    features: dict[str, Any],
    shocks: list[MonteCarloShock],
    n_simulations: int = 1000,
    distribution: str = "normal",
    threshold: float | None = None,
    seed: int | None = None,
    n_bins: int = 10,
    n_extremes: int = 3,
) -> MonteCarloResponse:
    from app.config import settings

    if threshold is None:
        threshold = settings.default_threshold

    artifact = load_artifact()
    metrics = load_metrics()
    preprocessor = artifact["preprocessor"]
    model = artifact["model"]
    allowed_columns: list[str] = artifact["allowed_columns"]

    notes: list[str] = []

    # Keep only shocks whose field is present and numeric in the base client.
    active = [
        s for s in shocks
        if isinstance(features.get(s.field), (int, float)) and not isinstance(features.get(s.field), bool)
    ]
    skipped = [s.field for s in shocks if s not in active]
    if skipped:
        notes.append(f"Ignored non-numeric/missing shock fields: {', '.join(skipped)}.")
    if not active:
        notes.append("No active shocks - all simulations equal the baseline client.")

    rng = np.random.default_rng(seed)
    frame, sampled = _build_sample_frame(features, active, n_simulations, distribution, rng)

    # Re-derive engineered ratios, align to the model's expected columns.
    frame = apply_feature_engineering(frame)
    for col in allowed_columns:
        if col not in frame.columns:
            frame[col] = np.nan
    model_input = frame[allowed_columns]

    transformed = preprocessor.transform(model_input)
    pd_all = model.predict_proba(transformed)[:, 1].astype(float)

    baseline_pd = float(pd_all[0])
    sims = pd_all[1:]

    mean_pd = float(sims.mean())
    std_pd = float(sims.std())
    pct_vals = np.percentile(sims, _PERCENTILES)
    percentiles = {f"p{p}": float(v) for p, v in zip(_PERCENTILES, pct_vals)}

    var_95 = float(percentiles["p95"])
    tail = sims[sims >= var_95]
    expected_shortfall_95 = float(tail.mean()) if tail.size else var_95

    risk_classes = [_risk_class(float(v)) for v in sims]
    risk_distribution = {
        "low": risk_classes.count("low"),
        "medium": risk_classes.count("medium"),
        "high": risk_classes.count("high"),
    }
    prob_exceeds_threshold = float(np.mean(sims >= threshold))

    counts, edges = np.histogram(sims, bins=n_bins, range=(0.0, 1.0))
    histogram = MonteCarloHistogram(edges=[float(e) for e in edges], counts=[int(c) for c in counts])

    extremes: list[MonteCarloExtreme] = []
    if n_extremes > 0 and sims.size:
        order = np.argsort(sims)
        k = min(n_extremes, sims.size)
        picks = list(order[:k]) + list(order[-k:])
        seen: set[int] = set()
        for idx in picks:
            if idx in seen:
                continue
            seen.add(idx)
            shocked_vals = {f: float(sampled[f][idx]) for f in sampled}
            extremes.append(
                MonteCarloExtreme(
                    index=int(idx) + 1,  # 1-based, baseline excluded
                    probability_default=float(sims[idx]),
                    risk_class=_risk_class(float(sims[idx])),
                    features=shocked_vals,
                )
            )
        extremes.sort(key=lambda e: e.probability_default)

    return MonteCarloResponse(
        n_simulations=int(sims.size),
        distribution=distribution,
        threshold=threshold,
        baseline_pd=baseline_pd,
        mean_pd=mean_pd,
        std_pd=std_pd,
        min_pd=float(sims.min()),
        max_pd=float(sims.max()),
        percentiles=percentiles,
        var_95=var_95,
        expected_shortfall_95=expected_shortfall_95,
        prob_exceeds_threshold=prob_exceeds_threshold,
        risk_distribution=risk_distribution,
        histogram=histogram,
        extremes=extremes,
        shocked_features=[s.field for s in active],
        model_name=str(artifact.get("model_name", "OptionC_RandomForest")),
        model_version=str(metrics.get("model_version", "v1")),
        notes=notes,
    )
