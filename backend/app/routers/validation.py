from fastapi import APIRouter

from app.schemas import FeaturePayload, ValidateResponse
from app.services.validation_service import validate_features

router = APIRouter(prefix="/validate", tags=["validation"])


@router.post("", response_model=ValidateResponse)
def validate(payload: FeaturePayload):
    return validate_features(payload.features)

