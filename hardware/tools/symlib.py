"""Symbol helpers: load KiCad library symbols (flattening `extends`) and build
project-specific symbols for the h2soil library."""
from __future__ import annotations

import copy
import os

from sexp import QStr, loads, find, find_all

KICAD_SYM_DIR = "/usr/share/kicad/symbols"
_cache: dict[str, list] = {}


def _lib(libname: str):
    if libname not in _cache:
        with open(os.path.join(KICAD_SYM_DIR, libname + ".kicad_sym"), encoding="utf-8") as f:
            _cache[libname] = loads(f.read())
    return _cache[libname]


def _raw_symbol(libname: str, name: str):
    lib = _lib(libname)
    for s in find_all(lib, "symbol"):
        if s[1] == name:
            return s
    raise KeyError(f"{libname}:{name} not found")


def _rename_units(sym, old: str, new: str):
    for sub in find_all(sym, "symbol"):
        if sub[1].startswith(old + "_"):
            sub[1] = QStr(new + sub[1][len(old):])


def load_symbol(libname: str, name: str):
    """Return a flattened copy of a library symbol (top name without lib prefix)."""
    sym = copy.deepcopy(_raw_symbol(libname, name))
    ext = find(sym, "extends")
    if ext is None:
        return sym
    parent = load_symbol(libname, ext[1])
    child_props = find_all(sym, "property")
    flat = [sym[0], QStr(name)]
    for item in parent[2:]:
        if isinstance(item, list) and item and item[0] in ("property", "symbol"):
            continue
        flat.append(copy.deepcopy(item))
    flat.extend(copy.deepcopy(child_props))
    # keep parent's non-standard properties that the child does not override (rare)
    names = {p[1] for p in child_props}
    for p in find_all(parent, "property"):
        if p[1] not in names:
            flat.append(copy.deepcopy(p))
    for sub in find_all(parent, "symbol"):
        s2 = copy.deepcopy(sub)
        flat.append(s2)
    _rename_units(flat, parent[1], name)
    return flat


def embed(sym, lib_prefix: str):
    """Return a copy of symbol `sym` named 'lib_prefix:Name' for lib_symbols."""
    s = copy.deepcopy(sym)
    s[1] = QStr(f"{lib_prefix}:{sym[1]}")
    return s


def pins_of(sym):
    """Yield dicts for every pin: number, name, type, x, y, angle, length, unit."""
    out = []
    for sub in find_all(sym, "symbol"):
        # unit index from name suffix NAME_U_S
        try:
            unit = int(str(sub[1]).rsplit("_", 2)[-2])
        except ValueError:
            unit = 0
        for p in find_all(sub, "pin"):
            at = find(p, "at")
            num = find(p, "number")[1]
            nm = find(p, "name")[1]
            ln = find(p, "length")
            out.append(dict(number=str(num), name=str(nm), type=p[1], x=float(at[1]), y=float(at[2]),
                            angle=float(at[3]) if len(at) > 3 else 0.0,
                            length=float(ln[1]) if ln else 0.0, unit=unit))
    return out


# ---------------------------------------------------------------------------
# Project symbols
# ---------------------------------------------------------------------------

def _eff(size=1.27, hide=False, justify=None):
    e = ["effects", ["font", ["size", size, size]]]
    if justify:
        e.append(["justify"] + justify.split())
    if hide:
        e.append("hide")
    return e


def _prop(name, value, x=0.0, y=0.0, hide=False, justify=None, angle=0):
    return ["property", QStr(name), QStr(value), ["at", x, y, angle], _eff(hide=hide, justify=justify)]


def _pin(ptype, x, y, angle, length, name, number, hide_name=False):
    p = ["pin", ptype, "line", ["at", x, y, angle], ["length", length]]
    if hide_name:
        p.append("hide")
    p.append(["name", QStr(name), _eff()])
    p.append(["number", QStr(number), _eff()])
    return p


def esp32_h2_wroom_02c():
    """ESP32-H2-WROOM-02C symbol (pin numbers follow datasheet v1.2, Table 2)."""
    name = "ESP32-H2-WROOM-02C"
    left = [  # (number, name, type)
        ("1", "3V3", "power_in"),
        ("2", "EN", "input"),
        ("14", "VBAT", "passive"),
        (None, None, None),
        ("7", "IO8", "bidirectional"),
        ("8", "IO9", "bidirectional"),
        ("20", "IO25", "bidirectional"),
        (None, None, None),
        ("21", "RXD0/IO23", "bidirectional"),
        ("22", "TXD0/IO24", "bidirectional"),
        ("23", "IO26/USB_D-", "bidirectional"),
        ("24", "IO27/USB_D+", "bidirectional"),
        (None, None, None),
        ("11", "IO13/XTAL_32K_P", "bidirectional"),
        ("12", "IO14/XTAL_32K_N", "bidirectional"),
    ]
    right = [
        ("28", "IO0", "bidirectional"),
        ("27", "IO1/ADC1_CH0", "bidirectional"),
        ("26", "IO2/ADC1_CH1/MTMS", "bidirectional"),
        ("25", "IO3/ADC1_CH2/MTDO", "bidirectional"),
        ("3", "IO4/ADC1_CH3/MTCK", "bidirectional"),
        ("4", "IO5/ADC1_CH4/MTDI", "bidirectional"),
        (None, None, None),
        ("5", "IO10", "bidirectional"),
        ("6", "IO11", "bidirectional"),
        ("10", "IO12", "bidirectional"),
        ("15", "IO22", "bidirectional"),
        (None, None, None),
        ("16", "NC", "no_connect"),
        ("17", "NC", "no_connect"),
        ("18", "NC", "no_connect"),
        ("19", "NC", "no_connect"),
    ]
    rows = max(len(left), len(right))
    top = (rows - 1) * 2.54 / 2
    top = round(top / 2.54) * 2.54
    w = 15.24
    pins = []
    for i, (num, nm, t) in enumerate(left):
        if num:
            pins.append(_pin(t, -w - 2.54, top - i * 2.54, 0, 2.54, nm, num))
    for i, (num, nm, t) in enumerate(right):
        if num:
            pins.append(_pin(t, w + 2.54, top - i * 2.54, 180, 2.54, nm, num))
    bottom_y = top - rows * 2.54 - 2.54
    for k, num in enumerate(["9", "13", "29"]):
        pins.append(_pin("power_in", -5.08 + k * 5.08, bottom_y - 2.54, 90, 2.54, "GND", num, hide_name=False))
    body = ["rectangle", ["start", -w, top + 2.54], ["end", w, bottom_y],
            ["stroke", ["width", 0.254], ["type", "default"]], ["fill", ["type", "background"]]]
    sym = ["symbol", QStr(name), ["pin_names", ["offset", 1.016]], ["in_bom", "yes"], ["on_board", "yes"],
           _prop("Reference", "U", -w, top + 3.81, justify="left"),
           _prop("Value", name, w, top + 3.81, justify="right"),
           _prop("Footprint", "h2soil:ESP32-H2-WROOM-02C", 0, 0, hide=True),
           _prop("Datasheet", "https://documentation.espressif.com/esp32-h2-wroom-02c_datasheet_en.pdf", 0, 0, hide=True),
           _prop("ki_keywords", "ESP32-H2 802.15.4 Thread Zigbee BLE module", 0, 0, hide=True),
           _prop("ki_description", "ESP32-H2 RISC-V module, 802.15.4 (Thread/Zigbee) + BLE 5.3, PCB antenna, 2/4 MB flash", 0, 0, hide=True),
           ["symbol", QStr(name + "_0_1"), body],
           ["symbol", QStr(name + "_1_1")] + pins]
    return sym


def soil_probe():
    name = "SoilProbe_Capacitive"
    g = [
        ["rectangle", ["start", -2.54, 3.81], ["end", 2.54, -3.81],
         ["stroke", ["width", 0.254], ["type", "default"]], ["fill", ["type", "none"]]],
        ["polyline", ["pts", ["xy", -1.524, 2.54], ["xy", -1.524, -2.54]], ["stroke", ["width", 0.508], ["type", "default"]], ["fill", ["type", "none"]]],
        ["polyline", ["pts", ["xy", 1.524, 2.54], ["xy", 1.524, -2.54]], ["stroke", ["width", 0.508], ["type", "default"]], ["fill", ["type", "none"]]],
        ["polyline", ["pts", ["xy", -0.762, 1.27], ["xy", -0.254, 1.778], ["xy", 0.254, 0.762], ["xy", 0.762, 1.27]],
         ["stroke", ["width", 0], ["type", "default"]], ["fill", ["type", "none"]]],
        ["polyline", ["pts", ["xy", -0.762, -0.508], ["xy", -0.254, 0], ["xy", 0.254, -1.016], ["xy", 0.762, -0.508]],
         ["stroke", ["width", 0], ["type", "default"]], ["fill", ["type", "none"]]],
    ]
    pins = [_pin("passive", -5.08, 0, 0, 2.54, "SENSE", "1", hide_name=True),
            _pin("passive", 5.08, 0, 180, 2.54, "GND", "2", hide_name=True)]
    return ["symbol", QStr(name), ["pin_names", ["offset", 0], "hide"], ["in_bom", "no"], ["on_board", "yes"],
            _prop("Reference", "PRB", 0, 5.08),
            _prop("Value", name, 0, -5.08),
            _prop("Footprint", "h2soil:SoilProbe_Capacitive_80mm", 0, 0, hide=True),
            _prop("Datasheet", "", 0, 0, hide=True),
            _prop("ki_description", "PCB-printed capacitive soil probe: SENSE electrode vs GND electrodes (covered by solder mask + conformal coating)", 0, 0, hide=True),
            ["symbol", QStr(name + "_0_1")] + g,
            ["symbol", QStr(name + "_1_1")] + pins]


def power_symbol(netname: str):
    """Supply power symbol (arrow up) creating a global net `netname`."""
    g = [["polyline", ["pts", ["xy", -0.762, 1.27], ["xy", 0, 2.54]], ["stroke", ["width", 0], ["type", "default"]], ["fill", ["type", "none"]]],
         ["polyline", ["pts", ["xy", 0, 0], ["xy", 0, 2.54]], ["stroke", ["width", 0], ["type", "default"]], ["fill", ["type", "none"]]],
         ["polyline", ["pts", ["xy", 0, 2.54], ["xy", 0.762, 1.27]], ["stroke", ["width", 0], ["type", "default"]], ["fill", ["type", "none"]]]]
    pin = ["pin", "power_in", "line", ["at", 0, 0, 90], ["length", 0], "hide",
           ["name", QStr(netname), _eff()], ["number", QStr("1"), _eff()]]
    return ["symbol", QStr(netname), ["power"], ["pin_names", ["offset", 0]], ["in_bom", "yes"], ["on_board", "yes"],
            _prop("Reference", "#PWR", 0, -3.81, hide=True),
            _prop("Value", netname, 0, 3.556),
            _prop("Footprint", "", 0, 0, hide=True),
            _prop("Datasheet", "", 0, 0, hide=True),
            _prop("ki_keywords", "power-flag", 0, 0, hide=True),
            _prop("ki_description", f"Power symbol creates a global label with name \"{netname}\"", 0, 0, hide=True),
            ["symbol", QStr(netname + "_0_1")] + g,
            ["symbol", QStr(netname + "_1_1"), pin]]


def project_symbols():
    return {
        "ESP32-H2-WROOM-02C": esp32_h2_wroom_02c(),
        "SoilProbe_Capacitive": soil_probe(),
        "VBAT": power_symbol("VBAT"),
        "VSENS": power_symbol("VSENS"),
    }
