"""Recover profile data from Wayback Machine archived snapshots."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import requests

_CDX_API = "http://web.archive.org/cdx/search/cdx"
_WEB_PREFIX = "http://web.archive.org/web"
_TIMEOUT = 25


@dataclass
class ArchivedProfile:
    """Data scraped from an archived Roblox profile page."""
    user_id: int
    username: str = ""
    snapshot_date: str = ""
    snapshot_url: str = ""
    friend_ids: list[int] = field(default_factory=list)
    game_place_ids: list[int] = field(default_factory=list)
    group_ids: list[int] = field(default_factory=list)


def _find_best_snapshot(user_id: int) -> tuple[str, str] | None:
    """Query Wayback CDX API for the best (most recent 200) snapshot.

    Returns (timestamp, original_url) or None.
    """
    url = f"{_CDX_API}"
    for original in (
        f"www.roblox.com/users/{user_id}/profile",
        f"roblox.com/users/{user_id}/profile",
    ):
        try:
            resp = requests.get(url, params={
                "url": original,
                "output": "json",
                "limit": 20,
                "filter": "statuscode:200",
                "fl": "timestamp,original",
            }, timeout=_TIMEOUT)
            if resp.status_code != 200 or not resp.text.strip():
                continue
            rows = resp.json()
            # First row is the header
            if len(rows) > 1:
                # Pick the most recent snapshot (last row)
                ts, orig = rows[-1]
                return ts, orig
        except Exception:
            continue
    return None


def _scrape_archived_page(timestamp: str, original_url: str,
                          user_id: int) -> ArchivedProfile:
    """Download an archived page and extract friend IDs, game place IDs,
    and group IDs with basic regex scraping."""
    wayback_url = f"{_WEB_PREFIX}/{timestamp}/{original_url}"
    profile = ArchivedProfile(
        user_id=user_id,
        snapshot_date=f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}",
        snapshot_url=wayback_url,
    )

    try:
        resp = requests.get(wayback_url, timeout=_TIMEOUT)
        if resp.status_code != 200:
            return profile
    except Exception:
        return profile

    text = resp.text

    # Username / display name
    # Modern layout: <h2>username</h2> or data attribute
    name_match = re.search(
        r'data-profileuserid="[^"]*"[^>]*data-profileusername="([^"]*)"', text)
    if not name_match:
        name_match = re.search(r'<h2[^>]*class="[^"]*profile-name[^"]*"[^>]*>([^<]+)', text)
    if not name_match:
        name_match = re.search(r'<h2>([^<]+)</h2>', text)
    if name_match:
        profile.username = name_match.group(1).strip()

    # Friend user IDs (modern + legacy URLs)
    friend_patterns = [
        r'/users/(\d+)/profile',
        r'/User\.aspx\?[Ii][Dd]=(\d+)',
    ]
    friend_ids: set[int] = set()
    for pat in friend_patterns:
        for m in re.finditer(pat, text):
            fid = int(m.group(1))
            if fid != user_id:
                friend_ids.add(fid)
    profile.friend_ids = sorted(friend_ids)

    # Game place IDs (modern + legacy)
    game_patterns = [
        r'/games/(\d+)/',
        r'/Place\.aspx\?[Ii][Dd]=(\d+)',
        r'data-placeid="(\d+)"',
    ]
    place_ids: set[int] = set()
    for pat in game_patterns:
        for m in re.finditer(pat, text):
            place_ids.add(int(m.group(1)))
    profile.game_place_ids = sorted(place_ids)

    # Group IDs
    group_patterns = [
        r'/groups/(\d+)/',
        r'/Group\.aspx\?[Gg]id=(\d+)',
        r'data-groupid="(\d+)"',
    ]
    group_ids: set[int] = set()
    for pat in group_patterns:
        for m in re.finditer(pat, text):
            group_ids.add(int(m.group(1)))
    profile.group_ids = sorted(group_ids)

    return profile


def fetch_archived_profile(user_id: int) -> ArchivedProfile | None:
    """Attempt to recover profile data from the Wayback Machine.

    Returns an ArchivedProfile with whatever data was found, or None
    if no archived snapshot exists at all.
    """
    result = _find_best_snapshot(user_id)
    if result is None:
        return None
    timestamp, original_url = result
    return _scrape_archived_page(timestamp, original_url, user_id)
