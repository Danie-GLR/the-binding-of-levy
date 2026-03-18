"""Persistent guild-level settings used by the Discord caption bot and web relay."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

_DEFAULT_DATA_DIR = os.path.join(os.path.expanduser("~"), ".roblox_tracker")


@dataclass
class GuildBotSettings:
    guild_id: int
    relay_channel_id: int = 0
    translation_enabled: bool = False
    translation_target: str = "en"
    caption_prefix: str = ""


def _data_dir() -> Path:
    data_dir = Path(os.environ.get("ROBLOX_TRACKER_DATA", _DEFAULT_DATA_DIR))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _settings_path() -> Path:
    return _data_dir() / "discord_bot_settings.json"


def _load_all() -> dict[str, dict]:
    path = _settings_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _save_all(data: dict[str, dict]) -> None:
    path = _settings_path()
    path.write_text(json.dumps(data, indent=2, sort_keys=True))


def get_guild_settings(guild_id: int) -> GuildBotSettings:
    all_settings = _load_all()
    raw = all_settings.get(str(int(guild_id)), {})
    return GuildBotSettings(
        guild_id=int(guild_id),
        relay_channel_id=int(raw.get("relay_channel_id", 0) or 0),
        translation_enabled=bool(raw.get("translation_enabled", False)),
        translation_target=str(raw.get("translation_target", "en") or "en"),
        caption_prefix=str(raw.get("caption_prefix", "") or ""),
    )


def save_guild_settings(settings: GuildBotSettings) -> GuildBotSettings:
    all_settings = _load_all()
    all_settings[str(int(settings.guild_id))] = asdict(settings)
    _save_all(all_settings)
    return settings
