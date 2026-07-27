from fastapi import APIRouter

from app.schemas import ScenarioRequest, ScenarioResponse
from app.services.scenario_service import run_scenario

router = APIRouter(prefix="/scenario", tags=["scenario"])


@router.post("", response_model=ScenarioResponse)
def simulate(payload: ScenarioRequest):
    return run_scenario(
        baseline_features=payload.baseline_features,
        changes=payload.changes,
        threshold=payload.threshold,
    )

