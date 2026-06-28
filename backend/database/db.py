from __future__ import annotations

import os
import sqlite3
from pathlib import Path


DEFAULT_DATABASE_PATH = Path("retailsignal.db")


def database_path_from_url(database_url: str | None = None) -> Path:
    url = database_url or os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DATABASE_PATH}")
    if not url.startswith("sqlite:///"):
        raise ValueError("Only sqlite:/// URLs are supported by the initial foundation")
    return Path(url.removeprefix("sqlite:///"))


def connect(database_url: str | None = None) -> sqlite3.Connection:
    path = database_path_from_url(database_url)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    connection.executescript(schema_path.read_text(encoding="utf-8"))
    connection.commit()
