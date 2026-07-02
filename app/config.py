from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI需求登记系统"
    debug: bool = True
    secret_key: str = "change-me-in-production"
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'dms.db'}"

    templates_dir: Path = BASE_DIR / "templates"
    static_dir: Path = BASE_DIR / "static"

    bootstrap_css: str = (
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
    )
    bootstrap_js: str = (
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
    )

    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # .env 优先于系统环境变量，避免旧 OPENAI_API_KEY 覆盖项目配置
        return init_settings, dotenv_settings, env_settings, file_secret_settings

    @field_validator("openai_api_key", "openai_base_url", mode="before")
    @classmethod
    def strip_optional_str(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


settings = Settings()
