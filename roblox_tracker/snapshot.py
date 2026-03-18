"""Snapshot & diff engine — saves state to JSON and reports changes."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .friends import FriendRecord
from .games import GameRecord

_DEFAULT_DATA_DIR = os.path.join(os.path.expanduser("~"), ".roblox_tracker")


def _data_dir() -> Path:
    d = Path(os.environ.get("ROBLOX_TRACKER_DATA", _DEFAULT_DATA_DIR))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _snapshot_path(user_id: int, kind: str) -> Path:
    return _data_dir() / f"{user_id}_{kind}.json"


# ------------------------------------------------------------------ #
#  Serialization helpers
# ------------------------------------------------------------------ #

def _games_to_dicts(games: list[GameRecord]) -> list[dict]:
    return [
        {"universe_id": g.universe_id, "name": g.name, "place_id": g.place_id,
         "creator_name": g.creator_name, "visits": g.visits,
         "playing": g.playing, "source": g.source}
        for g in games
    ]


def _friends_to_dicts(friends: list[FriendRecord]) -> list[dict]:
    return [
        {"user_id": f.user_id, "username": f.username,
         "display_name": f.display_name, "is_online": f.is_online}
        for f in friends
    ]


def _groups_to_dicts(groups: list[dict]) -> list[dict]:
    return [
        {"group_id": (entry.get("group") or {}).get("id", 0),
         "name": (entry.get("group") or {}).get("name", "Unknown"),
         "role": (entry.get("role") or {}).get("name", ""),
         "member_count": (entry.get("group") or {}).get("memberCount", 0)}
        for entry in groups
    ]


# ------------------------------------------------------------------ #
#  Save / Load
# ------------------------------------------------------------------ #

def save_snapshot(user_id: int, *,
                  games: list[GameRecord] | None = None,
                  friends: list[FriendRecord] | None = None,
                  groups: list[dict] | None = None) -> Path:
    """Persist current state to disk and return the data directory path."""
    ts = datetime.now(timezone.utc).isoformat()
    if games is not None:
        path = _snapshot_path(user_id, "games")
        payload = {"timestamp": ts, "data": _games_to_dicts(games)}
        path.write_text(json.dumps(payload, indent=2))
    if friends is not None:
        path = _snapshot_path(user_id, "friends")
        payload = {"timestamp": ts, "data": _friends_to_dicts(friends)}
        path.write_text(json.dumps(payload, indent=2))
    if groups is not None:
        path = _snapshot_path(user_id, "groups")
        payload = {"timestamp": ts, "data": _groups_to_dicts(groups)}
        path.write_text(json.dumps(payload, indent=2))
    return _data_dir()


def _load_snapshot(user_id: int, kind: str) -> tuple[str, list[dict]]:
    path = _snapshot_path(user_id, kind)
    if not path.exists():
        return "", []
    blob = json.loads(path.read_text())
    return blob.get("timestamp", ""), blob.get("data", [])


# ------------------------------------------------------------------ #
#  Diff
# ------------------------------------------------------------------ #

def diff_games(user_id: int, current: list[GameRecord]) -> dict:
    """Compare current games against the last snapshot."""
    old_ts, old_data = _load_snapshot(user_id, "games")
    if not old_data:
        return {"previous_snapshot": None, "added": [], "removed": []}

    old_ids = {g["universe_id"] for g in old_data}
    new_ids = {g.universe_id for g in current}

    added = [g for g in current if g.universe_id not in old_ids]
    removed = [g for g in old_data if g["universe_id"] not in new_ids]

    return {
        "previous_snapshot": old_ts,
        "added": added,
        "removed": removed,
    }


def diff_friends(user_id: int, current: list[FriendRecord]) -> dict:
    """Compare current friends against the last snapshot."""
    old_ts, old_data = _load_snapshot(user_id, "friends")
    if not old_data:
        return {"previous_snapshot": None, "added": [], "removed": []}

    old_ids = {f["user_id"] for f in old_data}
    new_ids = {f.user_id for f in current}

    added = [f for f in current if f.user_id not in old_ids]
    removed = [f for f in old_data if f["user_id"] not in new_ids]

    return {
        "previous_snapshot": old_ts,
        "added": added,
        "removed": removed,
    }


def diff_groups(user_id: int, current: list[dict]) -> dict:
    """Compare current groups against the last snapshot."""
    old_ts, old_data = _load_snapshot(user_id, "groups")
    if not old_data:
        return {"previous_snapshot": None, "added": [], "removed": []}

    current_dicts = _groups_to_dicts(current)
    old_ids = {g["group_id"] for g in old_data}
    new_ids = {g["group_id"] for g in current_dicts}

    added = [g for g in current_dicts if g["group_id"] not in old_ids]
    removed = [g for g in old_data if g["group_id"] not in new_ids]

    return {
        "previous_snapshot": old_ts,
        "added": added,
        "removed": removed,
    }


def get_past_groups(user_id: int, current: list[dict]) -> list[dict]:
    """Return groups from the snapshot that the user is no longer in."""
    _, old_data = _load_snapshot(user_id, "groups")
    if not old_data:
        return []
    current_ids = {(entry.get("group") or {}).get("id", 0) for entry in current}
    return [g for g in old_data if g["group_id"] not in current_ids]
