import json
from typing import Any

import httpx

from app.config import settings


def llm_available() -> bool:
    return settings.llm_enabled


def build_llm_prompt(message: str, tool_results: dict[str, Any]) -> str:
    lines = [
        "You are a credit risk analyst assistant for BFPME (SME lending in Tunisia).",
        "Use ONLY the tool outputs below. Do not invent, round, or estimate any numeric value.",
        "",
        "If a 'scenario' block is present, it is a REAL re-run of the RandomForest model with the",
        "analyst's hypothetical change already applied. You MUST report, with the exact numbers:",
        "  - baseline probability of default (baseline_pd),",
        "  - the new probability of default after the change (scenario_pd),",
        "  - the change (delta_pd, positive = risk increased), and the changed_features applied.",
        "Explain in plain language whether the change made the client safer or riskier.",
        "",
        "Structure your answer as: Decision Summary, Risk Drivers, Protective Drivers,",
        "Scenario Impact (only if a scenario block exists), and Caveats.",
        "Be concise but informative: aim for ~150-180 words total. Use short bullet points,",
        "lead with the key numbers, no preamble or repetition. Finish your last sentence.",
        "",
        f"Analyst question:\n{message}",
        "",
        "Tool outputs (JSON):",
        json.dumps(tool_results, indent=2, ensure_ascii=False, default=str),
    ]
    return "\n".join(lines)


async def summarize_with_llm(message: str, tool_results: dict[str, Any]) -> str:
    if not llm_available():
        return "LLM is disabled. Returning raw tool outputs only."

    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"

    payload = {
        "model": settings.llm_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a precise risk analyst assistant. Never fabricate numeric values. "
                    "Keep answers concise but informative — short, no filler."
                ),
            },
            {"role": "user", "content": build_llm_prompt(message, tool_results)},
        ],
        "temperature": 0.1,
        "max_tokens": settings.llm_max_tokens,
    }

    # Generous read timeout: a cold 7B model can take a while to load on first call.
    timeout = httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{settings.llm_base_url}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
            body = response.json()
            return body["choices"][0]["message"]["content"].strip()
    except httpx.ConnectError as exc:
        raise RuntimeError(
            f"cannot reach LLM server at {settings.llm_base_url} — is Ollama running?"
        ) from exc
    except httpx.ReadTimeout as exc:
        raise RuntimeError(
            f"LLM did not respond in time (model '{settings.llm_model}' may be cold-loading)"
        ) from exc

