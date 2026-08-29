# Installation (Raspberry Pi / Debian)

Target: `nerderiapi5.local` (Debian 12 bookworm, aarch64) -- Python 3.11 and
`python3.11-venv` are already present on that host, so only the genuinely missing
pieces are installed below. Mirrors the `linkedin-bot.service` pattern already
running on the same host (plain venv + systemd, `User=pi`, no containerization).

1. **Missing packages** (one-time):
   ```bash
   sudo apt update && sudo apt install rclone sqlite3
   ```

2. **Clone the repo**:
   ```bash
   mkdir -p /home/pi/source
   git clone https://github.com/wzr1337/ImmoManager.git /home/pi/source/ImmoManager
   cd /home/pi/source/ImmoManager
   ```

3. **Virtualenv**:
   ```bash
   python3.11 -m venv .venv
   .venv/bin/pip install -e .
   mkdir -p logs data
   ```

4. **Secrets**: copy your local `.env` to `/home/pi/source/ImmoManager/.env`
   (`scp .env pi@nerderiapi5.local:/home/pi/source/ImmoManager/.env`), then:
   ```bash
   chmod 600 /home/pi/source/ImmoManager/.env
   ```
   `.env` is never in git and never backed up automatically (see
   [backup/RESTORE.md](../backup/RESTORE.md)) -- keep your own copy somewhere safe
   (password manager), since it's the one thing a restore can't recover for you.

5. **Initialize the database**:
   ```bash
   .venv/bin/python -m scripts.init_db
   ```
   Then use the CLI (`.venv/bin/python -m scripts.cli --help`) to record the
   landlord profile, properties, units, tenants, and contracts before the bot is
   useful for anything.

6. **Backup remote** (interactive, one-time, needs your Google account):
   ```bash
   rclone config
   ```
   Create a `gdrive` remote (type `drive`, **scope `drive.file`** -- restricts the
   OAuth grant to only files rclone itself creates, so it structurally cannot touch
   anything else in your Drive; complete the OAuth flow in a browser, or `rclone
   config` will print a URL if run over SSH without a local browser), then a
   `grdrivecrypt` remote (type `crypt`, remote `gdrive:immomanager-backup`,
   filename encryption `standard`, and a password you store safely -- there's no
   recovery without it). See [backup/backup.sh](../backup/backup.sh).

7. **Install the systemd units**:
   ```bash
   sudo cp deploy/systemd/immomanager-bot.service /etc/systemd/system/
   sudo cp deploy/systemd/immomanager-backup.service /etc/systemd/system/
   sudo cp deploy/systemd/immomanager-backup.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now immomanager-bot.service
   sudo systemctl enable --now immomanager-backup.timer
   ```

8. **Verify**:
   ```bash
   sudo systemctl status immomanager-bot
   journalctl -u immomanager-bot -f
   ```
   Message the bot from a whitelisted Telegram account (`/start`) to confirm
   long-polling is working end to end.

9. **Templates**: drop your own styled `.docx` templates into `data/templates/`
   (they're gitignored and never overwritten by a `git pull` -- see
   `docgen/templates/` for the defaults this ships with).

## Updating after a `git pull`

```bash
cd /home/pi/source/ImmoManager
git pull
.venv/bin/pip install -e .   # in case dependencies changed
sudo systemctl restart immomanager-bot
```
