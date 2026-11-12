#!/usr/bin/env python3
"""Generate the project footprint library (lib/h2soil.pretty) and symbol library
(lib/h2soil.kicad_sym) plus the project sym/fp lib tables.

Usage: python3 gen_footprints.py <hardware_dir>
"""
from __future__ import annotations

import os
import sys
import uuid

from sexp import QStr, dumps
from symlib import project_symbols

NS = uuid.UUID("3f5d9a1c-2b44-4c1e-9b2a-77c1f0e4d6aa")


def tid(*k):
    return str(uuid.uuid5(NS, "/".join(map(str, k))))


def font(size=1.0, thick=0.15):
    return ["effects", ["font", ["size", size, size], ["thickness", thick]]]


class FP:
    def __init__(self, name, descr, tags, attr):
        self.name = name
        self.items = [["layer", QStr("F.Cu")], ["descr", QStr(descr)], ["tags", QStr(tags)], ["attr"] + attr]
        self.n = 0

    def _t(self):
        self.n += 1
        return ["tstamp", tid(self.name, self.n)]

    def text(self, kind, txt, x, y, layer, size=1.0):
        self.items.append(["fp_text", kind, QStr(txt), ["at", x, y], ["layer", QStr(layer)], font(size, 0.15 * size),
                           self._t()])

    def line(self, x1, y1, x2, y2, layer, w=0.12):
        self.items.append(["fp_line", ["start", x1, y1], ["end", x2, y2],
                           ["stroke", ["width", w], ["type", "solid"]], ["layer", QStr(layer)], self._t()])

    def rect(self, x1, y1, x2, y2, layer, w=0.05):
        self.items.append(["fp_rect", ["start", x1, y1], ["end", x2, y2],
                           ["stroke", ["width", w], ["type", "solid"]], ["fill", "none"], ["layer", QStr(layer)],
                           self._t()])

    def circle(self, cx, cy, r, layer, w=0.12):
        self.items.append(["fp_circle", ["center", cx, cy], ["end", cx + r, cy],
                           ["stroke", ["width", w], ["type", "solid"]], ["fill", "none"], ["layer", QStr(layer)],
                           self._t()])

    def smd(self, num, x, y, w, h, layers=("F.Cu", "F.Paste", "F.Mask"), shape="rect"):
        p = ["pad", QStr(num), "smd", shape, ["at", x, y], ["size", w, h], ["layers"] + [QStr(l) for l in layers]]
        if shape == "roundrect":
            p.append(["roundrect_rratio", 0.25])
        p.append(self._t())
        self.items.append(p)

    def tht(self, num, x, y, d, drill, layers=("*.Cu", "*.Mask"), shape="circle"):
        self.items.append(["pad", QStr(num), "thru_hole", shape, ["at", x, y], ["size", d, d], ["drill", drill],
                           ["layers"] + [QStr(l) for l in layers], self._t()])

    def npth(self, x, y, d):
        self.items.append(["pad", QStr(""), "np_thru_hole", "circle", ["at", x, y], ["size", d, d], ["drill", d],
                           ["layers", QStr("*.Cu"), QStr("*.Mask")], self._t()])

    def write(self, d):
        node = ["footprint", QStr(self.name), ["version", 20221018], ["generator", "pcbnew"]] + self.items
        with open(os.path.join(d, self.name + ".kicad_mod"), "w", encoding="utf-8") as f:
            f.write(dumps(node) + "\n")


def esp32_h2_wroom_02c():
    """Origin = module centre. Module 18 x 20 mm; antenna area = top 6 mm (y -10..-4)."""
    f = FP("ESP32-H2-WROOM-02C",
           "ESP32-H2-WROOM-02C (Espressif) 18x20x3.2mm, 1.5mm pitch, PCB antenna. Land pattern: datasheet v1.2 Fig.7. "
           "Place the antenna area outside the base board or keep it free of copper on all layers.",
           "ESP32-H2 Espressif module 802.15.4 Thread Zigbee BLE", ["smd"])
    ox, oy = 9.0, 10.0  # module (top-left origin) -> footprint origin
    f.text("reference", "REF**", 0, -11.2, "F.SilkS")
    f.text("value", "ESP32-H2-WROOM-02C", 0, 11.8, "F.Fab")
    # body / antenna on Fab + silk
    f.rect(-9, -10, 9, 10, "F.Fab", 0.1)
    f.line(-9, -4, 9, -4, "F.Fab", 0.1)
    f.text("user", "ANTENNA", 0, -7, "F.Fab", 1.0)
    # silk only beside the module body (the antenna area normally hangs over the board edge)
    for (x1, y1, x2, y2) in [(-9.85, -1.0, -9.85, 9.0), (9.85, -1.0, 9.85, 9.0)]:
        f.line(x1, y1, x2, y2, "F.SilkS", 0.12)
    f.text("user", "ANTENNA KEEPOUT (no copper)", 0, -8.5, "F.Fab", 0.8)
    f.circle(-10.05, -2.9, 0.15, "F.SilkS", 0.2)  # pin-1 marker
    f.rect(-9.85, -10.35, 9.85, 10.85, "F.CrtYd", 0.05)
    # left column pins 1..9 (x=0.25, y=7.1+1.5n), 1.5 x 0.9 mm
    for i in range(9):
        f.smd(str(1 + i), 0.25 - ox, 7.1 + 1.5 * i - oy, 1.5, 0.9)
    # bottom row 10..19 (x=2.25+1.5k, y=19.75), 0.9 x 1.5 mm
    for k in range(10):
        f.smd(str(10 + k), 2.25 + 1.5 * k - ox, 19.75 - oy, 0.9, 1.5)
    # right column 20..28 (x=17.75, from y=19.1 up to 7.1)
    for j in range(9):
        f.smd(str(20 + j), 17.75 - ox, 19.1 - 1.5 * j - oy, 1.5, 0.9)
    # EPAD (pin 29): 2.8x0.55 @ (8.53,12.01) + 2.8x1.6 @ (8.53,13.73)
    cx = 8.53 - ox
    f.smd("29", cx, 12.01 - oy, 2.8, 0.55, layers=("F.Cu", "F.Mask"))
    f.smd("29", cx, 13.73 - oy, 2.8, 1.6, layers=("F.Cu", "F.Mask"))
    f.smd("29", cx, 13.73 - oy, 2.2, 1.2, layers=("F.Paste",))
    for (vx, vy) in [(-1.0, 12.01), (0.0, 12.01), (1.0, 12.01),
                     (-1.0, 13.33), (0.0, 13.33), (1.0, 13.33), (-1.0, 14.13), (0.0, 14.13), (1.0, 14.13)]:
        f.tht("29", cx + vx, vy - oy, 0.5, 0.3, layers=("*.Cu",))
    return f


def battery_holder():
    """MYOUNG BH-123A-A1CJ002 (LCSC C5290177), CR123A, DIP 90deg.
    Origin = midpoint between terminals. Terminals 37.5 mm apart, hole d1.8.
    Body 43.3 x 18.2 mm spanning y -9.8..+8.4 (locating post d2.0 at +8.4)."""
    f = FP("BatteryHolder_MYOUNG_BH-123A-A1CJ002",
           "CR123A battery holder MYOUNG BH-123A-A1CJ002 (LCSC C5290177), through-hole. Pad 1 = +. "
           "Verify the locating-post side against the physical part (two NPTH provided).",
           "battery holder CR123A 123A", ["through_hole"])
    f.text("reference", "REF**", 0, -11.0, "F.SilkS")
    f.text("value", "CR123A", 0, 0, "F.Fab")
    f.rect(-21.65, -9.8, 21.65, 8.4, "F.Fab", 0.1)
    f.rect(-21.77, -9.92, 21.77, 8.52, "F.SilkS", 0.12)
    f.rect(-22.2, -10.3, 22.2, 8.9, "F.CrtYd", 0.05)
    f.tht("1", 18.75, 0, 3.0, 1.8, shape="rect")
    f.tht("2", -18.75, 0, 3.0, 1.8)
    f.npth(18.95, 8.4 - 1.2, 2.2)
    f.npth(-18.95, 8.4 - 1.2, 2.2)
    # polarity marks
    f.text("user", "+", 14.5, -5.5, "F.SilkS", 2.0)
    f.text("user", "-", -14.5, -5.5, "F.SilkS", 2.0)
    f.text("user", "CR123A 3V", 0, -5.5, "F.SilkS", 1.2)
    return f


def soil_probe():
    """Capacitive electrodes. Origin = centre line at the SOIL LINE.
    SENSE (pad 1): 8 x 66 mm, y 4..70, both copper layers, stitched, covered by mask.
    GND (pad 2): 3 mm edge strips (y -3..74) + bottom bar; F.Cu right strip narrowed
    to leave a channel for the NTC trace (guarded by GND)."""
    f = FP("SoilProbe_Capacitive_80mm",
           "PCB-printed capacitive soil moisture probe, coplanar electrodes on both layers, solder-mask covered "
           "(conformal coat the whole probe). Pad1=SENSE, Pad2=GND. Probe width 20 mm.",
           "soil moisture capacitive probe electrode", ["smd", "exclude_from_pos_files", "exclude_from_bom"])
    f.text("reference", "REF**", 0, 76.5, "F.SilkS")
    f.text("value", "SoilProbe_Capacitive_80mm", 0, 78.5, "F.Fab")
    for lay in ("F.Cu", "B.Cu"):
        f.smd("1", 0, 37, 8, 66, layers=(lay,))
        f.smd("2", -7.9, 35.5, 3.0, 77, layers=(lay,))
    f.smd("2", 7.9, 35.5, 3.0, 77, layers=("B.Cu",))     # right strip full width on bottom
    f.smd("2", 7.0, 35.5, 1.2, 77, layers=("F.Cu",))     # right strip narrow on top (NTC channel x 7.9..9.5)
    f.smd("2", -0.9, 73.0, 17.0, 2.0, layers=("F.Cu",))  # bottom bar (stops before NTC channel)
    f.smd("2", 0.0, 73.0, 18.8, 2.0, layers=("B.Cu",))
    for y in range(8, 70, 10):
        f.tht("1", 0, y, 0.8, 0.4, layers=("*.Cu",))
    for y in range(-1, 74, 10):
        f.tht("2", -7.9, y, 0.8, 0.4, layers=("*.Cu",))
        f.tht("2", 7.0, y, 0.8, 0.4, layers=("*.Cu",))
    f.rect(-10, -3.5, 7.7, 75, "F.CrtYd", 0.05)  # right channel (x>7.7) left free for the NTC
    f.rect(-4, 4, 4, 70, "F.Fab", 0.1)
    f.text("user", "SENSE", 0, 37, "F.Fab", 1.5)
    return f


def wson10_tps63900():
    """KiCad WSON-10-1EP_2.5x2.5mm_P0.5mm_EP1.2x2mm_ThermalVias with 0.3 mm thermal-via drills (std PCB process)."""
    import re as _re
    src = "/usr/share/kicad/footprints/Package_SON.pretty/WSON-10-1EP_2.5x2.5mm_P0.5mm_EP1.2x2mm_ThermalVias.kicad_mod"
    txt = open(src, encoding="utf-8").read()
    txt = txt.replace('(footprint "WSON-10-1EP_2.5x2.5mm_P0.5mm_EP1.2x2mm_ThermalVias"',
                      '(footprint "WSON-10-1EP_2.5x2.5mm_P0.5mm_EP1.2x2mm_ThermalVias_0.3mm"')
    txt = _re.sub(r'\(size 0\.5 0\.5\) \(drill 0\.2\)', '(size 0.5 0.5) (drill 0.3)', txt)
    return txt


def main(hw):
    lib = os.path.join(hw, "lib")
    pretty = os.path.join(lib, "h2soil.pretty")
    os.makedirs(pretty, exist_ok=True)
    for old in ("BatteryHolder_MYOUNG_BH-123A-A1CJ002.kicad_mod", "SoilProbe_Capacitive_80mm.kicad_mod"):
        if os.path.exists(os.path.join(pretty, old)):
            os.remove(os.path.join(pretty, old))   # v1 parts, not used by the v2 carrier board
    for f in (esp32_h2_wroom_02c(),):
        f.write(pretty)
    with open(os.path.join(pretty, "WSON-10-1EP_2.5x2.5mm_P0.5mm_EP1.2x2mm_ThermalVias_0.3mm.kicad_mod"), "w") as fh:
        fh.write(wson10_tps63900())
    syms = {k: v for k, v in project_symbols().items() if k != "SoilProbe_Capacitive"}
    node = ["kicad_symbol_lib", ["version", 20220914], ["generator", "kicad_symbol_editor"]] + list(syms.values())
    with open(os.path.join(lib, "h2soil.kicad_sym"), "w", encoding="utf-8") as fh:
        fh.write(dumps(node) + "\n")
    with open(os.path.join(hw, "sym-lib-table"), "w") as fh:
        fh.write('(sym_lib_table\n  (lib (name "h2soil")(type "KiCad")(uri "${KIPRJMOD}/lib/h2soil.kicad_sym")'
                 '(options "")(descr "H2 soil sensor project symbols"))\n)\n')
    with open(os.path.join(hw, "fp-lib-table"), "w") as fh:
        fh.write('(fp_lib_table\n  (lib (name "h2soil")(type "KiCad")(uri "${KIPRJMOD}/lib/h2soil.pretty")'
                 '(options "")(descr "H2 soil sensor project footprints"))\n)\n')
    print("footprints + symbols written to", lib)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "..")
