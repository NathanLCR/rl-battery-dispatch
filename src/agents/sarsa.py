"""Tabular SARSA agent (on-policy)."""

from __future__ import annotations

import numpy as np

from src.agents.q_table import QTable


class SARSAAgent:
    """
    On-policy tabular SARSA agent.

    The bootstrap target uses Q(s', a') where a' is the next action
    actually selected under the current epsilon-greedy policy.
    """

    name = "sarsa"

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
        self._next_action: int | None = None

    def greedy_action(self, state: int) -> int:
        return self.q.greedy_action(state)

    def select_action(self, state: int) -> int:
        return self.q.select_action(state, self.epsilon, self.rng)

    def start_episode(self, state: int) -> int:
        """Select the first action and cache it for the SARSA update chain."""
        self._next_action = self.select_action(state)
        return self._next_action

    def update(
        self,
        state: int,
        action: int,
        reward: float,
        next_state: int,
        done: bool,
    ) -> int:
        if done:
            target = reward
            next_action = 0
        else:
            next_action = self.select_action(next_state)
            target = reward + self.gamma * self.q.table[next_state, next_action]
        self.q.update(state, action, target, self.alpha)
        self._next_action = next_action if not done else None
        return next_action if not done else action

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def decay_alpha(self) -> None:
        self.alpha = max(self.alpha_min, self.alpha * self.alpha_decay)

    def action_fn(self, env) -> int:
        state = env._observe()
        if self._next_action is None:
            return self.start_episode(state)
        action = self._next_action
        return action

    def reset_episode(self) -> None:
        self._next_action = None

    def step_after_env(
        self,
        state: int,
        action: int,
        reward: float,
        next_state: int,
        done: bool,
    ) -> None:
        """Call after env.step during training."""
        self.update(state, action, reward, next_state, done)
