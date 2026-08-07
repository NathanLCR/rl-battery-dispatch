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
        alpha_decay: float = 1.0,
        alpha_min: float = 0.01,
        seed: int = 42,
        q_init: float = 0.0,
        n_states: int | None = None,
        n_actions: int | None = None,
    ) -> None:
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.alpha_decay = alpha_decay
        self.alpha_min = alpha_min
        self.rng = np.random.default_rng(seed)
        from src.discretizer import N_ACTIONS, N_STATES

        self.q = QTable(
            n_states=N_STATES if n_states is None else n_states,
            n_actions=N_ACTIONS if n_actions is None else n_actions,
            init_value=q_init,
        )

    def greedy_action(self, state: int) -> int:
        return self.q.greedy_action(state)

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

    def decay_alpha(self) -> None:
        self.alpha = max(self.alpha_min, self.alpha * self.alpha_decay)

    def action_fn(self, env) -> int:
        """Compatible with evaluate.run_episode_with_policy."""
        state = env._observe()
        return self.select_action(state)

    def reset_episode(self) -> None:
        pass
