"""Per-request DB connection helper. SQLite + WAL handles short-lived connections
from a single-user bot fine; opening one per handler call avoids any concern about
sharing a sqlite3.Connection across asyncio tasks."""

from __future__ import annotations

import sqlite3

from telegram.ext import ContextTypes

from config.settings import Settings
from db.connection import connect


def get_settings(context: ContextTypes.DEFAULT_TYPE) -> Settings:
    return context.bot_data["settings"]


def get_conn(context: ContextTypes.DEFAULT_TYPE) -> sqlite3.Connection:
    return connect(get_settings(context).db_path)
