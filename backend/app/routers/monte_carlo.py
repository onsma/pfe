from fastapi import APIRouter

from app.schemas import MonteCarloRequest, MonteCarloResponse
from app.services.monte_carlo_service import run_monte_carlo

router = APIRouter(prefix="/monte-carlo", tags=["monte-carlo"])


@router.post("", response_model=MonteCarloResponse)
def simulate(payload: MonteCarloRequest):
    return run_monte_carlo(
        features=payload.features,
        shocks=payload.shocks,
        n_simulations=payload.n_simulations,
        distribution=payload.distribution,
        threshold=payload.threshold,
        seed=payload.seed,
        n_bins=payload.n_bins,
        n_extremes=payload.n_extremes,
    )
