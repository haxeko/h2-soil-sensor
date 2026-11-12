#!/usr/bin/env python3
"""Illustrative top / bottom renders of the assembled carrier board.

KiCad 7 has no command-line 3D renderer, so the copper, solder-mask and silkscreen layers are
plotted with kicad-cli (black & white PDF), rasterised with pdftoppm at a common scale and
composited (green mask, ENIG pads, white silk, drill holes). Component bodies are drawn from
each footprint's F.Fab outline with simple per-type styles and a soft drop shadow.

Usage: python3 render.py   (after gen_pcb.py)  ->  hardware/docs/render_top.png, render_bottom.png,
                                                   render.png (both sides)
"""
from __future__ import annotations

import os
import subprocess
import tempfile

import numpy as np
import pcbnew
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import gen_pcb

PCB = gen_pcb.PCB_PATH
DOCS = os.path.join(gen_pcb.HW, "docs")
PX = 40                                   # pixels per mm
MX0, MY0 = -3.0, -8.5                     # crop window in board-local mm (antenna overhang on top)
MX1, MY1 = gen_pcb.W + 3.0, gen_pcb.H + 3.0
WPX, HPX = int((MX1 - MX0) * PX), int((MY1 - MY0) * PX)
TOMM = pcbnew.ToMM

BG = (238, 240, 242)
MASK_BARE = (22, 92, 52)                  # green mask over bare FR4
MASK_CU = (40, 128, 70)                   # green mask over copper
FR4 = (196, 182, 132)
ENIG = (222, 186, 92)
SILK = (246, 246, 240)
HOLE = (52, 54, 58)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def px(x, y):
    return (x - MX0) * PX, (y - MY0) * PX


def layer_mask(layer, tmp):
    name = layer.replace(".", "_")
    pdf = os.path.join(tmp, name + ".pdf")
    subprocess.run(["kicad-cli", "pcb", "export", "pdf", "--black-and-white", "--drill-shape-opt", "0",
                    "--layers", layer, "-o", pdf, PCB], check=True, capture_output=True)
    x0 = int(round((gen_pcb.X0 + MX0) * PX))
    y0 = int(round((gen_pcb.Y0 + MY0) * PX))
    subprocess.run(["pdftoppm", "-r", str(PX * 25.4), "-gray", "-x", str(x0), "-y", str(y0),
                    "-W", str(WPX), "-H", str(HPX), "-singlefile", pdf, os.path.join(tmp, name)],
                   check=True, capture_output=True)
    return np.array(Image.open(os.path.join(tmp, name + ".pgm"))) < 128


def board_mask():
    im = Image.new("L", (WPX, HPX), 0)
    ImageDraw.Draw(im).polygon([px(x, y) for x, y in gen_pcb.OUTLINE], fill=255)
    return np.array(im) > 0


def local(v):
    return TOMM(v.x) - gen_pcb.X0, TOMM(v.y) - gen_pcb.Y0


def holes(board):
    out = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.HasHole():
                x, y = local(pad.GetPosition())
                d = TOMM(min(pad.GetDrillSize().x, pad.GetDrillSize().y))
                out.append((x, y, d, pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH))
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            x, y = local(t.GetPosition())
            out.append((x, y, TOMM(t.GetDrillValue()), False))
    return out


def pcb_layers(side, tmp):
    F = side == "top"
    cu = layer_mask("F.Cu" if F else "B.Cu", tmp)
    mo = layer_mask("F.Mask" if F else "B.Mask", tmp)
    sk = layer_mask("F.SilkS" if F else "B.SilkS", tmp)
    bd = board_mask()
    img = np.zeros((HPX, WPX, 3), np.uint8)
    img[:] = BG
    img[bd] = MASK_BARE
    img[bd & cu] = MASK_CU
    img[bd & mo] = FR4
    img[bd & mo & cu] = ENIG
    img[bd & sk & ~mo] = SILK
    return Image.fromarray(img)


def draw_holes(im, hl):
    d = ImageDraw.Draw(im)
    for x, y, dia, npth in hl:
        cx, cy = px(x, y)
        r = dia / 2 * PX
        if npth:
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=BG, outline=(150, 150, 150), width=2)
        else:
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=HOLE, outline=(170, 170, 160), width=1)


# --------------------------------------------------------------------------- component bodies
def fab_box(fp):
    xs, ys = [], []
    for it in fp.GraphicalItems():
        if it.GetLayer() == pcbnew.F_Fab and isinstance(it, pcbnew.FP_SHAPE):
            bb = it.GetBoundingBox()
            x1, y1 = local(pcbnew.VECTOR2I(bb.GetX(), bb.GetY()))
            xs += [x1, x1 + TOMM(bb.GetWidth())]
            ys += [y1, y1 + TOMM(bb.GetHeight())]
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def rect(d, box, fill, inset=0.0, radius=0.12, outline=None):
    x1, y1, x2, y2 = box
    a, b = px(x1 + inset, y1 + inset)
    c, e = px(x2 - inset, y2 - inset)
    d.rounded_rectangle((a, b, c, e), radius=radius * PX, fill=fill, outline=outline,
                        width=max(1, int(0.05 * PX)) if outline else 0)


def two_terminal(d, box, body, cap=(205, 205, 200), cap_len=0.32):
    x1, y1, x2, y2 = box
    rect(d, box, body, radius=0.08)
    if (x2 - x1) >= (y2 - y1):
        rect(d, (x1, y1, x1 + cap_len, y2), cap, radius=0.05)
        rect(d, (x2 - cap_len, y1, x2, y2), cap, radius=0.05)
    else:
        rect(d, (x1, y1, x2, y1 + cap_len), cap, radius=0.05)
        rect(d, (x1, y2 - cap_len, x2, y2), cap, radius=0.05)


def pads_of(fp):
    out = []
    for p in fp.Pads():
        x, y = local(p.GetPosition())
        bb = p.GetBoundingBox()
        out.append((p.GetNumber(), x, y, TOMM(bb.GetWidth()), TOMM(bb.GetHeight())))
    return out


def gold_pin(d, x, y, s=0.64):
    rect(d, (x - s / 2, y - s / 2, x + s / 2, y + s / 2), (230, 196, 100), radius=0.05,
         outline=(160, 130, 60))


def draw_module(d, fp, box, font_px):
    x1, y1, x2, y2 = box
    rect(d, box, (24, 36, 60), radius=0.25)                 # module PCB
    # antenna meander (module y -10..-4 -> board y1 .. y1 + 6)
    ay1, ay2 = y1 + 0.6, y1 + 4.2
    xs = np.arange(x1 + 2.0, x2 - 2.0, 1.3)
    pts = [px(x1 + 2.0, y1 + 5.6)]
    up = True
    for x in xs:
        pts.append(px(x, ay1 if up else ay2))
        pts.append(px(x + 0.65, ay1 if up else ay2))
        up = not up
    d.line(pts, fill=(200, 160, 70), width=int(0.4 * PX), joint="curve")
    # RF shield can
    sx1, sy1, sx2, sy2 = x1 + 0.55, y1 + 6.5, x2 - 0.55, y2 - 0.55
    rect(d, (sx1, sy1, sx2, sy2), (206, 210, 214), radius=0.3, outline=(150, 154, 158))
    rect(d, (sx1 + 0.5, sy1 + 0.5, sx2 - 0.5, sy2 - 0.5), (214, 218, 222), radius=0.25)
    f1 = ImageFont.truetype(FONT, int(font_px * 1.05))
    f2 = ImageFont.truetype(FONT, int(font_px * 0.8))
    cx, cy = px((sx1 + sx2) / 2, (sy1 + sy2) / 2)
    d.text((cx, cy - font_px * 0.9), "ESP32-H2-WROOM-02C", fill=(70, 74, 80), font=f1, anchor="mm")
    d.text((cx, cy + font_px * 0.6), "802.15.4 / Thread / BLE 5", fill=(90, 94, 100), font=f2, anchor="mm")
    d.text((cx, cy + font_px * 1.9), "4 MB flash", fill=(90, 94, 100), font=f2, anchor="mm")


def draw_component(d, fp, box, font_px):
    ref = fp.GetReference()
    name = fp.GetFPID().GetLibItemName().wx_str()
    if ref == "U2":
        draw_module(d, fp, box, font_px)
    elif ref.startswith("R"):
        two_terminal(d, box, (28, 28, 30))
    elif ref.startswith("C"):
        two_terminal(d, box, (176, 140, 92))
    elif ref.startswith("L"):
        two_terminal(d, box, (70, 72, 76), cap_len=0.45)
    elif ref.startswith("D") and "LED" not in name:      # small-signal / TVS diode: body + cathode band
        rect(d, box, (32, 32, 34), radius=0.08)
        x1, y1, x2, y2 = box
        k = [(x, y) for num, x, y, _, _ in pads_of(fp) if num == "1"]
        if k:
            kx, ky = k[0]
            if (x2 - x1) >= (y2 - y1):
                bx = x1 + 0.15 if kx < (x1 + x2) / 2 else x2 - 0.45
                rect(d, (bx, y1 + 0.05, bx + 0.3, y2 - 0.05), (170, 170, 170), radius=0.03)
            else:
                by = y1 + 0.15 if ky < (y1 + y2) / 2 else y2 - 0.45
                rect(d, (x1 + 0.05, by, x2 - 0.05, by + 0.3), (170, 170, 170), radius=0.03)
    elif ref.startswith("D"):
        two_terminal(d, box, (236, 236, 230), cap_len=0.3)
        x1, y1, x2, y2 = box
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        rect(d, (cx - 0.3, cy - 0.25, cx + 0.3, cy + 0.25), (220, 40, 40), radius=0.1)
    elif ref.startswith(("Q", "U")):
        # gull-wing / bottom-terminated leads, then the moulded body
        for _, x, y, w, h in pads_of(fp):
            if w * h < 2.0:
                rect(d, (x - w * 0.32, y - h * 0.32, x + w * 0.32, y + h * 0.32), (196, 198, 200), radius=0.04)
        rect(d, box, (30, 30, 32), radius=0.1)
        x1, y1, x2, y2 = box
        r = 0.18
        a, b = px(x1 + 0.35, y1 + 0.35)
        d.ellipse((a - r * PX, b - r * PX, a + r * PX, b + r * PX), fill=(80, 80, 84))
    elif ref.startswith("SW"):
        rect(d, box, (178, 182, 186), radius=0.3, outline=(120, 124, 128))
        x1, y1, x2, y2 = box
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        r = min(x2 - x1, y2 - y1) * 0.28
        a, b = px(cx, cy)
        d.ellipse((a - r * PX, b - r * PX, a + r * PX, b + r * PX), fill=(32, 32, 34), outline=(10, 10, 10))
    elif "PinHeader" in name:
        rect(d, box, (26, 26, 28), radius=0.15)
        pads = pads_of(fp)
        for _, x, y, _, _ in pads:
            rect(d, (x - 1.15, y - 1.15, x + 1.15, y + 1.15), (36, 36, 38), radius=0.25)
            gold_pin(d, x, y)
    elif "JST_PH" in name:
        rect(d, box, (240, 234, 216), radius=0.2, outline=(200, 192, 170))
        x1, y1, x2, y2 = box
        rect(d, (x1 + 0.45, y1 + 0.45, x2 - 0.45, y2 - 1.3), (222, 213, 190), radius=0.15)
        for _, x, y, _, _ in pads_of(fp):
            gold_pin(d, x, y)


def components_layer(board):
    body = Image.new("RGBA", (WPX, HPX), (0, 0, 0, 0))
    shadow = Image.new("L", (WPX, HPX), 0)
    d = ImageDraw.Draw(body)
    ds = ImageDraw.Draw(shadow)
    font_px = int(1.0 * PX)
    for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
        ref = fp.GetReference()
        if ref.startswith(("H", "TP")) or ref in ("J1", "J3") or fp.HasProperty("DNP"):
            continue
        box = fab_box(fp)
        if not box:
            continue
        a, b = px(box[0] + 0.25, box[1] + 0.35)
        c, e = px(box[2] + 0.25, box[3] + 0.35)
        ds.rounded_rectangle((a, b, c, e), radius=0.2 * PX, fill=150 if ref != "U2" else 120)
        draw_component(d, fp, box, font_px)
    shadow = shadow.filter(ImageFilter.GaussianBlur(0.25 * PX))
    return body, shadow


def solder_joints(im, board):
    d = ImageDraw.Draw(im)
    for fp in board.GetFootprints():
        if fp.HasProperty("DNP") or not (fp.GetAttributes() & pcbnew.FP_THROUGH_HOLE) or fp.GetReference() == "J3":
            continue
        for _, x, y, w, h in pads_of(fp):
            r = min(w, h) / 2 * 0.92
            cx, cy = px(x, y)
            for k in range(6, 0, -1):          # simple radial shading for a solder fillet
                rr = r * k / 6
                c = int(150 + 14 * (6 - k))
                d.ellipse((cx - rr * PX, cy - rr * PX, cx + rr * PX, cy + rr * PX), fill=(c, c, c + 4))
            s = 0.32 * PX
            d.rectangle((cx - s, cy - s, cx + s, cy + s), fill=(120, 122, 126))


def main():
    board = pcbnew.LoadBoard(PCB)
    hl = holes(board)
    with tempfile.TemporaryDirectory() as tmp:
        top = pcb_layers("top", tmp)
        bot = pcb_layers("bottom", tmp)
    draw_holes(top, hl)
    draw_holes(bot, hl)
    body, shadow = components_layer(board)
    top = Image.composite(Image.new("RGB", top.size, (0, 0, 0)), top,
                          shadow.point(lambda v: int(v * 0.45)))
    top.paste(body, (0, 0), body)
    solder_joints(bot, board)
    bot = bot.transpose(Image.FLIP_LEFT_RIGHT)      # seen from below
    os.makedirs(DOCS, exist_ok=True)
    top.save(os.path.join(DOCS, "render_top.png"))
    bot.save(os.path.join(DOCS, "render_bottom.png"))
    gap = int(4 * PX)
    both = Image.new("RGB", (top.width * 2 + gap, top.height), BG)
    both.paste(top, (0, 0))
    both.paste(bot, (top.width + gap, 0))
    both = both.resize((both.width // 2, both.height // 2), Image.LANCZOS)
    both.save(os.path.join(DOCS, "render.png"))
    print("renders:", os.path.join(DOCS, "render_top.png"), os.path.join(DOCS, "render_bottom.png"),
          os.path.join(DOCS, "render.png"))


if __name__ == "__main__":
    main()
