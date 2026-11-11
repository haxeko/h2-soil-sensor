#!/usr/bin/env python3
"""Battery-life model for the H2 soil sensor (CR123A + TPS63900 + ESP32-H2 ICD).

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
BOARD_LEAK_UA = 0.3     # MOSFET Idss, MLCC IR, ADC/I2C pins Hi-Z (estimate)
MEAS_PERIOD_S = 900     # sensor measurement period
MEAS_MAS = 0.65         # one measurement: ~80 ms awake at ~8 mA (CPU + TLC555 + SHT40 + dividers)
REPORT_MAS = 1.5        # one report: active-mode window (fast poll) + TX/RX + MRP ack + crypto
REPORTS_PER_DAY = 72    # ~50 % of measurements change a value + hourly heartbeats

SCENARIOS = {
    #  name                      slow poll (s)  mAs per poll (TX power dependent)
    "SIT, poll 15 s, +10 dBm":  (15.0, 0.25),
    "SIT, poll 15 s, +20 dBm":  (15.0, 0.31),
    "LIT, poll 60 s, +10 dBm":  (60.0, 0.25),
    "LIT, poll 120 s, +10 dBm": (120.0, 0.25),
}


def daily_mah(poll_s, poll_mas):
    day = 86400.0
    sleep = (SLEEP_UA + BOARD_LEAK_UA) * 1e-3 * day          # mAs
    polls = (day / poll_s) * poll_mas
    meas = (day / MEAS_PERIOD_S) * MEAS_MAS
    rep = REPORTS_PER_DAY * REPORT_MAS
    to_bat_sleep = V_OUT / (V_BAT * ETA_SLEEP)
    to_bat_act = V_OUT / (V_BAT * ETA_ACTIVE)
    bat_mas = sleep * to_bat_sleep + (polls + meas + rep) * to_bat_act + IQ_BB_UA * 1e-3 * day
    parts = {k: v / 3600.0 for k, v in (("sleep", sleep), ("polls", polls), ("measure", meas), ("reports", rep))}
    return bat_mas / 3600.0, parts


def main():
    print(f"{'scenario':28s} {'rail mAh/day: sleep / polls / meas / reports':46s} {'bat mAh/d':>9s} {'avg uA':>7s} {'life':>7s}")
    for name, (poll_s, poll_mas) in SCENARIOS.items():
        bat, p = daily_mah(poll_s, poll_mas)
        years = (BAT_MAH * USABLE) / (bat * 365.0)
        years = years / (1 + SELF_DISCHARGE * years)
        avg_ua = bat / 24.0 * 1000.0
        print(f"{name:28s} {p['sleep']:.3f} / {p['polls']:.3f} / {p['measure']:.3f} / {p['reports']:.3f}"
              f"{'':16s} {bat:9.2f} {avg_ua:7.1f} {years:5.1f} y")


if __name__ == "__main__":
    main()
