"""
Synthetic data generator for the local Team Dashboard clone.

This mirrors the schema of the original app's two source tables:
  - report_match_history  -> one row per (player, match) they played
  - report_player_daily   -> daily aggregates per player (derived here on the
                              fly from report_match_history instead of being
                              stored separately, which keeps this file the
                              single source of truth)

HOW TO SWITCH TO REAL DATA LATER
---------------------------------
Replace `load_match_history()` and `load_accounts()` below with code that
reads your own manually-entered data (a CSV you fill in each night, a local
SQLite file, a Google Sheet export, etc.) but keep the same output columns
and the rest of the app (charts, tables, tabs) will keep working unchanged.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Team / roster configuration — edit this section to match your real team.
# ---------------------------------------------------------------------------

TEAM_NAME = "TS"

PLAYERS = ["TNhan", "TrPhuoc", "Boka", "TLinh", "Acacia", "Ducky", "Elly"]

# Relative "how much this player plays" weighting used only to shape the
# synthetic sample so the demo looks like a real, uneven roster.
PLAYER_WEIGHTS = {
    "TNhan": 3.0,
    "TrPhuoc": 2.2,
    "Boka": 2.0,
    "TLinh": 1.6,
    "Acacia": 1.15,
    "Ducky": 0.75,
    "Elly": 0.35,
}

SERVERS = ["VN", "TH", "TW"]

HEROES = [
    "Nakroth", "Liliana", "Hayate", "Annette", "Alice", "Aya", "FlowbornAD",
    "Rouie", "Zata", "Billow", "Cresht", "Violet", "Yan", "Krixi", "Baldum",
    "Zip", "Grakk", "Mina", "Tulen", "Elsu", "Raz", "TeeMee", "Capheny",
    "Y'bneth", "Enzo", "Dyadia", "Ryoma", "Bright", "Maloch", "Gildur",
    "Sinestrea", "Tachi", "Wiro", "Butterfly", "Airi", "Thane", "Ilumia",
    "Goverra", "Lauriel", "Toro", "Arum", "Omega", "Zephys", "Ishar",
    "Errol", "Kahlii", "Yena", "Slimz", "Xuan", "Xeniel",
]

GAME_MODES = ["Ranked", "Casual"]
MODE_WEIGHTS = [0.86, 0.14]

# (code, label, base skill level 0-100 used only to bias winrate/KDA)
RANK_TIERS = [
    ("11", "BK 5", 55),
    ("15", "BK 1", 60),
    ("21", "Tinh Anh 5", 64),
    ("25", "Tinh Anh 1", 68),
    ("26a", "Cao Thủ 1", 72),
    ("26b", "Đại Cao Thủ 4", 76),
    ("26c", "Đại Cao Thủ 3", 80),
    ("27", "Chiến Tướng 50*+", 85),
    ("28", "Chiến Thần 100*+", 92),
]
RANK_LOOKUP = {code: (label, skill) for code, label, skill in RANK_TIERS}

TIMEZONE_LABEL = "Asia/Ho_Chi_Minh"

# ---------------------------------------------------------------------------
# Deterministic helpers
# ---------------------------------------------------------------------------


def _stable_int(*parts: str, mod: int) -> int:
    """A hash that stays the same across runs/machines (unlike builtin hash())."""
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return int(h[:8], 16) % mod


def _rng_for(*parts: str) -> np.random.Generator:
    seed = _stable_int(*parts, mod=2**31 - 1)
    return np.random.default_rng(seed)


def hero_signature(player: str) -> list[str]:
    r = _rng_for("sig", player)
    return list(r.choice(HEROES, size=6, replace=False))


def color_for(name: str) -> str:
    """A deterministic pastel-ish hex color for avatar placeholders / charts."""
    hue = _stable_int("color", name, mod=360)
    # Fixed, pleasant saturation/lightness -> convert HSL to hex quickly.
    import colorsys

    r, g, b = colorsys.hls_to_rgb(hue / 360, 0.55, 0.55)
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


# ---------------------------------------------------------------------------
# Accounts (one or more per player, across servers)
# ---------------------------------------------------------------------------


def build_accounts() -> pd.DataFrame:
    rows = []
    dtdv_counter = 9
    aov_counter = 90
    for p in PLAYERS:
        rows.append({"player": p, "server": "VN", "account": f"dtdv{dtdv_counter:04d}"})
        dtdv_counter += 1

    r = _rng_for("accounts")
    extra_servers = ["TH", "TW"]
    for p in PLAYERS:
        if r.random() < 0.35:
            srv = r.choice(extra_servers)
            base = [row["account"] for row in rows if row["player"] == p][0]
            rows.append({"player": p, "server": srv, "account": base})
        if r.random() < 0.55:
            rows.append(
                {"player": p, "server": "VN", "account": f"aovrankvn{aov_counter:03d}"}
            )
            aov_counter += 1

    df = pd.DataFrame(rows)

    # Assign each account a "current" rank + stars + last-updated timestamp.
    ranks, stars, updated = [], [], []
    now = datetime.now()
    for _, row in df.iterrows():
        rr = _rng_for("rank", row["player"], row["server"], row["account"])
        # Better players (higher PLAYER_WEIGHTS) trend to higher tiers.
        weight = PLAYER_WEIGHTS.get(row["player"], 1.0)
        tier_bias = min(len(RANK_TIERS) - 1, int(rr.normal(4 + weight, 1.6)))
        tier_bias = max(0, tier_bias)
        code, label, _ = RANK_TIERS[tier_bias]
        ranks.append(code)
        stars.append(int(rr.integers(1, 90)))
        updated.append(now - timedelta(hours=float(rr.uniform(0, 200))))

    df["rank_code"] = ranks
    df["rank_label"] = [f"{c} - {RANK_LOOKUP[c][0]}" for c in ranks]
    df["stars"] = stars
    df["updated_at"] = updated
    return df


# ---------------------------------------------------------------------------
# Row-level match history (report_match_history equivalent)
# ---------------------------------------------------------------------------


def load_accounts() -> pd.DataFrame:
    return build_accounts()


def load_match_history(days: int = 31, end_date: datetime | None = None) -> pd.DataFrame:
    """Generate ~1 match-row per (player, game) they played over the window.

    Deterministic for a given `days` / `end_date` so the dashboard doesn't
    reshuffle itself on every rerun within the same day.
    """
    end_date = (end_date or datetime.now()).replace(
        hour=23, minute=59, second=0, microsecond=0
    )
    start_date = end_date - timedelta(days=days - 1)
    accounts = build_accounts()

    r = _rng_for("matches", start_date.date().isoformat(), str(days))

    rows = []
    battle_counter = 0
    day_dates = pd.date_range(
        pd.Timestamp(start_date).normalize(), pd.Timestamp(end_date).normalize(), freq="D"
    )

    for day in day_dates:
        # Weekly rhythm: more practice on weekends, occasional big scrim days.
        is_weekend = day.weekday() >= 5
        day_scale = (1.35 if is_weekend else 1.0) * float(r.uniform(0.55, 1.35))
        if r.random() < 0.08:
            day_scale *= float(r.uniform(1.5, 2.0))  # scrim / grind day spike

        for player in PLAYERS:
            weight = PLAYER_WEIGHTS.get(player, 1.0)
            expected = 4.0 * weight * day_scale
            n_games = int(r.poisson(max(expected, 0.05)))
            if n_games == 0:
                continue

            acct_rows = accounts[accounts["player"] == player]
            signature = hero_signature(player)

            # Minutes spread throughout the day/evening (practice sessions).
            session_start_minute = int(r.integers(11 * 60, 24 * 60))
            for g in range(n_games):
                acct = acct_rows.sample(1, random_state=int(r.integers(0, 1_000_000))).iloc[0]
                mode = r.choice(GAME_MODES, p=MODE_WEIGHTS)

                # 78% of the time play a signature hero, otherwise a random one.
                hero = r.choice(signature) if r.random() < 0.78 else r.choice(HEROES)

                win_p = np.clip(0.60 + (weight - 1.5) * 0.05 + r.normal(0, 0.05), 0.35, 0.85)
                result = "Win" if r.random() < win_p else "Loss"

                kill = int(max(0, r.normal(6.0 if result == "Win" else 3.2, 2.4)))
                death = int(max(0, r.normal(1.8 if result == "Win" else 2.8, 1.3)))
                assist = int(max(0, r.normal(9.5 if result == "Win" else 6.0, 3.4)))
                damage = int(max(2000, r.normal(78000, 28000) * (1.15 if result == "Win" else 0.9)))
                gold = int(max(1500, r.normal(9800, 2200)))
                farm = int(max(0, r.normal(30, 12)))
                level = int(np.clip(r.normal(13, 1.6), 6, 15))
                mvp = bool(result == "Win" and r.random() < 0.22)

                minute = min(23 * 60 + 59, session_start_minute + g * int(r.integers(9, 16)))
                ts = day + timedelta(minutes=minute)

                battle_id = battle_counter
                battle_counter += 1
                # Occasionally two teammates land in the same battle.
                teammate_row = None
                if r.random() < 0.05 and len(PLAYERS) > 1:
                    other_players = [p for p in PLAYERS if p != player]
                    teammate = r.choice(other_players)
                    teammate_row = {
                        "player": teammate,
                        "account": accounts[accounts["player"] == teammate].sample(
                            1, random_state=int(r.integers(0, 1_000_000))
                        ).iloc[0]["account"],
                    }

                rows.append(
                    {
                        "player": player,
                        "account": acct["account"],
                        "server": acct["server"],
                        "datetime": ts,
                        "hero": hero,
                        "mode": mode,
                        "result": result,
                        "kill": kill,
                        "death": death,
                        "assist": assist,
                        "damage": damage,
                        "gold": gold,
                        "farm": farm,
                        "level": level,
                        "mvp": mvp,
                        "rank_code": acct["rank_code"],
                        "rank_label": acct["rank_label"],
                        "battle_id": battle_id,
                    }
                )
                if teammate_row is not None:
                    rows.append(
                        {
                            "player": teammate_row["player"],
                            "account": teammate_row["account"],
                            "server": acct["server"],
                            "datetime": ts,
                            "hero": r.choice(HEROES),
                            "mode": mode,
                            "result": result,
                            "kill": int(max(0, r.normal(3.5, 2))),
                            "death": int(max(0, r.normal(3.5, 2))),
                            "assist": int(max(0, r.normal(6, 3))),
                            "damage": int(max(2000, r.normal(65000, 24000))),
                            "gold": int(max(1500, r.normal(9200, 2000))),
                            "farm": int(max(0, r.normal(26, 11))),
                            "level": int(np.clip(r.normal(12.5, 1.6), 6, 15)),
                            "mvp": False,
                            "rank_code": acct["rank_code"],
                            "rank_label": acct["rank_label"],
                            "battle_id": battle_id,
                        }
                    )

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["kda"] = (df["kill"] + df["assist"]) / df["death"].clip(lower=1)
    df["date"] = df["datetime"].dt.normalize()
    return df.sort_values("datetime", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Aggregation helpers shared across tabs
# ---------------------------------------------------------------------------


def kpi_kda(df: pd.DataFrame) -> float:
    if df.empty or df["death"].sum() == 0:
        return float(df["kill"].sum() + df["assist"].sum()) if not df.empty else 0.0
    return float((df["kill"].sum() + df["assist"].sum()) / max(df["death"].sum(), 1))


def kpi_winrate(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    return float((df["result"] == "Win").mean() * 100)


def kpi_mvp_rate(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    return float(df["mvp"].mean() * 100)
