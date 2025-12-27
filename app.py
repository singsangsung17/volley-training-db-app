import os
import sqlite3
from typing import Optional, Tuple

import pandas as pd
import streamlit as st

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "volley_training.db")
SCHEMA_PATH = os.path.join(APP_DIR, "schema.sql")
SEED_PATH = os.path.join(APP_DIR, "seed_data.sql")


# -----------------------
# DB helpers
# -----------------------
def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute("PRAGMA foreign_keys = ON;")
    return con


def run_sql_script(con: sqlite3.Connection, path: str) -> None:
    with open(path, "r", encoding="utf-8") as f:
        con.executescript(f.read())
    con.commit()


def init_db_if_needed() -> sqlite3.Connection:
    con = connect()
    if not os.path.exists(DB_PATH):
        # fresh create
        run_sql_script(con, SCHEMA_PATH)
        run_sql_script(con, SEED_PATH)
    else:
        # sanity: if DB exists but tables missing, recreate
        try:
            con.execute("SELECT 1 FROM players LIMIT 1;").fetchone()
        except Exception:
            # rebuild
            con.close()
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
            con = connect()
            run_sql_script(con, SCHEMA_PATH)
            run_sql_script(con, SEED_PATH)
    return con


def reset_db_to_seed() -> None:
    # Close any open connections by recreating DB file (Streamlit rerun will reconnect)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = connect()
    run_sql_script(con, SCHEMA_PATH)
    run_sql_script(con, SEED_PATH)
    con.close()


def df(con: sqlite3.Connection, sql: str, params: Tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(s
