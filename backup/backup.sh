#!/usr/bin/env bash
# Nightly encrypted backup of data/ (DB + invoice scans + generated docs + live
# templates) to Google Drive via an rclone crypt remote. .env and the git checkout
# are NOT backed up here -- see deploy/INSTALL.md for why.
#
# Everything below stays inside ONE dedicated Drive folder, enforced two ways:
#   1. The "gdrive" remote is scoped to the drive.file OAuth scope, so the Google
#      API itself refuses any access to a file/folder rclone didn't create --
#      structurally impossible for this script to touch anything else in the
#      Drive, not just a path convention.
#   2. "grdrivecrypt" (crypt remote) wraps gdrive:immomanager-backup as its root
#      (see `rclone config show grdrivecrypt`), so every path below the bare
#      "grdrivecrypt:" prefix lives inside that one folder. "current/" and
#      "_history/" below are sibling subfolders of that single root -- both
#      still inside the one dedicated folder -- not a second top-level folder;
#      rclone requires --backup-dir to sit outside the sync destination, so
#      they can't be nested inside each other.
#
# One-time setup required before this can run (interactive, not scriptable) --
# see deploy/INSTALL.md §6. STORE THE CRYPT PASSWORD SAFELY -- losing it means
# losing access to every backed-up file.
set -euo pipefail

APP_DIR="/home/pi/source/ImmoManager"
DATA_DIR="${IMMOMANAGER_DATA_DIR:-$APP_DIR/data}"
DATE_TAG="$(date +%F)"

rclone sync "$DATA_DIR" grdrivecrypt:current \
    --backup-dir "grdrivecrypt:_history/$DATE_TAG" \
    -v
