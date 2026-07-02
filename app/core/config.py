from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

APP_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = APP_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "校园AI需求管理与智能体平台"
    debug: bool = True
    secret_key: str = "change-me-in-production"
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'dms.db'}"

    templates_dir: Path = APP_DIR / "web" / "templates"
    static_dir: Path = APP_DIR / "web" / "static"

    bootstrap_css: str = (
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
    )
    bootstrap_js: str = (
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
    )

    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_timeout: float = 120.0

    def validate_runtime(self) -> None:
        if self.debug:
            return
        if self.secret_key == "change-me-in-production":
            raise RuntimeError("生产环境必须设置 SECRET_KEY")
        if len(self.secret_key) < 32:
            raise RuntimeError("SECRET_KEY 长度至少 32 位")

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
