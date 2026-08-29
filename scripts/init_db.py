"""Create/update data/immomanager.db from db/schema.sql. Idempotent (IF NOT EXISTS)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import REPO_ROOT, load_settings
from db.connection import connect


def main() -> None:
    settings = load_settings()
    schema_sql = (REPO_ROOT / "db" / "schema.sql").read_text()

    conn = connect(settings.db_path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()

    print(f"Database ready at {settings.db_path}")


if __name__ == "__main__":
    main()
