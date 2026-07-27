import pandas as pd

from app.schemas import ValidateResponse
from app.services.artifacts import load_artifact
from app.services.feature_engineering import apply_feature_engineering


def validate_features(features: dict) -> ValidateResponse:
    artifact = load_artifact()
    required_columns: list[str] = artifact["allowed_columns"]
    one_row = pd.DataFrame([features])
    engineered = apply_feature_engineering(one_row)

    incoming = set(engineered.columns)
    required = set(required_columns)
    missing = sorted(required - incoming)
    unknown = sorted(incoming - required)

    warnings: list[str] = []
    if missing:
        warnings.append("Some required model features are missing; they will be imputed.")
    if unknown:
        warnings.append("Some input features are not used by the model.")

    return ValidateResponse(
        valid=len(missing) == 0,
        missing_required=missing,
        unknown_features=unknown,
        warnings=warnings,
    )

