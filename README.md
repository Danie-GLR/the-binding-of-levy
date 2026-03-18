# Roblox User Tracker

A command-line tool that tracks a Roblox user's **games** (created & played) and **friends list**, with snapshot-based change detection so you can see what changed between runs.

## Features

- **Game tracking** — lists games the user created, plus games they've played (inferred from badge awards)
- **Friends tracking** — full friends list with online/offline status
- **Snapshot & diff** — saves state locally and highlights new/removed games and friends on subsequent runs
- **Web dashboard** — a clean browser UI to search users and view stats, games, friends & changes
- **Lookup by username or user ID**

## Setup

```bash
pip install -r requirements.txt
```

## Usage

### Full report (games + friends + diff)

```bash
# By username
python -m roblox_tracker track -u Roblox

# By user ID
python -m roblox_tracker track -i 1
```

### Games only

```bash
python -m roblox_tracker games -u Roblox
```

### Friends only

```bash
python -m roblox_tracker friends -u Roblox
```

### Skip saving a snapshot

```bash
python -m roblox_tracker track -u Roblox --no-save
```

### Web dashboard

```bash
# Start the web UI (default: http://localhost:5000)
python -m roblox_tracker serve

# Custom port
python -m roblox_tracker serve -p 8080

# With debug/auto-reload
python -m roblox_tracker serve --debug
```

Open the URL in your browser, search for any Roblox username or user ID, and view their games, friends, and changes in a dashboard.

### Discord stream subtitle overlay

You can also use a built-in overlay page that listens to your microphone and renders live captions at the bottom of the screen with a small icon above.

1. Start the web UI:

```bash
python -m roblox_tracker serve
```

2. Open `http://localhost:5000/stream-caption` in Chrome or Edge.
3. Click **Mic Access** to grant browser microphone permission, then click **Start**.
4. Share that browser window/tab in Discord.

Optional stream-ready mode:
- `http://localhost:5000/stream-caption?overlay=1` hides the control panel for a clean overlay-only output.
- `http://localhost:5000/stream-caption?overlay=1&to=en` enables live translation output (example: translate captions to English).
- `http://localhost:5000/stream-caption?overlay=1&icon=/static/azure_latch_icon.svg` sets a custom speaker icon image.
- `http://localhost:5000/stream-caption?overlay=1&relay=on&channel=123456789012345678` sends finalized captions into a Discord text channel.
- `http://localhost:5000/stream-caption?overlay=1&relay=on&guild=123456789012345678` uses relay channel/settings from `/dbot` commands for that server.
- In the overlay UI, you can paste a Discord server link (`discord.gg/...` or `discord.com/channels/...`) and click **Use Link** to auto-fill guild/channel IDs.
- `to=` targets: `en`, `es`, `fr`, `de`, `pt`, `it`, `ja`.
- Hotkey: **Alt+M** toggles caption mute/unmute during stream.

Notes:
- Direct Discord client text overlays are not publicly scriptable, so this works as a visual overlay by sharing the caption page itself.
- Relay mode posts captions as messages into Discord text channels (not voice/video overlay UI).
- For best Discord behavior, share the browser **tab/window** that runs the overlay and keep it open while streaming.
- You can change icon, input language, output translation, and Discord relay channel from the control panel when overlay-only mode is disabled.
- Discord relay requires `DISCORD_BOT_TOKEN` plus bot permissions in the target channel (View Channel + Send Messages).

### Real Discord bot install + slash commands

1. Set bot env vars:

```bash
export DISCORD_BOT_TOKEN="your-bot-token"
export DISCORD_APPLICATION_ID="your-application-id"
```

2. Start the bot process:

```bash
python -m roblox_tracker bot
```

3. In the web dashboard, use **Invite / Install Dbot**. Discord will prompt you to pick a server where your account has install permissions.

4. In your Discord server, configure with slash commands:
- `/dbot setup channel:#captions translation:true target:en prefix:[CAP]`
- `/dbot translation enabled:true target:en`
- `/dbot channel channel:#captions`
- `/dbot prefix text:[CAP]`
- `/dbot status`

Easy mode commands:
- `/d help` shows a setup card with quick actions.
- `/d quick channel:#captions` sets relay channel fast.
- `/d tr enabled:true target:en` toggles translation.
- `/d ch channel:#captions` sets relay channel.
- `/d p text:[CAP]` sets caption prefix.
- `/d s` shows current status.

Command note:
- Discord slash command names are lowercase, so use `/dbot` (not `/Dbot`).

## How it works

| Data            | Source                                         |
| --------------- | ---------------------------------------------- |
| Created games   | `games.roblox.com/v2/users/{id}/games`         |
| Played games    | Inferred from `badges.roblox.com` badge awards |
| Friends         | `friends.roblox.com/v1/users/{id}/friends`     |

Snapshots are saved as JSON files under `~/.roblox_tracker/` (override with `ROBLOX_TRACKER_DATA` env var).

## Limitations

- **Played games** are estimated via badges — if a user never earned a badge in a game, it won't be detected. Roblox doesn't expose a public "recently played" endpoint.
- Some profiles may have restricted API access due to privacy settings.
- Rate-limited to ~2 requests/second to respect Roblox API limits.

## Project structure

```
roblox_tracker/
├── __init__.py      # Package marker
├── __main__.py      # python -m entry point
├── api_client.py    # Roblox API wrapper
├── cli.py           # CLI argument parsing & commands
├── friends.py       # Friends fetching & data model
├── games.py         # Games fetching & data model
├── snapshot.py      # Save/load/diff snapshots
├── web.py           # Flask web server
└── templates/
    ├── index.html       # Search landing page
    └── dashboard.html   # User stats dashboard
```
