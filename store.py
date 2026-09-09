"""
Persistent data store — matches AND roster (players/accounts).

Backed by a Google Sheet (not local CSV) so that:
  - data survives Streamlit Community Cloud restarts (the cloud filesystem
    is wiped every time the app sleeps/redeploys — local CSV files would
    not survive that);
  - everyone who opens the deployed app (or runs it locally) reads/writes
    the exact same live data, no manual syncing needed.

Nothing is auto-generated: both sheet tabs ("matches" and "players") start
empty (just the header row) and only change through the add_*/delete_*
functions below, which the "Thêm ..." forms in app.py call.

Setup required (see README.md, section "Deploy lên Internet"):
  1. A Google Cloud service account with the Sheets + Drive APIs enabled,
     its JSON key pasted into Streamlit secrets under [gcp_service_account].
  2. A Google Sheet, shared (Editor) with that service account's email,
     with its ID saved into Streamlit secrets as SHEET_ID.
"""
from __future__ import annotations

from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

MATCHES_SHEET = "matches"
PLAYERS_SHEET = "players"

MATCH_COLUMNS = [
    "match_id", "player", "account", "server", "datetime", "hero", "mode",
    "result", "kill", "death", "assist", "damage", "gold", "farm", "level",
    "mvp", "rank_code", "rank_label", "battle_id",
]

PLAYER_COLUMNS = [
    "account_id", "player", "server", "account", "rank_code", "rank_label",
    "stars", "updated_at",
]

MATCH_NUMERIC_COLS = ["kill", "death", "assist", "damage", "gold", "farm", "level", "match_id", "battle_id"]
PLAYER_NUMERIC_COLS = ["account_id", "stars"]


# ---------------------------------------------------------------------------
# Low-level Google Sheets access
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner=False)
def _client() -> "gspread.Client":
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=SCOPES
    )
    return gspread.authorize(creds)


def _spreadsheet():
    return _client().open_by_key(st.secrets["SHEET_ID"])


def _worksheet(name: str, columns: list[str]):
    """Get a tab by name, creating it (with a header row) if missing.

    Streamlit can run this script more than once in close succession (page
    reload, WebSocket reconnect, multiple people opening the app at once on
    the deployed version) — two of those runs can both see the tab missing
    and both try to create it. Only one create wins; the other gets a
    "sheet already exists" error from the API. Treat that as success and
    just fetch the tab the other run created, instead of crashing.
    """
    sh = _spreadsheet()
    try:
        return sh.worksheet(name)
    except gspread.WorksheetNotFound:
        try:
            ws = sh.add_worksheet(title=name, rows=2000, cols=max(20, len(columns) + 2))
            ws.append_row(columns, value_input_option="RAW")
            return ws
        except gspread.exceptions.APIError as e:
            if "already exists" in str(e):
                return sh.worksheet(name)
            raise


def _read_sheet(name: str, columns: list[str]) -> pd.DataFrame:
    """Read a tab as a DataFrame of plain strings (no auto type-guessing —
    that's what caused the rank_code "11" -> 11 bug with local CSVs)."""
    ws = _worksheet(name, columns)
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame(columns=columns)
    header, body = values[0], values[1:]
    width = len(header)
    body = [row + [""] * (width - len(row)) for row in body]
    body = [row for row in body if any(cell.strip() for cell in row)]
    if not body:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(body, columns=header)
    return df.reindex(columns=columns)


def _write_sheet(name: str, columns: list[str], df: pd.DataFrame) -> None:
    """Overwrite a tab entirely with df (mirrors the old save_*-to-CSV
    semantics: whole-file replace, not incremental)."""
    ws = _worksheet(name, columns)
    ws.clear()
    ws.append_row(columns, value_input_option="RAW")
    body = df.reindex(columns=columns).fillna("").astype(str)
    if not body.empty:
        ws.append_rows(body.values.tolist(), value_input_option="RAW")


def _next_id(df: pd.DataFrame, col: str) -> int:
    if df.empty or col not in df.columns or df[col].isna().all():
        return 1
    return int(pd.to_numeric(df[col], errors="coerce").fillna(0).max()) + 1


# ---------------------------------------------------------------------------
# Matches
# ---------------------------------------------------------------------------


def load_matches() -> pd.DataFrame:
    df = _read_sheet(MATCHES_SHEET, MATCH_COLUMNS)
    if df.empty:
        df = pd.DataFrame(columns=MATCH_COLUMNS)
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    for col in MATCH_NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    if "mvp" in df.columns:
        df["mvp"] = df["mvp"].astype(str).str.strip().str.lower().isin(["true", "1", "yes"])
    df["date"] = df["datetime"].dt.normalize()
    df["kda"] = (df["kill"] + df["assist"]) / df["death"].clip(lower=1)
    return df.sort_values("datetime", ascending=False).reset_index(drop=True)


def save_matches(df: pd.DataFrame) -> None:
    _write_sheet(MATCHES_SHEET, MATCH_COLUMNS, df)


def add_match(row: dict) -> pd.DataFrame:
    df = load_matches()
    row = dict(row)
    row["match_id"] = _next_id(df, "match_id")
    if not row.get("battle_id"):
        row["battle_id"] = _next_id(df, "battle_id")
    new_row = pd.DataFrame([row]).reindex(columns=MATCH_COLUMNS)
    updated = pd.concat([df.reindex(columns=MATCH_COLUMNS), new_row], ignore_index=True)
    save_matches(updated)
    return load_matches()


def delete_match(match_id: int) -> pd.DataFrame:
    df = load_matches()
    save_matches(df[df["match_id"] != match_id])
    return load_matches()


def clear_all_matches() -> pd.DataFrame:
    save_matches(pd.DataFrame(columns=MATCH_COLUMNS))
    return load_matches()


# ---------------------------------------------------------------------------
# Players / accounts (the roster)
# ---------------------------------------------------------------------------


def load_players() -> pd.DataFrame:
    df = _read_sheet(PLAYERS_SHEET, PLAYER_COLUMNS)
    if df.empty:
        df = pd.DataFrame(columns=PLAYER_COLUMNS)
    for col in PLAYER_NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    if "updated_at" in df.columns:
        df["updated_at"] = pd.to_datetime(df["updated_at"], errors="coerce")
    return df.sort_values("player").reset_index(drop=True)


def save_players(df: pd.DataFrame) -> None:
    _write_sheet(PLAYERS_SHEET, PLAYER_COLUMNS, df)


def add_player(row: dict) -> pd.DataFrame:
    df = load_players()
    row = dict(row)
    row["account_id"] = _next_id(df, "account_id")
    row.setdefault("updated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    new_row = pd.DataFrame([row]).reindex(columns=PLAYER_COLUMNS)
    updated = pd.concat([df.reindex(columns=PLAYER_COLUMNS), new_row], ignore_index=True)
    save_players(updated)
    return load_players()


def update_player(account_id: int, row: dict) -> pd.DataFrame:
    """Update an existing player/account row in place (keeps its account_id,
    refreshes updated_at unless the caller already supplied one)."""
    df = load_players()
    idx = df.index[df["account_id"] == account_id]
    if len(idx) == 0:
        raise ValueError(f"Không tìm thấy tuyển thủ với account_id={account_id}")
    row = dict(row)
    row["account_id"] = account_id
    row.setdefault("updated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    for col, val in row.items():
        if col in df.columns:
            df.loc[idx, col] = val
    save_players(df)
    return load_players()


def delete_player(account_id: int) -> pd.DataFrame:
    df = load_players()
    save_players(df[df["account_id"] != account_id])
    return load_players()


def clear_all_players() -> pd.DataFrame:
    save_players(pd.DataFrame(columns=PLAYER_COLUMNS))
    return load_players()
