from fastapi import APIRouter

from app.schemas import ChatAnalyzeRequest, ChatAnalyzeResponse
from app.services.llm_service import llm_available, summarize_with_llm
from app.services.model_service import predict
from app.services.scenario_service import run_scenario
from app.services.shap_service import explain_prediction
from app.services.validation_service import validate_features

router = APIRouter(prefix="/chat", tags=["orchestration"])


@router.post("/analyze", response_model=ChatAnalyzeResponse)
async def chat_analyze(payload: ChatAnalyzeRequest):
    tool_results: dict = {}

    if payload.run_validation:
        tool_results["validation"] = validate_features(payload.features).model_dump()
    if payload.run_prediction:
        tool_results["prediction"] = predict(payload.features, payload.threshold).model_dump()
    if payload.run_explanation:
        tool_results["explanation"] = explain_prediction(payload.features, payload.top_k_shap).model_dump()
    if payload.scenario_changes:
        tool_results["scenario"] = run_scenario(
            baseline_features=payload.features,
            changes=payload.scenario_changes,
            threshold=payload.threshold,
        ).model_dump()

    used_llm = llm_available()
    if used_llm:
        try:
            llm_summary = await summarize_with_llm(payload.message, tool_results)
        except Exception as exc:  # noqa: BLE001 — never let an LLM hiccup discard computed results
            used_llm = False
            llm_summary = (
                f"The model results below were computed successfully, but the LLM summary "
                f"could not be generated ({type(exc).__name__}: {exc}). "
                f"Check that the LLM server at the configured URL is running and the model is pulled."
            )
    else:
        llm_summary = "LLM is disabled. Returning computed tool outputs only."

    return ChatAnalyzeResponse(tool_results=tool_results, llm_summary=llm_summary, used_llm=used_llm)

