"""Day dispatch timeline animation for the dashboard landing page."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation, PillowWriter
import pandas as pd

ACTION_COLORS = {"hold": "#93A3B5", "charge": "#5FB07E", "discharge": "#E68A4E"}
ACTION_LABELS = {"hold": "HOLD", "charge": "CHARGE", "discharge": "DISCHARGE"}
GRID_ROWS, GRID_COLS = 4, 12  # 48 half-hour steps

NAVY = "#37475A"
SLATE = "#6C7A88"


def pick_demo_day(df: pd.DataFrame, days: list[str]) -> str:
    """Choose a test day with strong solar for a readable demo."""
    best_day, best_pv = days[0], -1.0
    for day in days:
        ep = df[df["episode_day"] == day]
        if len(ep) != 48:
            continue
        total_pv = ep["pv_kwh"].sum()
        if total_pv > best_pv:
            best_pv = total_pv
            best_day = day
    return best_day


def _draw_timeline_grid(ax, trace: pd.DataFrame, step_idx: int) -> None:
    map_y0 = 0.35
    cell_w, cell_h = 0.72, 0.72
    gap = 0.08
    x0 = 0.55

    for i in range(min(48, len(trace))):
        row, col = divmod(i, GRID_COLS)
        cx = x0 + col * (cell_w + gap)
        cy = map_y0 + (GRID_ROWS - 1 - row) * (cell_h + gap)
        action = trace.iloc[i]["action"]
        fc = ACTION_COLORS.get(action, "#CBD5E1")
        ec = "#37475A" if i == step_idx else "#B9CADC"
        lw = 2.8 if i == step_idx else 0.8
        ax.add_patch(mpatches.FancyBboxPatch(
            (cx, cy), cell_w, cell_h, boxstyle="round,pad=0.02",
            fc=fc, ec=ec, lw=lw, alpha=0.95 if i <= step_idx else 0.35,
        ))
        if i == step_idx:
            ax.text(cx + cell_w / 2, cy + cell_h / 2, "●", ha="center", va="center",
                    fontsize=14, color="white", fontweight="bold")


def render_frame(ax, trace: pd.DataFrame, episode_df: pd.DataFrame, step_idx: int, margin: float, day: str) -> None:
    ax.clear()
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10.5)
    ax.axis("off")

    row = trace.iloc[step_idx]
    action = row["action"]
    soc = float(row["soc_pct"])
    pv = float(row["pv_kwh"])
    load = float(row["load_kwh"])
    grid = float(row["grid_import_kwh"])
    wholesale = float(row["price_per_kwh"])
    retail = wholesale + margin
    time_label = row["time_label"]
    ac = ACTION_COLORS.get(action, "#93A3B5")

    ax.text(5.0, 10.25, f"GréineQ dispatch  ·  {day}", ha="center", fontsize=12,
            fontweight="bold", color=NAVY)

    sun_r = 0.35 + min(1.2, pv * 2.5)
    ax.add_patch(plt.Circle((1.2, 7.2), sun_r, color="#E6C074", ec="#C6923A", lw=2))
    ax.text(1.2, 5.55, "Solar", ha="center", fontsize=9, color="#6B531B")

    bx, by, bw, bh = 3.6, 5.8, 1.4, 2.8
    ax.add_patch(mpatches.FancyBboxPatch(
        (bx, by), bw, bh, boxstyle="round,pad=0.02", fc="#EDE7DB", ec="#5E7690", lw=2
    ))
    fill_h = max(0.05, bh * soc / 100.0)
    ax.add_patch(mpatches.Rectangle(
        (bx + 0.08, by + 0.08), bw - 0.16, fill_h - 0.08,
        fc=ac, ec="none", alpha=0.85,
    ))
    ax.add_patch(mpatches.Rectangle((bx + bw * 0.35, by + bh), bw * 0.3, 0.25, fc="#5E7690"))
    ax.text(bx + bw / 2, by - 0.35, f"Battery\n{soc:.0f}%", ha="center", fontsize=9, color=NAVY)

    hx, hy = 6.4, 6.0
    ax.add_patch(mpatches.Polygon(
        [[hx, hy + 1.6], [hx + 1.2, hy + 0.9], [hx + 2.4, hy + 1.6], [hx + 2.4, hy], [hx, hy]],
        closed=True, fc="#5E7690", ec="#3B4A5C", lw=2,
    ))
    ax.text(hx + 1.2, hy - 0.45, f"Load\n{load:.2f} kWh", ha="center", fontsize=9, color=NAVY)

    ax.add_patch(mpatches.FancyBboxPatch(
        (8.2, 6.2), 1.4, 1.8, boxstyle="round,pad=0.02", fc="#F2E3DA", ec="#C08A6A", lw=2
    ))
    ax.text(8.9, 7.1, f"${retail:.2f}", ha="center", fontsize=10, fontweight="bold", color="#9A552A")
    ax.text(8.9, 5.7, f"Grid\n{grid:.2f} kWh", ha="center", fontsize=8, color=SLATE)

    if action == "charge" and pv > load:
        ax.annotate("", xy=(bx, 7.5), xytext=(1.8, 7.5),
                    arrowprops=dict(arrowstyle="->", color=ac, lw=3))
    elif action == "discharge" and load > pv:
        ax.annotate("", xy=(hx, 7.0), xytext=(bx + bw, 7.0),
                    arrowprops=dict(arrowstyle="->", color=ac, lw=3))

    ax.add_patch(mpatches.FancyBboxPatch(
        (3.2, 9.0), 3.6, 0.75, boxstyle="round,pad=0.04", fc=ac, ec="none", alpha=0.95
    ))
    ax.text(5.0, 9.37, ACTION_LABELS.get(action, action.upper()), ha="center", va="center",
            fontsize=13, fontweight="bold", color="white")
    ax.text(5.0, 8.55, f"Step {step_idx + 1}/48  ·  {time_label}", ha="center", fontsize=10, color=NAVY)

    ax.text(5.0, 4.35, "Daily timeline — each cell is one 30-minute interval", ha="center", fontsize=9, color=SLATE)
    _draw_timeline_grid(ax, trace, step_idx)

    legend_y = 0.08
    for j, (name, color) in enumerate(ACTION_COLORS.items()):
        lx = 2.2 + j * 2.2
        ax.add_patch(mpatches.Rectangle((lx, legend_y), 0.35, 0.35, fc=color))
        ax.text(lx + 0.5, legend_y + 0.17, name.capitalize(), va="center", fontsize=8, color=SLATE)


def build_demo_gif(
    trace: pd.DataFrame,
    episode_df: pd.DataFrame,
    day: str,
    retail_margin: float,
    fps: int = 3,
    cache_path: Path | None = None,
) -> bytes:
    """Build an animated GIF; optionally cache to disk."""
    if cache_path and cache_path.exists():
        return cache_path.read_bytes()

    fig, ax = plt.subplots(figsize=(10, 7))
    fig.patch.set_facecolor("#FBF7EE")

    def update(frame: int):
        render_frame(ax, trace, episode_df, frame, retail_margin, day)
        return []

    anim = FuncAnimation(fig, update, frames=len(trace), interval=1000 // fps, blit=False)

    if cache_path:
        out_path = cache_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        fd, out_name = tempfile.mkstemp(suffix=".gif")
        os.close(fd)
        out_path = Path(out_name)

    anim.save(str(out_path), writer=PillowWriter(fps=fps))
    plt.close(fig)
    gif_bytes = out_path.read_bytes()

    if not cache_path:
        out_path.unlink(missing_ok=True)

    return gif_bytes
