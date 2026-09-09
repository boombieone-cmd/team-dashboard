"""Dark theme CSS + small HTML helpers to mimic the original app's look:
navy background, left-accent metric cards, pill progress bars, etc.
"""
from __future__ import annotations

import streamlit as st

BG = "#0b0f19"
CARD_BG = "#141a29"
CARD_BORDER = "#232a3d"
TEXT_MUTED = "#8b93a7"

ACCENT_PURPLE = "#8b7cf6"
ACCENT_ORANGE = "#f2a65a"
ACCENT_TEAL = "#2dd4bf"
ACCENT_YELLOW = "#f5c542"
ACCENT_RED = "#f4694a"
ACCENT_BLUE = "#5b8def"

CSS = f"""
<style>
    .stApp {{
        background-color: {BG};
    }}
    section[data-testid="stSidebar"] {{
        background-color: #0d1220;
        border-right: 1px solid {CARD_BORDER};
    }}
    div[data-testid="stMetric"] {{
        background-color: {CARD_BG};
        border: 1px solid {CARD_BORDER};
        border-radius: 10px;
        padding: 12px 16px;
    }}

    /* ---- KPI card ---- */
    .kpi-card {{
        background-color: {CARD_BG};
        border: 1px solid {CARD_BORDER};
        border-left: 4px solid var(--accent, {ACCENT_PURPLE});
        border-radius: 10px;
        padding: 14px 16px;
        height: 100%;
    }}
    .kpi-label {{
        color: {TEXT_MUTED};
        font-size: 0.72rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        font-weight: 600;
        margin-bottom: 6px;
    }}
    .kpi-value {{
        color: #f1f3fa;
        font-size: 1.9rem;
        font-weight: 700;
        line-height: 1.15;
    }}
    .kpi-sub {{
        color: {TEXT_MUTED};
        font-size: 0.72rem;
        margin-top: 4px;
    }}

    /* ---- Insight bot card ---- */
    .insight-card {{
        background-color: {CARD_BG};
        border: 1px solid {CARD_BORDER};
        border-left: 4px solid {ACCENT_PURPLE};
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 8px;
    }}
    .insight-title {{
        color: {ACCENT_PURPLE};
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 6px;
    }}
    .insight-text {{
        color: #dde1ec;
        font-size: 0.86rem;
        line-height: 1.4;
    }}
    .insight-fact {{
        color: {TEXT_MUTED};
        font-size: 0.72rem;
        margin-top: 8px;
    }}

    /* ---- Section header ---- */
    .section-header {{
        font-size: 1.05rem;
        font-weight: 700;
        color: #f1f3fa;
        margin: 6px 0 2px 0;
    }}
    .section-divider {{
        border: none;
        border-top: 1px solid {CARD_BORDER};
        margin: 4px 0 14px 0;
    }}

    /* ---- Sidebar brand ---- */
    .brand-row {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 6px;
    }}
    .brand-emoji {{ font-size: 1.6rem; }}
    .brand-name {{ font-size: 1.35rem; font-weight: 800; color: #f1f3fa; }}

    .footer-note {{
        color: {TEXT_MUTED};
        font-size: 0.72rem;
        text-align: center;
        margin-top: 18px;
        line-height: 1.6;
    }}

    /* ---- WR progress pill (used inside dataframe-like custom tables) ---- */
    .wr-track {{
        background: #1c2436;
        border-radius: 6px;
        height: 10px;
        width: 100%;
        overflow: hidden;
    }}
    .wr-fill {{
        background: linear-gradient(90deg, {ACCENT_PURPLE}, {ACCENT_BLUE});
        height: 100%;
        border-radius: 6px;
    }}

    div[data-baseweb="tab-list"] {{
        gap: 4px;
    }}

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
</style>
"""


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def kpi_card(label: str, value: str, sub: str = "", accent: str = ACCENT_PURPLE) -> str:
    return f"""
    <div class="kpi-card" style="--accent:{accent}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>
    """


def section_header(icon: str, title: str) -> None:
    st.markdown(f'<div class="section-header">{icon} {title}</div>', unsafe_allow_html=True)
    st.markdown('<hr class="section-divider" />', unsafe_allow_html=True)


def wr_bar(pct: float) -> str:
    pct = max(0.0, min(100.0, pct))
    return f"""
    <div class="wr-track"><div class="wr-fill" style="width:{pct:.1f}%"></div></div>
    """
