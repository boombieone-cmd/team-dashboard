"""Reusable Plotly chart builders, styled to match the dark dashboard theme."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from theme import ACCENT_BLUE, ACCENT_ORANGE, ACCENT_PURPLE, ACCENT_TEAL, ACCENT_YELLOW

PAPER_BG = "rgba(0,0,0,0)"
PLOT_BG = "rgba(0,0,0,0)"
GRID_COLOR = "#232a3d"
FONT_COLOR = "#c7cde0"


def _base_layout(fig: go.Figure, height: int = 340, legend: bool = True) -> go.Figure:
    fig.update_layout(
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=FONT_COLOR, size=12),
        margin=dict(l=10, r=10, t=10, b=10),
        height=height,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
        )
        if legend
        else None,
        showlegend=legend,
        hoverlabel=dict(bgcolor="#1c2436", font_color="#f1f3fa"),
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, zeroline=False)
    fig.update_yaxes(gridcolor=GRID_COLOR, zeroline=False)
    return fig


def daily_training_chart(daily: pd.DataFrame) -> go.Figure:
    """Bar = play count per day, line = win rate % per day (dual axis)."""
    fig = go.Figure()
    fig.add_bar(
        x=daily["date"],
        y=daily["games"],
        name="Lượt chơi",
        marker_color=ACCENT_PURPLE,
        yaxis="y1",
    )
    fig.add_trace(
        go.Scatter(
            x=daily["date"],
            y=daily["winrate"],
            name="WinRate %",
            mode="lines+markers",
            line=dict(color=ACCENT_TEAL, width=2),
            marker=dict(size=5),
            yaxis="y2",
        )
    )
    fig.update_layout(
        yaxis=dict(title="Lượt chơi", gridcolor=GRID_COLOR),
        yaxis2=dict(
            title="WinRate %",
            overlaying="y",
            side="right",
            range=[0, 100],
            showgrid=False,
        ),
    )
    return _base_layout(fig, height=360)


def top_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, color: str, x_title: str) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=df[x_col],
            y=df[y_col],
            orientation="h",
            marker_color=color,
        )
    )
    fig.update_layout(
        yaxis=dict(autorange="reversed"),
        xaxis=dict(title=x_title, gridcolor=GRID_COLOR),
    )
    return _base_layout(fig, height=max(220, 34 * len(df)), legend=False)


def rank_distribution_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=df["rank_x"],
            y=df["count"],
            marker_color=df["color"],
        )
    )
    fig.update_layout(
        xaxis=dict(title="Rank", tickangle=-45),
        yaxis=dict(title="Số tuyển thủ"),
    )
    return _base_layout(fig, height=360, legend=False)


def player_history_chart(daily: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=daily["date"], y=daily["games"], name="Lượt chơi", marker_color=ACCENT_PURPLE, yaxis="y1")
    fig.add_trace(
        go.Scatter(
            x=daily["date"], y=daily["winrate"], name="WinRate %",
            mode="lines+markers", line=dict(color=ACCENT_TEAL, width=2), yaxis="y2",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily["date"], y=daily["kda"], name="KDA",
            mode="lines+markers", line=dict(color=ACCENT_YELLOW, width=2, dash="dot"), yaxis="y2",
        )
    )
    fig.update_layout(
        yaxis=dict(title="Lượt chơi"),
        yaxis2=dict(title="WinRate % / KDA", overlaying="y", side="right", showgrid=False),
    )
    return _base_layout(fig, height=340)


def dgf_chart(daily: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily["date"], y=daily["damage"], name="Damage TB",
                              mode="lines+markers", line=dict(color=ACCENT_ORANGE, width=2), yaxis="y1"))
    fig.add_trace(go.Scatter(x=daily["date"], y=daily["gold"], name="Gold TB",
                              mode="lines+markers", line=dict(color=ACCENT_YELLOW, width=2), yaxis="y1"))
    fig.add_trace(go.Scatter(x=daily["date"], y=daily["farm"], name="Farm TB",
                              mode="lines+markers", line=dict(color=ACCENT_TEAL, width=2), yaxis="y2"))
    fig.update_layout(
        yaxis=dict(title="Damage / Gold"),
        yaxis2=dict(title="Farm", overlaying="y", side="right", showgrid=False),
    )
    return _base_layout(fig, height=340)


def hero_trend_chart(daily: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=daily["date"], y=daily["games"], name="Lượt chơi", marker_color=ACCENT_PURPLE, yaxis="y1")
    fig.add_trace(go.Scatter(x=daily["date"], y=daily["winrate"], name="WinRate %",
                              mode="lines+markers", line=dict(color=ACCENT_TEAL, width=2), yaxis="y2"))
    fig.update_layout(
        yaxis=dict(title="Lượt chơi"),
        yaxis2=dict(title="WinRate %", overlaying="y", side="right", range=[0, 100], showgrid=False),
    )
    return _base_layout(fig, height=320)


RADAR_COLORS = [ACCENT_PURPLE, ACCENT_TEAL, ACCENT_ORANGE, ACCENT_YELLOW, ACCENT_BLUE]


def compare_radar_chart(rows: list[dict], axes: list[str]) -> go.Figure:
    fig = go.Figure()
    for i, row in enumerate(rows):
        values = [row[a] for a in axes] + [row[axes[0]]]
        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=axes + [axes[0]],
                fill="toself",
                name=row["player"],
                line=dict(color=RADAR_COLORS[i % len(RADAR_COLORS)]),
                opacity=0.75,
            )
        )
    fig.update_layout(
        polar=dict(
            bgcolor=PLOT_BG,
            radialaxis=dict(visible=True, range=[0, 100], gridcolor=GRID_COLOR, showticklabels=True),
            angularaxis=dict(gridcolor=GRID_COLOR),
        ),
        paper_bgcolor=PAPER_BG,
        font=dict(color=FONT_COLOR, size=12),
        margin=dict(l=30, r=30, t=20, b=20),
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
    )
    return fig
