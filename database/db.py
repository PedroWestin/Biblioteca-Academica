import sqlite3
from pathlib import Path
from flask import current_app, g

SCHEMA = Path(__file__).with_name("schema.sql")


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn):
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    conn.commit()


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def init_app(app):
    def close_db(_exc=None):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    app.teardown_appcontext(close_db)
    conn = connect(app.config["DATABASE"])
    init_schema(conn)
    conn.close()
