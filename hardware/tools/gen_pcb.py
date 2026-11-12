#!/usr/bin/env python3
"""Build, route and check the H2 soil sensor carrier PCB v2 (KiCad 7, pcbnew Python API).

v3 = ESP32-H2 module + CR123A power stage + one JST-PH connector for the capacitive soil
module, round programming pads instead of a header. 26 x 45 mm, 2 layers.

Steps
  1. read the netlist exported from the schematic (kicad-cli) - single source of truth
  2. place footprints (python3 gen_pcb.py --check only prints courtyard overlaps)
  3. pre-route the TPS63900 switching loop, GND fan-out vias, then route all other nets
     with a 2-layer grid A* router (router.py)
  4. GND pours on both layers + stitching vias, zone fill, DRC report

Usage: python3 gen_pcb.py [--check]      (run from hardware/tools)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

import pcbnew

import fpinfo
import router
from sexp import find, find_all, loads

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
PCB_PATH = os.path.join(HW, "h2-soil-sensor.kicad_pcb")
PRO_PATH = os.path.join(HW, "h2-soil-sensor.kicad_pro")
SCH_PATH = os.path.join(HW, "h2-soil-sensor.kicad_sch")
KICAD_FP = "/usr/share/kicad/footprints"
X0, Y0 = 100.0, 40.0          # board-local (0,0) -> absolute KiCad coordinates
W, H = 26.0, 45.0             # board size (mm); module antenna overhangs the top edge

MM = pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(MM(X0 + x), MM(Y0 + y))


# ref: (x, y, rotation_deg) in board-local mm, all on the top side
PLACE = {
    # ESP32-H2 module, antenna (module y -10..-4) hangs over the top board edge
    "U2": (13.0, 4.0, 0),
    "C9": (2.0, 2.3, 270), "C8": (2.0, 5.4, 270), "R11": (2.0, 10.4, 270),
    "R22": (20.3, 16.8, 0), "D2": (23.6, 16.8, 180),
    # TPS63900 power stage (unchanged since rev 1, pre-routed switching loop)
    "C1": (3.3, 21.7, 180), "R10": (6.6, 21.7, 0), "C2": (9.9, 21.7, 0), "C3": (9.9, 23.6, 0),
    "U1": (7.6, 26.0, 0), "L1": (11.4, 26.4, 270), "C4": (10.6, 29.4, 0), "C5": (10.6, 31.4, 0),
    "R2": (3.7, 25.2, 180), "R3": (3.7, 26.7, 180), "R4": (3.7, 28.2, 180),
    # battery measurement + VSENS load switch
    "Q2": (16.6, 21.0, 0), "R5": (13.7, 21.0, 90), "Q3": (16.6, 25.4, 0), "R6": (13.7, 25.4, 270),
    "R7": (20.2, 21.0, 0), "R8": (22.8, 22.6, 270), "C6": (24.4, 22.6, 270),
    "Q4": (16.6, 30.0, 0), "R9": (13.7, 30.0, 90), "C7": (20.1, 30.0, 0),
    # button, soil module connector + front-end
    "SW1": (5.0, 35.9, 0), "R21": (10.8, 34.2, 180), "C21": (10.8, 36.0, 0),
    "J4": (20.5, 35.4, 180), "R12": (24.6, 34.6, 90), "C13": (24.6, 31.6, 90), "D3": (24.6, 37.6, 90),
    "C14": (12.4, 38.5, 0),
    # battery pads (+ square / - round), reverse-polarity P-FET, programming pads (bottom row)
    "J3": (6.8, 41.4, 180), "Q1": (10.6, 41.4, 180), "R1": (13.9, 42.4, 90),
    "J1": (16.2, 43.0, 90),
}

OUTLINE = [(1, 0), (W - 1, 0), (W, 1), (W, H - 1), (W - 1, H), (1, H), (0, H - 1), (0, 1)]

# silkscreen labels: (text, x, y, size, angle, justify) on F.SilkS
LABELS = [
    ("BOOT", 5.0, 32.4, 0.8, 0, "center"),
    ("LED", 23.6, 18.4, 0.8, 0, "center"),
    ("SOIL", 12.2, 33.0, 0.8, 0, "center"),
    ("A", 16.5, 38.45, 0.8, 0, "center"), ("V", 18.5, 38.45, 0.8, 0, "center"), ("G", 20.5, 38.45, 0.8, 0, "center"),
    ("1", 14.95, 43.0, 0.8, 0, "center"),
    ("-", 2.2, 43.75, 1.0, 0, "center"), ("BAT", 4.5, 43.75, 0.8, 0, "center"), ("+", 6.8, 43.75, 1.0, 0, "center"),
]
BACK_TEXT = [   # (text, y, size, bold) on B.SilkS, mirrored
    ("H2 SOIL SENSOR v3", 17.0, 1.2, True), ("Matter over Thread", 19.2, 1.0, False),
    ("ESP32-H2 + CR123A", 21.2, 1.0, False), ("BAT 2.0-3.3V, reverse protected", 23.4, 0.8, False),
    ("Design by Haxeko", 26.2, 1.0, False), ("Made in Vietnam", 28.2, 1.0, False),
]
FULL_ZONE_PADS = set()

NETCLASSES = {
    "Default": dict(track=0.2, clearance=0.2),
    "Power": dict(track=0.4, clearance=0.2),
    "Analog": dict(track=0.25, clearance=0.3),
}
NET_TO_CLASS = {
    "+3V3": "Power", "VBAT": "Power", "VBAT_RAW": "Power", "VIN_BB": "Power", "LX1": "Power", "LX2": "Power",
    "VSENS": "Power", "GND": "Power",
    "SOIL_AOUT": "Analog", "SOIL_ADC": "Analog", "VBAT_ADC": "Analog",
}


# --------------------------------------------------------------------------- netlist
def read_netlist():
    out = os.path.join(tempfile.mkdtemp(), "net.net")
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", out, SCH_PATH],
                   check=True, capture_output=True)
    nl = loads(open(out, encoding="utf-8").read())
    comps = {}
    for c in find_all(find(nl, "components"), "comp"):
        ref = str(find(c, "ref")[1])
        fields = {}
        fl = find(c, "fields")
        if fl:
            for f in find_all(fl, "field"):
                fields[str(find(f, "name")[1])] = str(f[2]) if len(f) > 2 else ""
        props = {str(find(p, "name")[1]): str(find(p, "value")[1]) if find(p, "value") else ""
                 for p in find_all(c, "property")}
        comps[ref] = dict(value=str(find(c, "value")[1]), footprint=str(find(c, "footprint")[1]),
                          fields=fields, dnp="dnp" in props)
    nets = {}
    for n in find_all(find(nl, "nets"), "net"):
        name = str(find(n, "name")[1])
        short = name.rsplit("/", 1)[-1] if name.startswith("/") else name
        nets[short] = [(str(find(nd, "ref")[1]), str(find(nd, "pin")[1])) for nd in find_all(n, "node")]
    return comps, nets


# --------------------------------------------------------------------------- project / rules
def write_project_rules():
    with open(PRO_PATH) as f:
        pro = json.load(f)
    classes = []
    for name, c in NETCLASSES.items():
        classes.append({"bus_width": 12, "clearance": c["clearance"], "diff_pair_gap": 0.25,
                        "diff_pair_via_gap": 0.25, "diff_pair_width": 0.2, "line_style": 0,
                        "microvia_diameter": 0.3, "microvia_drill": 0.1, "name": name,
                        "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)",
                        "track_width": c["track"], "via_diameter": 0.6, "via_drill": 0.3, "wire_width": 6})
    pro["net_settings"] = {"classes": classes, "meta": {"version": 3}, "net_colors": None,
                           "netclass_assignments": None,
                           "netclass_patterns": [{"netclass": c, "pattern": n} for n, c in NET_TO_CLASS.items()]}
    with open(PRO_PATH, "w") as f:
        json.dump(pro, f, indent=2)


def setup_design_rules(board):
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ds.m_CopperEdgeClearance = MM(0.45)
    ds.m_MinClearance = MM(0.15)
    ds.m_TrackMinWidth = MM(0.15)
    ds.m_ViasMinSize = MM(0.5)
    ds.m_MinThroughDrill = MM(0.3)
    ds.m_HoleClearance = MM(0.25)
    ds.m_HoleToHoleMin = MM(0.25)
    ds.m_SolderMaskMinWidth = MM(0.0)
    try:
        ds.SetBoardThickness(MM(1.6))
    except Exception:
        pass


# --------------------------------------------------------------------------- build
def lib_path(fpid):
    lib, name = fpid.split(":")
    if lib == "h2soil":
        return os.path.join(HW, "lib", "h2soil.pretty"), name
    return os.path.join(KICAD_FP, lib + ".pretty"), name


def add_segment(board, a, b, layer, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(P(*a))
    s.SetEnd(P(*b))
    s.SetLayer(layer)
    s.SetWidth(MM(width))
    board.Add(s)


def add_text(board, txt, x, y, layer, size=1.0, angle=0, mirrored=False, bold=False, justify="center"):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt)
    t.SetPosition(P(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(size * (0.2 if bold else 0.15)))
    if angle:
        t.SetTextAngleDegrees(angle)
    if mirrored:
        t.SetMirrored(True)
    if justify == "left":
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    elif justify == "right":
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_RIGHT)
    board.Add(t)


def add_track(board, net, pts, layer=pcbnew.F_Cu, width=0.25):
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(P(*a))
        t.SetEnd(P(*b))
        t.SetWidth(MM(width))
        t.SetLayer(layer)
        t.SetNet(net)
        t.SetLocked(True)
        board.Add(t)


def check_placement(comps):
    """Courtyard overlap / board-edge check (module antenna overhang is intended)."""
    boxes = {}
    for ref, c in sorted(comps.items()):
        x, y, r = PLACE[ref]
        boxes[ref] = fpinfo.placed_bbox(c["footprint"], x, y, r)
    bad = 0
    refs = sorted(boxes)
    for i, a in enumerate(refs):
        ax1, ay1, ax2, ay2 = boxes[a]
        if a != "U2" and (ax1 < 0 or ay1 < 0 or ax2 > W or ay2 > H):
            print(f"  outside board: {a} {tuple(round(v, 2) for v in boxes[a])}")
            bad += 1
        for b in refs[i + 1:]:
            bx1, by1, bx2, by2 = boxes[b]
            ox, oy = min(ax2, bx2) - max(ax1, bx1), min(ay2, by2) - max(ay1, by1)
            if ox > 0.01 and oy > 0.01:
                print(f"  courtyard overlap {a} / {b}: {ox:.2f} x {oy:.2f} mm")
                bad += 1
    print("placement check:", "OK" if not bad else f"{bad} problems")
    return bad


def build(comps, nets):
    board = pcbnew.NewBoard(PCB_PATH)
    setup_design_rules(board)
    tb = board.GetTitleBlock()
    tb.SetTitle("H2 Soil Sensor v3 - compact ESP32-H2 board for a capacitive soil module")
    tb.SetRevision("3.0")
    tb.SetDate("2026-11-12")
    tb.SetCompany("H2 Soil Sensor")
    tb.SetComment(0, "2-layer FR4 1.6mm 26x45mm, HASL/ENIG, green mask; module antenna overhangs top edge")
    netinfo = {}
    for name in sorted(nets):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    pin_net = {(r, p): n for n, nodes in nets.items() for (r, p) in nodes}

    for ref, c in sorted(comps.items()):
        if ref not in PLACE:
            raise SystemExit(f"no placement for {ref}")
        path, name = lib_path(c["footprint"])
        fp = pcbnew.FootprintLoad(path, name)
        if fp is None:
            raise SystemExit(f"cannot load {c['footprint']}")
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetFPID(pcbnew.LIB_ID(*c["footprint"].split(":")))
        for k in ("LCSC", "MPN", "Manufacturer"):
            if c["fields"].get(k):
                fp.SetProperty(k, c["fields"][k])
        x, y, rot = PLACE[ref]
        fp.SetPosition(P(x, y))
        fp.SetOrientationDegrees(rot)
        attrs = fp.GetAttributes()
        if c["dnp"]:
            attrs |= pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES
            fp.SetProperty("DNP", "DNP")
        if ref.startswith("H") or ref.startswith("TP") or ref in ("J1", "J3"):
            attrs |= pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES
        fp.SetAttributes(attrs)
        board.Add(fp)
        for pad in fp.Pads():
            n = pin_net.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(netinfo[n])
        # reference designators go to the assembly (Fab) layer; silk keeps only user-facing labels
        fp.Reference().SetLayer(pcbnew.F_Fab)
        fp.Reference().SetTextSize(pcbnew.VECTOR2I(MM(0.5), MM(0.5)))
        fp.Reference().SetTextThickness(MM(0.08))
        fp.Reference().SetPosition(fp.GetPosition())
        fp.Value().SetVisible(False)
        for pad in fp.Pads():
            if ref in ("U1", "U2") and pad.HasHole():
                pad.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
            if (ref, pad.GetNumber()) in FULL_ZONE_PADS:   # crowded GND pads: solid zone connection
                pad.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

    # outline (chamfered rectangle)
    pts = OUTLINE + [OUTLINE[0]]
    for a, b in zip(pts, pts[1:]):
        add_segment(board, a, b, pcbnew.Edge_Cuts, 0.1)

    # silkscreen: user-facing labels only
    for txt, x, y, size, ang, just in LABELS:
        add_text(board, txt, x, y, pcbnew.F_SilkS, size, angle=ang, justify=just)
    for txt, y, size, bold in BACK_TEXT:
        add_text(board, txt, W / 2, y, pcbnew.B_SilkS, size, mirrored=True, bold=bold)
    add_text(board, "^ ANTENNA (no metal) ^", PLACE["U2"][0], -1.0, pcbnew.F_Fab, 0.8)

    # ---------------------------------------------------------------- TPS63900 power stage (short loops)
    vin, lx1, lx2, v33, gnd = (netinfo[n] for n in ("VIN_BB", "LX1", "LX2", "+3V3", "GND"))
    add_track(board, vin, [(8.812, 25.0), (9.2, 24.6), (9.2, 23.6)], width=0.3)      # VIN -> C3
    add_track(board, vin, [(9.075, 23.6), (9.0, 22.3), (9.0, 21.7)], width=0.3)      # C3 -> C2
    add_track(board, vin, [(7.425, 21.7), (8.95, 21.7)], width=0.3)                  # R10 -> C2
    add_track(board, vin, [(6.388, 25.0), (6.388, 24.3), (7.425, 23.1), (7.425, 21.7)], width=0.25)  # EN -> VIN
    add_track(board, gnd, [(6.388, 25.5), (7.3, 25.5)], width=0.25)                  # SEL -> EP (GND)
    add_track(board, gnd, [(8.812, 26.0), (7.9, 26.0)], width=0.25)                  # GND pin -> EP
    add_track(board, lx1, [(8.812, 25.5), (9.6, 25.5)], width=0.25)
    add_track(board, lx1, [(9.6, 25.5), (10.6, 25.4)], width=0.4)
    add_track(board, lx2, [(8.812, 26.5), (9.6, 26.5)], width=0.25)
    add_track(board, lx2, [(9.6, 26.5), (10.6, 27.2)], width=0.4)
    add_track(board, v33, [(8.812, 27.0), (9.2, 27.35), (9.65, 28.8)], width=0.3)     # VOUT -> C4
    add_track(board, v33, [(9.65, 29.4), (9.65, 31.4)], width=0.4)                   # C4 -> C5
    pcbnew.SaveBoard(PCB_PATH, board)
    return board


def main():
    if os.environ.get("PYTHONHASHSEED") != "0":   # deterministic routing (set/dict order)
        os.execve(sys.executable, [sys.executable] + sys.argv, dict(os.environ, PYTHONHASHSEED="0"))
    comps, nets = read_netlist()
    if check_placement(comps) and "--force" not in sys.argv:
        raise SystemExit("fix placement first (or --force)")
    if "--check" in sys.argv:
        return
    write_project_rules()
    board = build(comps, nets)
    board = pcbnew.LoadBoard(PCB_PATH)   # reload so project net classes apply
    stats = router.route_board(board, origin=(X0, Y0), width=W, route_ymax=H,
                               netclasses=NETCLASSES, net_to_class=NET_TO_CLASS, outline=OUTLINE, slot=())
    print("router:", stats)
    router.finish_ground(board, origin=(X0, Y0), rect=(-1.0, -1.0, W + 1.0, H + 1.0))
    pcbnew.SaveBoard(PCB_PATH, board)
    txt = open(PCB_PATH, encoding="utf-8").read().replace('(paper "A4")', '(paper "A4" portrait)', 1)
    open(PCB_PATH, "w", encoding="utf-8").write(txt)
    board = pcbnew.LoadBoard(PCB_PATH)
    rpt = os.path.join(HW, "docs", "drc_report.txt")
    os.makedirs(os.path.dirname(rpt), exist_ok=True)
    pcbnew.WriteDRCReport(board, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    print("DRC report:", rpt)


if __name__ == "__main__":
    main()
