#!/usr/bin/env python3
"""Generate the hierarchical KiCad 7 schematic for the H2 soil sensor from design.py.

Connections are made with short wire stubs ending in power symbols, local
labels (single-sheet nets) or global labels (multi-sheet nets), so the result
is fully checkable with `kicad-cli sch erc`.

Usage: python3 gen_schematic.py <output_dir>
"""
from __future__ import annotations

import math
import os
import sys
import uuid

import blockdiag
import design
from sexp import QStr, dumps
from symlib import embed, load_symbol, pins_of, project_symbols

NS = uuid.UUID("6f1c5f2e-7a77-4b8e-9d7e-3a6e2c1b9a10")
GRID = 1.27
STUB = 2.54
TEXT = 1.27


def uid(*key) -> str:
    return str(uuid.uuid5(NS, "/".join(str(k) for k in key)))


def snap(v: float) -> float:
    return round(round(v / GRID) * GRID, 4)


def fx(v: float) -> float:
    return round(v, 4)


ROOT_UUID = uid("root")
PROJECT_SYMS = project_symbols()


def get_symbol(lib: str, name: str):
    if lib == "h2soil":
        return PROJECT_SYMS[name]
    return load_symbol(lib, name)


def eff(size=TEXT, justify=None, hide=False):
    e = ["effects", ["font", ["size", size, size]]]
    if justify:
        e.append(["justify"] + justify.split())
    if hide:
        e.append("hide")
    return e


def prop(name, value, x, y, angle=0, justify=None, hide=False):
    return ["property", QStr(name), QStr(value), ["at", fx(x), fx(y), angle], eff(justify=justify, hide=hide)]


def rot_vec(x, y, deg):
    r = math.radians(deg)
    return x * math.cos(r) - y * math.sin(r), x * math.sin(r) + y * math.cos(r)


def pin_geom(pin, X, Y, rot):
    """Absolute schematic position of a pin and its outward unit vector (screen coords)."""
    px, py = rot_vec(pin["x"], pin["y"], rot)
    pos = (fx(X + px), fx(Y - py))
    a = math.radians(pin["angle"] + 180 + rot)
    d = (round(math.cos(a)), -round(math.sin(a)))
    return pos, d


def dir_name(d):
    return {(1, 0): "R", (-1, 0): "L", (0, -1): "U", (0, 1): "D"}[d]


# rotation for power symbols so the graphic points along the stub direction
GND_ROT = {"D": 0, "U": 180, "L": 270, "R": 90}
SUP_ROT = {"U": 0, "D": 180, "L": 90, "R": 270}


class Sheet:
    def __init__(self, info, glob_nets, counters):
        self.info = info
        self.uuid = uid("sheet", info["name"])
        self.items = []
        self.libsyms = {}
        self.glob = glob_nets
        self.counters = counters

    @property
    def path(self):
        return f"/{ROOT_UUID}/{self.uuid}"

    def use_symbol(self, lib, name):
        key = f"{lib}:{name}"
        if key not in self.libsyms:
            self.libsyms[key] = embed(get_symbol(lib, name), lib)
        return key

    # ----------------------------------------------------------------- items
    def wire(self, p1, p2):
        self.items.append(["wire", ["pts", ["xy", p1[0], p1[1]], ["xy", p2[0], p2[1]]],
                           ["stroke", ["width", 0], ["type", "default"]], ["uuid", uid("w", self.info["name"], p1, p2)]])

    def no_connect(self, p):
        self.items.append(["no_connect", ["at", p[0], p[1]], ["uuid", uid("nc", self.info["name"], p)]])

    def label(self, net, p, d):
        angle = {"R": 0, "L": 180, "U": 90, "D": 270}[d]
        just = {"R": "left bottom", "L": "right bottom", "U": "left bottom", "D": "right bottom"}[d]
        if net in self.glob:
            gjust = {"R": "left", "L": "right", "U": "left", "D": "right"}[d]
            self.items.append(["global_label", QStr(net), ["shape", "bidirectional"], ["at", p[0], p[1], angle],
                               ["fields_autoplaced"], eff(justify=gjust), ["uuid", uid("gl", self.info["name"], net, p)],
                               ["property", QStr("Intersheetrefs"), QStr("${INTERSHEET_REFS}"), ["at", p[0], p[1], 0],
                                eff(size=1.27, hide=True)]])
        else:
            self.items.append(["label", QStr(net), ["at", p[0], p[1], angle], ["fields_autoplaced"],
                               eff(justify=just), ["uuid", uid("l", self.info["name"], net, p)]])

    def power(self, net, p, d):
        lib, name, kind = design.POWER_NETS[net]
        key = self.use_symbol(lib, name)
        rot = (GND_ROT if kind == "gnd" else SUP_ROT)[d]
        self.counters["pwr"] += 1
        ref = f"#PWR{self.counters['pwr']:03d}"
        # value text offset along the stub direction
        off = {"D": (0, 3.81), "U": (0, -3.81), "L": (-3.81, 0), "R": (3.81, 0)}[d] if kind == "supply" else \
              {"D": (0, 3.81), "U": (0, -3.81), "L": (-3.81, 0), "R": (3.81, 0)}[d]
        just = {"D": None, "U": None, "L": "right", "R": "left"}[d]
        hide_val = kind == "gnd" and d in ("L", "R")
        vang = rot if rot in (90, 270) else 0
        u = uid("pwr", self.info["name"], net, p)
        self.items.append(["symbol", ["lib_id", QStr(key)], ["at", p[0], p[1], rot], ["unit", 1],
                           ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"], ["uuid", u],
                           prop("Reference", ref, p[0], p[1], hide=True),
                           prop("Value", name, p[0] + off[0], p[1] + off[1], angle=vang, justify=just, hide=hide_val),
                           prop("Footprint", "", p[0], p[1], hide=True),
                           prop("Datasheet", "", p[0], p[1], hide=True),
                           ["pin", QStr("1"), ["uuid", uid("pwrpin", u)]],
                           ["instances", ["project", QStr(design.PROJECT),
                                          ["path", QStr(self.path), ["reference", QStr(ref)], ["unit", 1]]]]])

    def text(self, x, y, s):
        self.items.append(["text", QStr(s), ["at", x, y, 0], eff(size=1.524, justify="left top"),
                           ["uuid", uid("t", self.info["name"], x, y)]])

    # -------------------------------------------------------------- component
    def component(self, c):
        lib, name = c["lib"], c["sym"]
        key = self.use_symbol(lib, name)
        sym = get_symbol(lib, name)
        X, Y, rot = snap(c["x"]), snap(c["y"]), c["rot"]
        pins = pins_of(sym)
        u = uid("sym", c["ref"])
        virtual = c.get("virtual", False)
        nums = {p["number"] for p in pins}
        two_pin = len(nums) == 2 and name in ("R", "C", "L", "Thermistor_NTC", "Battery_Cell")
        # field angle is stored relative to the symbol: use `rot` so text is shown horizontal
        ang = rot if rot in (90, 270) else 0
        rp = []
        for p in pins:
            px, py = rot_vec(p["x"], p["y"], rot)
            rp.append((px, -py))
        minx = min([q[0] for q in rp] or [0]); maxx = max([q[0] for q in rp] or [0])
        miny = min([q[1] for q in rp] or [0]); maxy = max([q[1] for q in rp] or [0])
        just = None
        if two_pin and rot in (0, 180):
            rpos, vpos, just = (X + 2.54, Y - 1.27), (X + 2.54, Y + 1.27), "left"
        elif two_pin:
            rpos, vpos = (X, Y - 2.54), (X, Y + 2.54)
        elif name in ("TestPoint",):
            rpos, vpos, just = (X + 1.27, Y - 5.08), (X + 1.27, Y - 3.0), "left"
        elif name == "PWR_FLAG":
            rpos, vpos = (X, Y - 5.0), (X, Y - 3.0)
        elif name in ("SW_Push", "LED", "D", "Crystal", "MountingHole"):
            rpos, vpos = (X, Y - 3.81), (X, Y + 3.81)
        elif len(nums) == 3:  # MOSFETs
            if (maxy - miny) >= (maxx - minx):
                rpos, vpos, just = (X + maxx + 1.27, Y - 1.27), (X + maxx + 1.27, Y + 1.27), "left"
            else:
                rpos, vpos = (X, Y + miny - 6.35), (X, Y + miny - 3.81)
        else:  # ICs: reference above top-left, value below bottom-right (clear of power symbols)
            rpos, vpos = (X + minx + 2.54, Y + miny - 3.81), (X + maxx - 2.54, Y + maxy + 8.89)
            just = None
        ref = c["ref"]
        sym_item = ["symbol", ["lib_id", QStr(key)], ["at", X, Y, rot], ["unit", 1],
                    ["in_bom", "no" if (lib == "h2soil" and name == "SoilProbe_Capacitive") else "yes"],
                    ["on_board", "yes"], ["dnp", "yes" if c.get("dnp") else "no"],
                    ["uuid", u],
                    prop("Reference", ref, *rpos, angle=ang, justify=just, hide=virtual and False),
                    prop("Value", c["value"], *vpos, angle=ang, justify=just),
                    prop("Footprint", c["fp"], X, Y, hide=True),
                    prop("Datasheet", "", X, Y, hide=True)]
        for fname, fval in (("LCSC", c.get("lcsc", "")), ("MPN", c.get("mpn", "")),
                            ("Manufacturer", c.get("mfr", "")), ("Note", c.get("note", ""))):
            if fval:
                sym_item.append(prop(fname, fval, X, Y, hide=True))
        seen = set()
        for p in pins:
            if p["number"] in seen:
                continue
            seen.add(p["number"])
            sym_item.append(["pin", QStr(p["number"]), ["uuid", uid("pin", ref, p["number"])]])
        sym_item.append(["instances", ["project", QStr(design.PROJECT),
                                       ["path", QStr(self.path), ["reference", QStr(ref)], ["unit", 1]]]])
        self.items.append(sym_item)

        # connections
        done = set()
        for p in pins:
            num = p["number"]
            if num in done:
                continue
            done.add(num)
            if num not in c["pins"]:
                if p["type"] == "no_connect":
                    continue
                raise SystemExit(f"{ref}: pin {num} ({p['name']}) has no net assigned")
            net = c["pins"][num]
            pos, d = pin_geom(p, X, Y, rot)
            if net == "NC":
                self.no_connect(pos)
                continue
            dn = dir_name(d)
            end = (fx(pos[0] + d[0] * STUB), fx(pos[1] + d[1] * STUB))
            self.wire(pos, end)
            if net in design.POWER_NETS:
                self.power(net, end, dn)
            elif dn in ("U", "D"):
                # L-shaped stub so the label text is horizontal
                end2 = (fx(end[0] + STUB), end[1])
                self.wire(end, end2)
                self.label(net, end2, "R")
            else:
                self.label(net, end, dn)
        for num in c["pins"]:
            if num not in done:
                raise SystemExit(f"{ref}: net for unknown pin {num}")

    # ------------------------------------------------------------------ write
    def write(self, path, title, rev, date):
        head = ["kicad_sch", ["version", 20230121], ["generator", "eeschema"],
                ["uuid", self.uuid], ["paper", QStr("A3")],
                ["title_block", ["title", QStr(title)], ["date", QStr(date)], ["rev", QStr(rev)],
                 ["company", QStr("H2 Soil Sensor - Matter over Thread")],
                 ["comment", 1, QStr("ESP32-H2-WROOM-02C, CR123A, TPS63900")]],
                ["lib_symbols"] + [self.libsyms[k] for k in sorted(self.libsyms)]]
        body = head + self.items
        with open(path, "w", encoding="utf-8") as f:
            f.write(dumps(body) + "\n")


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    rev, date = "1.0", "2026-11-11"
    # nets per sheet -> global nets
    sheets_of_net: dict[str, set] = {}
    for c in design.COMPONENTS:
        for n in c["pins"].values():
            if n != "NC" and n not in design.POWER_NETS:
                sheets_of_net.setdefault(n, set()).add(c["sheet"])
    glob = {n for n, s in sheets_of_net.items() if len(s) > 1}
    counters = {"pwr": 0}
    sheets = []
    for info in design.SHEETS:
        sh = Sheet(info, glob, counters)
        for c in design.COMPONENTS:
            if c["sheet"] == info["name"]:
                sh.component(c)
        for (x, y, t) in design.NOTES.get(info["name"], []):
            sh.text(x, y, t)
        sh.write(os.path.join(outdir, info["file"]), info["title"], rev, date)
        sheets.append(sh)

    # --------------------------------------------------------------- root
    root = ["kicad_sch", ["version", 20230121], ["generator", "eeschema"], ["uuid", ROOT_UUID], ["paper", QStr("A3")],
            ["title_block", ["title", QStr("H2 Soil Sensor - Matter over Thread (ESP32-H2, CR123A)")],
             ["date", QStr(date)], ["rev", QStr(rev)], ["company", QStr("H2 Soil Sensor")],
             ["comment", 1, QStr("Root sheet: so do khoi + 4 sheet con (ket noi bang global label)")]],
            ["lib_symbols"]]
    bx = 30.48
    for i, sh in enumerate(sheets):
        x, y, w, h = bx + i * 95.25, 172.72, 76.2, 38.1
        root.append(["sheet", ["at", x, y], ["size", w, h], ["fields_autoplaced"],
                     ["stroke", ["width", 0.1524], ["type", "solid"]], ["fill", ["color", 0, 0, 0, 0.0]],
                     ["uuid", sh.uuid],
                     ["property", QStr("Sheetname"), QStr(sh.info["name"]), ["at", x, y - 0.7, 0],
                      eff(size=1.524, justify="left bottom")],
                     ["property", QStr("Sheetfile"), QStr(sh.info["file"]), ["at", x, y + h + 0.6, 0],
                      eff(size=1.27, justify="left top")],
                     ["instances", ["project", QStr(design.PROJECT),
                                    ["path", QStr(f"/{ROOT_UUID}"), ["page", QStr(sh.info["page"])]]]]])
        root.append(["text", QStr(sh.info["title"].replace(", ", ",\n")), ["at", x + 2.54, y + 5.08, 0],
                     eff(size=1.524, justify="left top"), ["uuid", uid("roottext", i)]])
    root.extend(blockdiag.build(uid, fx, eff))
    root.append(["sheet_instances", ["path", QStr("/"), ["page", QStr("1")]]])
    with open(os.path.join(outdir, design.PROJECT + ".kicad_sch"), "w", encoding="utf-8") as f:
        f.write(dumps(root) + "\n")
    print("wrote", len(sheets), "sheets; global nets:", ", ".join(sorted(glob)))





if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "..")
