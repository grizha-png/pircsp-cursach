from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv_if_present(project_root: Path) -> None:
    dotenv_path = project_root / ".env"
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        os.environ.setdefault(key.strip(), value.strip())


def _parse_origins(raw_value: str) -> list[str]:
    values = [item.strip() for item in raw_value.split(",")]
    return [item for item in values if item]


@dataclass(slots=True)
class Settings:
    app_name: str
    secret_key: str
    token_ttl_hours: int
    database_path: Path
    cors_origins: list[str]


def get_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[2]
    _load_dotenv_if_present(project_root)
    default_data_dir = project_root / "data"
    database_path = Path(os.getenv("DB_PATH", default_data_dir / "app.db"))
    raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080")
    return Settings(
        app_name=os.getenv("APP_NAME", "Interactive Educational Tests Constructor"),
        secret_key=os.getenv("SECRET_KEY", "change-me-for-production"),
        token_ttl_hours=int(os.getenv("TOKEN_TTL_HOURS", "12")),
        database_path=database_path,
        cors_origins=_parse_origins(raw_origins),
    )
