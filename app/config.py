from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    sources_dir: Path
    db_path: Path

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        bot_token = os.getenv("BOT_TOKEN", "").strip()
        sources_dir = Path(os.getenv("SOURCES_DIR", "sources")).resolve()
        db_path = Path(os.getenv("DB_PATH", "data/imo_index.db")).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return cls(
            bot_token=bot_token,
            sources_dir=sources_dir,
            db_path=db_path,
        )

