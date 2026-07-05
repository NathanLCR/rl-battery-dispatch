"""Tabular Q-table with epsilon-greedy action selection."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from src.discretizer import N_ACTIONS, N_STATES


class QTable:
    """Fixed-size Q(s, a) table with epsilon-greedy exploration and TD updates."""

    def __init__(self, n_states: int = N_STATES, n_actions: int = N_ACTIONS) -> None:
        self.n_states = n_states
        self.n_actions = n_actions
        self.table = np.zeros((n_states, n_actions), dtype=np.float64)

    def copy(self) -> "QTable":
        other = QTable(self.n_states, self.n_actions)
        other.table = self.table.copy()
        return other

    def select_action(self, state: int, epsilon: float, rng: np.random.Generator) -> int:
        """Epsilon-greedy action selection for training."""
        if rng.random() < epsilon:
            return int(rng.integers(0, self.n_actions))
        return int(np.argmax(self.table[state]))

    def greedy_action(self, state: int) -> int:
        return int(np.argmax(self.table[state]))

    def max_value(self, state: int) -> float:
        return float(np.max(self.table[state]))

    def update(self, state: int, action: int, target: float, alpha: float) -> None:
        """TD target update: Q(s,a) <- Q(s,a) + alpha * (target - Q(s,a))."""
        self.table[state, action] += alpha * (target - self.table[state, action])

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, self.table)

    @classmethod
    def load(cls, path: Path) -> "QTable":
        table_arr = np.load(path)
        qt = cls(table_arr.shape[0], table_arr.shape[1])
        qt.table = table_arr.astype(np.float64)
        return qt
