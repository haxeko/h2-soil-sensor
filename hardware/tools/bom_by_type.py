#!/usr/bin/env python3
"""BOM grouped by component type with JLC/LCSC unit prices -> fab/h2-soil-sensor_BOM_by_type.csv.

Usage: python3 bom_by_type.py [prices.json]   (json: {LCSC: {"p10": usd}}; prices optional)
"""
import csv
import json
import os
import re
import sys

import gen_pcb

CAT = {"C": "1. Tụ điện", "R": "2. Điện trở", "L": "3. Cuộn cảm", "D": "4. Diode / LED", "Q": "5. MOSFET",
       "U": "6. IC / module", "SW": "7. Nút nhấn", "J": "8. Cổng / pad"}


def nat(r):
    m = re.match(r"([A-Z]+)(\d+)", r)
    return (m.group(1), int(m.group(2)))


def main():
    prices = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else {}
    prices.setdefault("C61148", {"p10": 0.0372})
    comps, _ = gen_pcb.read_netlist()
    groups = {}
    for ref, c in comps.items():
        k = (c["value"], c["footprint"].split(":")[1], c["fields"].get("LCSC", ""), c["fields"].get("MPN", ""),
             c["fields"].get("Manufacturer", ""))
        groups.setdefault(k, []).append(ref)
    rows = []
    for k, refs in groups.items():
        refs = sorted(refs, key=nat)
        p10 = prices.get(k[2], {}).get("p10")
        rows.append((CAT[re.match(r"[A-Z]+", refs[0]).group()], *k, len(refs), ", ".join(refs), p10))
    rows.sort(key=lambda r: (r[0], nat(r[7].split(",")[0])))
    out = os.path.join(gen_pcb.HW, "fab", "h2-soil-sensor_BOM_by_type.csv")
    total = 0.0
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Loai", "Gia tri", "Footprint", "LCSC", "MPN", "Hang", "SL", "Ky hieu", "Don gia USD (SL10)",
                    "Thanh tien USD"])
        for r in rows:
            t = round(r[8] * r[6], 4) if r[8] else ""
            total += t or 0
            w.writerow(list(r[:8]) + [r[8] or "", t])
        w.writerow(["TONG", "", "", "", "", "", sum(r[6] for r in rows), "", "", round(total, 3)])
    print(out, "total USD", round(total, 3))


if __name__ == "__main__":
    main()
