#!/usr/bin/env python3
"""Connectivity check (ERC substitute for KiCad 7 CLI).

Exports the netlist with kicad-cli, then verifies that every pin of every
component lands on exactly the net declared in design.py, that NC pins are
unconnected, that no net has a single node, and that power-input pins are
driven (power_out pin or PWR_FLAG on the net).

Usage: python3 check_netlist.py <root.kicad_sch>
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import design
from sexp import find, find_all, loads
from symlib import load_symbol, pins_of, project_symbols

PROJ = project_symbols()


def sym_pins(lib, name):
    s = PROJ[name] if lib == "h2soil" else load_symbol(lib, name)
    return {p["number"]: p for p in pins_of(s)}


def main(root):
    out = os.path.join(tempfile.mkdtemp(), "net.net")
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", out, root],
                   check=True, capture_output=True)
    nl = loads(open(out, encoding="utf-8").read())
    nets = find(nl, "nets")
    pin2net = {}
    net_nodes = {}
    for n in find_all(nets, "net"):
        name = str(find(n, "name")[1])
        short = name.rsplit("/", 1)[-1] if name.startswith("/") else name
        nodes = []
        for node in find_all(n, "node"):
            ref = str(find(node, "ref")[1])
            pin = str(find(node, "pin")[1])
            ptype = find(node, "pintype")
            nodes.append((ref, pin, str(ptype[1]) if ptype else ""))
            pin2net[(ref, pin)] = short
        net_nodes[short] = nodes

    errors, warnings = [], []
    comps = {c["ref"]: c for c in design.COMPONENTS}
    flagged = {c["pins"]["1"] for c in design.COMPONENTS if c.get("virtual")}
    for ref, c in comps.items():
        if ref.startswith("#"):
            continue  # power flags are not exported to the netlist
        pins = sym_pins(c["lib"], c["sym"])
        for num, p in pins.items():
            exp = c["pins"].get(num, "NC" if p["type"] == "no_connect" else None)
            got = pin2net.get((ref, num))
            if c.get("virtual"):
                got = got  # PWR_FLAGs appear as nodes too
            if exp is None:
                errors.append(f"{ref}.{num}: no expected net")
                continue
            if exp == "NC":
                if got is not None and not got.startswith("unconnected-"):
                    errors.append(f"{ref}.{num} ({p['name']}): expected NC, got {got}")
                continue
            if got != exp:
                errors.append(f"{ref}.{num} ({p['name']}): expected {exp}, got {got}")

    for net, nodes in net_nodes.items():
        if net.startswith("unconnected-"):
            continue
        real = [n for n in nodes if not n[0].startswith("#")]
        if len(real) < 2:
            errors.append(f"net {net} has <2 component pins: {nodes}")
        types = {t.split("+")[0] for (_, _, t) in nodes}
        has_pwr_in = any(t.startswith("power_in") for (r, _, t) in nodes if not r.startswith("#PWR"))
        driven = any(t.startswith("power_out") for (_, _, t) in nodes) or net in flagged
        if has_pwr_in and not driven:
            errors.append(f"net {net}: power_in pins without driver (add PWR_FLAG): {nodes}")
        if not types:
            warnings.append(f"net {net}: no pin types")

    print(f"nets: {len(net_nodes)}  components checked: {len(comps)}")
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    if errors:
        sys.exit(1)
    print("OK: schematic connectivity matches design.py")


if __name__ == "__main__":
    main(sys.argv[1])
