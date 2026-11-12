#!/usr/bin/env python3
"""Fabrication outputs: Gerbers + drill (zip), JLCPCB BOM + CPL, assembly PDF, renders.

Usage: python3 make_fab.py   (run from hardware/tools, after gen_pcb.py)
"""
from __future__ import annotations

import csv
import glob
import os
import shutil
import subprocess
import zipfile

import fpinfo
import gen_pcb

HW = gen_pcb.HW
PCB = gen_pcb.PCB_PATH
FAB = os.path.join(HW, "fab")
DOCS = os.path.join(HW, "docs")
ENV = dict(os.environ, KICAD7_FOOTPRINT_DIR="/usr/share/kicad/footprints",
           KICAD7_SYMBOL_DIR="/usr/share/kicad/symbols")


def run(*args):
    subprocess.run(list(args), check=True, capture_output=True, env=ENV)


def gerbers():
    out = os.path.join(FAB, "gerbers")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    run("kicad-cli", "pcb", "export", "gerbers", "--layers",
        "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",
        "--subtract-soldermask", "-o", out + "/", PCB)
    run("kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th",
        "--generate-map", "--map-format", "pdf", "-u", "mm", "-o", out + "/", PCB)
    zpath = os.path.join(FAB, "h2-soil-sensor_gerbers.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(glob.glob(out + "/*")):
            if not f.endswith(".pdf"):
                z.write(f, os.path.basename(f))
    return zpath


def bom_and_cpl():
    comps, _ = gen_pcb.read_netlist()
    # ---- BOM (JLCPCB SMT format); module / THT connectors / holes / test points / DNP listed separately
    groups = {}
    excluded = []
    for ref, c in sorted(comps.items()):
        lcsc = c["fields"].get("LCSC", "")
        if c["dnp"] or not lcsc or ref.startswith(("U2", "H", "TP")) or fpinfo.info(c["footprint"])["tht"]:
            if c["dnp"]:
                why = "DNP (tuy chon)"
            elif ref == "U2":
                why = "module ESP32-H2 - han tay / dat rieng"
            elif fpinfo.info(c["footprint"])["tht"] and lcsc:
                why = "THT - han tay (" + lcsc + ")"
            else:
                why = "khong lap (pad/lo/test point)"
            excluded.append((ref, c["value"], why))
            continue
        key = (c["value"], c["footprint"].split(":")[1], lcsc, c["fields"].get("MPN", ""),
               c["fields"].get("Manufacturer", ""))
        groups.setdefault(key, []).append(ref)
    bom = os.path.join(FAB, "h2-soil-sensor_BOM_JLCPCB.csv")
    with open(bom, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "MPN", "Manufacturer", "Qty"])
        def nat(r):
            import re
            m = re.match(r"([A-Z]+)(\d+)", r)
            return (m.group(1), int(m.group(2))) if m else (r, 0)
        for (val, fp, lcsc, mpn, mfr), refs in sorted(groups.items(), key=lambda kv: nat(sorted(kv[1], key=nat)[0])):
            refs = sorted(refs, key=nat)
            w.writerow([val, ",".join(refs), fp, lcsc, mpn, mfr, len(refs)])
    with open(os.path.join(FAB, "h2-soil-sensor_not_assembled.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Value", "Reason"])
        for row in excluded:
            w.writerow(row)
    # ---- CPL
    raw = os.path.join(FAB, "pos_raw.csv")
    run("kicad-cli", "pcb", "export", "pos", "--side", "front", "--format", "csv", "--units", "mm",
        "--exclude-fp-th", "-o", raw, PCB)
    cpl = os.path.join(FAB, "h2-soil-sensor_CPL_JLCPCB.csv")
    keep = {r for refs in groups.values() for r in refs}
    with open(raw) as fi, open(cpl, "w", newline="") as fo:
        rd = csv.DictReader(fi)
        w = csv.writer(fo)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for row in rd:
            if row["Ref"] not in keep:
                continue
            w.writerow([row["Ref"], row["PosX"] + "mm", row["PosY"] + "mm",
                        "Top" if row["Side"] == "top" else "Bottom", row["Rot"]])
    os.remove(raw)
    return bom, cpl


def drawings():
    os.makedirs(DOCS, exist_ok=True)
    run("kicad-cli", "sch", "export", "pdf", "-o", os.path.join(DOCS, "schematic.pdf"), gen_pcb.SCH_PATH)
    run("kicad-cli", "pcb", "export", "pdf", "--layers", "F.Fab,Edge.Cuts", "--include-border-title",
        "-o", os.path.join(DOCS, "assembly_top.pdf"), PCB)
    run("kicad-cli", "pcb", "export", "pdf", "--layers", "F.Cu,F.SilkS,F.Mask,Edge.Cuts", "--include-border-title",
        "-o", os.path.join(DOCS, "pcb_top.pdf"), PCB)
    run("kicad-cli", "pcb", "export", "pdf", "--mirror", "--layers", "B.Cu,B.SilkS,Edge.Cuts", "--include-border-title",
        "-o", os.path.join(DOCS, "pcb_bottom.pdf"), PCB)
    # PNG renders (board only)
    try:
        from PIL import Image
    except ImportError:
        return
    tmp = os.path.join(FAB, "_r")
    os.makedirs(tmp, exist_ok=True)
    for name, layers, mirror in (("pcb_top", "F.Cu,F.SilkS,F.Mask,Edge.Cuts", False),
                                 ("pcb_bottom", "B.Cu,B.SilkS,Edge.Cuts", True)):
        pdf = os.path.join(tmp, name + ".pdf")
        args = ["kicad-cli", "pcb", "export", "pdf", "--layers", layers, "-o", pdf, PCB]
        if mirror:
            args.insert(4, "--mirror")
        run(*args)
        run("pdftoppm", "-r", "300", "-png", pdf, os.path.join(tmp, name))
        img = Image.open(glob.glob(os.path.join(tmp, name + "*.png"))[0]).convert("RGB")
        g = img.convert("L").point(lambda v: 0 if v > 245 else 255)
        x1, y1, x2, y2 = g.getbbox()
        img.crop((x1 - 12, y1 - 12, x2 + 12, y2 + 12)).save(os.path.join(DOCS, name + ".png"))
    shutil.rmtree(tmp, ignore_errors=True)


def main():
    os.makedirs(FAB, exist_ok=True)
    z = gerbers()
    bom, cpl = bom_and_cpl()
    drawings()
    print("gerbers:", z)
    print("bom:", bom)
    print("cpl:", cpl)


if __name__ == "__main__":
    main()
