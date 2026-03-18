"""Tracks friends of a Roblox user."""

from __future__ import annotations

from dataclasses import dataclass

from .api_client import RobloxClient

_PRESENCE_LABELS = {
    0: "Offline",
    1: "Online",
    2: "In Game",
    3: "In Studio",
}


@dataclass
class FriendRecord:
    user_id: int
    username: str
    display_name: str
    is_online: bool = False
    presence_type: int = 0  # 0=offline 1=website 2=in-game 3=in-studio
    last_location: str = ""
    created: str = ""  # when the friendship was established (if available)

    @property
    def presence_label(self) -> str:
        return _PRESENCE_LABELS.get(self.presence_type, "Offline")

    def summary_line(self) -> str:
        return f"  {self.display_name} (@{self.username})  [{self.presence_label}]"


def fetch_friends(client: RobloxClient, user_id: int) -> list[FriendRecord]:
    """Return the full friends list for a user, enriched with real
    usernames (bulk user API) and live presence data."""
    raw = client.get_friends(user_id)
    if not raw:
        return []

    friend_ids = [f.get("id", 0) for f in raw if f.get("id")]

    # Bulk-fetch real usernames (friends endpoint often returns empty names)
    user_info = client.get_bulk_user_info(friend_ids)

    # Fetch live presence
    presences = client.get_user_presences(friend_ids)

    friends: list[FriendRecord] = []
    for f in raw:
        fid = f.get("id", 0)
        info = user_info.get(fid, {})
        pres = presences.get(fid, {})
        presence_type = pres.get("userPresenceType", 0)

        username = info.get("name") or f.get("name") or "Unknown"
        display_name = info.get("displayName") or f.get("displayName") or username

        friends.append(FriendRecord(
            user_id=fid,
            username=username,
            display_name=display_name,
            is_online=presence_type > 0,
            presence_type=presence_type,
            last_location=pres.get("lastLocation", ""),
            created=f.get("created", ""),
        ))

    # Sort: online users first
    friends.sort(key=lambda fr: (fr.presence_type == 0, fr.display_name.lower()))
    return friends
