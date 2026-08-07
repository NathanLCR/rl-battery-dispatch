"""Shared RL constants for the microgrid dispatch MDP."""

# Action space: hold, charge from surplus solar, discharge to meet load,
# grid-charge (import to charge, CA2 arbitrage extension), export (discharge
# to sell beyond covering load, CA2 arbitrage extension)
HOLD = 0
CHARGE = 1
DISCHARGE = 2
GRID_CHARGE = 3
EXPORT = 4

ACTION_NAMES = {
    HOLD: "hold",
    CHARGE: "charge",
    DISCHARGE: "discharge",
    GRID_CHARGE: "grid_charge",
    EXPORT: "export",
}
N_ACTIONS = 5

# Solar-only action set (CA1 baseline) — used by heuristics that must not arbitrage.
SOLAR_ONLY_ACTIONS = (HOLD, CHARGE, DISCHARGE)

STEP_HOURS = 0.5  # Each environment step spans one 30-minute interval
