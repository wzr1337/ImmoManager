#!/usr/bin/env bash
# Nightly encrypted backup of data/ (DB + invoice scans + generated docs + live
# templates) to Google Drive via an rclone crypt remote. .env and the git checkout
# are NOT backed up here -- see deploy/INSTALL.md for why.
#
# One-time setup required before this can run (interactive, not scriptable):
#   rclone config
#     -> create a remote named "gdrive" (type: drive), complete the OAuth flow
#     -> create a remote named "gdrive-crypt" (type: crypt, remote: gdrive:immomanager-backup,
#        filename_encryption: standard), choose a password and STORE IT SAFELY --
#        losing it means losing access to every backed-up file.
set -euo pipefail

APP_DIR="/home/pi/source/ImmoManager"
DATA_DIR="${IMMOMANAGER_DATA_DIR:-$APP_DIR/data}"
DATE_TAG="$(date +%F)"

rclone sync "$DATA_DIR" gdrive-crypt:immomanager-backup \
    --backup-dir "gdrive-crypt:immomanager-backup-history/$DATE_TAG" \
    -v
