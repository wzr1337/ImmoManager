"""Runtime configuration, loaded from .env locally or systemd EnvironmentFile in prod."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv_if_present() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str | None
    telegram_allowed_chat_ids: frozenset[int]
    anthropic_api_key: str | None
    db_path: Path
    data_dir: Path
    invoices_dir: Path = field(init=False)
    generated_dir: Path = field(init=False)
    templates_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "invoices_dir", self.data_dir / "invoices")
        object.__setattr__(self, "generated_dir", self.data_dir / "generated")
        object.__setattr__(self, "templates_dir", self.data_dir / "templates")


def _parse_chat_ids(raw: str | None) -> frozenset[int]:
    if not raw:
        return frozenset()
    return frozenset(int(x.strip()) for x in raw.split(",") if x.strip())


def load_settings() -> Settings:
    _load_dotenv_if_present()

    data_dir = Path(os.environ.get("IMMOMANAGER_DATA_DIR") or REPO_ROOT / "data")
    db_path = Path(os.environ.get("IMMOMANAGER_DB_PATH") or data_dir / "immomanager.db")

    return Settings(
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN") or None,
        telegram_allowed_chat_ids=_parse_chat_ids(os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS")),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
        db_path=db_path,
        data_dir=data_dir,
    )
