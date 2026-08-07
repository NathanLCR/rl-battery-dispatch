"""Tabular Double Q-Learning agent (reduces maximisation bias)."""

from __future__ import annotations

import numpy as np

from src.agents.q_table import QTable


class DoubleQLearningAgent:
    """Double Q-Learning with two independent Q-tables."""

    name = "double_q_learning"

    def __init__(
        self,
        alpha: float = 0.1,
        gamma: float = 0.95,
        epsilon: float = 0.1,
        epsilon_min: float = 0.01,
        epsilon_decay: float = 0.999,
        alpha_decay: float = 1.0,
        alpha_min: float = 0.01,
        seed: int = 42,
        q_init: float = 0.0,
    ) -> None:
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.alpha_decay = alpha_decay
        self.alpha_min = alpha_min
        self.rng = np.random.default_rng(seed)
        self.q_a = QTable(init_value=q_init)
        self.q_b = QTable(init_value=q_init)

    @property
    def q(self) -> QTable:
        """Combined Q_A + Q_B for evaluation and export (allocates a new table)."""
        combined = QTable()
        combined.table = self.q_a.table + self.q_b.table
        return combined

    def _combined_values(self, state: int) -> np.ndarray:
        return self.q_a.table[state] + self.q_b.table[state]

    def select_action(self, state: int) -> int:
        if self.rng.random() < self.epsilon:
            return int(self.rng.integers(0, self.q_a.n_actions))
        return int(np.argmax(self._combined_values(state)))

    def greedy_action(self, state: int) -> int:
        return int(np.argmax(self._combined_values(state)))

    def update(
        self,
        state: int,
        action: int,
        reward: float,
        next_state: int,
        done: bool,
    ) -> None:
        use_a = self.rng.random() < 0.5
        if done:
            target = reward
        elif use_a:
            best = int(np.argmax(self.q_a.table[next_state]))
            target = reward + self.gamma * self.q_b.table[next_state, best]
        else:
            best = int(np.argmax(self.q_b.table[next_state]))
            target = reward + self.gamma * self.q_a.table[next_state, best]

        if use_a:
            self.q_a.update(state, action, target, self.alpha)
        else:
            self.q_b.update(state, action, target, self.alpha)

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def decay_alpha(self) -> None:
        self.alpha = max(self.alpha_min, self.alpha * self.alpha_decay)

    def save(self, path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, np.stack([self.q_a.table, self.q_b.table]))

    def load(self, path) -> None:
        arr = np.load(path)
        if arr.ndim == 3 and arr.shape[0] == 2:
            self.q_a.table = arr[0].astype(np.float64)
            self.q_b.table = arr[1].astype(np.float64)
        else:
            self.q_a = QTable.load(path)

    def reset_episode(self) -> None:
        pass
