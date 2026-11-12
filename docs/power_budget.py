#!/usr/bin/env python3
"""Battery-life model for the H2 soil sensor v3 (CR123A + TPS63900 + ESP32-H2 ICD)
with one capacitive soil moisture module v1.2 on the switched VSENS rail.

All charges are at the 3.3 V rail; the TPS63900 converts them to battery current.
Edit the parameters and run:  python3 docs/power_budget.py
"""

BAT_MAH = 1500          # CR123A nominal capacity (to 2.0 V, low drain)
USABLE = 0.85           # derating: temperature, end-voltage, pulse capability
SELF_DISCHARGE = 0.01   # per year (Li-MnO2 ~1 %/year)
V_BAT = 3.0             # mean loaded battery voltage over life (V)
V_OUT = 3.3             # rail
ETA_SLEEP = 0.88        # TPS63900 efficiency at ~30 uA load
ETA_ACTIVE = 0.90       # at mA loads
IQ_BB_UA = 0.075        # TPS63900 quiescent current (input side)

SLEEP_UA = 25.0         # ESP32-H2 light sleep, TOP domain + radio off (datasheet 25 uA)
BOARD_LEAK_UA = 0.3     # MOSFET Idss, MLCC IR, ADC pins Hi-Z, TVS D3 unbiased; VSENS + module OFF (estimate)

# ---- one measurement (sensors.c): VSENS on (1 ms soft start) -> wait CONFIG_SOIL_SETTLE_MS in light
#      sleep -> battery divider 3 ms -> ADC (64 + 32 samples) -> everything off
VSENS_ON_S = 1.55       # CONFIG_SOIL_SETTLE_MS (1500 ms) + divider/ADC time
SOIL_MODULE_MA = 5.0    # capacitive soil module v1.2 (DFRobot SEN0193 wiki: 5 mA)
MCU_AWAKE_S = 0.03      # CPU awake: soft start, divider wait, ADC, log (sensors.h: ~30-120 ms; no I2C on v3)
MCU_AWAKE_MA = 7.0      # ESP32-H2 at 96 MHz, radio off (same assumption as the v1/v2 models)
# battery divider: VBAT/200k = 15 uA for ~10 ms per measurement -> negligible, not modelled

REPORT_MAS = 1.5        # one report: active-mode window (fast poll) + TX/RX + MRP ack + crypto
MAX_REPORT_INTERVAL_S = 3600   # CONFIG_SOIL_MAX_REPORT_INTERVAL_S (heartbeat)

SCENARIOS = [
    # name                                   slow poll (s)  mAs/poll  meas period (s)
    ("SIT, poll 15 s, +10 dBm (default)",    15.0,  0.25,  900),
    ("SIT, poll 15 s, +20 dBm",              15.0,  0.31,  900),
    ("LIT, poll 60 s, +10 dBm",              60.0,  0.25,  900),
    ("LIT, poll 120 s, +10 dBm",            120.0,  0.25,  900),
    ("SIT 15 s, measure every 30 min",       15.0,  0.25, 1800),
    ("LIT 60 s, measure every 30 min",       60.0,  0.25, 1800),
]


def measurement_mas():
    """Charge of one measurement at the 3.3 V rail (mAs), split by consumer."""
    parts = {
        "soil module": SOIL_MODULE_MA * VSENS_ON_S,
        "MCU awake": MCU_AWAKE_MA * MCU_AWAKE_S,
    }
    return sum(parts.values()), parts


def reports_per_day(meas_period_s):
    # ~50 % of the measurements change a value + hourly heartbeats, at most one report per measurement
    n_meas = 86400.0 / meas_period_s
    return min(n_meas, 0.5 * n_meas + 86400.0 / MAX_REPORT_INTERVAL_S)


def daily_mah(poll_s, poll_mas, meas_period_s):
    day = 86400.0
    sleep = (SLEEP_UA + BOARD_LEAK_UA) * 1e-3 * day          # mAs
    polls = (day / poll_s) * poll_mas
    meas = (day / meas_period_s) * measurement_mas()[0]
    rep = reports_per_day(meas_period_s) * REPORT_MAS
    to_bat_sleep = V_OUT / (V_BAT * ETA_SLEEP)
    to_bat_act = V_OUT / (V_BAT * ETA_ACTIVE)
    bat_mas = sleep * to_bat_sleep + (polls + meas + rep) * to_bat_act + IQ_BB_UA * 1e-3 * day
    parts = {k: v / 3600.0 for k, v in (("sleep", sleep), ("polls", polls), ("measure", meas), ("reports", rep))}
    return bat_mas / 3600.0, parts


def main():
    total, parts = measurement_mas()
    print("one measurement at the 3.3 V rail:")
    for k, v in parts.items():
        print(f"  {k:12s} {v:6.2f} mAs")
    print(f"  {'total':12s} {total:6.2f} mAs")
    print()
    print(f"{'scenario':34s} {'rail mAh/day: sleep / polls / meas / reports':46s} {'bat mAh/d':>9s} {'avg uA':>7s} {'life':>7s}")
    for name, poll_s, poll_mas, meas_s in SCENARIOS:
        bat, p = daily_mah(poll_s, poll_mas, meas_s)
        years = (BAT_MAH * USABLE) / (bat * 365.0)
        years = years / (1 + SELF_DISCHARGE * years)
        avg_ua = bat / 24.0 * 1000.0
        print(f"{name:34s} {p['sleep']:.3f} / {p['polls']:.3f} / {p['measure']:.3f} / {p['reports']:.3f}"
              f"{'':16s} {bat:9.2f} {avg_ua:7.1f} {years:5.1f} y")


if __name__ == "__main__":
    main()
