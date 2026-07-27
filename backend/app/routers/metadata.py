from fastapi import APIRouter

from app.config import settings
from app.services.artifacts import load_artifact, load_metrics, reload_artifact
from app.services.eda_service import compute_eda

router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.get("/eda")
def dataset_eda():
    """Chart-ready exploratory summary of the training dataset for the home dashboard."""
    return compute_eda()


@router.get("/model")
def model_metadata():
    artifact = load_artifact()
    metrics = load_metrics()
    return {
        "model_name": artifact.get("model_name", "OptionC_RandomForest"),
        "allowed_columns_count": len(artifact["allowed_columns"]),
        "metrics": metrics,
        "artifact_path": str(settings.model_artifact_path),
    }


@router.get("/tools")
def tool_catalog():
    return {
        "tools": [
            "validate_payload",
            "predict_client",
            "explain_prediction_shap",
            "simulate_scenario",
            "chat_analyze",
        ]
    }


@router.post("/reload-model")
def reload_model():
    """Clear in-memory caches and load joblib again from MODEL_ARTIFACT_PATH (no server restart)."""
    artifact = reload_artifact()
    metrics = load_metrics()
    return {
        "status": "reloaded",
        "artifact_path": str(settings.model_artifact_path),
        "allowed_columns_count": len(artifact["allowed_columns"]),
        "model_name": artifact.get("model_name"),
        "metrics": metrics,
    }

