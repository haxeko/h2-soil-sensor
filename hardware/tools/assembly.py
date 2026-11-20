#!/usr/bin/env python3
"""Component placement drawing (PDF): enlarged top view with reference designators + parts table.

Usage: python3 assembly.py  (after gen_pcb.py)  ->  hardware/docs/assembly_drawing.pdf
"""
from __future__ import annotations

import os
import subprocess
import tempfile

import numpy as np
import pcbnew
from PIL import Image, ImageDraw, ImageFont

import gen_pcb

PCB = gen_pcb.PCB_PATH
OUT = os.path.join(gen_pcb.HW, "docs", "assembly_drawing.pdf")
DPI = 200                                  # page raster resolution
PAGE = (int(210 / 25.4 * DPI), int(297 / 25.4 * DPI))
SCALE = 4.5                                # drawing scale (board 26 x 45 mm -> 117 x 203 mm)
PX = SCALE * DPI / 25.4                    # pixels per board mm
MX0, MY0, MX1, MY1 = -1.0, -7.0, gen_pcb.W + 1.0, gen_pcb.H + 1.0
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONTB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TOMM = pcbnew.ToMM


def layer(name, tmp, erd=True):
    pdf = os.path.join(tmp, name.replace(".", "_") + ".pdf")
    args = ["kicad-cli", "pcb", "export", "pdf", "--black-and-white", "--layers", name, "-o", pdf, PCB]
    if erd:
        args[4:4] = ["--exclude-refdes", "--exclude-value"]
    subprocess.run(args, check=True, capture_output=True)
    res = PX * 25.4
    x0, y0 = int(round((gen_pcb.X0 + MX0) * PX)), int(round((gen_pcb.Y0 + MY0) * PX))
    w, h = int((MX1 - MX0) * PX), int((MY1 - MY0) * PX)
    base = os.path.join(tmp, name.replace(".", "_"))
    subprocess.run(["pdftoppm", "-r", str(res), "-gray", "-x", str(x0), "-y", str(y0), "-W", str(w), "-H", str(h),
                    "-singlefile", pdf, base], check=True, capture_output=True)
    return np.array(Image.open(base + ".pgm")) < 140


def main():
    board = pcbnew.LoadBoard(PCB)
    comps, _ = gen_pcb.read_netlist()
    with tempfile.TemporaryDirectory() as tmp:
        edge = layer("Edge.Cuts", tmp)
        mask = layer("F.Mask", tmp)
        fab = layer("F.Fab", tmp)
    h, w = edge.shape
    img = np.full((h, w, 3), 255, np.uint8)
    img[mask] = (235, 200, 120)            # pads
    img[fab] = (90, 90, 90)                # component outlines
    img[edge] = (0, 0, 0)
    draw_im = Image.fromarray(img)
    d = ImageDraw.Draw(draw_im)
    fsz = int(1.15 * PX)
    f = ImageFont.truetype(FONTB, fsz)
    fs = ImageFont.truetype(FONTB, int(0.8 * PX))
    for fp in sorted(board.GetFootprints(), key=lambda m: m.GetReference()):
        ref = fp.GetReference()
        x = TOMM(fp.GetPosition().x) - gen_pcb.X0
        y = TOMM(fp.GetPosition().y) - gen_pcb.Y0
        cx, cy = (x - MX0) * PX, (y - MY0) * PX
        font = f if ref in ("U2", "J1", "J3", "J4", "SW1", "U1", "L1") else fs
        color = (200, 0, 0) if ref == "U2" else (0, 40, 160)
        if fp.HasProperty("DNP"):
            color = (150, 150, 150)
        bb = d.textbbox((0, 0), ref, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        d.rectangle((cx - tw / 2 - 3, cy - th / 2 - 3, cx + tw / 2 + 3, cy + th / 2 + 5), fill=(255, 255, 255))
        d.text((cx, cy), ref, fill=color, font=font, anchor="mm")
    # pin-1 / polarity hints
    hint = ImageFont.truetype(FONT, int(0.75 * PX))
    for txt, x, y in (("+", 6.8, 43.6), ("-", 2.2, 43.6), ("1=GND", 20.5, 33.3), ("pad 1", 16.2, 44.5)):
        d.text(((x - MX0) * PX, (y - MY0) * PX), txt, fill=(200, 0, 0), font=hint, anchor="mm")

    # ---------------------------------------------------------------- page 1
    page1 = Image.new("RGB", PAGE, "white")
    pd = ImageDraw.Draw(page1)
    title = ImageFont.truetype(FONTB, int(0.22 * DPI))
    small = ImageFont.truetype(FONT, int(0.11 * DPI))
    pd.text((PAGE[0] / 2, int(0.35 * DPI)), "H2 Soil Sensor v3 - So do vi tri linh kien (mat tren)",
            fill="black", font=title, anchor="mm")
    pd.text((PAGE[0] / 2, int(0.62 * DPI)),
            f"Ty le {SCALE:g}:1  |  Bo 26 x 45 mm  |  Tat ca linh kien o mat tren  |  Design by Haxeko - Made in Vietnam",
            fill=(60, 60, 60), font=small, anchor="mm")
    ox = (PAGE[0] - w) // 2
    oy = int(0.85 * DPI)
    page1.paste(draw_im, (ox, oy))
    pd.text((PAGE[0] / 2, oy + h + int(0.18 * DPI)),
            "Do = module ESP32-H2 (han tay)   Xanh = linh kien SMT (JLC lap)   "
            "Anten module nho ra ngoai mep tren", fill=(60, 60, 60), font=small, anchor="mm")

    # ---------------------------------------------------------------- page 2: parts table
    page2 = Image.new("RGB", PAGE, "white")
    td = ImageDraw.Draw(page2)
    td.text((PAGE[0] / 2, int(0.35 * DPI)), "Danh sach linh kien", fill="black", font=title, anchor="mm")
    hdr = ImageFont.truetype(FONTB, int(0.105 * DPI))
    row = ImageFont.truetype(FONT, int(0.1 * DPI))
    cols = [(0.45, "Ref"), (1.05, "Gia tri"), (2.65, "Footprint"), (5.0, "LCSC"), (5.85, "Lap rap")]
    y = int(0.7 * DPI)
    for cx, name in cols:
        td.text((int(cx * DPI), y), name, fill="black", font=hdr)
    y += int(0.2 * DPI)
    td.line((int(0.4 * DPI), y - 5, PAGE[0] - int(0.4 * DPI), y - 5), fill="black", width=2)

    def nat(r):
        import re
        m = re.match(r"([A-Z]+)(\d+)", r)
        return (m.group(1), int(m.group(2))) if m else (r, 0)

    for ref in sorted(comps, key=nat):
        c = comps[ref]
        fpname = c["footprint"].split(":")[1]
        lcsc = c["fields"].get("LCSC", "")
        if ref == "U2":
            how = "han tay (mua rieng)"
        elif ref in ("J1", "J3"):
            how = "chi la pad"
        elif ref == "J4":
            how = "han tay (THT)"
        else:
            how = "JLC SMT"
        vals = [ref, c["value"][:22], fpname[:30], lcsc, how]
        for (cx, _), v in zip(cols, vals):
            td.text((int(cx * DPI), y), v, fill="black", font=row)
        y += int(0.17 * DPI)
    page1.save(OUT, "PDF", resolution=DPI, save_all=True, append_images=[page2])
    print("assembly drawing:", OUT)


if __name__ == "__main__":
    main()
