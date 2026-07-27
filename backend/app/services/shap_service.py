from functools import lru_cache
from typing import Any

import numpy as np
import shap

from app.schemas import ExplainResponse, ShapFeatureContribution
from app.services.artifacts import load_artifact, load_metrics
from app.services.model_service import prepare_model_frame


@lru_cache(maxsize=1)
def _tree_explainer():
    artifact = load_artifact()
    return shap.TreeExplainer(artifact["model"])


def explain_prediction(features: dict[str, Any], top_k: int = 8) -> ExplainResponse:
    artifact = load_artifact()
    metrics = load_metrics()

    preprocessor = artifact["preprocessor"]
    model = artifact["model"]
    model_input = prepare_model_frame(features)
    transformed = preprocessor.transform(model_input)

    feature_names = (
        preprocessor.get_feature_names_out().tolist()
        if hasattr(preprocessor, "get_feature_names_out")
        else [f"f_{i}" for i in range(transformed.shape[1])]
    )

    explainer = _tree_explainer()
    shap_values = explainer.shap_values(transformed)
    if isinstance(shap_values, list):
        # Older API / multi-output: list of per-class arrays, take positive class.
        shap_row = np.array(shap_values[-1][0])
        base_value = float(np.array(explainer.expected_value).reshape(-1)[-1])
    else:
        # ndarray: (n_samples, n_features) for XGBoost, or
        # (n_samples, n_features, n_classes) for RandomForest. Take positive class.
        shap_row = np.array(shap_values[0])
        if shap_row.ndim > 1:
            shap_row = shap_row[..., -1]
        expected = np.array(explainer.expected_value).reshape(-1)
        base_value = float(expected[-1] if expected.size > 1 else expected[0])

    top_idx = np.argsort(np.abs(shap_row))[::-1][:top_k]

    transformed_row = transformed[0]
    contributions: list[ShapFeatureContribution] = []
    for idx in top_idx:
        contributions.append(
            ShapFeatureContribution(
                feature=feature_names[idx],
                value=float(transformed_row[idx]) if np.isscalar(transformed_row[idx]) else str(transformed_row[idx]),
                shap_value=float(shap_row[idx]),
                direction="increase_risk" if shap_row[idx] >= 0 else "decrease_risk",
            )
        )

    prediction = float(model.predict_proba(transformed)[0, 1])
    return ExplainResponse(
        base_value=base_value,
        prediction=prediction,
        top_contributions=contributions,
        model_name=str(artifact.get("model_name", "OptionC_RandomForest")),
        model_version=str(metrics.get("model_version", "v1")),
        notes=["SHAP values are computed on transformed model features."],
    )

