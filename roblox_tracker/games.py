"""Tracks games (experiences) a Roblox user has created or played."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .api_client import RobloxClient, RobloxAPIError


@dataclass
class GameRecord:
    universe_id: int
    name: str
    place_id: int | None = None
    creator_name: str = ""
    playing: int = 0
    visits: int = 0
    max_players: int = 0
    created: str = ""
    updated: str = ""
    source: str = ""  # "created", "badge", or "favorite"
    badge_count: int = 0  # how many badges earned in this game
    hours_played: float = 0.0
    thumbnail_url: str = ""

    def summary_line(self) -> str:
        return (
            f"  [{self.source:7s}] {self.name}  "
            f"(visits: {self.visits:,}  playing: {self.playing:,})"
        )


def _extract_hours_played(payload: dict) -> float:
    """Best-effort extract of per-user playtime hours from API payloads."""
    for key in (
        "hoursPlayed",
        "hours_played",
        "playTimeHours",
        "playtimeHours",
        "playTime",
        "playtime",
        "userPlayTimeHours",
    ):
        value = payload.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def fetch_created_games(client: RobloxClient, user_id: int) -> list[GameRecord]:
    """Return games the user created."""
    try:
        raw = client.get_user_games(user_id)
    except RobloxAPIError:
        return []
    records: list[GameRecord] = []
    for g in raw:
        records.append(GameRecord(
            universe_id=g.get("id", 0),
            name=g.get("name", "Unknown"),
            place_id=g.get("rootPlaceId"),
            creator_name=g.get("creator", {}).get("name", ""),
            playing=g.get("playing") or 0,
            visits=g.get("visits") or 0,
            max_players=g.get("maxPlayers") or 0,
            created=g.get("created", ""),
            updated=g.get("updated", ""),
            source="created",
            hours_played=_extract_hours_played(g),
        ))
    return records


def fetch_played_games_via_badges(client: RobloxClient,
                                   user_id: int) -> tuple[list[GameRecord], dict[int, int]]:
    """Infer games played from badge awards. Returns (records, badge_counts_by_universe)."""
    try:
        badges = client.get_user_badges(user_id)
    except RobloxAPIError:
        return [], {}

    # Badges reference Place IDs in awarder.id, not Universe IDs.
    # Collect unique place IDs and convert them.
    place_ids_set: set[int] = set()
    badge_counts_by_place: dict[int, int] = {}

    for b in badges:
        awarder = b.get("awarder", {})
        pid = awarder.get("id")
        if pid:
            badge_counts_by_place[pid] = badge_counts_by_place.get(pid, 0) + 1
            place_ids_set.add(pid)

    if not place_ids_set:
        return [], {}

    # Convert place IDs → universe IDs
    place_to_universe = client.place_ids_to_universe_ids(list(place_ids_set))

    # Build badge counts keyed by universe ID
    badge_counts: dict[int, int] = {}
    for pid, count in badge_counts_by_place.items():
        uid = place_to_universe.get(pid)
        if uid:
            badge_counts[uid] = badge_counts.get(uid, 0) + count

    universe_ids = list(set(place_to_universe.values()))
    if not universe_ids:
        return [], badge_counts

    # Fetch details in chunks of 100
    records: list[GameRecord] = []
    details = client.get_game_details(universe_ids)
    for d in details:
        uid = d.get("id", 0)
        records.append(GameRecord(
            universe_id=uid,
            name=d.get("name", "Unknown"),
            place_id=d.get("rootPlaceId"),
            creator_name=d.get("creator", {}).get("name", ""),
            playing=d.get("playing") or 0,
            visits=d.get("visits") or 0,
            max_players=d.get("maxPlayers") or 0,
            created=d.get("created", ""),
            updated=d.get("updated", ""),
            source="badge",
            badge_count=badge_counts.get(uid) or 0,
            hours_played=_extract_hours_played(d),
        ))
    return records, badge_counts


def fetch_favorite_games(client: RobloxClient, user_id: int) -> list[GameRecord]:
    """Return games the user has favorited."""
    try:
        raw = client.get_favorite_games(user_id)
    except RobloxAPIError:
        return []
    records: list[GameRecord] = []
    for g in raw:
        records.append(GameRecord(
            universe_id=g.get("id", 0),
            name=g.get("name", "Unknown"),
            place_id=(g.get("rootPlace") or {}).get("id"),
            creator_name=(g.get("creator") or {}).get("name", ""),
            playing=0,
            visits=g.get("placeVisits") or 0,
            max_players=0,
            created=g.get("created", ""),
            updated=g.get("updated", ""),
            source="favorite",
            hours_played=_extract_hours_played(g),
        ))
    return records


def fetch_all_games(client: RobloxClient, user_id: int) -> list[GameRecord]:
    """Return created, badge-inferred, and favorited games, de-duplicated.
    Also attaches thumbnails and per-game badge counts."""
    created = fetch_created_games(client, user_id)
    played, badge_counts = fetch_played_games_via_badges(client, user_id)
    favorites = fetch_favorite_games(client, user_id)

    seen: dict[int, GameRecord] = {}
    for g in created:
        g.badge_count = badge_counts.get(g.universe_id, 0)
        seen[g.universe_id] = g
    for g in played:
        if g.universe_id not in seen:
            seen[g.universe_id] = g
        else:
            seen[g.universe_id].badge_count = max(
                seen[g.universe_id].badge_count, g.badge_count)
    for g in favorites:
        if g.universe_id not in seen:
            g.badge_count = badge_counts.get(g.universe_id, 0)
            seen[g.universe_id] = g
        else:
            # Mark as also-favorited
            existing = seen[g.universe_id]
            if existing.source != "favorite":
                existing.source = existing.source + "+fav"

    combined = list(seen.values())

    # Fetch thumbnails
    universe_ids = [g.universe_id for g in combined if g.universe_id]
    if universe_ids:
        try:
            thumbs = client.get_game_thumbnails(universe_ids)
            for g in combined:
                g.thumbnail_url = thumbs.get(g.universe_id, "")
        except RobloxAPIError:
            pass

    return combined

    return combined
