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

import random
import time
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
    "result", "phe", "phut", "kill", "death", "assist", "damage", "gold",
    "farm", "tru", "level", "mvp", "rank_code", "rank_label", "battle_id",
]

PLAYER_COLUMNS = [
    "account_id", "player", "server", "account", "rank_code", "rank_label",
    "stars", "updated_at",
]

MATCH_NUMERIC_COLS = [
    "kill", "death", "assist", "damage", "gold", "farm", "level", "match_id",
    "battle_id", "phut", "tru",
]
PLAYER_NUMERIC_COLS = ["account_id", "stars"]

REPORTS_SHEET = "reports"
REPORT_COLUMNS = ["report_id", "player", "report_type", "date"]
REPORT_NUMERIC_COLS = ["report_id"]


# ---------------------------------------------------------------------------
# Low-level Google Sheets access
# ---------------------------------------------------------------------------


def _is_quota_error(e: Exception) -> bool:
    resp = getattr(e, "response", None)
    status = getattr(resp, "status_code", None)
    if status == 429:
        return True
    text = str(e)
    return "RESOURCE_EXHAUSTED" in text or "Quota exceeded" in text or "429" in text


def _with_retry(fn, *args, max_attempts: int = 5, **kwargs):
    """Google's free Sheets API quota (read + write requests per minute) is
    shared by the ONE service account behind this app — every person using
    the deployed dashboard at once counts against the same limit. A burst of
    activity (several teammates adding matches/reports around the same time)
    can trip that limit and gspread raises APIError (HTTP 429). Instead of
    letting that crash the page, wait a little (exponential backoff) and
    retry a few times — almost always the next attempt succeeds once the
    per-minute window rolls over."""
    delay = 1.0
    for attempt in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            if not _is_quota_error(e) or attempt == max_attempts - 1:
                raise
            time.sleep(delay + random.uniform(0, 0.5))
            delay = min(delay * 2, 8.0)


@st.cache_resource(show_spinner=False)
def _client() -> "gspread.Client":
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=SCOPES
    )
    return gspread.authorize(creds)


@st.cache_resource(show_spinner=False)
def _spreadsheet():
    """Cached for the life of the app process (not just a few seconds) —
    opening a spreadsheet by key is itself an API call, so without this every
    single read/write used to pay for it again on top of the actual read or
    write, doubling the request count for no reason."""
    return _with_retry(_client().open_by_key, st.secrets["SHEET_ID"])


@st.cache_resource(show_spinner=False)
def _worksheet(name: str, _columns: list[str]):
    """Get a tab by name, creating it (with a header row) if missing —
    cached per tab name for the life of the app process, same reasoning as
    _spreadsheet() above (the leading underscore on `_columns` tells
    Streamlit not to hash it — it's only needed the one time a tab has to be
    created, it's not part of the tab's identity).

    Streamlit can run this script more than once in close succession (page
    reload, WebSocket reconnect, multiple people opening the app at once on
    the deployed version) — two of those runs can both see the tab missing
    and both try to create it. Only one create wins; the other gets a
    "sheet already exists" error from the API. Treat that as success and
    just fetch the tab the other run created, instead of crashing.
    """
    sh = _spreadsheet()
    try:
        return _with_retry(sh.worksheet, name)
    except gspread.WorksheetNotFound:
        try:
            ws = _with_retry(
                sh.add_worksheet, title=name, rows=2000, cols=max(20, len(_columns) + 2)
            )
            _with_retry(ws.append_row, _columns, value_input_option="RAW")
            return ws
        except gspread.exceptions.APIError as e:
            if "already exists" in str(e):
                return _with_retry(sh.worksheet, name)
            raise


def _read_sheet(name: str, columns: list[str]) -> pd.DataFrame:
    """Read a tab as a DataFrame of plain strings (no auto type-guessing —
    that's what caused the rank_code "11" -> 11 bug with local CSVs)."""
    ws = _worksheet(name, columns)
    values = _with_retry(ws.get_all_values)
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
    semantics: whole-file replace, not incremental). Clears then writes
    header+body in a single `update()` call (previously a separate
    append_row + append_rows) — one less API request per save, which adds up
    when several people are saving around the same time."""
    ws = _worksheet(name, columns)
    _with_retry(ws.clear)
    body = df.reindex(columns=columns).fillna("").astype(str)
    rows = [columns] + body.values.tolist()
    _with_retry(ws.update, rows, value_input_option="RAW")


def _next_id(df: pd.DataFrame, col: str) -> int:
    if df.empty or col not in df.columns or df[col].isna().all():
        return 1
    return int(pd.to_numeric(df[col], errors="coerce").fillna(0).max()) + 1


# ---------------------------------------------------------------------------
# Matches
# ---------------------------------------------------------------------------


def _load_matches_fresh() -> pd.DataFrame:
    df = _read_sheet(MATCHES_SHEET, MATCH_COLUMNS)
    if df.empty:
        df = pd.DataFrame(columns=MATCH_COLUMNS)
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce", format="mixed")
    for col in MATCH_NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    if "mvp" in df.columns:
        df["mvp"] = df["mvp"].astype(str).str.strip().str.lower().isin(["true", "1", "yes"])
    if "phe" in df.columns:
        # Plain text column (not numeric) — just make sure old rows that
        # predate this column (blank/NaN from the sheet reindex) show "" not NaN.
        df["phe"] = df["phe"].fillna("").astype(str)
    df["date"] = df["datetime"].dt.normalize()
    df["kda"] = (df["kill"] + df["assist"]) / df["death"].clip(lower=1)
    return df.sort_values("datetime", ascending=False).reset_index(drop=True)


@st.cache_data(ttl=10, show_spinner=False)
def load_matches() -> pd.DataFrame:
    """Cached for a few seconds — Streamlit reruns the whole script on every
    click, and with several people using the deployed app at once that adds
    up to a lot of Google Sheets reads very fast (hitting the API's rate
    limit, which is what caused the "gspread.exceptions.APIError" crash).
    A short cache keeps the app responsive without saturating the quota
    (combined with _spreadsheet()/_worksheet() also being cached now, and
    _with_retry() absorbing brief quota bumps instead of crashing the page);
    add_match/delete_match/clear_all_matches always read fresh (via
    _load_matches_fresh) before writing, so this cache never causes stale
    writes — only stale *reads* for up to ~10s, and any write clears it
    immediately so the person who made the change sees it right away."""
    return _load_matches_fresh()


def save_matches(df: pd.DataFrame) -> None:
    _write_sheet(MATCHES_SHEET, MATCH_COLUMNS, df)


def add_match(row: dict) -> pd.DataFrame:
    df = _load_matches_fresh()
    row = dict(row)
    row["match_id"] = _next_id(df, "match_id")
    if not row.get("battle_id"):
        row["battle_id"] = _next_id(df, "battle_id")
    new_row = pd.DataFrame([row]).reindex(columns=MATCH_COLUMNS)
    updated = pd.concat([df.reindex(columns=MATCH_COLUMNS), new_row], ignore_index=True)
    save_matches(updated)
    load_matches.clear()
    return _load_matches_fresh()


def delete_match(match_id: int) -> pd.DataFrame:
    df = _load_matches_fresh()
    save_matches(df[df["match_id"] != match_id])
    load_matches.clear()
    return _load_matches_fresh()


def clear_all_matches() -> pd.DataFrame:
    save_matches(pd.DataFrame(columns=MATCH_COLUMNS))
    load_matches.clear()
    return _load_matches_fresh()


# ---------------------------------------------------------------------------
# Players / accounts (the roster)
# ---------------------------------------------------------------------------


def _load_players_fresh() -> pd.DataFrame:
    df = _read_sheet(PLAYERS_SHEET, PLAYER_COLUMNS)
    if df.empty:
        df = pd.DataFrame(columns=PLAYER_COLUMNS)
    for col in PLAYER_NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    if "updated_at" in df.columns:
        df["updated_at"] = pd.to_datetime(df["updated_at"], errors="coerce", format="mixed")
    return df.sort_values("player").reset_index(drop=True)


@st.cache_data(ttl=10, show_spinner=False)
def load_players() -> pd.DataFrame:
    """See load_matches() docstring — same short-cache reasoning applies."""
    return _load_players_fresh()


def save_players(df: pd.DataFrame) -> None:
    _write_sheet(PLAYERS_SHEET, PLAYER_COLUMNS, df)


def add_player(row: dict) -> pd.DataFrame:
    df = _load_players_fresh()
    row = dict(row)
    row["account_id"] = _next_id(df, "account_id")
    row.setdefault("updated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    new_row = pd.DataFrame([row]).reindex(columns=PLAYER_COLUMNS)
    updated = pd.concat([df.reindex(columns=PLAYER_COLUMNS), new_row], ignore_index=True)
    save_players(updated)
    load_players.clear()
    return _load_players_fresh()


def update_player(account_id: int, row: dict) -> pd.DataFrame:
    """Update an existing player/account row in place (keeps its account_id,
    refreshes updated_at unless the caller already supplied one)."""
    df = _load_players_fresh()
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
    load_players.clear()
    return _load_players_fresh()


def delete_player(account_id: int) -> pd.DataFrame:
    df = _load_players_fresh()
    save_players(df[df["account_id"] != account_id])
    load_players.clear()
    return _load_players_fresh()


def clear_all_players() -> pd.DataFrame:
    save_players(pd.DataFrame(columns=PLAYER_COLUMNS))
    load_players.clear()
    return _load_players_fresh()


# ---------------------------------------------------------------------------
# Behavior reports (tab "⚠️ Hành Vi") — AFK/Feeding/Bad Words/Sabotage/
# Lane Steal/Hack, nhập tay từng report một, không tự sinh dữ liệu.
# ---------------------------------------------------------------------------


def _load_reports_fresh() -> pd.DataFrame:
    df = _read_sheet(REPORTS_SHEET, REPORT_COLUMNS)
    if df.empty:
        df = pd.DataFrame(columns=REPORT_COLUMNS)
    for col in REPORT_NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce", format="mixed")
    if "report_type" in df.columns:
        df["report_type"] = df["report_type"].fillna("").astype(str)
    return df.sort_values("date", ascending=False).reset_index(drop=True)


@st.cache_data(ttl=10, show_spinner=False)
def load_reports() -> pd.DataFrame:
    """See load_matches() docstring — same short-cache reasoning applies."""
    return _load_reports_fresh()


def save_reports(df: pd.DataFrame) -> None:
    _write_sheet(REPORTS_SHEET, REPORT_COLUMNS, df)


def add_report(row: dict) -> pd.DataFrame:
    df = _load_reports_fresh()
    row = dict(row)
    row["report_id"] = _next_id(df, "report_id")
    new_row = pd.DataFrame([row]).reindex(columns=REPORT_COLUMNS)
    updated = pd.concat([df.reindex(columns=REPORT_COLUMNS), new_row], ignore_index=True)
    save_reports(updated)
    load_reports.clear()
    return _load_reports_fresh()


def delete_report(report_id: int) -> pd.DataFrame:
    df = _load_reports_fresh()
    save_reports(df[df["report_id"] != report_id])
    load_reports.clear()
    return _load_reports_fresh()


def clear_all_reports() -> pd.DataFrame:
    save_reports(pd.DataFrame(columns=REPORT_COLUMNS))
    load_reports.clear()
    return _load_reports_fresh()
