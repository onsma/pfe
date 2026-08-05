# BFPME Backend (FastAPI + SHAP + LLM Orchestration)

## What is included

- `POST /validate` - payload validation against model feature contract
- `POST /predict` - credit default prediction
- `POST /explain` - SHAP local explanation (top-k contributions)
- `POST /scenario` - what-if simulation (`delta_pd`)
- `POST /chat/analyze` - orchestration endpoint for analyst chat
- `GET /metadata/model` - model metadata and metrics
- `GET /metadata/tools` - tool catalog for function-calling layer
- `GET /health` - health check

## Folder structure

```text
backend/
  app/
    main.py
    config.py
    schemas.py
    routers/
    services/
  requirements.txt
  .env.example
```

## Quick start

```bash
cd backend
python -m pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Docs:

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json`
- Dashboard UI: `http://127.0.0.1:8000/dashboard`

## Notes

- Backend expects `c:/pfe/data/option_c_randomforest_model.joblib`.
- After retraining, either restart uvicorn or call `POST /metadata/reload-model` so the new joblib is loaded (artifacts are cached in memory).
- Train with `python scripts/train_option_c_randomforest.py` (uses `data/final_dataset.csv`, Option C feature set aligned with the notebook). The deployed model is RandomForest; `scripts/train_option_c_xgboost.py` remains available for the XGBoost variant.
- SHAP explanations are computed on transformed features from the preprocessor.
- `POST /chat/analyze` can run with or without LLM (`LLM_ENABLED=true|false`).
