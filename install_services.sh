#!/usr/bin/env bash
set -euo pipefail

# ================================================================== #
#  Roblox Tracker — systemd service installer
#
#  Usage:
#    sudo ./install_services.sh            # uses current $SUDO_USER
#    sudo ./install_services.sh  myuser    # explicit username
#
#  This installs two systemd services:
#    roblox-tracker-web@<user>      — the Flask web dashboard (port 5000)
#    roblox-tracker-scanner@<user>  — standalone background scanner
#
#  Both run as the specified user and auto-start on boot.
#  Data is stored in  ~<user>/.roblox_tracker/
# ================================================================== #

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYSTEMD_DIR="/etc/systemd/system"

# Determine user
TARGET_USER="${1:-${SUDO_USER:-}}"
if [[ -z "$TARGET_USER" ]]; then
    echo "Error: could not determine target user."
    echo "Usage: sudo $0 <username>"
    exit 1
fi

# Verify user exists
if ! id "$TARGET_USER" &>/dev/null; then
    echo "Error: user '$TARGET_USER' does not exist."
    exit 1
fi

USER_HOME="$(eval echo "~$TARGET_USER")"

echo "==> Installing Roblox Tracker services for user: $TARGET_USER"
echo "    Data directory: $USER_HOME/.roblox_tracker/"

# Ensure data dir exists
install -d -o "$TARGET_USER" -g "$TARGET_USER" -m 0750 "$USER_HOME/.roblox_tracker"

# Install Python dependencies
echo "==> Installing Python dependencies..."
REPO_DIR="$SCRIPT_DIR"
if [[ -f "$REPO_DIR/requirements.txt" ]]; then
    sudo -u "$TARGET_USER" pip3 install --user -q -r "$REPO_DIR/requirements.txt"
fi

# Make sure the package is accessible — install in user site-packages
echo "==> Installing roblox_tracker package..."
sudo -u "$TARGET_USER" pip3 install --user -q -e "$REPO_DIR"

# Copy service files
echo "==> Installing systemd unit files..."
cp "$SCRIPT_DIR/systemd/roblox-tracker-web@.service" "$SYSTEMD_DIR/"
cp "$SCRIPT_DIR/systemd/roblox-tracker-scanner@.service" "$SYSTEMD_DIR/"

# Reload systemd
systemctl daemon-reload

# Enable and start services
echo "==> Enabling and starting services..."
systemctl enable --now "roblox-tracker-web@${TARGET_USER}.service"
systemctl enable --now "roblox-tracker-scanner@${TARGET_USER}.service"

echo ""
echo "Done! Both services are running and will start on boot."
echo ""
echo "  Web dashboard:  http://localhost:5000"
echo "  Scanner status:  http://localhost:5000/scheduler"
echo ""
echo "Useful commands:"
echo "  systemctl status  roblox-tracker-web@${TARGET_USER}"
echo "  systemctl status  roblox-tracker-scanner@${TARGET_USER}"
echo "  journalctl -u roblox-tracker-scanner@${TARGET_USER} -f   # live logs"
echo "  systemctl restart roblox-tracker-scanner@${TARGET_USER}  # restart scanner"
echo "  systemctl stop    roblox-tracker-scanner@${TARGET_USER}  # stop scanner"
