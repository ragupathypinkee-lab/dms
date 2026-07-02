from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "AI需求登记系统"
    debug: bool = True
    database_url: str = f"sqlite:///{BASE_DIR.parent / 'dms.db'}"

    templates_dir: Path = BASE_DIR / "templates"
    static_dir: Path = BASE_DIR / "static"

    bootstrap_css: str = (
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
    )
    bootstrap_js: str = (
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
    )


settings = Settings()
