from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]

class SimonSettings(BaseSettings):

    """ Central application settings for Simon """

    model_config = SettingsConfigDict(
        env_prefix = "SIMON_",
        env_file = ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Simon"
    environment: str = "development"

    model_base_url: str = "http://127.0.0.1:11434"
    model_name: str = "qwen3:4b"

    database_path: Path = PROJECT_ROOT / "data" / "simon.db"
    log_dir: Path = PROJECT_ROOT/ "logs"

    max_plan_steps: int = Field(default=12,ge=1,le=50)
    require_approval: bool = True

def load_settings() -> SimonSettings:

    settings = SimonSettings()

    settings.database_path.parent.mkdir(parents=True,exist_ok=True)
    settings.log_dir.mkdir(parents=True,exist_ok=True)

    return settings

    




    