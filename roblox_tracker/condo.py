"""Condo group detection — flags users who belong to known condo groups."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path

from .api_client import RobloxClient, RobloxAPIError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  Data directory (shared with snapshot.py)
# ---------------------------------------------------------------------------
_DEFAULT_DATA_DIR = os.path.join(os.path.expanduser("~"), ".roblox_tracker")


def _data_dir() -> Path:
    d = Path(os.environ.get("ROBLOX_TRACKER_DATA", _DEFAULT_DATA_DIR))
    d.mkdir(parents=True, exist_ok=True)
    return d


_DISCOVERED_FILE = "discovered_condo_groups.json"

# Known condo group IDs (manually curated + cross-referenced from member overlap)
KNOWN_CONDO_GROUP_IDS: set[int] = {
    # ---- Original (manually added) ----
    35216426,    # Bunny Studio
    1018746,     # Goddess Stella
    1094217708,  # Superior Inferiority
    1029384,     # Bull Coffee
    5812000,     # Beauty of the Beasts
    6546926,     # Black Lives Mater
    1653,        # Bunnies
    297881562,   # Bunny Mart
    35931858,    # The Great British Bake Off

    # ---- Discovered via member-overlap research (overlap count / 84 sampled) ----
    # 35+ overlapping members
    557719733,   # -Spade Kingdom-          (35/84)
    # 20+ overlapping members
    16772560,    # 'descending              (22/84)
    35785938,    # QOH hub                  (22/84)
    # 15-19 overlapping members
    1035713,     # :Legos                   (18/84)
    139707350,   # BR4TH4V3N               (18/84)
    35824430,    # [ Content Deleted ]      (17/84)
    120078543,   # #BLACKLIVESMATTER >:3    (15/84)
    35934502,    # Club of brooks           (15/84)
    437446803,   # vals homeless shelter    (15/84)
    # 10-14 overlapping members
    33821543,    # [PARADISE OF HORSE]      (14/84)
    6639453,     # #BlackLivesMatter#       (14/84)
    213308234,   # Church Of The Beast!     (14/84)
    13271776,    # AxolotlCookie            (13/84)
    16410374,    # Strong Bull Studios      (12/84)
    6488944,     # #BLACKLIVESMATTER!!!     (12/84)
    20750,       # Horse lovers!!!!         (12/84)
    33508385,    # #YIH                     (12/84)
    32406321,    # 'pawchii                 (12/84)
    656706450,   # slop dungeon             (10/84)
    35509013,    # Abyssal Paradise         (10/84)
    17379511,    # ! p a w z               (10/84)
    10096972,    # afterschooI              (10/84)
    # 7-9 overlapping members
    4810700,     # The Queen Studios        (9/84)
    35969048,    # 'happy place             (9/84)
    35328440,    # Goat Conz                (9/84)
    7424914,     # backalley                (8/84)
    754202805,   # QOH Studios              (8/84)
    35310876,    # _ - ; aced ; - _         (8/84)
    911816,      # [THE NWO]                (7/84)
    36023557,    # cryt's humble abode      (7/84)
    33849843,    # [ Content Deleted ]      (7/84)
    # 5-6 overlapping members
    5636665,     # . . . --                 (6/84)
    35994866,    # 'bwisness                (6/84)
    34816688,    # 'sweetheartt             (6/84)
    226283782,   # easysword                (6/84)
    7953154,     # - $ Drip dolls -         (5/84)
    16120327,    # _ - Pawshie Avatar Ranking - _  (5/84)
    859619644,   # Mysterious Spades        (5/84)
    16167671,    # !Preschool Club!         (5/84)
    14823046,    # - Barbie Boutique -      (5/84)
    211037341,   # 4fun's place official    (5/84)
    8147373,     # FGC - Store              (5/84)
    1004148644,  # Alisas fandom            (5/84)
    438093681,   # Superior Inferiority (alt) (5/84)
}

# ---------------------------------------------------------------------------
#  Keyword-based auto-flagging
#
#  Each rule is (pattern, fields_to_check, label) where:
#   - pattern:  compiled regex (case-insensitive, word-boundary aware)
#   - fields:   set of field names to test — "name" and/or "description"
#   - label:    human-readable reason string shown in the UI
# ---------------------------------------------------------------------------
_FLAG_RULES: list[tuple[re.Pattern, set[str], str]] = [
    # "bbc" — in name, description, or thumbnail text (thumbnail checked separately)
    (re.compile(r"\bbbc\b", re.IGNORECASE),
     {"name", "description"}, "keyword 'bbc'"),

    # "bunny" — in name or description
    (re.compile(r"\bbunny\b", re.IGNORECASE),
     {"name", "description"}, "keyword 'bunny'"),
    (re.compile(r"\bbunnies\b", re.IGNORECASE),
     {"name", "description"}, "keyword 'bunnies'"),

    # "brat" — in name or description
    (re.compile(r"\bbrat\b", re.IGNORECASE),
     {"name", "description"}, "keyword 'brat'"),
    (re.compile(r"\bbrats\b", re.IGNORECASE),
     {"name", "description"}, "keyword 'brats'"),

    # "babysitter" / "babysitting" — in name or description
    (re.compile(r"\bbabysit(?:ter|ting|ters)?\b", re.IGNORECASE),
     {"name", "description"}, "keyword 'babysitter'"),

    # legacy — "blm" in description
    (re.compile(r"\bblm\b", re.IGNORECASE),
     {"description"}, "keyword 'blm'"),
]


def _check_keyword_flags(name: str, description: str) -> list[str]:
    """Return a list of human-readable reason strings for every matching rule."""
    fields = {"name": name, "description": description}
    hits: list[str] = []
    seen_labels: set[str] = set()
    for pattern, check_fields, label in _FLAG_RULES:
        if label in seen_labels:
            continue
        for field_name in check_fields:
            text = fields.get(field_name, "")
            if text and pattern.search(text):
                match_field = f"in {field_name}"
                hits.append(f"{label} ({match_field})")
                seen_labels.add(label)
                break
    return hits


def check_condo_groups(groups: list[dict]) -> list[dict]:
    """Check a user's groups for condo indicators.

    *groups* is the raw list from ``RobloxClient.get_user_groups()`` —
    each entry has ``group`` and ``role`` dicts.

    Returns a list of dicts describing each flagged group::

        {"group_id": ..., "name": ..., "reason": "known_id" | "keyword ..."}
    """
    all_known = get_all_condo_ids()
    discovered = load_discovered_groups()

    flagged: list[dict] = []
    for entry in groups:
        group = entry.get("group") or {}
        gid = group.get("id", 0)
        name = group.get("name", "Unknown")
        description = group.get("description", "")

        reasons: list[str] = []
        if gid in KNOWN_CONDO_GROUP_IDS:
            reasons.append("known_id")
        if gid in discovered:
            info = discovered[gid]
            reasons.append(f"auto-discovered (overlap: {info.get('overlap', '?')})")
        reasons.extend(_check_keyword_flags(name, description))

        if reasons:
            flagged.append({
                "group_id": gid,
                "name": name,
                "role": (entry.get("role") or {}).get("name", ""),
                "reason": ", ".join(reasons),
                "description_snippet": description[:120],
            })

    return flagged


# ---------------------------------------------------------------------------
#  Discovered groups — persisted to JSON on disk
# ---------------------------------------------------------------------------

def load_discovered_groups() -> dict[int, dict]:
    """Load auto-discovered condo group IDs from disk.

    Returns {group_id: {"name": ..., "overlap": ..., "discovered_at": ...}}
    """
    path = _data_dir() / _DISCOVERED_FILE
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return {int(k): v for k, v in data.items()}
    except Exception:
        return {}


def save_discovered_groups(groups: dict[int, dict]) -> None:
    """Persist auto-discovered condo group IDs to disk."""
    path = _data_dir() / _DISCOVERED_FILE
    path.write_text(json.dumps(
        {str(k): v for k, v in groups.items()}, indent=2))


def get_all_condo_ids() -> set[int]:
    """Return the union of hardcoded + auto-discovered condo group IDs."""
    return KNOWN_CONDO_GROUP_IDS | set(load_discovered_groups().keys())


# ---------------------------------------------------------------------------
#  Automatic condo group discovery via member-overlap analysis
# ---------------------------------------------------------------------------

# Minimum overlap count to auto-flag a group
_MIN_OVERLAP = 3
# Maximum group member-count — huge groups (>500k) are likely legit
_MAX_MEMBER_COUNT = 500_000
# How many members to sample per group
_SAMPLE_SIZE = 15


def discover_condo_groups(
    client: RobloxClient | None = None,
    min_overlap: int = _MIN_OVERLAP,
    max_member_count: int = _MAX_MEMBER_COUNT,
    sample_size: int = _SAMPLE_SIZE,
) -> dict[int, dict]:
    """Scan members of known condo groups to discover new ones.

    For each known condo group, samples members and checks their other
    group memberships. Groups appearing in *min_overlap* or more
    condo-member profiles (and with <= *max_member_count* members) are
    flagged as newly discovered condo groups.

    Returns the *newly added* groups (also persists them to disk).
    """
    if client is None:
        client = RobloxClient()

    seed_ids = get_all_condo_ids()
    logger.info("Condo discovery: starting with %d seed groups", len(seed_ids))

    # {group_id: {"name", "description", "memberCount", "users": set}}
    overlap_tracker: dict[int, dict] = {}
    sampled_users: set[int] = set()

    for gid in sorted(seed_ids):
        members = _fetch_group_members(client, gid, max_members=sample_size)
        for uid in members:
            if uid in sampled_users:
                continue
            sampled_users.add(uid)

            try:
                user_groups = client.get_user_groups(uid)
            except RobloxAPIError:
                continue
            time.sleep(0.4)

            for entry in user_groups:
                g = entry.get("group") or {}
                ugid = g.get("id", 0)
                if ugid in seed_ids:
                    continue

                if ugid not in overlap_tracker:
                    overlap_tracker[ugid] = {
                        "name": g.get("name", ""),
                        "description": g.get("description", ""),
                        "memberCount": g.get("memberCount", 0),
                        "users": set(),
                    }
                overlap_tracker[ugid]["users"].add(uid)

    total_sampled = len(sampled_users)
    logger.info("Condo discovery: sampled %d users, found %d candidate groups",
                total_sampled, len(overlap_tracker))

    # Filter: must meet minimum overlap AND not be a mega-group
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    existing = load_discovered_groups()
    newly_added: dict[int, dict] = {}

    for ugid, info in overlap_tracker.items():
        n_users = len(info["users"])
        member_count = info.get("memberCount", 0)
        if n_users >= min_overlap and member_count <= max_member_count:
            entry = {
                "name": info["name"],
                "overlap": n_users,
                "total_sampled": total_sampled,
                "member_count": member_count,
                "discovered_at": now,
            }
            if ugid not in existing:
                newly_added[ugid] = entry
            existing[ugid] = entry

    save_discovered_groups(existing)
    logger.info("Condo discovery: %d new groups added (%d total discovered on disk)",
                len(newly_added), len(existing))
    return newly_added


def _fetch_group_members(client: RobloxClient, group_id: int,
                         max_members: int = 15) -> list[int]:
    """Fetch up to *max_members* user IDs from a group."""
    members: list[int] = []
    url = f"https://groups.roblox.com/v1/groups/{int(group_id)}/users"
    cursor = None
    while len(members) < max_members:
        params: dict = {"limit": 25, "sortOrder": "Desc"}
        if cursor:
            params["cursor"] = cursor
        try:
            data = client._get(url, params=params)
        except RobloxAPIError:
            break
        for item in data.get("data", []):
            uid = (item.get("user") or {}).get("userId")
            if uid:
                members.append(uid)
        cursor = data.get("nextPageCursor")
        if not cursor:
            break
        time.sleep(0.5)
    return members[:max_members]
