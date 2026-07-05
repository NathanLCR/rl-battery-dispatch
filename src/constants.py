"""Shared RL constants for the microgrid dispatch MDP."""

# Action space: hold, charge from surplus solar, discharge to meet load
HOLD = 0
CHARGE = 1
DISCHARGE = 2

ACTION_NAMES = {HOLD: "hold", CHARGE: "charge", DISCHARGE: "discharge"}
N_ACTIONS = 3

STEP_HOURS = 0.5  # Each environment step spans one 30-minute interval
