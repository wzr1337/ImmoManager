"""Create/update data/immomanager.db from db/schema.sql, then apply any files in
db/migrations/ in filename order. Idempotent: schema.sql uses CREATE TABLE IF NOT
EXISTS, and a migration that's already been applied (e.g. an ALTER TABLE ADD
COLUMN whose column already exists) is skipped -- there's no migrations-applied
ledger table, which is fine at this project's scale (a handful of migrations
against one SQLite file), but means every migration must itself tolerate re-running
(ADD COLUMN is the main case; SQLite has no ADD COLUMN IF NOT EXISTS, so we detect
"duplicate column name" specifically rather than swallowing all errors)."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import REPO_ROOT, load_settings
from db.connection import connect


def _apply_migrations(conn: sqlite3.Connection) -> None:
    migrations_dir = REPO_ROOT / "db" / "migrations"
    for path in sorted(migrations_dir.glob("*.sql")):
        try:
            conn.executescript(path.read_text())
            conn.commit()
            print(f"  applied {path.name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"  skipped {path.name} (already applied)")
            else:
                raise


def main() -> None:
    settings = load_settings()
    schema_sql = (REPO_ROOT / "db" / "schema.sql").read_text()

    conn = connect(settings.db_path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
        _apply_migrations(conn)
    finally:
        conn.close()

    print(f"Database ready at {settings.db_path}")


if __name__ == "__main__":
    main()
