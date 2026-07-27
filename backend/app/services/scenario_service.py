from app.config import settings
from app.schemas import ScenarioResponse
from app.services.model_service import predict


def run_scenario(baseline_features: dict, changes: dict, threshold: float | None = None) -> ScenarioResponse:
    if threshold is None:
        threshold = settings.default_threshold
    baseline = predict(baseline_features, threshold=threshold)
    scenario_features = {**baseline_features, **changes}
    scenario = predict(scenario_features, threshold=threshold)

    return ScenarioResponse(
        baseline_pd=baseline.probability_default,
        scenario_pd=scenario.probability_default,
        delta_pd=scenario.probability_default - baseline.probability_default,
        changed_features=changes,
        baseline_risk_class=baseline.risk_class,
        scenario_risk_class=scenario.risk_class,
    )

