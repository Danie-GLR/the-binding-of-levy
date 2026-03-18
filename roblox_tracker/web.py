"""Flask web server — serves the Roblox tracker dashboard."""

from __future__ import annotations

import dataclasses
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from urllib.parse import urlparse

import requests as http_requests
from flask import Flask, jsonify, render_template, request, redirect, url_for

from .api_client import RobloxClient, RobloxAPIError
from .archive import fetch_archived_profile
from .condo import check_condo_groups, load_discovered_groups, get_all_condo_ids
from .discord import DiscordAPIError, DiscordClient, parse_discord_user_id
from .discord_settings import get_guild_settings
from .friends import fetch_friends
from .games import fetch_all_games, fetch_favorite_games, GameRecord
from .scheduler import BackgroundScanner
from .snapshot import diff_friends, diff_games, diff_groups, get_past_groups, save_snapshot

# Module-level scanner so it persists across requests
_scanner = BackgroundScanner()
_SERVER_SCAN_CACHE_TTL_SECONDS = max(
    10, int(os.environ.get("ROBLOX_TRACKER_SERVER_SCAN_CACHE_TTL", "90")))
_SERVER_SCAN_USER_CHUNK_SIZE = max(
    10, int(os.environ.get("ROBLOX_TRACKER_SERVER_SCAN_CHUNK_SIZE", "60")))
_SERVER_SCAN_CHUNK_DELAY_SECONDS = max(
    0.0, float(os.environ.get("ROBLOX_TRACKER_SERVER_SCAN_CHUNK_DELAY", "0.2")))
_SERVER_SCAN_MAX_WORKERS = max(
    2, int(os.environ.get("ROBLOX_TRACKER_SERVER_SCAN_MAX_WORKERS", "6")))
_server_scan_cache: dict[int, dict[str, Any]] = {}
_server_scan_cache_lock = Lock()
_discord_invite_cache: dict[str, Any] = {"url": "", "timestamp": 0.0}


def get_scanner() -> BackgroundScanner:
    return _scanner


def _resolve_place_and_universe_id(client: RobloxClient, raw_game_id: str,
                                   id_type: str) -> tuple[int, int]:
    """Resolve input game identifier to (place_id, universe_id)."""
    if not raw_game_id or not raw_game_id.isdigit():
        raise ValueError("Game ID must be numeric")

    numeric_id = int(raw_game_id)
    mode = (id_type or "auto").strip().lower()

    if mode not in {"auto", "place", "universe"}:
        mode = "auto"

    if mode in {"auto", "place"}:
        mapping = client.place_ids_to_universe_ids([numeric_id])
        if numeric_id in mapping:
            return numeric_id, mapping[numeric_id]
        if mode == "place":
            raise RobloxAPIError("Could not resolve that place ID")

    details = client.get_game_details([numeric_id])
    if not details:
        raise RobloxAPIError("Could not resolve that universe ID")

    universe_id = details[0].get("id") or numeric_id
    place_id = details[0].get("rootPlaceId")
    if not place_id:
        raise RobloxAPIError("That universe does not expose a root place ID")
    return int(place_id), int(universe_id)


def _extract_server_player_ids(servers: list[dict[str, Any]]) -> tuple[list[int], set[int], int]:
    """Return (all_visible_player_ids, unique_user_ids, servers_with_visible_players)."""
    all_visible_player_ids: list[int] = []
    user_ids: set[int] = set()
    servers_with_visible_players = 0

    for server in servers:
        players = server.get("players") or []
        if players:
            servers_with_visible_players += 1
        for player in players:
            uid = (
                player.get("id")
                or player.get("playerId")
                or player.get("userId")
                or (player.get("player") or {}).get("id")
                or (player.get("player") or {}).get("userId")
            )
            if uid:
                try:
                    parsed = int(uid)
                    all_visible_player_ids.append(parsed)
                    user_ids.add(parsed)
                except (TypeError, ValueError):
                    continue

    return all_visible_player_ids, user_ids, servers_with_visible_players


def _get_cached_server_scan(place_id: int) -> dict[str, Any] | None:
    now = time.monotonic()
    with _server_scan_cache_lock:
        entry = _server_scan_cache.get(place_id)
        if not entry:
            return None
        age = now - entry["timestamp"]
        if age > _SERVER_SCAN_CACHE_TTL_SECONDS:
            _server_scan_cache.pop(place_id, None)
            return None

        payload = dict(entry["payload"])
        payload["cache_hit"] = True
        payload["cache_age_seconds"] = int(age)
        return payload


def _set_cached_server_scan(place_id: int, payload: dict[str, Any]) -> None:
    # Keep cache entries compact and bounded in age.
    with _server_scan_cache_lock:
        _server_scan_cache[place_id] = {
            "timestamp": time.monotonic(),
            "payload": dict(payload),
        }


def _normalize_language_code(raw_code: str, *, fallback: str) -> str:
    """Normalize codes like en-US, EN_us -> en for translation APIs."""
    cleaned = (raw_code or "").strip().lower().replace("_", "-")
    if not cleaned:
        return fallback
    if cleaned == "auto":
        return "auto"
    return cleaned.split("-", 1)[0]


def _translate_text_server(text: str, source_lang: str, target_lang: str) -> str:
    """Translate text using the backend translation provider."""
    if not text:
        return ""

    source = _normalize_language_code(source_lang, fallback="en")
    target = _normalize_language_code(target_lang, fallback="en")
    if source == target:
        return text

    response = http_requests.get(
        "https://api.mymemory.translated.net/get",
        params={"q": text, "langpair": f"{source}|{target}"},
        timeout=8,
    )
    response.raise_for_status()
    payload = response.json()
    translated_text = ((payload.get("responseData") or {}).get("translatedText") or "").strip()
    if not translated_text:
        raise ValueError("Translation unavailable")
    return translated_text


def _resolve_discord_invite_url() -> str:
    """Best-effort Discord OAuth install URL for bot + slash commands."""
    now = time.monotonic()
    age = now - float(_discord_invite_cache.get("timestamp") or 0.0)
    if age < 300 and _discord_invite_cache.get("url"):
        return str(_discord_invite_cache["url"])

    app_id = DiscordClient.get_application_id_from_env()
    if app_id:
        url = DiscordClient.build_bot_invite_url(app_id)
        _discord_invite_cache.update({"url": url, "timestamp": now})
        return url
    if not DiscordClient.is_configured():
        return ""

    try:
        client = DiscordClient()
        app_id = client.get_application_id()
        url = DiscordClient.build_bot_invite_url(app_id)
        _discord_invite_cache.update({"url": url, "timestamp": now})
        return url
    except DiscordAPIError:
        return ""


def _parse_discord_link(raw_link: str) -> dict[str, str]:
    """Parse known Discord URL patterns into guild/channel IDs when possible."""
    value = (raw_link or "").strip()
    if not value:
        return {"error": "Missing link"}

    if value.isdigit():
        return {"guild_id": value, "channel_id": ""}

    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"

    parsed = urlparse(value)
    host = (parsed.netloc or "").lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    # https://discord.com/channels/<guild_id>/<channel_id>
    if host.endswith("discord.com") and len(path_parts) >= 2 and path_parts[0] == "channels":
        guild_id = path_parts[1] if path_parts[1].isdigit() else ""
        channel_id = path_parts[2] if len(path_parts) >= 3 and path_parts[2].isdigit() else ""
        if guild_id:
            return {"guild_id": guild_id, "channel_id": channel_id}

    # https://discord.com/invite/<code> or https://discord.gg/<code>
    invite_code = ""
    if host.endswith("discord.gg") and path_parts:
        invite_code = path_parts[0]
    elif host.endswith("discord.com") and len(path_parts) >= 2 and path_parts[0] == "invite":
        invite_code = path_parts[1]

    if invite_code:
        try:
            response = http_requests.get(
                f"https://discord.com/api/v10/invites/{invite_code}",
                params={"with_counts": "false", "with_expiration": "false"},
                timeout=8,
            )
            if response.status_code != 200:
                return {"error": "Invite link could not be resolved."}
            payload = response.json()
            guild_id = str(((payload.get("guild") or {}).get("id") or "")).strip()
            channel_id = str(((payload.get("channel") or {}).get("id") or "")).strip()
            if guild_id.isdigit():
                return {
                    "guild_id": guild_id,
                    "channel_id": channel_id if channel_id.isdigit() else "",
                }
            return {"error": "Invite resolved, but no server ID was returned."}
        except (http_requests.RequestException, ValueError):
            return {"error": "Failed to resolve invite link."}

    return {"error": "Unsupported Discord link format."}


def create_app() -> Flask:
    app = Flask(__name__)

    # Start background scanner automatically
    _scanner.start()

    @app.context_processor
    def inject_discord_ui_context() -> dict[str, Any]:
        return {
            "discord_enabled": DiscordClient.is_configured(),
            "discord_invite_url": _resolve_discord_invite_url(),
        }

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/discord")
    def discord_lookup():
        raw_value = request.args.get("discord_user", "").strip()
        if not raw_value:
            return render_template(
                "index.html",
                discord_enabled=DiscordClient.is_configured(),
                discord_error="Enter a Discord user ID or mention.",
            )

        try:
            discord_user_id = parse_discord_user_id(raw_value)
            client = DiscordClient()
            discord_user = client.get_user(discord_user_id)
            mutual_guilds = client.list_mutual_guilds(discord_user_id)
        except DiscordAPIError as e:
            return render_template(
                "index.html",
                discord_enabled=DiscordClient.is_configured(),
                discord_error=str(e),
                discord_query=raw_value,
            )

        scanned_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return render_template(
            "discord.html",
            discord_enabled=DiscordClient.is_configured(),
            discord_query=raw_value,
            discord_user=discord_user,
            mutual_guilds=mutual_guilds,
            scanned_at=scanned_at,
        )

    @app.route("/track")
    def track():
        username = request.args.get("username", "").strip()
        user_id_str = request.args.get("user_id", "").strip()

        if not username and not user_id_str:
            return render_template("index.html", error="Enter a username or user ID.")

        client = RobloxClient()

        # Resolve user
        is_unavailable = False
        try:
            if username:
                user_id = client.get_user_id(username)
            else:
                user_id = int(user_id_str)
        except RobloxAPIError as e:
            return render_template("index.html", error=str(e))
        except ValueError:
            return render_template("index.html", error="Invalid user ID.")

        try:
            info = client.get_user_info(user_id)
        except RobloxAPIError:
            # User profile is unavailable (deleted / terminated) — build
            # a minimal stub so the dashboard can still show any residual
            # activity (games, badges, etc.) that the API still exposes.
            info = {
                "name": f"[User {user_id}]",
                "displayName": f"[User {user_id}]",
                "created": "",
                "description": "",
                "isBanned": False,
            }
            is_unavailable = True

        display_name = info.get("displayName", info.get("name", str(user_id)))
        roblox_username = info.get("name", str(user_id))
        created_date = info.get("created", "")
        description = info.get("description", "")
        is_banned = info.get("isBanned", False)

        # Fetch data concurrently. Each task uses its own client instance to avoid
        # sharing HTTP sessions across threads.
        def _safe(callable_):
            try:
                return callable_()
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=5) as pool:
            fut_avatar = pool.submit(_safe, lambda: RobloxClient().get_user_headshot(user_id))
            fut_games = pool.submit(_safe, lambda: fetch_all_games(RobloxClient(), user_id))
            fut_friends = pool.submit(_safe, lambda: fetch_friends(RobloxClient(), user_id))
            fut_favorites = pool.submit(_safe, lambda: fetch_favorite_games(RobloxClient(), user_id))
            fut_groups = pool.submit(_safe, lambda: RobloxClient().get_user_groups(user_id))

            avatar_url = fut_avatar.result() or ""
            games = fut_games.result() or []
            friends = fut_friends.result() or []
            standalone_favorites = fut_favorites.result() or []
            groups = fut_groups.result() or []
        # Merge thumbnails into standalone favorites from allgames map
        thumb_map = {g.universe_id: g.thumbnail_url for g in games if g.thumbnail_url}
        missing_thumb_ids = [
            fg.universe_id for fg in standalone_favorites
            if fg.universe_id not in thumb_map and fg.universe_id
        ]
        if missing_thumb_ids:
            try:
                extra_thumbs = client.get_game_thumbnails(missing_thumb_ids)
                thumb_map.update(extra_thumbs)
            except Exception:
                pass
        for fg in standalone_favorites:
            if not fg.thumbnail_url:
                fg.thumbnail_url = thumb_map.get(fg.universe_id, "")

        # Condo group detection
        condo_flags = check_condo_groups(groups)

        # Diff
        games_diff = diff_games(user_id, games)
        friends_diff = diff_friends(user_id, friends)
        groups_diff = diff_groups(user_id, groups)
        past_groups = get_past_groups(user_id, groups)

        # Save snapshot
        save_snapshot(user_id, games=games, friends=friends, groups=groups)

        # Auto-track this user for background scanning
        _scanner.add_user(user_id, username=roblox_username)

        # Archived data recovery for banned / unavailable users
        archived = None
        archived_games: list[GameRecord] = []
        archived_groups: list[dict] = []
        if is_banned or is_unavailable:
            try:
                archived = fetch_archived_profile(user_id)
            except Exception:
                archived = None
            if archived:
                # Resolve archived game place IDs to real game records
                if archived.game_place_ids:
                    try:
                        p2u = client.place_ids_to_universe_ids(archived.game_place_ids)
                        universe_ids = list(set(p2u.values()))
                        # Skip universes already in the live games list
                        known = {g.universe_id for g in games}
                        new_uids = [u for u in universe_ids if u not in known]
                        if new_uids:
                            details = client.get_game_details(new_uids)
                            for d in details:
                                archived_games.append(GameRecord(
                                    universe_id=d.get("id", 0),
                                    name=d.get("name", "Unknown"),
                                    place_id=d.get("rootPlaceId"),
                                    creator_name=d.get("creator", {}).get("name", ""),
                                    playing=d.get("playing", 0),
                                    visits=d.get("visits", 0),
                                    source="archived",
                                ))
                    except Exception:
                        pass
                # Resolve archived group IDs
                if archived.group_ids:
                    for gid in archived.group_ids:
                        try:
                            gdata = client._get(
                                f"https://groups.roblox.com/v1/groups/{int(gid)}")
                            archived_groups.append(gdata)
                        except Exception:
                            continue

        # Stats
        online_count = sum(1 for f in friends if f.is_online)
        total_hours = sum(g.hours_played for g in games)
        total_badges = sum(g.badge_count for g in games)
        total_playing = sum(g.playing for g in games)
        created_games = [g for g in games if g.source == "created"]
        played_games = [g for g in games if g.source == "badge"]

        scanned_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        return render_template(
            "dashboard.html",
            user_id=user_id,
            display_name=display_name,
            username=roblox_username,
            avatar_url=avatar_url,
            is_banned=is_banned,
            is_unavailable=is_unavailable,
            created_date=created_date[:10] if created_date else "N/A",
            description=description,
            scanned_at=scanned_at,
            games=games,
            created_games=created_games,
            played_games=played_games,
            favorite_games=standalone_favorites,
            friends=friends,
            groups=groups,
            online_count=online_count,
            total_hours=total_hours,
            total_badges=total_badges,
            total_playing=total_playing,
            games_diff=games_diff,
            friends_diff=friends_diff,
            groups_diff=groups_diff,
            past_groups=past_groups,
            archived=archived,
            archived_games=archived_games,
            archived_groups=archived_groups,
            condo_flags=condo_flags,
        )

    @app.route("/scan-servers")
    def scan_servers():
        raw_game_id = request.args.get("game_id", "").strip()
        id_type = request.args.get("id_type", "auto").strip().lower()
        force_refresh = request.args.get("refresh", "").strip() == "1"

        if not raw_game_id:
            return render_template(
                "index.html",
                discord_enabled=DiscordClient.is_configured(),
                game_error="Enter a game ID (place or universe).",
            )

        client = RobloxClient()
        try:
            place_id, universe_id = _resolve_place_and_universe_id(
                client, raw_game_id, id_type)
        except (RobloxAPIError, ValueError) as e:
            return render_template(
                "index.html",
                discord_enabled=DiscordClient.is_configured(),
                game_error=str(e),
                game_query=raw_game_id,
                game_id_type=id_type,
            )

        if not force_refresh:
            cached_payload = _get_cached_server_scan(place_id)
            if cached_payload is not None:
                cached_payload["game_query"] = raw_game_id
                cached_payload["place_id"] = place_id
                cached_payload["universe_id"] = universe_id
                return render_template("game_scan.html", **cached_payload)

        try:
            game_detail = client.get_game_details([universe_id])
            game_name = (game_detail[0].get("name") if game_detail else None) or f"Game {universe_id}"
            servers = client.get_public_servers(place_id)
        except RobloxAPIError as e:
            return render_template(
                "index.html",
                discord_enabled=DiscordClient.is_configured(),
                game_error=f"Failed to fetch game servers: {e}",
                game_query=raw_game_id,
                game_id_type=id_type,
            )

        all_visible_player_ids, player_ids, servers_with_visible_players = _extract_server_player_ids(servers)

        def _scan_user(uid: int, info_map: dict[int, dict[str, Any]]) -> dict[str, Any]:
            try:
                groups = RobloxClient().get_user_groups(uid)
                flags = check_condo_groups(groups)
                lookup_ok = True
                lookup_error = ""
            except Exception:
                groups = []
                flags = []
                lookup_ok = False
                lookup_error = "group lookup failed"

            info = info_map.get(uid, {})
            status = "unknown"
            if lookup_ok:
                status = "flagged" if flags else "clean"

            return {
                "user_id": uid,
                "username": info.get("name") or f"User {uid}",
                "display_name": info.get("displayName") or info.get("name") or f"User {uid}",
                "is_flagged": bool(flags),
                "status": status,
                "flags": flags,
                "group_count": len(groups),
                "lookup_ok": lookup_ok,
                "lookup_error": lookup_error,
            }

        player_rows: list[dict[str, Any]] = []
        if player_ids:
            sorted_player_ids = sorted(player_ids)
            for idx in range(0, len(sorted_player_ids), _SERVER_SCAN_USER_CHUNK_SIZE):
                chunk = sorted_player_ids[idx: idx + _SERVER_SCAN_USER_CHUNK_SIZE]
                chunk_info = client.get_bulk_user_info(chunk)

                with ThreadPoolExecutor(max_workers=_SERVER_SCAN_MAX_WORKERS) as pool:
                    futures = [pool.submit(_scan_user, uid, chunk_info) for uid in chunk]
                    for fut in futures:
                        player_rows.append(fut.result())

                has_more = (idx + _SERVER_SCAN_USER_CHUNK_SIZE) < len(sorted_player_ids)
                if has_more and _SERVER_SCAN_CHUNK_DELAY_SECONDS > 0:
                    time.sleep(_SERVER_SCAN_CHUNK_DELAY_SECONDS)

        status_rank = {"flagged": 0, "unknown": 1, "clean": 2}
        player_rows.sort(key=lambda row: (status_rank.get(row["status"], 3), row["username"].lower()))

        flagged_count = sum(1 for row in player_rows if row["status"] == "flagged")
        clean_count = sum(1 for row in player_rows if row["status"] == "clean")
        unknown_count = sum(1 for row in player_rows if row["status"] == "unknown")
        total_playing = sum((s.get("playing") or 0) for s in servers)
        total_capacity = sum((s.get("maxPlayers") or 0) for s in servers)
        scanned_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        payload = {
            "game_query": raw_game_id,
            "game_name": game_name,
            "place_id": place_id,
            "universe_id": universe_id,
            "servers": servers,
            "server_count": len(servers),
            "total_playing": total_playing,
            "total_capacity": total_capacity,
            "servers_with_visible_players": servers_with_visible_players,
            "visible_player_entries": len(all_visible_player_ids),
            "unique_players": len(player_ids),
            "player_rows": player_rows,
            "flagged_count": flagged_count,
            "clean_count": clean_count,
            "unknown_count": unknown_count,
            "scanned_at": scanned_at,
            "cache_hit": False,
            "cache_age_seconds": 0,
            "cache_ttl_seconds": _SERVER_SCAN_CACHE_TTL_SECONDS,
        }

        _set_cached_server_scan(place_id, payload)
        return render_template("game_scan.html", **payload)

    # ---- Scheduler status & control routes ---- #

    @app.route("/scheduler")
    def scheduler_status():
        tracked = _scanner.get_tracked_users()
        log = _scanner.get_scan_log()[:20]
        return render_template(
            "scheduler.html",
            scanner=_scanner,
            tracked=tracked,
            log=log,
        )

    @app.route("/scheduler/remove")
    def scheduler_remove():
        uid = request.args.get("user_id", "").strip()
        if uid.isdigit():
            _scanner.remove_user(int(uid))
        return redirect(url_for("scheduler_status"))

    @app.route("/scheduler/discover")
    def run_discovery():
        """Manually trigger condo group discovery."""
        newly_added = _scanner.run_discovery_now()
        return redirect(url_for("scheduler_status"))

    @app.route("/stream-caption")
    def stream_caption_overlay():
        """Live speech-to-text overlay designed for Discord screen share."""
        return render_template("stream_caption.html")

    @app.route("/discord-caption", methods=["POST"])
    def discord_caption_relay():
        """Relay live captions into a Discord text channel using the configured bot."""
        payload = request.get_json(silent=True) or {}
        channel_id_raw = str(payload.get("channel_id", "")).strip()
        guild_id_raw = str(payload.get("guild_id", "")).strip()
        source_lang = str(payload.get("source", "en")).strip() or "en"
        text = str(payload.get("text", "")).strip()

        if not text:
            return jsonify({"error": "Message text cannot be empty."}), 400

        guild_settings = None
        if guild_id_raw.isdigit():
            guild_settings = get_guild_settings(int(guild_id_raw))

        if not channel_id_raw and guild_settings and guild_settings.relay_channel_id:
            channel_id_raw = str(guild_settings.relay_channel_id)

        if not channel_id_raw.isdigit():
            return jsonify({"error": "Invalid channel ID."}), 400

        outbound_text = text
        if guild_settings:
            if guild_settings.translation_enabled:
                try:
                    outbound_text = _translate_text_server(
                        outbound_text,
                        source_lang,
                        guild_settings.translation_target,
                    )
                except (http_requests.RequestException, ValueError):
                    # Keep relay functional if translation provider is down.
                    pass
            if guild_settings.caption_prefix:
                outbound_text = f"{guild_settings.caption_prefix} {outbound_text}".strip()

        try:
            client = DiscordClient()
            sent = client.send_channel_message(int(channel_id_raw), outbound_text)
            return jsonify({
                "ok": True,
                "message_id": sent.get("id", ""),
            })
        except DiscordAPIError as e:
            return jsonify({"error": str(e)}), 502

    @app.route("/discord-resolve-link")
    def discord_resolve_link():
        """Resolve Discord server/channel IDs from user-provided links."""
        raw_link = request.args.get("link", "")
        parsed = _parse_discord_link(raw_link)
        if parsed.get("error"):
            return jsonify(parsed), 400
        return jsonify(parsed)

    @app.route("/translate")
    def translate_text():
        """Translate subtitle text for live overlay display."""
        text = request.args.get("text", "").strip()
        source_lang = _normalize_language_code(
            request.args.get("source", "en"), fallback="en")
        target_lang = _normalize_language_code(
            request.args.get("target", "en"), fallback="en")

        if not text:
            return jsonify({"translated_text": ""})

        if source_lang == target_lang:
            return jsonify({"translated_text": text})

        # MyMemory free endpoint: no key required for lightweight live subtitles.
        # Keeping translation on the server avoids browser CORS failures.
        try:
            translated_text = _translate_text_server(text, source_lang, target_lang)
            return jsonify({"translated_text": translated_text})
        except (http_requests.RequestException, ValueError):
            return jsonify({"error": "Translation request failed"}), 502

    return app
