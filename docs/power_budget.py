#!/usr/bin/env python3
"""Battery-life model for the H2 soil sensor v2 (CR123A + TPS63900 + ESP32-H2 ICD)
with off-the-shelf sensor modules on the switched VSENS rail.

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
BOARD_LEAK_UA = 0.3     # MOSFET Idss, MLCC IR, ADC/I2C pins Hi-Z; VSENS + modules are OFF (estimate)

# ---- one measurement (sensors.c): VSENS on -> 45 ms -> I2C read -> wait CONFIG_SOIL_SETTLE_MS
#      in light sleep -> battery divider 3 ms -> ADC -> everything off
VSENS_ON_S = 1.55       # CONFIG_SOIL_SETTLE_MS (1500 ms) + divider/ADC time
SOIL_MODULE_MA = 5.0    # capacitive soil module v1.2/v2.0 (DFRobot SEN0193: 5 mA)
AIR_MODULE_MA = 1.0     # I2C T/RH module (sensor + LDO + pull-ups), upper end of 0.3-1 mA, no power LED
NTC_MA = 3.3 / 20e3 * 1e3   # VSENS -> R18 10k -> NTC 10k at 25 degC: 0.165 mA
MCU_AWAKE_S = 0.12      # CPU awake: soft-start, I2C transfer (AHT20 80 ms worst case), ADC; rest = light sleep
MCU_AWAKE_MA = 7.0      # ESP32-H2 at 96 MHz, radio off (same assumption as the v1 model)
# battery divider: VBAT/200k = 15 uA for ~10 ms per measurement -> negligible, not modelled

REPORT_MAS = 1.5        # one report: active-mode window (fast poll) + TX/RX + MRP ack + crypto
MAX_REPORT_INTERVAL_S = 3600   # CONFIG_SOIL_MAX_REPORT_INTERVAL_S (heartbeat)

ALL_MODULES = (True, True)     # (I2C air module present, NTC probe present)
SOIL_ONLY = (False, False)

SCENARIOS = [
    # name                                   slow poll (s)  mAs/poll  meas period (s)  modules
    ("SIT, poll 15 s, +10 dBm (default)",    15.0,  0.25,  900, ALL_MODULES),
    ("SIT, poll 15 s, +20 dBm",              15.0,  0.31,  900, ALL_MODULES),
    ("LIT, poll 60 s, +10 dBm",              60.0,  0.25,  900, ALL_MODULES),
    ("LIT, poll 120 s, +10 dBm",            120.0,  0.25,  900, ALL_MODULES),
    ("SIT 15 s, measure every 30 min",       15.0,  0.25, 1800, ALL_MODULES),
    ("SIT 15 s, soil module only",           15.0,  0.25,  900, SOIL_ONLY),
    ("LIT 60 s, measure every 30 min",       60.0,  0.25, 1800, ALL_MODULES),
]


def measurement_mas(air=True, ntc=True):
    """Charge of one measurement at the 3.3 V rail (mAs), split by consumer."""
    parts = {
        "soil module": SOIL_MODULE_MA * VSENS_ON_S,
        "I2C module": (AIR_MODULE_MA if air else 0.0) * VSENS_ON_S,
        "NTC divider": (NTC_MA if ntc else 0.0) * VSENS_ON_S,
        "MCU awake": MCU_AWAKE_MA * MCU_AWAKE_S,
    }
    return sum(parts.values()), parts


def reports_per_day(meas_period_s):
    # ~50 % of the measurements change a value + hourly heartbeats, at most one report per measurement
    n_meas = 86400.0 / meas_period_s
    return min(n_meas, 0.5 * n_meas + 86400.0 / MAX_REPORT_INTERVAL_S)


def daily_mah(poll_s, poll_mas, meas_period_s, modules):
    day = 86400.0
    sleep = (SLEEP_UA + BOARD_LEAK_UA) * 1e-3 * day          # mAs
    polls = (day / poll_s) * poll_mas
    meas = (day / meas_period_s) * measurement_mas(*modules)[0]
    rep = reports_per_day(meas_period_s) * REPORT_MAS
    to_bat_sleep = V_OUT / (V_BAT * ETA_SLEEP)
    to_bat_act = V_OUT / (V_BAT * ETA_ACTIVE)
    bat_mas = sleep * to_bat_sleep + (polls + meas + rep) * to_bat_act + IQ_BB_UA * 1e-3 * day
    parts = {k: v / 3600.0 for k, v in (("sleep", sleep), ("polls", polls), ("measure", meas), ("reports", rep))}
    return bat_mas / 3600.0, parts


def main():
    total, parts = measurement_mas(*ALL_MODULES)
    print("one measurement at the 3.3 V rail (all modules):")
    for k, v in parts.items():
        print(f"  {k:12s} {v:6.2f} mAs")
    print(f"  {'total':12s} {total:6.2f} mAs   (soil module only: {measurement_mas(*SOIL_ONLY)[0]:.2f} mAs)")
    print()
    print(f"{'scenario':34s} {'rail mAh/day: sleep / polls / meas / reports':46s} {'bat mAh/d':>9s} {'avg uA':>7s} {'life':>7s}")
    for name, poll_s, poll_mas, meas_s, modules in SCENARIOS:
        bat, p = daily_mah(poll_s, poll_mas, meas_s, modules)
        years = (BAT_MAH * USABLE) / (bat * 365.0)
        years = years / (1 + SELF_DISCHARGE * years)
        avg_ua = bat / 24.0 * 1000.0
        print(f"{name:34s} {p['sleep']:.3f} / {p['polls']:.3f} / {p['measure']:.3f} / {p['reports']:.3f}"
              f"{'':16s} {bat:9.2f} {avg_ua:7.1f} {years:5.1f} y")


if __name__ == "__main__":
    main()
