from typing import Any

import numpy as np
import pandas as pd

from app.config import settings
from app.schemas import PredictionResponse
from app.services.artifacts import load_artifact, load_metrics
from app.services.feature_engineering import apply_feature_engineering


def _risk_class(probability_default: float) -> str:
    if probability_default >= 0.7:
        return "high"
    if probability_default >= 0.4:
        return "medium"
    return "low"


def prepare_model_frame(features: dict[str, Any]) -> pd.DataFrame:
    artifact = load_artifact()
    allowed_columns: list[str] = artifact["allowed_columns"]

    row_df = pd.DataFrame([features])
    row_df = apply_feature_engineering(row_df)

    for col in allowed_columns:
        if col not in row_df.columns:
            row_df[col] = np.nan
    return row_df[allowed_columns]


def predict(features: dict[str, Any], threshold: float | None = None) -> PredictionResponse:
    if threshold is None:
        threshold = settings.default_threshold
    artifact = load_artifact()
    metrics = load_metrics()
    preprocessor = artifact["preprocessor"]
    model = artifact["model"]

    model_input = prepare_model_frame(features)
    transformed = preprocessor.transform(model_input)
    proba_non_default, proba_default = model.predict_proba(transformed)[0].tolist()
    pred = int(proba_default >= threshold)

    return PredictionResponse(
        prediction=pred,
        probability_default=float(proba_default),
        probability_non_default=float(proba_non_default),
        threshold=threshold,
        risk_class=_risk_class(float(proba_default)),
        model_name=str(artifact.get("model_name", "OptionC_RandomForest")),
        model_version=str(metrics.get("model_version", "v1")),
    )

