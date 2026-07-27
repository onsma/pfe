from fastapi import APIRouter, Query

from app.schemas import ExplainResponse, FeaturePayload
from app.services.shap_service import explain_prediction

router = APIRouter(prefix="/explain", tags=["explainability"])


@router.post("", response_model=ExplainResponse)
def explain(payload: FeaturePayload, top_k: int = Query(default=8, ge=1, le=30)):
    return explain_prediction(payload.features, top_k=top_k)

