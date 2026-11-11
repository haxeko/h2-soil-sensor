#!/usr/bin/env python3
"""Build, route and check the H2 soil sensor PCB (KiCad 7, pcbnew Python API).

Steps
  1. read the netlist exported from the schematic (kicad-cli) - single source of truth
  2. place footprints (stake-shaped 2-layer board, 26 mm electronics / 20 mm probe)
  3. hand-route the analog probe nets (sense electrode, NTC on the stake)
  4. GND fan-out vias, then route all other nets with a 2-layer grid A* router (router.py)
  5. GND pours on both layers + stitching vias, zone fill, DRC report

Usage: python3 gen_pcb.py            (run from hardware/tools)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

import pcbnew

import router
from sexp import find, find_all, loads

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
PCB_PATH = os.path.join(HW, "h2-soil-sensor.kicad_pcb")
PRO_PATH = os.path.join(HW, "h2-soil-sensor.kicad_pro")
SCH_PATH = os.path.join(HW, "h2-soil-sensor.kicad_sch")
KICAD_FP = "/usr/share/kicad/footprints"
X0, Y0 = 100.0, 40.0          # board-local (0,0) -> absolute KiCad coordinates
W = 26.0                      # electronics section width
SOIL_Y = 124.0                # soil line (probe footprint origin)

MM = pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(MM(X0 + x), MM(Y0 + y))


# ref: (x, y, rotation_deg) in board-local mm, all on the top side
PLACE = {
    "U2": (13.0, 4.0, 0),
    "C9": (2.0, 2.3, 270), "C8": (2.0, 5.4, 270), "R11": (2.0, 10.4, 270),
    "Y1": (8.5, 16.8, 180), "C10": (5.6, 17.2, 270), "C11": (11.4, 17.2, 270),
    "R22": (20.3, 16.8, 0), "D2": (23.6, 16.8, 180),
    # TPS63900 power stage
    "C1": (3.3, 21.7, 180), "R10": (6.6, 21.7, 0), "C2": (9.9, 21.7, 0), "C3": (9.9, 23.6, 0),
    "U1": (7.6, 26.0, 0), "L1": (11.4, 26.4, 270), "C4": (10.6, 29.4, 0), "C5": (10.6, 31.4, 0),
    "R2": (3.7, 25.2, 180), "R3": (3.7, 26.7, 180), "R4": (3.7, 28.2, 180),
    # battery measurement + VSENS switch
    "Q2": (16.6, 21.0, 0), "R5": (13.7, 21.0, 90), "Q3": (16.6, 25.4, 0), "R6": (13.7, 25.4, 270),
    "R7": (20.2, 21.0, 0), "R8": (22.8, 22.6, 270), "C6": (24.4, 22.6, 270),
    "Q4": (16.6, 30.0, 0), "R9": (13.7, 30.0, 90), "C7": (20.1, 30.0, 0),
    # UI
    "SW1": (5.0, 38.0, 0), "R21": (10.8, 36.1, 180), "C21": (10.8, 37.9, 0),
    "SW2": (5.0, 45.0, 0), "C12": (10.8, 43.1, 0),
    "TP1": (13.8, 34.6, 0), "TP2": (16.0, 34.6, 0), "TP3": (18.2, 34.6, 0), "TP4": (16.0, 37.0, 0),
    "J1": (4.11, 50.0, 90),
    # SHT40 thermal island (slot x 20.0..20.8, y 33..46)
    "R19": (23.6, 35.0, 0), "R20": (23.6, 36.6, 0), "U4": (23.6, 39.5, 0), "C20": (23.6, 42.6, 0),
    # reverse polarity + battery
    "R1": (5.6, 53.65, 180), "Q1": (9.0, 54.6, 0),
    "BT1": (13.7, 79.0, 90),
    # probe front-end (just above the soil line)
    "C14": (2.6, 103.8, 90), "R12": (2.6, 107.0, 90), "U3": (8.0, 107.0, 0),
    "C15": (13.2, 105.0, 270), "C13": (13.2, 108.9, 270),
    "R18": (19.0, 105.0, 0), "C19": (19.0, 106.8, 180), "TP5": (24.6, 109.4, 0),
    "C18": (19.0, 110.8, 0), "R17": (19.0, 112.6, 0), "R16": (16.4, 114.2, 90),
    "R13": (6.0, 111.8, 0), "R14": (6.0, 113.6, 0), "R15": (10.0, 115.4, 270),
    "D1": (13.0, 117.6, 180), "C17": (16.4, 117.6, 270), "TP6": (7.4, 117.4, 0),
    "H1": (2.6, 118.0, 0), "H2": (23.4, 118.0, 0),
    "PRB1": (13.0, SOIL_Y, 0),
    "RT1": (21.6, 173.0, 270),
}

OUTLINE = [(0, 0), (W, 0), (W, 120), (23, SOIL_Y), (23, 200), (13, 212), (3, 200), (3, SOIL_Y), (0, 120)]
SLOT = (20.0, 33.0, 20.8, 46.0)      # SHT40 thermal isolation slot (x1, y1, x2, y2)

NETCLASSES = {
    "Default": dict(track=0.2, clearance=0.2),
    "Power": dict(track=0.4, clearance=0.2),
    "Analog": dict(track=0.25, clearance=0.3),
}
NET_TO_CLASS = {
    "+3V3": "Power", "VBAT": "Power", "VBAT_RAW": "Power", "VIN_BB": "Power", "LX1": "Power", "LX2": "Power",
    "VSENS": "Power", "GND": "Power",
    "PROBE_SENSE": "Analog", "PROBE_EXC": "Analog", "PROBE_DET": "Analog", "OSC_OUT": "Analog",
    "SOIL_ADC": "Analog", "NTC_ADC": "Analog",
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


def add_text(board, txt, x, y, layer, size=1.0, angle=0, mirrored=False, bold=False):
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


def build(comps, nets):
    board = pcbnew.NewBoard(PCB_PATH)
    setup_design_rules(board)
    tb = board.GetTitleBlock()
    tb.SetTitle("H2 Soil Sensor - Matter over Thread (ESP32-H2, CR123A)")
    tb.SetRevision("1.0")
    tb.SetDate("2026-11-11")
    tb.SetCompany("H2 Soil Sensor")
    tb.SetComment(0, "2-layer FR4 1.6mm, HASL/ENIG, green mask; probe: conformal coat")
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
        if ref.startswith("PRB") or ref.startswith("H") or ref.startswith("TP"):
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
            if (ref in ("U1", "U2") and pad.HasHole()) or ref == "PRB1":
                pad.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

    # outline + slot
    pts = OUTLINE + [OUTLINE[0]]
    for a, b in zip(pts, pts[1:]):
        add_segment(board, a, b, pcbnew.Edge_Cuts, 0.1)
    x1, y1, x2, y2 = SLOT
    for a, b in [((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)), ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))]:
        add_segment(board, a, b, pcbnew.Edge_Cuts, 0.1)

    # silkscreen
    add_segment(board, (3.4, SOIL_Y), (22.6, SOIL_Y), pcbnew.F_SilkS, 0.2)
    add_text(board, "SOIL LINE / MAT DAT", 13, SOIL_Y - 1.0, pcbnew.F_SilkS, 0.8)
    add_text(board, "CONFORMAL COAT", 13, 150, pcbnew.F_SilkS, 1.2, angle=90)
    add_text(board, "H2 SOIL SENSOR  Matter/Thread  rev1.0", 13, 150, pcbnew.B_SilkS, 1.2, angle=90, mirrored=True)
    add_text(board, "BOOT", 5.0, 41.5, pcbnew.F_SilkS, 0.8)
    add_text(board, "RST", 11.0, 45.4, pcbnew.F_SilkS, 0.8)
    add_text(board, "SHT40", 23.4, 44.9, pcbnew.F_SilkS, 0.8)
    for i, lab in enumerate(["3V3", "GND", "TX", "RX", "EN", "IO9", "D-", "D+"]):
        add_text(board, lab, 4.11 + 2.54 * i, 47.6, pcbnew.B_SilkS, 0.8, mirrored=True)
    add_text(board, "J1", 1.2, 50.0, pcbnew.F_SilkS, 0.8, angle=90)
    add_text(board, "LED", 23.6, 18.6, pcbnew.F_SilkS, 0.8)
    add_text(board, "ANTENNA ->", 13, -1.0, pcbnew.F_Fab, 0.8)

    # ---------------------------------------------------------------- hand routes (analog)
    sense = netinfo["PROBE_SENSE"]
    add_track(board, sense, [(10.0, 116.225), (10.0, 117.6), (11.95, 117.6)])
    add_track(board, sense, [(11.95, 117.6), (11.95, 120.0), (13.0, 121.05), (13.0, 129.0)])
    ntc = netinfo["NTC_ADC"]
    add_track(board, ntc, [(19.825, 106.8), (21.9, 108.875), (21.9, 171.5), (21.6, 171.8), (21.6, 172.175)],
              width=0.25)
    add_track(board, netinfo["GND"], [(21.6, 173.825), (20.3, 173.825)], width=0.3)

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
    write_project_rules()
    comps, nets = read_netlist()
    board = build(comps, nets)
    board = pcbnew.LoadBoard(PCB_PATH)   # reload so project net classes apply
    stats = router.route_board(board, origin=(X0, Y0), width=W, route_ymax=SOIL_Y - 1.0,
                               netclasses=NETCLASSES, net_to_class=NET_TO_CLASS)
    print("router:", stats)
    router.finish_ground(board, origin=(X0, Y0), soil_y=SOIL_Y, slot=SLOT)
    pcbnew.SaveBoard(PCB_PATH, board)
    txt = open(PCB_PATH, encoding="utf-8").read().replace('(paper "A4")', '(paper "A3" portrait)', 1)
    open(PCB_PATH, "w", encoding="utf-8").write(txt)
    board = pcbnew.LoadBoard(PCB_PATH)
    rpt = os.path.join(HW, "docs", "drc_report.txt")
    os.makedirs(os.path.dirname(rpt), exist_ok=True)
    pcbnew.WriteDRCReport(board, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    print("DRC report:", rpt)


if __name__ == "__main__":
    main()
