#!/usr/bin/env python3
"""CLI entry point for the Roblox User Tracker."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from .api_client import RobloxClient, RobloxAPIError
from .friends import FriendRecord, fetch_friends
from .games import GameRecord, fetch_all_games, fetch_created_games
from .snapshot import diff_friends, diff_games, save_snapshot


# ------------------------------------------------------------------ #
#  Formatting helpers
# ------------------------------------------------------------------ #

def _header(text: str) -> str:
    line = "=" * 60
    return f"\n{line}\n  {text}\n{line}"


def _print_games(games: list[GameRecord]) -> None:
    if not games:
        print("  (none found)")
        return
    for g in games:
        print(g.summary_line())


def _print_friends(friends: list[FriendRecord]) -> None:
    if not friends:
        print("  (none found)")
        return
    for f in friends:
        print(f.summary_line())


def _print_diff_section(label: str, added, removed) -> None:
    if added:
        print(f"\n  ++ {label} added:")
        for item in added:
            if isinstance(item, (GameRecord, FriendRecord)):
                print(f"     {item.summary_line()}")
            elif isinstance(item, dict):
                name = item.get("name", item.get("username", "unknown"))
                print(f"     {name}")
    if removed:
        print(f"\n  -- {label} removed:")
        for item in removed:
            if isinstance(item, (GameRecord, FriendRecord)):
                print(f"     {item.summary_line()}")
            elif isinstance(item, dict):
                name = item.get("name", item.get("username", "unknown"))
                print(f"     {name}")


# ------------------------------------------------------------------ #
#  Commands
# ------------------------------------------------------------------ #

def cmd_track(args: argparse.Namespace) -> None:
    """Full tracking report: games + friends, with optional diff."""
    client = RobloxClient()

    # Resolve username → ID
    if args.username:
        try:
            user_id = client.get_user_id(args.username)
        except RobloxAPIError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        user_id = args.user_id

    info = client.get_user_info(user_id)
    display = info.get("displayName", info.get("name", str(user_id)))
    username = info.get("name", str(user_id))

    print(_header(f"Roblox Tracker — {display} (@{username})  [ID: {user_id}]"))
    print(f"  Scanned at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # --- Games ---
    print(_header("Games (created + played via badges)"))
    games = fetch_all_games(client, user_id)
    _print_games(games)
    print(f"\n  Total games found: {len(games)}")

    # --- Friends ---
    print(_header("Friends"))
    friends = fetch_friends(client, user_id)
    _print_friends(friends)
    online = sum(1 for f in friends if f.is_online)
    print(f"\n  Total friends: {len(friends)}  (online: {online})")

    # --- Diff against previous snapshot ---
    if not args.no_save:
        gd = diff_games(user_id, games)
        fd = diff_friends(user_id, friends)

        if gd["previous_snapshot"] or fd["previous_snapshot"]:
            print(_header("Changes since last snapshot"))
            ts = gd["previous_snapshot"] or fd["previous_snapshot"]
            print(f"  Previous snapshot: {ts}")
            _print_diff_section("Games", gd["added"], gd["removed"])
            _print_diff_section("Friends", fd["added"], fd["removed"])
            if not gd["added"] and not gd["removed"] and not fd["added"] and not fd["removed"]:
                print("  No changes detected.")
        else:
            print("\n  (First run — no previous snapshot to compare against)")

        data_dir = save_snapshot(user_id, games=games, friends=friends)
        print(f"\n  Snapshot saved to {data_dir}")


def cmd_games(args: argparse.Namespace) -> None:
    """Show only games."""
    client = RobloxClient()
    user_id = _resolve_user(client, args)
    info = client.get_user_info(user_id)
    print(_header(f"Games for @{info.get('name', user_id)}"))
    games = fetch_all_games(client, user_id)
    _print_games(games)
    print(f"\n  Total: {len(games)}")


def cmd_friends(args: argparse.Namespace) -> None:
    """Show only friends."""
    client = RobloxClient()
    user_id = _resolve_user(client, args)
    info = client.get_user_info(user_id)
    print(_header(f"Friends of @{info.get('name', user_id)}"))
    friends = fetch_friends(client, user_id)
    _print_friends(friends)
    online = sum(1 for f in friends if f.is_online)
    print(f"\n  Total: {len(friends)}  (online: {online})")


def cmd_serve(args: argparse.Namespace) -> None:
    """Launch the web dashboard."""
    from .web import create_app
    app = create_app()
    print(f"Starting Roblox Tracker web UI on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


def cmd_scan(args: argparse.Namespace) -> None:
    """Run the background scanner as a standalone foreground process."""
    import logging
    from .scheduler import BackgroundScanner

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    scanner = BackgroundScanner(interval=args.interval)
    tracked = scanner.get_tracked_users()
    print(f"Scanner starting — {len(tracked)} tracked user(s), "
          f"interval {args.interval}s ({args.interval // 3600}h {(args.interval % 3600) // 60}m)")
    if not tracked:
        print("No tracked users yet. Search for users via the web UI or "
              "'roblox-tracker track' first.")
    scanner.run_forever()


def cmd_bot(args: argparse.Namespace) -> None:
    """Run the Discord bot process with /dbot slash commands."""
    from .discord_bot import run_discord_bot

    print("Starting Discord bot process...")
    run_discord_bot()


def _resolve_user(client: RobloxClient, args: argparse.Namespace) -> int:
    if args.username:
        return client.get_user_id(args.username)
    return args.user_id


# ------------------------------------------------------------------ #
#  Argument parsing
# ------------------------------------------------------------------ #

def _add_user_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-u", "--username", help="Roblox username to look up")
    group.add_argument("-i", "--user-id", type=int, help="Roblox user ID")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="roblox-tracker",
        description="Track a Roblox user's games and friends over time.",
    )
    sub = parser.add_subparsers(dest="command")

    # track (default full report)
    p_track = sub.add_parser("track", help="Full report: games + friends + diff")
    _add_user_args(p_track)
    p_track.add_argument("--no-save", action="store_true",
                         help="Don't save a snapshot after this run")

    # games
    p_games = sub.add_parser("games", help="Show games only")
    _add_user_args(p_games)

    # friends
    p_friends = sub.add_parser("friends", help="Show friends only")
    _add_user_args(p_friends)

    # serve (web UI)
    p_serve = sub.add_parser("serve", help="Launch the web dashboard")
    p_serve.add_argument("-p", "--port", type=int, default=5000, help="Port (default: 5000)")
    p_serve.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    p_serve.add_argument("--debug", action="store_true", help="Enable Flask debug mode")

    # scan (standalone background scanner)
    p_scan = sub.add_parser("scan", help="Run the background scanner in the foreground")
    p_scan.add_argument("--interval", type=int, default=3600,
                        help="Seconds between scan cycles (default: 3600 = 1 hour)")

    # bot (discord slash commands)
    sub.add_parser("bot", help="Run Discord bot with /dbot slash commands")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "track": cmd_track,
        "games": cmd_games,
        "friends": cmd_friends,
        "serve": cmd_serve,
        "scan": cmd_scan,
        "bot": cmd_bot,
    }
    try:
        dispatch[args.command](args)
    except RobloxAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(130)


if __name__ == "__main__":
    main()
