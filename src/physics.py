"""Shared battery dispatch physics (used by environment and oracle)."""

from __future__ import annotations

from src.config import Config
from src.constants import CHARGE, DISCHARGE, EXPORT, GRID_CHARGE, HOLD, STEP_HOURS


def apply_battery_action(
    soc_pct: float,
    action: int,
    pv_kwh: float,
    load_kwh: float,
    cfg: Config,
) -> dict[str, float]:
    """Simulate one 30-min step and return post-action quantities.

    Five mutually exclusive actions (no simultaneous charge+export):
      HOLD          — no battery activity.
      CHARGE        — store surplus solar (AC in → DC stored via η_c).
      DISCHARGE     — cover load deficit from the battery (DC → AC via η_d).
      GRID_CHARGE   — import from the grid purely to charge the battery.
      EXPORT        — discharge to sell beyond covering load.

    Efficiencies: stored = electrical_in * charge_efficiency;
    electrical_out = stored_drawn * discharge_efficiency.
    """
    capacity = cfg.battery_capacity_kwh
    soc_kwh = soc_pct / 100.0 * capacity
    min_soc_kwh = cfg.min_soc_pct / 100.0 * capacity
    max_soc_kwh = cfg.max_soc_pct / 100.0 * capacity
    max_charge_kwh = cfg.max_charge_kw * STEP_HOURS
    max_discharge_kwh = cfg.max_discharge_kw * STEP_HOURS
    eta_c = max(1e-6, float(cfg.charge_efficiency))
    eta_d = max(1e-6, float(cfg.discharge_efficiency))

    # Electrical (AC-side) and DC-side accounting
    charge_kwh = 0.0          # AC from PV into charger
    grid_charge_kwh = 0.0     # AC from grid into charger
    discharge_kwh = 0.0       # AC delivered to load from battery
    export_kwh = 0.0          # AC exported to grid from battery
    dc_charged_kwh = 0.0
    dc_discharged_kwh = 0.0
    invalid = False

    surplus = max(0.0, pv_kwh - load_kwh)
    deficit = max(0.0, load_kwh - pv_kwh)
    room_dc = max(0.0, max_soc_kwh - soc_kwh)
    available_dc = max(0.0, soc_kwh - min_soc_kwh)

    if action == CHARGE:
        # AC in limited by surplus, power rating, and DC room / η_c
        ac_cap = min(max_charge_kwh, surplus, room_dc / eta_c)
        charge_kwh = max(0.0, ac_cap)
        dc_charged_kwh = charge_kwh * eta_c
        if surplus > 0 and room_dc <= 0:
            invalid = True
    elif action == DISCHARGE:
        desired_ac = min(max_discharge_kwh, deficit)
        ac_cap = min(desired_ac, available_dc * eta_d)
        discharge_kwh = max(0.0, ac_cap)
        dc_discharged_kwh = discharge_kwh / eta_d
        if deficit > 0 and available_dc <= 0:
            invalid = True
    elif action == GRID_CHARGE:
        ac_cap = min(max_charge_kwh, room_dc / eta_c)
        grid_charge_kwh = max(0.0, ac_cap)
        dc_charged_kwh = grid_charge_kwh * eta_c
        if room_dc <= 0:
            invalid = True
    elif action == EXPORT:
        # Cover load deficit first, then export remaining discharge capacity.
        load_ac = min(max_discharge_kwh, deficit, available_dc * eta_d)
        discharge_kwh = max(0.0, load_ac)
        dc_for_load = discharge_kwh / eta_d if discharge_kwh > 0 else 0.0
        remaining_dc = max(0.0, available_dc - dc_for_load)
        remaining_ac_power = max(0.0, max_discharge_kwh - discharge_kwh)
        export_ac = min(remaining_ac_power, remaining_dc * eta_d)
        export_kwh = max(0.0, export_ac)
        dc_discharged_kwh = dc_for_load + (export_kwh / eta_d if export_kwh > 0 else 0.0)
        if available_dc <= 0:
            invalid = True
    elif action == HOLD:
        pass
    else:
        raise ValueError(f"Unknown action {action}")

    soc_kwh = soc_kwh + dc_charged_kwh - dc_discharged_kwh
    soc_kwh = max(0.0, min(capacity, soc_kwh))
    soc_pct_out = soc_kwh / capacity * 100.0

    grid_import_kwh = max(0.0, load_kwh - pv_kwh - discharge_kwh) + grid_charge_kwh
    solar_waste_kwh = max(0.0, pv_kwh - load_kwh - charge_kwh)

    # Soft SOC-band degradation (existing) + explicit cycling throughput
    battery_deg = 0.0
    if soc_pct_out < cfg.min_soc_pct:
        battery_deg += (cfg.min_soc_pct - soc_pct_out) / 100.0
    if soc_pct_out > cfg.max_soc_pct:
        battery_deg += (soc_pct_out - cfg.max_soc_pct) / 100.0

    throughput_kwh = dc_charged_kwh + dc_discharged_kwh
    cycling_cost = throughput_kwh * cfg.cycling_cost_per_kwh

    return {
        "charge_kwh": charge_kwh,
        "discharge_kwh": discharge_kwh,
        "grid_charge_kwh": grid_charge_kwh,
        "export_kwh": export_kwh,
        "dc_charged_kwh": dc_charged_kwh,
        "dc_discharged_kwh": dc_discharged_kwh,
        "throughput_kwh": throughput_kwh,
        "cycling_cost_aud": cycling_cost,
        "grid_import_kwh": grid_import_kwh,
        "solar_waste_kwh": solar_waste_kwh,
        "soc_pct": soc_pct_out,
        "soc_kwh": soc_kwh,
        "battery_deg": battery_deg,
        "invalid_action": float(invalid),
    }
