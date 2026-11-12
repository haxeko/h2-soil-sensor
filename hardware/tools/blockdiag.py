"""Block diagram for the root schematic sheet (text boxes + polylines)."""
from __future__ import annotations

from sexp import QStr


def build(uid, fx, eff):
    items = []

    def box(key, x, y, w, h, txt, bold=False):
        font = ["font", ["size", 1.524, 1.524]] + (["bold"] if bold else [])
        items.append(["text_box", QStr(txt), ["at", x, y, 0], ["size", w, h],
                      ["stroke", ["width", 0.3], ["type", "default"]], ["fill", ["type", "none"]],
                      ["effects", font, ["justify", "left", "top"]], ["uuid", uid("bd", key)]])

    def line(key, pts, label=None):
        items.append(["polyline", ["pts"] + [["xy", fx(a), fx(b)] for a, b in pts],
                      ["stroke", ["width", 0.3], ["type", "default"]], ["uuid", uid("bdl", key)]])
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        if x2 != x1:
            s = 1 if x2 > x1 else -1
            head = [(x2 - s * 1.5, y2 - 0.9), (x2, y2), (x2 - s * 1.5, y2 + 0.9)]
        else:
            s = 1 if y2 > y1 else -1
            head = [(x2 - 0.9, y2 - s * 1.5), (x2, y2), (x2 + 0.9, y2 - s * 1.5)]
        items.append(["polyline", ["pts"] + [["xy", fx(a), fx(b)] for a, b in head],
                      ["stroke", ["width", 0.3], ["type", "default"]], ["uuid", uid("bda", key)]])
        if label:
            (a1, b1), (a2, b2) = pts[0], pts[1]
            items.append(["text", QStr(label), ["at", fx((a1 + a2) / 2), fx(min(b1, b2) - 1.0), 0], eff(size=1.27),
                          ["uuid", uid("bdt", key)]])

    items.append(["text", QStr("SO DO KHOI v3 - ESP32-H2 + pin CR123A + module do am dat dien dung (Matter over Thread)"),
                  ["at", 25.4, 22.86, 0], eff(size=2.54, justify="left bottom"), ["uuid", uid("bdtitle")]])
    box("bat", 25.4, 33.02, 33.02, 20.32, "CR123A 3.0V\nLi-MnO2 ~1500mAh\n(de pin co day)\nJ3: 2 pad han + / -", True)
    box("rpp", 73.66, 33.02, 33.02, 15.24, "Chong nguoc cuc\nQ1 AO3415A\n(P-MOSFET)")
    box("bb", 121.92, 33.02, 43.18, 15.24, "Buck-boost TPS63900\n1.8-5.5V -> 3.3V\nIq 75nA, >90% @10uA", True)
    box("mcu", 195.58, 33.02, 63.5, 71.12,
        "ESP32-H2-WROOM-02C\nRISC-V 96MHz, 802.15.4 + BLE\nMatter over Thread\nSED / ICD (SIT/LIT)\n\n"
        "IO1  ADC1_CH0  SOIL_ADC\nIO2  ADC1_CH1  VBAT_ADC\nIO10 SENS_PWR_EN_N\n"
        "IO11 VBAT_MEAS_EN\nIO9  nut BOOT/USER\nIO0  LED\nIO23/24 UART0, IO26/27 USB", True)
    box("vbat", 73.66, 63.5, 43.18, 15.24, "Do pin: Q2/Q3 cong tac\n+ cau chia 1/2\n(0 ro khi ngu)")
    box("lsw", 121.92, 91.44, 43.18, 12.7, "Load switch Q4 (P-FET)\n-> VSENS (chi bat khi do)")
    box("soil", 25.4, 124.46, 50.8, 20.32, "J4 PH2.0-3P ->\nMODULE DO AM DAT DIEN DUNG\nCapacitive Soil Moisture v1.2\n(TLC555), AOUT 0-3V, ~5mA")
    box("esd", 86.36, 152.4, 50.8, 10.16, "D3 TVS: chong ESD day AOUT")
    box("ui", 274.32, 33.02, 50.8, 25.4, "UI / nap:\nSW1 BOOT/USER (IO9)\nLED do (IO0)\nJ1: 8 pad tron (UART+USB)")
    box("rf", 274.32, 68.58, 50.8, 20.32, "Anten PCB cua module\nnho ra ngoai mep PCB\nkhong dong ben duoi")
    line("l1", [(58.42, 40.64), (73.66, 40.64)], "VBAT_RAW")
    line("l2", [(106.68, 40.64), (121.92, 40.64)], "VBAT")
    line("l3", [(165.1, 40.64), (195.58, 40.64)], "+3V3")
    line("l4", [(95.25, 48.26), (95.25, 63.5)])
    line("l5", [(116.84, 71.12), (195.58, 71.12)], "VBAT_ADC")
    line("l6", [(143.51, 48.26), (143.51, 91.44)])
    line("l7", [(195.58, 99.06), (165.1, 99.06)], "SENS_PWR_EN_N")
    line("l8", [(143.51, 104.14), (143.51, 116.84), (50.8, 116.84), (50.8, 124.46)], "VSENS")
    line("l11", [(50.8, 144.78), (50.8, 170.18), (193.04, 170.18), (193.04, 88.9), (195.58, 88.9)])
    line("l14", [(259.08, 45.72), (274.32, 45.72)])
    line("l15", [(259.08, 78.74), (274.32, 78.74)])
    items.append(["text", QStr("SOIL_ADC"), ["at", 165.1, 175.26, 0], eff(size=1.27),
                  ["uuid", uid("bdt", "adc")]])
    return items
