from typing import Any, Literal

from pydantic import BaseModel, Field

from app.config import settings


class FeaturePayload(BaseModel):
    features: dict[str, Any] = Field(default_factory=dict)


class ValidateResponse(BaseModel):
    valid: bool
    missing_required: list[str]
    unknown_features: list[str]
    warnings: list[str]


class PredictionResponse(BaseModel):
    prediction: int
    probability_default: float
    probability_non_default: float
    threshold: float
    risk_class: Literal["low", "medium", "high"]
    model_name: str
    model_version: str


class ShapFeatureContribution(BaseModel):
    feature: str
    value: Any
    shap_value: float
    direction: Literal["increase_risk", "decrease_risk"]


class ExplainResponse(BaseModel):
    base_value: float
    prediction: float
    top_contributions: list[ShapFeatureContribution]
    model_name: str
    model_version: str
    notes: list[str] = Field(default_factory=list)


class ScenarioRequest(BaseModel):
    baseline_features: dict[str, Any]
    changes: dict[str, Any]
    threshold: float = Field(default_factory=lambda: settings.default_threshold)


class ScenarioResponse(BaseModel):
    baseline_pd: float
    scenario_pd: float
    delta_pd: float
    changed_features: dict[str, Any]
    baseline_risk_class: str
    scenario_risk_class: str


class ChatAnalyzeRequest(BaseModel):
    message: str
    features: dict[str, Any]
    run_validation: bool = True
    run_prediction: bool = True
    run_explanation: bool = True
    scenario_changes: dict[str, Any] | None = None
    threshold: float = Field(default_factory=lambda: settings.default_threshold)
    top_k_shap: int = 8


class ChatAnalyzeResponse(BaseModel):
    tool_results: dict[str, Any]
    llm_summary: str
    used_llm: bool


# ── Monte Carlo ──────────────────────────────────────────────────────────────
class MonteCarloShock(BaseModel):
    """One feature to perturb. `pct` is a relative magnitude (0.2 => ±20%)."""

    field: str
    pct: float = Field(ge=0.0, le=2.0)


class MonteCarloRequest(BaseModel):
    features: dict[str, Any]
    shocks: list[MonteCarloShock] = Field(default_factory=list)
    n_simulations: int = Field(default=1000, ge=10, le=20000)
    distribution: Literal["normal", "uniform"] = "normal"
    threshold: float = Field(default_factory=lambda: settings.default_threshold)
    seed: int | None = None
    n_bins: int = Field(default=10, ge=4, le=50)
    n_extremes: int = Field(default=3, ge=0, le=20)


class MonteCarloExtreme(BaseModel):
    index: int
    probability_default: float
    risk_class: str
    features: dict[str, float]


class MonteCarloHistogram(BaseModel):
    edges: list[float]
    counts: list[int]


class MonteCarloResponse(BaseModel):
    n_simulations: int
    distribution: str
    threshold: float
    baseline_pd: float
    mean_pd: float
    std_pd: float
    min_pd: float
    max_pd: float
    percentiles: dict[str, float]
    var_95: float
    expected_shortfall_95: float
    prob_exceeds_threshold: float
    risk_distribution: dict[str, int]
    histogram: MonteCarloHistogram
    extremes: list[MonteCarloExtreme]
    shocked_features: list[str]
    model_name: str
    model_version: str
    notes: list[str] = Field(default_factory=list)

