"""Tabular Q-Learning agent (off-policy)."""

from __future__ import annotations

import numpy as np

from src.agents.q_table import QTable


class QLearningAgent:
    """
    Off-policy tabular Q-Learning agent.

    The bootstrap target uses max_a' Q(s', a') regardless of the
    behaviour policy, which allows learning the greedy policy while
    exploring with epsilon-greedy action selection.
    """

    name = "q_learning"

    def __init__(
        self,
        alpha: float = 0.1,
        gamma: float = 0.95,
        epsilon: float = 0.1,
        epsilon_min: float = 0.01,
        epsilon_decay: float = 0.999,
        seed: int = 42,
    ) -> None:
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.rng = np.random.default_rng(seed)
        self.q = QTable()

    def select_action(self, state: int) -> int:
        return self.q.select_action(state, self.epsilon, self.rng)

    def update(
        self,
        state: int,
        action: int,
        reward: float,
        next_state: int,
        done: bool,
    ) -> None:
        if done:
            target = reward
        else:
            target = reward + self.gamma * self.q.max_value(next_state)
        self.q.update(state, action, target, self.alpha)

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def action_fn(self, env) -> int:
        """Compatible with evaluate.run_episode_with_policy."""
        state = env._observe()
        return self.select_action(state)

    def reset_episode(self) -> None:
        pass
