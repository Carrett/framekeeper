#!/bin/sh
# One-time setup: installs the NAS mount wrapper and a scoped sudoers rule.
# Run with: sudo sh scripts/install_sudoers.sh
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET_USER="${SUDO_USER:-$(id -un)}"
CRED_DIR="/home/${TARGET_USER}/.config/mdmgr"
CRED_FILE="${CRED_DIR}/nas.cred"
CONFIG_FILE="${PROJECT_DIR}/config.json"
WRAPPER_DST="/usr/local/sbin/mdmgr-mount-nas.sh"
SUDOERS_FILE="/etc/sudoers.d/mdmgr-mount"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this script with sudo." >&2
  exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
  echo "Missing configuration: $CONFIG_FILE" >&2
  echo "Copy config.example.json to config.json and adapt it first." >&2
  exit 1
fi

mkdir -p "$CRED_DIR"
chown "${TARGET_USER}:${TARGET_USER}" "$CRED_DIR"
chmod 700 "$CRED_DIR"

if [ ! -f "$CRED_FILE" ]; then
  echo "Missing credentials file: $CRED_FILE" >&2
  echo "Create it first with:" >&2
  echo "  username=YOUR_NAS_USER" >&2
  echo "  password=YOUR_NAS_PASSWORD" >&2
  exit 1
fi
chown "${TARGET_USER}:${TARGET_USER}" "$CRED_FILE"
chmod 600 "$CRED_FILE"

NAS_HOST="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["nas"]["host"])' "$CONFIG_FILE")"
NAS_SHARE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["nas"]["share"])' "$CONFIG_FILE")"
MOUNT_POINT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["nas"]["mount_point"])' "$CONFIG_FILE")"
TARGET_UID="$(id -u "$TARGET_USER")"
TARGET_GID="$(id -g "$TARGET_USER")"

TMP_WRAPPER="$(mktemp)"
sed \
  -e "s|@NAS_HOST@|${NAS_HOST}|g" \
  -e "s|@NAS_SHARE@|${NAS_SHARE}|g" \
  -e "s|@MOUNT_POINT@|${MOUNT_POINT}|g" \
  -e "s|@CREDENTIALS_FILE@|${CRED_FILE}|g" \
  -e "s|@UID@|${TARGET_UID}|g" \
  -e "s|@GID@|${TARGET_GID}|g" \
  "${PROJECT_DIR}/scripts/mdmgr-mount-nas.sh" > "$TMP_WRAPPER"
install -o root -g root -m 755 "$TMP_WRAPPER" "$WRAPPER_DST"
rm -f "$TMP_WRAPPER"

TMP_SUDOERS="$(mktemp)"
echo "${TARGET_USER} ALL=(root) NOPASSWD: ${WRAPPER_DST}" > "$TMP_SUDOERS"
visudo -cf "$TMP_SUDOERS"
install -o root -g root -m 440 "$TMP_SUDOERS" "$SUDOERS_FILE"
rm -f "$TMP_SUDOERS"

echo "Installed wrapper at $WRAPPER_DST and sudoers rule at $SUDOERS_FILE"
echo "Test with: sudo -n $WRAPPER_DST"
