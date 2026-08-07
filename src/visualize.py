"""Plot greedy policy maps and Q-value heatmaps from a trained model."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from src.agents.q_table import QTable
from src.config import load_config
from src.constants import ACTION_NAMES, N_ACTIONS
from src.discretizer import (
    N_FEATURE_BINS,
    N_SOC_BINS,
    N_TIME_BINS,
    decode_state_index,
)

# hold, charge, discharge, grid_charge, export
ACTION_COLORS = ["#94a3b8", "#22c55e", "#f97316", "#0ea5e9", "#a855f7"]
SOC_LABELS = ["low", "mid", "high"]
PRICE_LABELS = ["cheap", "mid", "pricey"]
TIME_LABELS = ["Night", "Morning", "Afternoon", "Evening"]


def greedy_policy_map(q: QTable) -> np.ndarray:
    """Greedy action for each of the 324 states."""
    return np.argmax(q.table, axis=1)


def plot_policy_panels(q: QTable, out_path: Path) -> None:
    """Greedy action by SOC and price bin, one panel per time-of-day period."""
    policy = greedy_policy_map(q)
    n_states = q.table.shape[0]
    decoded = np.array([decode_state_index(s) for s in range(n_states)])  # (s,p,l,r,t)

    cmap = ListedColormap(ACTION_COLORS[:N_ACTIONS])
    fig, axes = plt.subplots(1, N_TIME_BINS, figsize=(4 * N_TIME_BINS, 3.6), sharey=True)

    for t in range(N_TIME_BINS):
        grid = np.zeros((N_SOC_BINS, N_FEATURE_BINS), dtype=int)
        for soc in range(N_SOC_BINS):
            for price in range(N_FEATURE_BINS):
                mask = (decoded[:, 0] == soc) & (decoded[:, 3] == price) & (decoded[:, 4] == t)
                acts = policy[mask]
                grid[soc, price] = np.bincount(acts, minlength=N_ACTIONS).argmax() if len(acts) else 0

        ax = axes[t]
        ax.imshow(grid, cmap=cmap, vmin=0, vmax=N_ACTIONS - 1, aspect="auto", origin="lower")
        ax.set_title(TIME_LABELS[t])
        ax.set_xticks(range(N_FEATURE_BINS), PRICE_LABELS)
        ax.set_yticks(range(N_SOC_BINS), SOC_LABELS)
        ax.set_xlabel("Price")
        if t == 0:
            ax.set_ylabel("Battery SOC")
        for soc in range(N_SOC_BINS):
            for price in range(N_FEATURE_BINS):
                ax.text(price, soc, ACTION_NAMES[grid[soc, price]][:4],
                        ha="center", va="center", fontsize=8, color="black")

    handles = [Patch(color=ACTION_COLORS[a], label=ACTION_NAMES[a]) for a in range(N_ACTIONS)]
    fig.suptitle("Greedy policy by SOC and price (majority over PV/load bins)", y=1.06)
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=9,
               frameon=False, bbox_to_anchor=(0.5, -0.08))
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_q_heatmap(q: QTable, out_path: Path) -> None:
    """Heatmap of Q(s, a) for states visited during training."""
    table = q.table
    visited = np.any(table != 0.0, axis=1)
    shown = table[visited]
    fig, ax = plt.subplots(figsize=(4.5, 9))
    im = ax.imshow(shown, aspect="auto", cmap="viridis")
    ax.set_xticks(range(N_ACTIONS), [ACTION_NAMES[a] for a in range(N_ACTIONS)])
    ax.set_xlabel("Action")
    ax.set_ylabel(f"Visited state (n={visited.sum()} of {len(table)})")
    ax.set_title("Q-values")
    fig.colorbar(im, ax=ax, shrink=0.6, label="Q(s, a)")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualise a trained Q-table")
    parser.add_argument("--model", type=Path, required=True, help="Path to Q_*.npy")
    parser.add_argument("--tag", type=str, default="", help="Suffix on output filenames")
    args = parser.parse_args()

    cfg = load_config()
    q = QTable.load(args.model)
    tag = f"_{args.tag}" if args.tag else ""

    policy_path = cfg.results_plots / f"policy_map{tag}.png"
    heatmap_path = cfg.results_plots / f"q_heatmap{tag}.png"
    plot_policy_panels(q, policy_path)
    plot_q_heatmap(q, heatmap_path)
    print(f"Saved policy map -> {policy_path}")
    print(f"Saved Q heatmap  -> {heatmap_path}")


if __name__ == "__main__":
    main()
