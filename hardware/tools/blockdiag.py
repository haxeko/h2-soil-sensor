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

    items.append(["text", QStr("SO DO KHOI - H2 Soil Sensor (Matter over Thread, ESP32-H2, 1x CR123A)"),
                  ["at", 25.4, 22.86, 0], eff(size=2.54, justify="left bottom"), ["uuid", uid("bdtitle")]])
    box("bat", 25.4, 33.02, 33.02, 15.24, "CR123A 3.0V\nLi-MnO2 ~1500mAh\n(BT1, gia THT)", True)
    box("rpp", 73.66, 33.02, 33.02, 15.24, "Chong nguoc cuc\nQ1 AO3415A\n(P-MOSFET)")
    box("bb", 121.92, 33.02, 43.18, 15.24, "Buck-boost TPS63900\n1.8-5.5V -> 3.3V\nIq 75nA, >90% @10uA", True)
    box("mcu", 195.58, 33.02, 63.5, 71.12,
        "ESP32-H2-WROOM-02C\nRISC-V 96MHz, 802.15.4 + BLE\nMatter over Thread\nSED / ICD (SIT/LIT)\n\n"
        "IO1  ADC1_CH0  SOIL_ADC\nIO2  ADC1_CH1  VBAT_ADC\nIO3  ADC1_CH2  NTC_ADC\nIO10 SENS_PWR_EN_N\n"
        "IO11 VBAT_MEAS_EN\nIO12/IO22 I2C SDA/SCL\nIO9  nut BOOT/USER\nIO0  LED\nIO23/24 UART0, IO26/27 USB", True)
    box("vbat", 73.66, 63.5, 43.18, 15.24, "Do pin: Q2/Q3 cong tac\n+ cau chia 1/2\n(0 ro khi ngu)")
    box("lsw", 121.92, 91.44, 43.18, 12.7, "Load switch Q4 (P-FET)\n-> VSENS (chi bat khi do)")
    box("osc", 25.4, 124.46, 38.1, 15.24, "TLC555I astable\n~0.5-0.7 MHz\n50% duty")
    box("probe", 76.2, 124.46, 43.18, 15.24, "RS 10k + dien cuc SENSE\nin tren PCB (que 80mm)\nC_dat 15..250 pF")
    box("det", 132.08, 124.46, 43.18, 15.24, "D1 tach dinh + C17\nchia 1/2 (R16/R17)\n-> ~0.7..1.4 V")
    box("ntc", 76.2, 152.4, 43.18, 12.7, "NTC 10k B3380\n(nhiet do dat)")
    box("sht", 132.08, 152.4, 43.18, 12.7, "SHT40-AD1F (I2C)\nnhiet/am khong khi")
    box("ui", 274.32, 33.02, 50.8, 25.4, "UI / nap:\nSW1 BOOT/USER (IO9)\nLED do (IO0)\nJ1: UART0 + USB-JTAG")
    box("rf", 274.32, 68.58, 50.8, 20.32, "Anten PCB cua module\nnho ra ngoai mep PCB\nkhong dong ben duoi")
    line("l1", [(58.42, 40.64), (73.66, 40.64)], "VBAT_RAW")
    line("l2", [(106.68, 40.64), (121.92, 40.64)], "VBAT")
    line("l3", [(165.1, 40.64), (195.58, 40.64)], "+3V3")
    line("l4", [(95.25, 48.26), (95.25, 63.5)])
    line("l5", [(116.84, 71.12), (195.58, 71.12)], "VBAT_ADC")
    line("l6", [(143.51, 48.26), (143.51, 91.44)])
    line("l7", [(195.58, 99.06), (165.1, 99.06)], "SENS_PWR_EN_N")
    line("l8", [(143.51, 104.14), (143.51, 116.84), (44.45, 116.84), (44.45, 124.46)], "VSENS")
    line("l9", [(63.5, 132.08), (76.2, 132.08)])
    line("l10", [(119.38, 132.08), (132.08, 132.08)])
    line("l11", [(175.26, 132.08), (185.42, 132.08), (185.42, 88.9), (195.58, 88.9)])
    line("l12", [(119.38, 158.75), (190.5, 158.75), (190.5, 93.98), (195.58, 93.98)])
    line("l13", [(175.26, 162.56), (193.04, 162.56), (193.04, 96.52), (195.58, 96.52)])
    line("l14", [(259.08, 45.72), (274.32, 45.72)])
    line("l15", [(259.08, 78.74), (274.32, 78.74)])
    items.append(["text", QStr("SOIL_ADC / NTC_ADC / I2C"), ["at", 165.1, 114.3, 0], eff(size=1.27),
                  ["uuid", uid("bdt", "adc")]])
    return items
