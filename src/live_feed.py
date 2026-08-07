"""Live AEMO NSW1 wholesale price feed (CA2 real-world deployment extension).

GréineQ's CA1 environment and CA2 arbitrage extension are trained on *historical*
Ausgrid/AEMO data (2012-13), replayed day-by-day. This module pulls AEMO's public
NEM dashboard feed for the *current* NSW1 dispatch price, so the dashboard can show
the trained agent's decision against a genuinely live, currently-ticking price
signal — a small, honest step from "replay" toward "deployed".

Household solar generation and load are NOT available live (no real smart-meter
feed), so live-mode decisions combine the real live price with a *representative*
solar/load profile (median-by-time-of-day from the historical dataset). This
mixed reality is deliberately surfaced in the UI rather than hidden — it is
itself the CA2 "theory vs deployed" story: price is real-time, but the rest of
the state is estimated, exactly as it would be before a genuine metering
integration existed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

AEMO_5MIN_URL = "https://visualisations.aemo.com.au/aemo/apps/api/report/5MIN"
DEFAULT_REGION = "NSW1"
REQUEST_TIMEOUT_S = 6


@dataclass
class LivePricePoint:
    settlement_time: str  # ISO-ish, AEMO local (AEST/AEDT) timestamp string
    region: str
    rrp_aud_per_mwh: float
    rrp_aud_per_kwh: float
    period_type: str
    fetched_at_utc: str


class LiveFeedError(RuntimeError):
    """Raised when the AEMO feed is unreachable or returns unexpected data."""


def _fetch_json_via_urllib(timeout: float) -> dict:
    body = json.dumps({"timeScale": ["5MIN"]}).encode("utf-8")
    req = urllib.request.Request(
        AEMO_5MIN_URL,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fetch_json_via_curl(timeout: float) -> dict:
    """Fallback transport for environments where Python's bundled CA store
    doesn't trust a local TLS-inspecting proxy but the OS trust store (used by
    curl) does — common on locked-down corporate/sandboxed networks."""
    if not shutil.which("curl"):
        raise LiveFeedError("AEMO feed unreachable via urllib and curl is not installed")
    try:
        result = subprocess.run(
            [
                "curl", "-sS", "-X", "POST", AEMO_5MIN_URL,
                "-H", "Content-Type: application/json",
                "-d", '{"timeScale":["5MIN"]}',
                "--max-time", str(int(timeout)),
            ],
            capture_output=True, text=True, timeout=timeout + 2, check=True,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        raise LiveFeedError(f"AEMO feed unreachable via curl: {exc}") from exc
    return json.loads(result.stdout)


def fetch_latest_price(region: str = DEFAULT_REGION, timeout: float = REQUEST_TIMEOUT_S) -> LivePricePoint:
    """Fetch the most recent 5-minute dispatch price for ``region`` from AEMO's
    public NEM dashboard API. Raises :class:`LiveFeedError` on any failure —
    callers must handle this and fall back to replay mode; a live demo should
    never hard-crash on an upstream outage.
    """
    try:
        payload = _fetch_json_via_urllib(timeout)
    except (urllib.error.URLError, TimeoutError, OSError):
        try:
            payload = _fetch_json_via_curl(timeout)
        except LiveFeedError as exc:
            raise LiveFeedError(f"AEMO feed unreachable: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise LiveFeedError(f"AEMO feed returned malformed data: {exc}") from exc

    rows = [r for r in payload.get("5MIN", []) if r.get("REGIONID") == region]
    if not rows:
        raise LiveFeedError(f"No rows for region {region!r} in AEMO feed response")

    rows.sort(key=lambda r: r["SETTLEMENTDATE"])
    latest = rows[-1]
    rrp_mwh = float(latest["RRP"])
    return LivePricePoint(
        settlement_time=latest["SETTLEMENTDATE"],
        region=region,
        rrp_aud_per_mwh=rrp_mwh,
        rrp_aud_per_kwh=rrp_mwh / 1000.0,
        period_type=latest.get("PERIODTYPE", "UNKNOWN"),
        fetched_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def typical_pv_load_for_time(df, hour: float) -> tuple[float, float]:
    """Median PV/load (kWh) across the historical dataset for the half-hour
    bucket nearest ``hour`` — a stand-in for real live metering, used only to
    give the live-mode demo a plausible household context alongside the real
    live price."""
    bucket = round(hour * 2) / 2.0  # nearest 30-min mark
    mask = df["timestamp"].apply(lambda ts: abs((ts.hour + ts.minute / 60.0) - bucket) < 0.01)
    subset = df[mask]
    if subset.empty:
        return 0.0, 0.0
    return float(subset["pv_kwh"].median()), float(subset["load_kwh"].median())


def current_local_hour(tz_offset_hours: float = 10.0) -> float:
    """Approximate current hour-of-day in Australia/NSW (AEST, UTC+10; does not
    account for DST — acceptable for an illustrative live-mode demo)."""
    now_utc = datetime.now(timezone.utc)
    local = now_utc + timedelta(hours=tz_offset_hours)
    return local.hour + local.minute / 60.0
