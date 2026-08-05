# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BFPME is a credit default prediction (PD) platform for SME lending. It exposes a FastAPI backend that validates features, predicts default probability via XGBoost, generates SHAP explanations, and runs what-if scenario simulations. An optional LLM layer (Ollama-compatible) orchestrates the full analyst workflow. A secondary module implements the IFRS 9 ECL framework.

## Commands

### Start the backend

```powershell
cd backend
pip install -r requirements.txt
copy .env.example .env   # then edit paths/flags as needed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI: `http://127.0.0.1:8000/docs`  
Dashboard: `http://127.0.0.1:8000/dashboard`

### Train or retrain the model

```powershell
python scripts/train_option_c_xgboost.py
```

Writes `data/option_c_xgboost_model.joblib` and `data/option_c_xgboost_metrics.json`.

### Reload model without restart

```
POST /metadata/reload-model
```

## Architecture

### Backend (`backend/app/`)

| Layer | Purpose |
|---|---|
| `main.py` | FastAPI app, mounts routers and static frontend |
| `config.py` | Pydantic `BaseSettings` — all env-var-driven config |
| `schemas.py` | All request/response Pydantic models |
| `routers/` | One file per endpoint group (prediction, explain, scenario, chat, …) |
| `services/` | Business logic decoupled from HTTP layer |

Key services:
- `artifacts.py` — loads and caches the joblib model + preprocessor at startup
- `model_service.py` — runs feature engineering then `predict_proba`
- `shap_service.py` — `TreeExplainer` on the transformed feature matrix
- `scenario_service.py` — computes baseline vs. modified PD and `delta_pd`
- `llm_service.py` — async `httpx` call to an Ollama-compatible endpoint
- `feature_engineering.py` — derives ratios at inference time (not during training)

### Request flow

```
POST /chat/analyze
  └─ validate → predict → explain → scenario (optional)
       └─ build_llm_prompt → LLM call (if LLM_ENABLED=true) → structured response

POST /predict
  └─ apply_feature_engineering → preprocessor.transform → xgb.predict_proba → risk_class
```

### Preprocessing pipeline (joblib artifact)

Winsorizer (1–99 pct) → OrdinalEncoder → OneHotEncoder → SimpleImputer → StandardScaler

Feature engineering (runtime ratios: `loan_to_revenue`, `cash_to_debt`, `payment_stress_index`, `garantie_to_loan`, etc.) is applied **before** the preprocessor, inside `model_service.py`, not baked into the artifact.

### Three model options

| Option | Feature set | Status |
|---|---|---|
| A | All features | Benchmark (notebook only) |
| B | No BFPME scores | Pure ML (notebook only) |
| C | Hybrid minimal BFPME | **Deployed** |

Option C keeps `score_bfpme_global` and `score_bfpme_gap` but drops the 62 SF_* sub-factors to reduce noise while retaining regulatory explainability.

### Data (`data/`)

- `final_dataset.csv` — synthetic SME credit dataset (~1 000 rows, 100+ features, target: `default_flag`)
- `option_c_xgboost_model.joblib` — trained artifact
- `option_c_xgboost_metrics.json` — AUC, F1, precision, recall

The dataset is intentionally synthetic with latent risk drivers; reported AUC (~0.96+) reflects synthetic coherence, not real-world performance.

### IFRS 9 module (`dataset_IFRS9/`, `notebook_ifrs/`, `scripts/`)

Separate from the API. Produces ECL contributions via:

```
ECL_t = PD_t × LGD_t × EAD_t × DF_t
ECL_weighted = Σ_scenario (weight_s × ECL_lifetime_s)
```

Input tables: `ifrs9_exposure_snapshot.csv`, `ifrs9_macro_scenarios.csv`, `ifrs9_pd_curve.csv`, `ifrs9_lgd_curve.csv`, `ifrs9_ead_curve.csv`, `ifrs9_discount_curve.csv`.

### Frontend (`backend/frontend/`)

Static HTML/CSS/JS — no build step. Served by FastAPI at `/dashboard`. The sample SME payload is embedded in `app.js`.

## Configuration (`.env`)

```
MODEL_ARTIFACT_PATH=c:/pfe/data/option_c_xgboost_model.joblib
MODEL_METRICS_PATH=c:/pfe/data/option_c_xgboost_metrics.json
LLM_ENABLED=false
LLM_BASE_URL=http://127.0.0.1:11434/v1   # Ollama default
LLM_MODEL=qwen2.5:7b-instruct
LLM_API_KEY=                              # optional
APP_HOST=0.0.0.0
APP_PORT=8000
```

## Key reference files

- `texts/BFPME_PD_Modeling_Report.md` — modeling strategy, dataset generation rationale, results interpretation
- `texts/dataset_final_variable_dictionary.txt` — definitions for all 150+ variables
- `notebook_ifrs/README_IFRS9_schema.txt` — IFRS 9 table schemas and ECL logic
