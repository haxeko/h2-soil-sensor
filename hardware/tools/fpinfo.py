"""Footprint geometry helpers (courtyard bbox, pads) parsed from .kicad_mod files."""
from __future__ import annotations

import math
import os

from sexp import find, find_all, loads

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
KICAD_FP = os.environ.get("KICAD7_FOOTPRINT_DIR", "/usr/share/kicad/footprints")
_cache = {}


def mod_path(fpid):
    lib, name = fpid.split(":")
    d = os.path.join(HW, "lib", "h2soil.pretty") if lib == "h2soil" else os.path.join(KICAD_FP, lib + ".pretty")
    return os.path.join(d, name + ".kicad_mod")


def _pts(node):
    out = []
    for key in ("start", "end", "center", "mid"):
        n = find(node, key)
        if n:
            out.append((float(n[1]), float(n[2])))
    p = find(node, "pts")
    if p:
        out += [(float(xy[1]), float(xy[2])) for xy in find_all(p, "xy")]
    return out


def info(fpid):
    if fpid in _cache:
        return _cache[fpid]
    m = loads(open(mod_path(fpid), encoding="utf-8").read())
    crt = []
    for kind in ("fp_line", "fp_rect", "fp_poly", "fp_circle", "fp_arc"):
        for n in find_all(m, kind):
            lay = find(n, "layer")
            if lay and str(lay[1]) == "F.CrtYd":
                pts = _pts(n)
                if kind == "fp_circle":
                    cx, cy = float(find(n, "center")[1]), float(find(n, "center")[2])
                    ex, ey = float(find(n, "end")[1]), float(find(n, "end")[2])
                    r = math.hypot(ex - cx, ey - cy)
                    pts = [(cx - r, cy - r), (cx + r, cy + r)]
                crt += pts
    pads = []
    for p in find_all(m, "pad"):
        at = find(p, "at")
        sz = find(p, "size")
        pads.append((str(p[1]), float(at[1]), float(at[2]), float(sz[1]), float(sz[2]), str(p[2])))
    attr = find(m, "attr")
    tht = bool(attr) and str(attr[1]) == "through_hole"
    if crt:
        xs, ys = [a for a, _ in crt], [b for _, b in crt]
        bb = (min(xs), min(ys), max(xs), max(ys))
    else:
        xs = [x - w / 2 for _, x, _, w, _, _ in pads] + [x + w / 2 for _, x, _, w, _, _ in pads]
        ys = [y - h / 2 for _, _, y, _, h, _ in pads] + [y + h / 2 for _, _, y, _, h, _ in pads]
        bb = (min(xs) - 0.25, min(ys) - 0.25, max(xs) + 0.25, max(ys) + 0.25)
    _cache[fpid] = dict(crt=bb, pads=pads, tht=tht)
    return _cache[fpid]


def rot(x, y, deg):
    """KiCad rotation (positive = counter-clockwise on screen, y down)."""
    a = math.radians(deg)
    c, s = round(math.cos(a), 9), round(math.sin(a), 9)
    return x * c + y * s, -x * s + y * c


def placed_bbox(fpid, x, y, deg):
    x1, y1, x2, y2 = info(fpid)["crt"]
    pts = [rot(px, py, deg) for px, py in ((x1, y1), (x2, y1), (x2, y2), (x1, y2))]
    xs, ys = [x + a for a, _ in pts], [y + b for _, b in pts]
    return min(xs), min(ys), max(xs), max(ys)


def placed_pads(fpid, x, y, deg):
    out = []
    for num, px, py, w, h, kind in info(fpid)["pads"]:
        a, b = rot(px, py, deg)
        if deg % 180:
            w, h = h, w
        out.append((num, round(x + a, 3), round(y + b, 3), w, h, kind))
    return out
