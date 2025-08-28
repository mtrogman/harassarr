from __future__ import annotations
from typing import Any, Dict

# Backcompat shim for Pydantic v1/v2
try:
    from pydantic import BaseModel, Field, EmailStr, ConfigDict  # v2
    _V2 = True
except Exception:  # pydantic v1
    from pydantic import BaseModel, Field, EmailStr  # type: ignore
    ConfigDict = None  # type: ignore
    _V2 = False


class DiscordSettings(BaseModel):
    token: str = Field(..., description="Discord bot token")


class DatabaseSettings(BaseModel):
    host: str
    port: int
    database: str
    user: str
    password: str


class LogSettings(BaseModel):
    retention: int = 90


class Settings(BaseModel):
    # In v2 use model_config; in v1 use inner Config
    if _V2:
        model_config = ConfigDict(extra="allow")  # type: ignore
    else:
        class Config:  # type: ignore
            extra = "allow"

    database: DatabaseSettings
    discord: DiscordSettings
    log: LogSettings = LogSettings()
    # NOTE: All other keys (including PLEX-* and "1080p"/"4k") are allowed and passed through.


def validate_config(raw: Dict[str, Any]) -> Settings:
    """
    Validate core sections of config.yml and allow all extras unchanged.
    """
    return Settings(**raw)
