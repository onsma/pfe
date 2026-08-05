from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="BFPME Risk Backend", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    model_artifact_path: Path = Field(
        default=Path("c:/pfe/data/option_c_randomforest_model.joblib"),
        alias="MODEL_ARTIFACT_PATH",
    )
    model_metrics_path: Path = Field(
        default=Path("c:/pfe/data/option_c_randomforest_metrics.json"),
        alias="MODEL_METRICS_PATH",
    )
    dataset_path: Path = Field(
        default=Path("c:/pfe/data/final_dataset.csv"),
        alias="DATASET_PATH",
    )

    # Decision threshold on probability_default: pred = 1 (default/risky) when PD >= this.
    # Lower it (e.g. 0.3) to catch more risky clients at the cost of more false alarms.
    default_threshold: float = Field(default=0.5, ge=0.0, le=1.0, alias="DEFAULT_THRESHOLD")

    llm_enabled: bool = Field(default=False, alias="LLM_ENABLED")
    llm_base_url: str = Field(default="http://127.0.0.1:11434/v1", alias="LLM_BASE_URL")
    llm_model: str = Field(default="qwen2.5:7b-instruct", alias="LLM_MODEL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    # Cap the answer length: concise but informative. Lower => shorter answers.
    llm_max_tokens: int = Field(default=500, ge=64, le=4096, alias="LLM_MAX_TOKENS")


settings = Settings()

