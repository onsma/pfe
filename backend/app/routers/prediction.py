from fastapi import APIRouter, Query

from app.config import settings
from app.schemas import FeaturePayload, PredictionResponse
from app.services.model_service import predict

router = APIRouter(prefix="/predict", tags=["prediction"])


@router.post("", response_model=PredictionResponse)
def predict_client(
    payload: FeaturePayload,
    threshold: float = Query(default=None, ge=0.0, le=1.0),
):
    effective_threshold = settings.default_threshold if threshold is None else threshold
    return predict(payload.features, threshold=effective_threshold)

