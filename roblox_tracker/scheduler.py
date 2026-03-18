"""Background scheduler — periodically re-scans tracked users."""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .api_client import RobloxClient
from .condo import discover_condo_groups
from .friends import fetch_friends
from .games import fetch_all_games
from .snapshot import save_snapshot, _data_dir

logger = logging.getLogger(__name__)

_TRACKED_FILE = "tracked_users.json"
_DEFAULT_INTERVAL = 3600  # 1 hour
_DISCOVERY_INTERVAL = 6  # run condo discovery every N scan cycles


class BackgroundScanner:
    """Periodically re-scans all tracked users and saves snapshots.

    The list of tracked user IDs is persisted to disk so it survives
    server restarts.  Scanning only happens while the server process
    is running — when the server is stopped, no scans occur, but the
    tracked list and all previously collected history remain on disk.
    On next server start the scanner resumes automatically.
    """

    def __init__(self, interval: int = _DEFAULT_INTERVAL):
        self._interval = interval
        self._timer: threading.Timer | None = None
        self._running = False
        self._lock = threading.Lock()
        self._scan_log: list[dict] = []  # recent scan results (in-memory)
        self._cycle_count = 0  # tracks cycles for periodic discovery

    # -- tracked users persistence ---------------------------------- #

    @staticmethod
    def _tracked_path() -> Path:
        return _data_dir() / _TRACKED_FILE

    def get_tracked_users(self) -> dict[int, dict]:
        """Return {user_id: {username, added_at}} from disk."""
        path = self._tracked_path()
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text())
            # Ensure keys are ints
            return {int(k): v for k, v in data.items()}
        except Exception:
            return {}

    def _save_tracked(self, tracked: dict[int, dict]) -> None:
        path = self._tracked_path()
        path.write_text(json.dumps(
            {str(k): v for k, v in tracked.items()}, indent=2))

    def add_user(self, user_id: int, username: str = "") -> None:
        """Register a user for background scanning."""
        with self._lock:
            tracked = self.get_tracked_users()
            if user_id not in tracked:
                tracked[user_id] = {
                    "username": username,
                    "added_at": datetime.now(timezone.utc).isoformat(),
                }
                self._save_tracked(tracked)

    def remove_user(self, user_id: int) -> None:
        """Stop tracking a user."""
        with self._lock:
            tracked = self.get_tracked_users()
            if user_id in tracked:
                del tracked[user_id]
                self._save_tracked(tracked)

    # -- scanning --------------------------------------------------- #

    def _scan_all(self) -> None:
        """Run one scan cycle over every tracked user."""
        tracked = self.get_tracked_users()
        if not tracked:
            logger.info("Scheduler: no tracked users, skipping cycle.")
            return

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        logger.info("Scheduler: scanning %d user(s) at %s", len(tracked), ts)

        client = RobloxClient()
        results: list[dict] = []

        for uid, meta in tracked.items():
            entry = {"user_id": uid, "username": meta.get("username", ""),
                     "time": ts, "ok": False, "error": ""}
            try:
                games = fetch_all_games(client, uid)
                friends = fetch_friends(client, uid)
                try:
                    groups = client.get_user_groups(uid)
                except Exception:
                    groups = []
                save_snapshot(uid, games=games, friends=friends, groups=groups)
                entry["ok"] = True
                entry["games"] = len(games)
                entry["friends"] = len(friends)
                entry["groups"] = len(groups)
            except Exception as exc:
                entry["error"] = str(exc)
                logger.warning("Scheduler: failed to scan user %s: %s", uid, exc)
            results.append(entry)
            time.sleep(1)  # be polite to the API between users

        with self._lock:
            self._scan_log = (results + self._scan_log)[:200]

        logger.info("Scheduler: cycle complete — %d/%d succeeded.",
                     sum(1 for r in results if r["ok"]), len(results))

        # Periodically run condo group discovery
        self._cycle_count += 1
        if self._cycle_count % _DISCOVERY_INTERVAL == 0:
            self._run_condo_discovery()

    def _run_condo_discovery(self) -> None:
        """Run condo group cross-reference discovery."""
        logger.info("Scheduler: starting condo group discovery...")
        try:
            newly_added = discover_condo_groups()
            if newly_added:
                names = [v["name"] for v in newly_added.values()]
                logger.info("Scheduler: discovered %d new condo groups: %s",
                            len(newly_added), ", ".join(names[:10]))
            else:
                logger.info("Scheduler: condo discovery found no new groups.")
        except Exception as exc:
            logger.warning("Scheduler: condo discovery failed: %s", exc)

    def run_discovery_now(self) -> dict[int, dict]:
        """Manually trigger condo discovery. Returns newly found groups."""
        return discover_condo_groups()

    def _loop(self) -> None:
        """Timer callback — scan then reschedule."""
        if not self._running:
            return
        try:
            self._scan_all()
        except Exception as exc:
            logger.exception("Scheduler: unhandled error in scan loop: %s", exc)
        # Reschedule
        if self._running:
            self._timer = threading.Timer(self._interval, self._loop)
            self._timer.daemon = True
            self._timer.start()

    # -- control ---------------------------------------------------- #

    def start(self) -> None:
        """Start the background scanner."""
        if self._running:
            return
        self._running = True
        # Run first scan after a short delay to let the server start up
        self._timer = threading.Timer(10, self._loop)
        self._timer.daemon = True
        self._timer.start()
        logger.info("Scheduler: started (interval=%ds)", self._interval)

    def stop(self) -> None:
        """Stop the background scanner."""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        logger.info("Scheduler: stopped")

    def run_forever(self) -> None:
        """Run the scanner in the foreground (blocking).

        Used by the standalone ``scan`` CLI command / systemd service.
        Keeps scanning in a simple sleep loop until interrupted.
        """
        self._running = True
        logger.info("Scanner: running in foreground (interval=%ds). Ctrl+C to stop.",
                     self._interval)
        try:
            while self._running:
                self._scan_all()
                # Sleep in small increments so Ctrl+C is responsive
                for _ in range(self._interval):
                    if not self._running:
                        break
                    time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            logger.info("Scanner: stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def interval(self) -> int:
        return self._interval

    @interval.setter
    def interval(self, value: int) -> None:
        self._interval = max(60, value)  # minimum 1 minute

    def get_scan_log(self) -> list[dict]:
        """Return recent scan results (most recent first)."""
        with self._lock:
            return list(self._scan_log)
