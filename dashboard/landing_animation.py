"""Day dispatch timeline animation — matches Q-Learning system design layout."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation, PillowWriter
import pandas as pd

# System design palette (matches dispatch widget + Figma reference)
CHARGE = "#22c55e"
DISCHARGE = "#f59c1a"
HOLD = "#94a3b8"
ACTION_COLORS = {"hold": HOLD, "charge": CHARGE, "discharge": DISCHARGE}
ACTION_LABELS = {"hold": "HOLD", "charge": "CHARGE", "discharge": "DISCHARGE"}
GRID_ROWS, GRID_COLS = 4, 12  # 48 half-hour steps

BG = "#FAFAF8"
TEXT = "#37475A"
TEXT_MUTED = "#64748b"
SOLAR = "#fbbf24"
SOLAR_EDGE = "#d97706"
BATTERY_SHELL = "#e2e8f0"
BATTERY_EDGE = "#64748b"
LOAD_FILL = "#6366f1"
LOAD_EDGE = "#4338ca"
GRID_BOX = "#fef3c7"
GRID_EDGE = "#d97706"


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
    """4×12 grid — orange discharge, green charge, grey hold; white dot on active step."""
    map_y0 = 0.55
    cell_w, cell_h = 0.72, 0.72
    gap = 0.08
    x0 = 0.55

    for i in range(min(48, len(trace))):
        row, col = divmod(i, GRID_COLS)
        cx = x0 + col * (cell_w + gap)
        cy = map_y0 + (GRID_ROWS - 1 - row) * (cell_h + gap)
        action = trace.iloc[i]["action"]
        fc = ACTION_COLORS.get(action, HOLD)
        alpha = 0.95 if i <= step_idx else 0.28
        h = cell_h * 1.15 if i == step_idx else cell_h
        y_off = (cell_h - h) / 2 if i == step_idx else 0
        ax.add_patch(mpatches.FancyBboxPatch(
            (cx, cy + y_off), cell_w, h, boxstyle="round,pad=0.02",
            fc=fc, ec="none", lw=0, alpha=alpha,
        ))
        if i == step_idx:
            ax.text(cx + cell_w / 2, cy + cell_h / 2, "●", ha="center", va="center",
                    fontsize=11, color="white", fontweight="bold", zorder=5)


def _draw_solar(ax, pv: float, x: float = 1.15, y: float = 7.15) -> None:
    r = 0.38 + min(1.0, pv * 2.2)
    glow = plt.Circle((x, y), r + 0.12, color=SOLAR, alpha=0.22, zorder=1)
    ax.add_patch(glow)
    ax.add_patch(plt.Circle((x, y), r, color=SOLAR, ec=SOLAR_EDGE, lw=1.8, zorder=2))
    ax.text(x, y - r - 0.42, "Solar", ha="center", fontsize=9, color=TEXT_MUTED, fontweight="600")


def _draw_battery(ax, soc: float, bx: float = 3.55, by: float = 5.55, bw: float = 1.35, bh: float = 3.0) -> None:
    ax.add_patch(mpatches.FancyBboxPatch(
        (bx, by), bw, bh, boxstyle="round,pad=0.03", fc=BATTERY_SHELL, ec=BATTERY_EDGE, lw=2, zorder=2
    ))
    fill_h = max(0.12, (bh - 0.16) * soc / 100.0)
    ax.add_patch(mpatches.FancyBboxPatch(
        (bx + 0.08, by + 0.08), bw - 0.16, fill_h,
        boxstyle="round,pad=0.02", fc=CHARGE, ec="none", alpha=0.92, zorder=3
    ))
    ax.add_patch(mpatches.Rectangle(
        (bx + bw * 0.32, by + bh), bw * 0.36, 0.22, fc=BATTERY_EDGE, zorder=2
    ))
    pct_y = by + fill_h / 2 if fill_h > 0.45 else by + bh / 2
    ax.text(bx + bw / 2, pct_y, f"{soc:.0f}%", ha="center", va="center",
            fontsize=10, fontweight="bold", color="white" if fill_h > 0.45 else TEXT, zorder=4)
    ax.text(bx + bw / 2, by - 0.38, "Battery", ha="center", fontsize=9, color=TEXT_MUTED, fontweight="600")


def _draw_load(ax, load: float, hx: float = 6.35, hy: float = 5.85) -> None:
    peak = hy + 1.75
    ax.add_patch(mpatches.Polygon(
        [[hx, hy], [hx + 0.55, peak], [hx + 1.15, hy + 1.05],
         [hx + 1.75, peak - 0.15], [hx + 2.35, hy]],
        closed=True, fc=LOAD_FILL, ec=LOAD_EDGE, lw=1.8, alpha=0.88, zorder=2
    ))
    ax.text(hx + 1.15, hy - 0.42, f"Load\n{load:.2f} kWh", ha="center", fontsize=8.5,
            color=TEXT_MUTED, fontweight="600", linespacing=1.25)


def _draw_grid_box(ax, grid: float, retail: float, gx: float = 8.35, gy: float = 6.35) -> None:
    alert = grid > 0.01
    fc = "#fee2e2" if alert else GRID_BOX
    ec = "#f87171" if alert else GRID_EDGE
    ax.add_patch(mpatches.FancyBboxPatch(
        (gx, gy), 1.35, 1.75, boxstyle="round,pad=0.04", fc=fc, ec=ec, lw=1.8, zorder=2
    ))
    ax.text(gx + 0.67, gy + 1.15, f"${retail:.2f}", ha="center", fontsize=10,
            fontweight="bold", color="#b45309" if not alert else "#dc2626", zorder=3)
    ax.text(gx + 0.67, gy - 0.38, f"Grid\n{grid:.2f} kWh", ha="center", fontsize=8,
            color=TEXT_MUTED, fontweight="600", linespacing=1.2)


def _draw_flow_arrow(ax, action: str, pv: float, load: float,
                     bx: float, bw: float, hx: float) -> None:
    ac = ACTION_COLORS.get(action, HOLD)
    y = 7.05
    if action == "charge" and pv > 0.05:
        ax.annotate("", xy=(bx, y), xytext=(1.85, y),
                    arrowprops=dict(arrowstyle="-|>", color=ac, lw=3.2, mutation_scale=14))
    elif action == "discharge" and load > pv:
        ax.annotate("", xy=(hx, y - 0.15), xytext=(bx + bw + 0.05, y - 0.15),
                    arrowprops=dict(arrowstyle="-|>", color=ac, lw=3.2, mutation_scale=14))


def render_frame(
    ax,
    trace: pd.DataFrame,
    episode_df: pd.DataFrame,
    step_idx: int,
    margin: float,
    day: str,
) -> None:
    ax.clear()
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10.5)
    ax.axis("off")
    ax.set_facecolor(BG)

    row = trace.iloc[step_idx]
    action = row["action"]
    soc = float(row["soc_pct"])
    pv = float(row["pv_kwh"])
    load = float(row["load_kwh"])
    grid = float(row["grid_import_kwh"])
    wholesale = float(row["price_per_kwh"])
    retail = wholesale + margin
    time_label = row["time_label"]
    ac = ACTION_COLORS.get(action, HOLD)

    ax.text(5.0, 10.05, f"GréineQ dispatch  ·  {day}", ha="center", fontsize=11.5,
            fontweight="bold", color=TEXT)

    badge_w, badge_h = 2.8, 0.72
    ax.add_patch(mpatches.FancyBboxPatch(
        (5.0 - badge_w / 2, 9.05), badge_w, badge_h,
        boxstyle="round,pad=0.06", fc=ac, ec="none", alpha=0.96, zorder=3
    ))
    ax.text(5.0, 9.41, ACTION_LABELS.get(action, action.upper()), ha="center", va="center",
            fontsize=12, fontweight="bold", color="white", zorder=4)
    ax.text(5.0, 8.72, f"Step {step_idx + 1}/48  ·  {time_label}", ha="center",
            fontsize=9.5, color=TEXT_MUTED, fontweight="600")

    _draw_solar(ax, pv)
    _draw_battery(ax, soc)
    _draw_load(ax, load)
    _draw_grid_box(ax, grid, retail)
    _draw_flow_arrow(ax, action, pv, load, bx=3.55, bw=1.35, hx=6.35)

    ax.text(5.0, 4.55, "Daily timeline — each cell is one 30-minute interval",
            ha="center", fontsize=8.5, color=TEXT_MUTED)
    _draw_timeline_grid(ax, trace, step_idx)

    legend_y = 0.12
    for j, (name, color) in enumerate(ACTION_COLORS.items()):
        lx = 2.15 + j * 2.25
        ax.add_patch(mpatches.FancyBboxPatch(
            (lx, legend_y), 0.32, 0.32, boxstyle="round,pad=0.02", fc=color, ec="none"
        ))
        ax.text(lx + 0.48, legend_y + 0.16, name.capitalize(), va="center",
                fontsize=8, color=TEXT_MUTED, fontweight="600")


def build_demo_gif(
    trace: pd.DataFrame,
    episode_df: pd.DataFrame,
    day: str,
    retail_margin: float,
    fps: int = 4,
    cache_path: Path | None = None,
) -> bytes:
    """Build an animated GIF; optionally cache to disk."""
    if cache_path and cache_path.exists() and cache_path.stat().st_size > 0:
        return cache_path.read_bytes()

    fig, ax = plt.subplots(figsize=(10, 6.8))
    fig.patch.set_facecolor(BG)

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
