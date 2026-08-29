# Restore

Recovers `data/` (SQLite DB, invoice scans, generated documents, live docx
templates) from the encrypted Google Drive backup onto a fresh or repaired Pi.

## Prerequisites

- A working install through [deploy/INSTALL.md](../deploy/INSTALL.md) step 5
  (i.e. `.env` recreated from your own secure backup of it -- see that doc for why
  `.env` isn't included in this backup).
- `rclone config` already set up with the `gdrive-crypt` remote and its password
  (the same one used when the backup was created -- there is no recovery without it).

## Steps

```bash
cd /home/pi/source/ImmoManager
sudo systemctl stop immomanager-bot   # avoid writes mid-restore

rclone sync gdrive-crypt:immomanager-backup data/

sqlite3 data/immomanager.db "PRAGMA integrity_check;"   # expect: ok

sudo systemctl start immomanager-bot
sudo systemctl status immomanager-bot
```

Then, in Telegram: `/pending` (any invoices mid-flight) and check the most recent
`billing_runs` look right (via the CLI: `python -m scripts.cli list-invoices
--property-id <id> --billing-year <year>`).

## Restoring one specific file

`--backup-dir` gives free point-in-time versioning: anything a sync would have
overwritten or deleted was moved into a dated history folder instead of being
destroyed.

```bash
rclone lsf gdrive-crypt:immomanager-backup-history/    # list available dates
rclone copy gdrive-crypt:immomanager-backup-history/2026-03-05/path/to/file data/path/to/file
```
