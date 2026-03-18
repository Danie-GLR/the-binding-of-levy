"""Discord user lookup helpers for mutual server discovery."""

from __future__ import annotations

import os
import re
import time
from urllib.parse import urlencode
from dataclasses import dataclass

import requests

_DISCORD_API = "https://discord.com/api/v10"
_DISCORD_CDN = "https://cdn.discordapp.com"
_USER_ID_PATTERN = re.compile(r"(?:<@!?(\d+)>|\D*(\d{5,})\D*)")


class DiscordAPIError(Exception):
    """Raised when a Discord API request fails or config is missing."""


@dataclass
class DiscordUserRecord:
    user_id: int
    username: str
    global_name: str = ""
    discriminator: str = ""
    avatar_url: str = ""
    banner_url: str = ""

    @property
    def display_name(self) -> str:
        return self.global_name or self.username

    @property
    def tag(self) -> str:
        if self.discriminator and self.discriminator != "0":
            return f"{self.username}#{self.discriminator}"
        return self.username


@dataclass
class DiscordGuildRecord:
    guild_id: int
    name: str
    icon_url: str = ""
    nickname: str = ""
    joined_at: str = ""
    owner: bool = False


def parse_discord_user_id(raw_value: str) -> int:
    """Parse a Discord user ID from raw input or a mention."""
    value = (raw_value or "").strip()
    if not value:
        raise DiscordAPIError("Enter a Discord user ID or mention.")
    if value.isdigit():
        return int(value)

    match = _USER_ID_PATTERN.fullmatch(value)
    if not match:
        raise DiscordAPIError("Discord lookups require a user ID or mention like <@123>." )
    user_id = match.group(1) or match.group(2)
    return int(user_id)


class DiscordClient:
    """Small Discord REST client for user and mutual guild lookups."""

    def __init__(self, token: str | None = None, timeout: int = 15):
        self._token = (token or os.environ.get("DISCORD_BOT_TOKEN", "")).strip()
        if not self._token:
            raise DiscordAPIError(
                "Discord lookup is not configured. Set DISCORD_BOT_TOKEN first."
            )

        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "Authorization": f"Bot {self._token}",
            "User-Agent": "roblox-tracker/1.0",
        })
        self._timeout = timeout

    @staticmethod
    def is_configured() -> bool:
        return bool(os.environ.get("DISCORD_BOT_TOKEN", "").strip())

    @staticmethod
    def get_application_id_from_env() -> int:
        raw = os.environ.get("DISCORD_APPLICATION_ID", "").strip()
        return int(raw) if raw.isdigit() else 0

    def _request(self, method: str, path: str,
                 *, params: dict | None = None,
                 json_body: dict | None = None,
                 expected: tuple[int, ...] = (200,)) -> dict | list:
        url = f"{_DISCORD_API}{path}"
        retries = 3
        while True:
            try:
                resp = self._session.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    timeout=self._timeout,
                )
            except requests.RequestException as exc:
                raise DiscordAPIError(f"Discord request failed: {exc}") from exc

            if resp.status_code == 429 and retries > 0:
                retry_after = resp.json().get("retry_after", 1)
                time.sleep(float(retry_after))
                retries -= 1
                continue

            if resp.status_code not in expected:
                if resp.status_code == 404:
                    raise DiscordAPIError("Discord user or server not found.")
                if resp.status_code == 403:
                    raise DiscordAPIError("Discord bot token is valid but missing access for this lookup.")
                if resp.status_code == 401:
                    raise DiscordAPIError("Discord bot token was rejected by the API.")
                try:
                    payload = resp.json()
                    message = payload.get("message", resp.text)
                except ValueError:
                    message = resp.text
                raise DiscordAPIError(f"Discord API error {resp.status_code}: {message}")

            if resp.status_code == 204:
                return {}

            try:
                return resp.json()
            except ValueError as exc:
                raise DiscordAPIError("Discord API returned invalid JSON.") from exc

    def _build_asset_url(self, asset_type: str, entity_id: int,
                         asset_hash: str | None, *, size: int = 256) -> str:
        if not asset_hash:
            return ""
        extension = "gif" if asset_hash.startswith("a_") else "png"
        return f"{_DISCORD_CDN}/{asset_type}/{entity_id}/{asset_hash}.{extension}?size={size}"

    def get_user(self, user_id: int) -> DiscordUserRecord:
        data = self._request("GET", f"/users/{int(user_id)}")
        return DiscordUserRecord(
            user_id=int(data["id"]),
            username=data.get("username", str(user_id)),
            global_name=data.get("global_name") or "",
            discriminator=data.get("discriminator") or "",
            avatar_url=self._build_asset_url("avatars", int(data["id"]), data.get("avatar")),
            banner_url=self._build_asset_url("banners", int(data["id"]), data.get("banner"), size=512),
        )

    def get_application_id(self) -> int:
        data = self._request("GET", "/oauth2/applications/@me")
        app = data.get("application") if isinstance(data, dict) else None
        app_id = (app or {}).get("id") or data.get("id")
        if not app_id:
            raise DiscordAPIError("Could not resolve Discord application ID.")
        return int(app_id)

    @staticmethod
    def build_bot_invite_url(application_id: int, permissions: int = 274877918208) -> str:
        """Build OAuth2 URL that prompts server selection for bot install."""
        query = urlencode({
            "client_id": int(application_id),
            "permissions": int(permissions),
            "scope": "bot applications.commands",
            "disable_guild_select": "false",
        })
        return f"https://discord.com/oauth2/authorize?{query}"

    def get_bot_guilds(self) -> list[dict]:
        guilds: list[dict] = []
        after = None
        while True:
            params = {"limit": 200}
            if after:
                params["after"] = after
            page = self._request("GET", "/users/@me/guilds", params=params)
            if not isinstance(page, list):
                raise DiscordAPIError("Unexpected response while listing Discord servers.")
            if not page:
                break
            guilds.extend(page)
            after = page[-1].get("id")
            if len(page) < 200:
                break
        return guilds

    def list_mutual_guilds(self, user_id: int) -> list[DiscordGuildRecord]:
        mutuals: list[DiscordGuildRecord] = []
        for guild in self.get_bot_guilds():
            guild_id = int(guild["id"])
            try:
                member = self._request(
                    "GET",
                    f"/guilds/{guild_id}/members/{int(user_id)}",
                    expected=(200, 404),
                )
            except DiscordAPIError as exc:
                if "not found" in str(exc).lower():
                    continue
                raise

            if not member or not isinstance(member, dict):
                continue

            mutuals.append(DiscordGuildRecord(
                guild_id=guild_id,
                name=guild.get("name", str(guild_id)),
                icon_url=self._build_asset_url("icons", guild_id, guild.get("icon")),
                nickname=member.get("nick") or "",
                joined_at=member.get("joined_at") or "",
                owner=bool(member.get("roles") == [] and member.get("premium_since") is None and guild.get("owner")),
            ))

            time.sleep(0.1)

        mutuals.sort(key=lambda guild: guild.name.lower())
        return mutuals

    def send_channel_message(self, channel_id: int, content: str) -> dict:
        """Send a plain text message to a Discord text channel."""
        text = (content or "").strip()
        if not text:
            raise DiscordAPIError("Cannot send an empty Discord message.")
        if len(text) > 2000:
            text = text[:1997] + "..."

        payload = {
            "content": text,
            "allowed_mentions": {"parse": []},
        }
        return self._request(
            "POST",
            f"/channels/{int(channel_id)}/messages",
            expected=(200, 201),
            json_body=payload,
        )