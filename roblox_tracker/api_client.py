"""Roblox API client — wraps the public Roblox web APIs."""

import time
from typing import Any
from urllib.parse import quote

import requests

# Public Roblox API base URLs
_USERS_API = "https://users.roblox.com"
_FRIENDS_API = "https://friends.roblox.com"
_GAMES_API = "https://games.roblox.com"
_GROUPS_API = "https://groups.roblox.com"
_THUMBNAILS_API = "https://thumbnails.roblox.com"

# Respect rate-limits: wait between paginated requests
_PAGE_DELAY = 0.5  # seconds
_GET_MAX_RETRIES = 5
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class RobloxAPIError(Exception):
    """Raised when a Roblox API call fails."""


class RobloxClient:
    """Lightweight wrapper around the public Roblox REST APIs."""

    def __init__(self, timeout: int = 15):
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
        })
        self._timeout = timeout

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #
    def _get(self, url: str, params: dict | None = None) -> Any:
        last_error: Exception | None = None

        for attempt in range(_GET_MAX_RETRIES + 1):
            try:
                resp = self._session.get(url, params=params, timeout=self._timeout)
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= _GET_MAX_RETRIES:
                    break
                time.sleep(min(0.5 * (2 ** attempt), 8.0))
                continue

            if resp.status_code in _RETRYABLE_STATUS_CODES and attempt < _GET_MAX_RETRIES:
                retry_after = resp.headers.get("Retry-After")
                delay: float | None = None
                if retry_after:
                    try:
                        delay = max(0.0, float(retry_after))
                    except ValueError:
                        delay = None
                if delay is None:
                    delay = min(0.6 * (2 ** attempt), 10.0)
                time.sleep(delay)
                continue

            try:
                resp.raise_for_status()
                return resp.json()
            except ValueError as exc:
                raise RobloxAPIError(f"Invalid JSON response from {url}") from exc
            except requests.RequestException as exc:
                raise RobloxAPIError(f"Request to {url} failed: {exc}") from exc

        if last_error is not None:
            raise RobloxAPIError(f"Request to {url} failed after retries: {last_error}") from last_error
        raise RobloxAPIError(
            f"Request to {url} failed after retries due to rate limiting or transient server errors"
        )

    def _get_paginated(self, url: str, params: dict | None = None,
                       limit: int = 100, max_pages: int = 50) -> list[dict]:
        """Follow Roblox cursor-based pagination and return all items."""
        params = dict(params or {})
        params.setdefault("limit", min(limit, 100))
        results: list[dict] = []
        cursor: str | None = None

        for _ in range(max_pages):
            if cursor:
                params["cursor"] = cursor
            data = self._get(url, params)
            results.extend(data.get("data", []))
            cursor = data.get("nextPageCursor")
            if not cursor:
                break
            time.sleep(_PAGE_DELAY)

        return results

    # ------------------------------------------------------------------ #
    #  User look-up
    # ------------------------------------------------------------------ #
    def get_user_id(self, username: str) -> int:
        """Resolve a Roblox username to a user ID."""
        url = f"{_USERS_API}/v1/usernames/users"
        try:
            data = self._session.post(
                url,
                json={"usernames": [username], "excludeBannedUsers": False},
                timeout=self._timeout,
            )
            data.raise_for_status()
            body = data.json()
        except ValueError as exc:
            raise RobloxAPIError("Received an invalid response while resolving the username") from exc
        except requests.RequestException as exc:
            raise RobloxAPIError(f"Unable to resolve username '{username}': {exc}") from exc

        entries = body.get("data", [])
        if not entries:
            raise RobloxAPIError(f"User '{username}' not found")
        return entries[0]["id"]

    def get_user_info(self, user_id: int) -> dict:
        """Return profile information for a user ID."""
        return self._get(f"{_USERS_API}/v1/users/{int(user_id)}")

    # ------------------------------------------------------------------ #
    #  Friends
    # ------------------------------------------------------------------ #
    def get_friends(self, user_id: int) -> list[dict]:
        """Return the full friends list for a user."""
        url = f"{_FRIENDS_API}/v1/users/{int(user_id)}/friends"
        data = self._get(url)
        return data.get("data", [])

    def get_friends_count(self, user_id: int) -> int:
        url = f"{_FRIENDS_API}/v1/users/{int(user_id)}/friends/count"
        return self._get(url).get("count", 0)

    def get_bulk_user_info(self, user_ids: list[int]) -> dict[int, dict]:
        """Return {user_id: {name, displayName}} for up to 100 users at a time."""
        result: dict[int, dict] = {}
        for i in range(0, len(user_ids), 100):
            chunk = user_ids[i:i + 100]
            try:
                resp = self._session.post(
                    f"{_USERS_API}/v1/users",
                    json={"userIds": chunk, "excludeBannedUsers": False},
                    timeout=self._timeout,
                )
                resp.raise_for_status()
                for u in resp.json().get("data", []):
                    result[u["id"]] = u
            except requests.RequestException:
                pass
        return result

    def get_user_presences(self, user_ids: list[int]) -> dict[int, dict]:
        """Return {user_id: presence_dict} via the Presence API."""
        result: dict[int, dict] = {}
        for i in range(0, len(user_ids), 50):
            chunk = user_ids[i:i + 50]
            try:
                resp = self._session.post(
                    "https://presence.roblox.com/v1/presence/users",
                    json={"userIds": chunk},
                    timeout=self._timeout,
                )
                resp.raise_for_status()
                for p in resp.json().get("userPresences", []):
                    result[p["userId"]] = p
            except requests.RequestException:
                pass
        return result

    # ------------------------------------------------------------------ #
    #  Groups
    # ------------------------------------------------------------------ #
    def get_user_groups(self, user_id: int) -> list[dict]:
        """Return groups the user belongs to (with role info)."""
        url = f"{_GROUPS_API}/v2/users/{int(user_id)}/groups/roles"
        data = self._get(url)
        return data.get("data", [])

    # ------------------------------------------------------------------ #
    #  Games / Experiences
    # ------------------------------------------------------------------ #
    def get_user_games(self, user_id: int) -> list[dict]:
        """Return games (experiences) created by the user."""
        url = f"{_GAMES_API}/v2/users/{int(user_id)}/games"
        return self._get_paginated(url, params={"sortOrder": "Desc"})

    def get_game_details(self, universe_ids: list[int]) -> list[dict]:
        """Return details for one or more universe IDs."""
        if not universe_ids:
            return []
        results: list[dict] = []
        for i in range(0, len(universe_ids), 100):
            chunk = universe_ids[i:i + 100]
            ids_str = ",".join(str(int(uid)) for uid in chunk)
            url = f"{_GAMES_API}/v1/games"
            data = self._get(url, params={"universeIds": ids_str})
            results.extend(data.get("data", []))
        return results

    def get_public_servers(self, place_id: int, max_pages: int = 200,
                           limit: int = 100) -> list[dict]:
        """Return all public servers for a place ID.

        Roblox uses cursor pagination for servers. We iterate until there is
        no next cursor or *max_pages* is reached.
        """
        url = f"{_GAMES_API}/v1/games/{int(place_id)}/servers/Public"
        params: dict[str, Any] = {
            "limit": min(max(10, int(limit)), 100),
            "sortOrder": "Asc",
        }
        results: list[dict] = []
        cursor: str | None = None

        for _ in range(max_pages):
            if cursor:
                params["cursor"] = cursor
            data = self._get(url, params=params)
            results.extend(data.get("data", []))
            cursor = data.get("nextPageCursor")
            if not cursor:
                break
            # Keep full-server scans responsive while still being polite.
            time.sleep(0.1)

        return results

    def place_ids_to_universe_ids(self, place_ids: list[int]) -> dict[int, int]:
        """Convert place IDs to universe IDs. Returns {place_id: universe_id}."""
        result: dict[int, int] = {}
        for pid in place_ids:
            try:
                url = f"https://apis.roblox.com/universes/v1/places/{int(pid)}/universe"
                data = self._get(url)
                uid = data.get("universeId")
                if uid:
                    result[pid] = uid
            except RobloxAPIError:
                continue
            time.sleep(0.1)  # light rate-limit
        return result

    def get_favorite_games(self, user_id: int) -> list[dict]:
        """Return games the user has favorited."""
        url = f"{_GAMES_API}/v2/users/{int(user_id)}/favorite/games"
        return self._get_paginated(url, params={"sortOrder": "Desc"})

    def get_game_thumbnails(self, universe_ids: list[int],
                            size: str = "150x150") -> dict[int, str]:
        """Return {universe_id: image_url} for the given games."""
        if not universe_ids:
            return {}
        result: dict[int, str] = {}
        for i in range(0, len(universe_ids), 100):
            chunk = universe_ids[i:i + 100]
            ids_str = ",".join(str(int(uid)) for uid in chunk)
            url = f"{_THUMBNAILS_API}/v1/games/icons"
            data = self._get(url, params={
                "universeIds": ids_str,
                "returnPolicy": "PlaceHolder",
                "size": size,
                "format": "Png",
                "isCircular": "false",
            })
            for item in data.get("data", []):
                if item.get("imageUrl"):
                    result[item["targetId"]] = item["imageUrl"]
        return result

    # ------------------------------------------------------------------ #
    #  User avatar / headshot
    # ------------------------------------------------------------------ #
    def get_user_headshot(self, user_id: int, size: str = "150x150") -> str:
        """Return the headshot thumbnail URL for a user."""
        url = f"{_THUMBNAILS_API}/v1/users/avatar-headshot"
        data = self._get(url, params={
            "userIds": str(int(user_id)),
            "size": size,
            "format": "Png",
            "isCircular": "true",
        })
        for item in data.get("data", []):
            if item.get("imageUrl"):
                return item["imageUrl"]
        return ""

    # ------------------------------------------------------------------ #
    #  Badge / recent game activity (public badges proxy)
    # ------------------------------------------------------------------ #
    def get_user_badges(self, user_id: int, max_pages: int = 10) -> list[dict]:
        """Return badges earned by the user — used to infer games played."""
        url = f"https://badges.roblox.com/v1/users/{int(user_id)}/badges"
        return self._get_paginated(url, params={"sortOrder": "Desc"},
                                   max_pages=max_pages)
