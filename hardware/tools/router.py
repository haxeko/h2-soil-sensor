"""Small 2-layer grid router for KiCad boards (pcbnew Python API + numpy).

Model
  * 0.1 mm grid in board-local coordinates; two layers (F.Cu = 0, B.Cu = 1)
  * for every (layer, track width, clearance) an `owner` map: -1 free, k = only net k is
    within keep-out distance, -2 blocked (other nets / board edge / holes / keep-outs).
    A cell is usable by net k if owner in (-1, k). Obstacles are stamped with their real
    geometry inflated by (w/2 + clearance + margin), so the result is DRC-clean by design.
  * nets are routed one by one with A* (8-connected, vias, bottom layer and turn penalties),
    growing a Steiner-like tree from pad to pad.
  * GND is not routed: SMD GND pads get a fan-out via, then both layers are poured and
    stitched (finish_ground).
"""
from __future__ import annotations

import heapq
import math

import numpy as np
import pcbnew

RES = 0.1
MARGIN = 0.05
VIA_D, VIA_DRILL = 0.6, 0.3
EDGE_CLR = 0.5
HOLE_CLR = 0.3
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)
COST_BOTTOM = 1.8
COST_VIA = 14.0
COST_TURN = 0.4
MM = pcbnew.FromMM
TOMM = pcbnew.ToMM


class Ctx:
    pass


def _local(ctx, pt):
    return TOMM(pt.x) - ctx.ox, TOMM(pt.y) - ctx.oy


def _P(ctx, x, y):
    return pcbnew.VECTOR2I(MM(ctx.ox + x), MM(ctx.oy + y))


# ----------------------------------------------------------------------------- geometry
def _window(ctx, x1, y1, x2, y2):
    i1 = max(int(math.floor(x1 / RES)), 0)
    i2 = min(int(math.ceil(x2 / RES)), ctx.nx - 1)
    j1 = max(int(math.floor((y1 - ctx.gy0) / RES)), 0)
    j2 = min(int(math.ceil((y2 - ctx.gy0) / RES)), ctx.ny - 1)
    if i1 > i2 or j1 > j2:
        return None
    xs = np.arange(i1, i2 + 1) * RES
    ys = ctx.gy0 + np.arange(j1, j2 + 1) * RES
    X, Y = np.meshgrid(xs, ys)
    return (j1, j2 + 1, i1, i2 + 1), X, Y


def _dist_rect(X, Y, cx, cy, hw, hh):
    dx = np.maximum(np.abs(X - cx) - hw, 0)
    dy = np.maximum(np.abs(Y - cy) - hh, 0)
    return np.hypot(dx, dy)


def _dist_circle(X, Y, cx, cy, r):
    return np.maximum(np.hypot(X - cx, Y - cy) - r, 0)


def _dist_seg(X, Y, x1, y1, x2, y2, hw):
    vx, vy = x2 - x1, y2 - y1
    L2 = vx * vx + vy * vy
    if L2 == 0:
        t = np.zeros_like(X)
    else:
        t = np.clip(((X - x1) * vx + (Y - y1) * vy) / L2, 0, 1)
    px, py = x1 + t * vx, y1 + t * vy
    return np.maximum(np.hypot(X - px, Y - py) - hw, 0)


class Shape:
    """Obstacle: kind rect/circle/seg with size params, layers (0/1), net id (-2 = no net), clearance.
    hole=True: drilled hole - blocks via placement for every net (hole-to-hole rule)."""

    def __init__(self, kind, params, layers, net, clr, hole=False, shrink=0.0, keepout=False):
        self.kind, self.params, self.layers, self.net, self.clr = kind, params, layers, net, clr
        self.hole, self.shrink, self.keepout = hole, shrink, keepout

    def bbox(self):
        k, p = self.kind, self.params
        if k == "rect":
            cx, cy, hw, hh = p
            return cx - hw, cy - hh, cx + hw, cy + hh
        if k == "circle":
            cx, cy, r = p
            return cx - r, cy - r, cx + r, cy + r
        x1, y1, x2, y2, hw = p
        return min(x1, x2) - hw, min(y1, y2) - hw, max(x1, x2) + hw, max(y1, y2) + hw

    def dist(self, X, Y):
        if self.kind == "rect":
            return _dist_rect(X, Y, *self.params)
        if self.kind == "circle":
            return _dist_circle(X, Y, *self.params)
        return _dist_seg(X, Y, *self.params)


# ----------------------------------------------------------------------------- maps
def _map_keys(ctx):
    keys = []
    for L in (0, 1):
        for w in ctx.widths:
            for c in ctx.clrs:
                keys.append((L, w, c))
        for c in ctx.clrs:
            keys.append((L, "via", c))
    return keys


def stamp(ctx, sh: Shape):
    ctx.cache = {}
    x1, y1, x2, y2 = sh.bbox()
    for key in ctx.maps:
        L, w, c = key
        if L not in sh.layers:
            continue
        half = VIA_D / 2 if w == "via" else w / 2
        clr = max(c, sh.clr)
        infl = (half + 0.02) if sh.keepout else (half + clr + MARGIN)
        win = _window(ctx, x1 - infl, y1 - infl, x2 + infl, y2 + infl)
        if win is None:
            continue
        (a, b, c0, d), X, Y = win
        mask = sh.dist(X, Y) <= infl
        sub = ctx.maps[key][a:b, c0:d]
        if sh.net < 0 or (sh.hole and w == "via"):
            sub[mask] = -2
        else:
            m_free = mask & (sub == -1)
            m_other = mask & (sub != -1) & (sub != sh.net)
            sub[m_free] = sh.net
            sub[m_other] = -2


def stamp_edges(ctx, outline, slot):
    """Block cells outside the board or closer than EDGE_CLR (+w/2) to the outline/slot."""
    xs = np.arange(ctx.nx) * RES
    ys = ctx.gy0 + np.arange(ctx.ny) * RES
    X, Y = np.meshgrid(xs, ys)
    # point in polygon (even-odd)
    inside = np.zeros(X.shape, dtype=bool)
    pts = outline + [outline[0]]
    dmin = np.full(X.shape, 1e9)
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        cond = ((ya > Y) != (yb > Y))
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = (xb - xa) * (Y - ya) / (yb - ya + 1e-12) + xa
        inside ^= cond & (X < xint)
        dmin = np.minimum(dmin, _dist_seg(X, Y, xa, ya, xb, yb, 0.0))
    if slot:
        sx1, sy1, sx2, sy2 = slot
        dslot = _dist_rect(X, Y, (sx1 + sx2) / 2, (sy1 + sy2) / 2, (sx2 - sx1) / 2, (sy2 - sy1) / 2)
    else:
        dslot = np.full(X.shape, 1e9)
    in_slot = dslot <= 0
    for key, arr in ctx.maps.items():
        L, w, c = key
        half = VIA_D / 2 if w == "via" else w / 2
        lim = EDGE_CLR + half + MARGIN
        bad = (~inside) | (dmin < lim) | in_slot | (dslot < lim)
        arr[bad] = -2


# ----------------------------------------------------------------------------- board scan
def _pad_shapes(ctx, pad, net_id, clr):
    """Return (shape, layers) for a pad; axis-aligned rectangles/circles (rotations are k*90deg)."""
    layers = tuple(i for i, lay in enumerate(LAYERS) if pad.IsOnLayer(lay))
    if not layers:
        return []
    cx, cy = _local(ctx, pad.GetPosition())
    bb = pad.GetBoundingBox()
    w, h = TOMM(bb.GetWidth()), TOMM(bb.GetHeight())
    shp = pad.GetShape()
    out = []
    if shp == pcbnew.PAD_SHAPE_CIRCLE or (shp == pcbnew.PAD_SHAPE_OVAL and abs(w - h) < 1e-3):
        out.append(Shape("circle", (cx, cy, w / 2), layers, net_id, clr, shrink=0.05))
    else:
        shrink = 0.0 if shp == pcbnew.PAD_SHAPE_RECT else min(w, h) * 0.15
        out.append(Shape("rect", (cx, cy, w / 2, h / 2), layers, net_id, clr, shrink=shrink))
    if pad.HasHole():
        d = TOMM(pad.GetDrillSize().x)
        out.append(Shape("circle", (cx, cy, d / 2), (0, 1), net_id, HOLE_CLR, hole=True))
    return out


def _cells_in(ctx, sh: Shape, shrink=0.0):
    x1, y1, x2, y2 = sh.bbox()
    win = _window(ctx, x1, y1, x2, y2)
    if win is None:
        return []
    (a, b, c0, d), X, Y = win
    if sh.kind == "rect":
        cx, cy, hw, hh = sh.params
        m = (np.abs(X - cx) <= hw - shrink) & (np.abs(Y - cy) <= hh - shrink)
    elif sh.kind == "circle":
        cx, cy, r = sh.params
        m = np.hypot(X - cx, Y - cy) <= r - shrink
    else:
        m = sh.dist(X, Y) <= 0.0
    jj, ii = np.nonzero(m)
    return [(L, a + j, c0 + i) for L in sh.layers for j, i in zip(jj.tolist(), ii.tolist())]


def _fps(board):
    """Footprints in a stable order (file order follows random UUIDs)."""
    return sorted(board.GetFootprints(), key=lambda f: f.GetReference())


def _pads(fp):
    return sorted(fp.Pads(), key=lambda p: (p.GetNumber(), p.GetPosition().x, p.GetPosition().y))


def scan_board(ctx, board):
    ctx.net_id = {}
    ctx.net_pads = {}
    ctx.pad_shapes = {}
    for fp in _fps(board):
        for pad in _pads(fp):
            net = pad.GetNetname()
            nid = ctx.netcode(net) if net else -2
            clr = ctx.clr_of(net)
            shapes = _pad_shapes(ctx, pad, nid, clr)
            for sh in shapes:
                stamp(ctx, sh)
            if net and shapes:
                ctx.net_pads.setdefault(net, []).append((fp.GetReference(), pad.GetNumber(), shapes[0], pad))
    # footprint rule areas (e.g. Sensirion keep-out under the SHT4x)
    for fp in _fps(board):
        for z in fp.Zones():
            if z.GetIsRuleArea() and z.GetDoNotAllowTracks():
                r = z.GetBoundingBox()
                x1, y1 = TOMM(r.GetX()) - ctx.ox, TOMM(r.GetY()) - ctx.oy
                x2, y2 = x1 + TOMM(r.GetWidth()), y1 + TOMM(r.GetHeight())
                lays = tuple(i for i, lay in enumerate(LAYERS) if z.GetLayerSet().Contains(lay))
                stamp(ctx, Shape("rect", ((x1 + x2) / 2, (y1 + y2) / 2, (x2 - x1) / 2, (y2 - y1) / 2), lays, -2, 0.0,
                                 keepout=True))
    # module body keep-out on the top layer (Espressif: keep GND under the module)
    for fp in _fps(board):
        if fp.GetReference() == "U2":
            x, y = _local(ctx, fp.GetPosition())
            stamp(ctx, Shape("rect", (x, y - 1.3, 7.4, 8.4), (0,), -2, 0.0))
        # no tracks / vias under mounting screw heads (GND pour is still allowed there)
        if fp.GetReference().startswith("H"):
            x, y = _local(ctx, fp.GetPosition())
            stamp(ctx, Shape("circle", (x, y, 3.2), (0, 1), -2, 0.0, keepout=True))
    # pre-routed tracks / vias
    ctx.prerouted = {}
    for t in sorted(board.GetTracks(), key=lambda t: (t.GetNetname(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y)):
        net = t.GetNetname()
        nid = ctx.netcode(net)
        if isinstance(t, pcbnew.PCB_VIA):
            x, y = _local(ctx, t.GetPosition())
            sh = Shape("circle", (x, y, TOMM(t.GetWidth()) / 2), (0, 1), nid, ctx.clr_of(net))
            stamp(ctx, Shape("circle", (x, y, TOMM(t.GetDrillValue()) / 2), (0, 1), nid, HOLE_CLR, hole=True))
        else:
            (x1, y1), (x2, y2) = _local(ctx, t.GetStart()), _local(ctx, t.GetEnd())
            L = 0 if t.GetLayer() == pcbnew.F_Cu else 1
            sh = Shape("seg", (x1, y1, x2, y2, TOMM(t.GetWidth()) / 2), (L,), nid, ctx.clr_of(net))
        stamp(ctx, sh)
        ctx.prerouted.setdefault(net, []).append(sh)


# ----------------------------------------------------------------------------- A*
DIRS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
        (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]


def astar(ctx, nid, w, clr, sources, targets, window):
    nx, ny = ctx.nx, ctx.ny
    N = nx * ny
    ck = (nid, w, clr)
    if ck not in ctx.cache:
        pF = ((ctx.maps[(0, w, clr)] == -1) | (ctx.maps[(0, w, clr)] == nid)).ravel().tobytes()
        pB = ((ctx.maps[(1, w, clr)] == -1) | (ctx.maps[(1, w, clr)] == nid)).ravel().tobytes()
        vF = ctx.maps[(0, "via", clr)]
        vB = ctx.maps[(1, "via", clr)]
        pV = (((vF == -1) | (vF == nid)) & ((vB == -1) | (vB == nid))).ravel().tobytes()
        ctx.cache[ck] = (pF, pB, pV)
    passF, passB, passV = ctx.cache[ck]
    passL = (passF, passB)
    i1, j1, i2, j2 = window
    tset = set(L * N + j * nx + i for (L, j, i) in targets)
    if not tset:
        return None
    tx = sum(i for _, _, i in targets) / len(targets)
    ty = sum(j for _, j, _ in targets) / len(targets)

    def h(j, i):
        dx, dy = abs(i - tx), abs(j - ty)
        return (max(dx, dy) + 0.4142 * min(dx, dy))

    g = {}
    came = {}
    dirof = {}
    heap = []
    for (L, j, i) in sources:
        s = L * N + j * nx + i
        if not (i1 <= i <= i2 and j1 <= j <= j2):
            continue
        g[s] = 0.0
        came[s] = -1
        dirof[s] = -1
        heapq.heappush(heap, (h(j, i), 0.0, s))
    expanded = 0
    while heap:
        f, gc, s = heapq.heappop(heap)
        if gc > g.get(s, 1e18):
            continue
        if s in tset:
            path = []
            while s != -1:
                path.append(s)
                s = came[s]
            return path[::-1]
        expanded += 1
        if expanded > 600000:
            return None
        L, rem = divmod(s, N)
        j, i = divmod(rem, nx)
        lf = 1.0 if L == 0 else COST_BOTTOM
        pd = dirof[s]
        pl = passL[L]
        for k, (di, dj, c) in enumerate(DIRS):
            ii, jj = i + di, j + dj
            if ii < i1 or ii > i2 or jj < j1 or jj > j2:
                continue
            idx = jj * nx + ii
            if not pl[idx]:
                continue
            if di and dj:  # no corner cutting
                if not pl[j * nx + ii] or not pl[jj * nx + i]:
                    continue
            ns = L * N + idx
            ng = gc + c * lf + (COST_TURN if (pd != -1 and pd != k) else 0.0)
            if ng < g.get(ns, 1e18):
                g[ns] = ng
                came[ns] = s
                dirof[ns] = k
                heapq.heappush(heap, (ng + h(jj, ii), ng, ns))
        # via
        idx = j * nx + i
        if passV[idx]:
            OL = 1 - L
            if passL[OL][idx]:
                ns = OL * N + idx
                ng = gc + COST_VIA
                if ng < g.get(ns, 1e18):
                    g[ns] = ng
                    came[ns] = s
                    dirof[ns] = -1
                    heapq.heappush(heap, (ng + h(j, i), ng, ns))
    return None


# ----------------------------------------------------------------------------- commit
def _path_to_items(ctx, path):
    nx, N = ctx.nx, ctx.nx * ctx.ny
    pts = []
    for s in path:
        L, rem = divmod(s, N)
        j, i = divmod(rem, nx)
        pts.append((L, i * RES, ctx.gy0 + j * RES))
    segs, vias = [], []
    run = [pts[0]]
    for p in pts[1:]:
        if p[0] != run[-1][0]:
            vias.append((p[1], p[2]))
            if len(run) > 1:
                segs.append(run)
            run = [p]
        else:
            run.append(p)
    if len(run) > 1:
        segs.append(run)
    # simplify collinear points
    out = []
    for run in segs:
        simp = [run[0]]
        for k in range(1, len(run) - 1):
            a, b, c = simp[-1], run[k], run[k + 1]
            d1 = (round((b[1] - a[1]) / RES), round((b[2] - a[2]) / RES))
            d2 = (round((c[1] - b[1]) / RES), round((c[2] - b[2]) / RES))
            n1 = (int(np.sign(d1[0])), int(np.sign(d1[1])))
            n2 = (int(np.sign(d2[0])), int(np.sign(d2[1])))
            if n1 != n2:
                simp.append(b)
        simp.append(run[-1])
        out.append(simp)
    return out, vias


def commit(ctx, board, net, nid, w, path):
    segs, vias = _path_to_items(ctx, path)
    ni = board.FindNet(net)
    clr = ctx.clr_of(net)
    for run in segs:
        L = run[0][0]
        for a, b in zip(run, run[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(_P(ctx, a[1], a[2]))
            t.SetEnd(_P(ctx, b[1], b[2]))
            t.SetWidth(MM(w))
            t.SetLayer(LAYERS[L])
            t.SetNet(ni)
            board.Add(t)
            stamp(ctx, Shape("seg", (a[1], a[2], b[1], b[2], w / 2), (L,), nid, clr))
    for (x, y) in vias:
        add_via(ctx, board, ni, nid, x, y, clr)
    return len(segs), len(vias)


def add_via(ctx, board, ni, nid, x, y, clr):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(_P(ctx, x, y))
    v.SetDrill(MM(VIA_DRILL))
    v.SetWidth(MM(VIA_D))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(ni)
    board.Add(v)
    stamp(ctx, Shape("circle", (x, y, VIA_D / 2), (0, 1), nid, clr))
    stamp(ctx, Shape("circle", (x, y, VIA_DRILL / 2), (0, 1), nid, HOLE_CLR, hole=True))


# ----------------------------------------------------------------------------- driver
def _make_ctx(board, origin, width, route_ymax, netclasses, net_to_class):
    ctx = Ctx()
    ctx.ox, ctx.oy = origin
    ctx.gy0 = 0.0
    ctx.nx = int(round(width / RES)) + 1
    ctx.ny = int(round(route_ymax / RES)) + 1
    ctx.widths = sorted({c["track"] for c in netclasses.values()} | {0.3})
    ctx.cache = {}
    ctx.clrs = sorted({c["clearance"] for c in netclasses.values()})
    ctx.maps = {k: np.full((ctx.ny, ctx.nx), -1, dtype=np.int32) for k in _map_keys(ctx)}
    names = sorted({str(n) for n in board.GetNetsByName().keys() if str(n)})
    ctx._codes = {n: i for i, n in enumerate(names)}
    ctx.netcode = lambda n: ctx._codes.get(n, -2)
    ctx.clr_of = lambda n: netclasses[net_to_class.get(n, "Default")]["clearance"]
    ctx.w_of = lambda n: netclasses[net_to_class.get(n, "Default")]["track"]
    return ctx


def _clean(board):
    for t in list(board.GetTracks()):
        if not t.IsLocked():
            board.Remove(t)


def route_board(board, origin, width, route_ymax, netclasses, net_to_class, outline=None, slot=None, tries=8):
    import gen_pcb  # outline/slot definitions
    global COST_BOTTOM
    outline = outline or gen_pcb.OUTLINE
    slot = slot if slot is not None else getattr(gen_pcb, "SLOT", None)
    order = None
    failed = []
    for attempt in range(tries):
        _clean(board)
        ctx = _make_ctx(board, origin, width, route_ymax, netclasses, net_to_class)
        stamp_edges(ctx, outline, slot)
        scan_board(ctx, board)
        board_ctx[0] = ctx
        fanout_ground(ctx, board, quiet=attempt > 0)
        nets = [n for n in ctx.net_pads if n != "GND" and len(ctx.net_pads[n]) >= 2]
        if order is None:
            def prio(n):
                pads = ctx.net_pads[n]
                xs = [p[2].params[0] for p in pads]
                ys = [p[2].params[1] for p in pads]
                span = (max(xs) - min(xs)) + (max(ys) - min(ys))
                power = 0 if net_to_class.get(n) == "Power" else 1
                return (0 if span < 6.0 else 1, power, round(span, 3), n)
            order = sorted(nets, key=prio)
        COST_BOTTOM = 1.8
        failed = []
        for net in order:
            if not route_net(ctx, board, net):
                failed.append(net)
        print(f"attempt {attempt}: failed {failed}")
        if not failed:
            break
        order = failed + [n for n in order if n not in failed]
    return dict(routed=len(order) - len(failed), failed=failed, attempts=attempt + 1)


board_ctx = [None]


def route_net(ctx, board, net, big=False):
    nid = ctx.netcode(net)
    w = ctx.w_of(net)
    clr = ctx.clr_of(net)
    pads = ctx.net_pads[net]
    tree = set()
    for sh in ctx.prerouted.get(net, []):
        tree.update(_cells_in(ctx, sh))
    remaining = list(pads)
    if not tree:
        first = remaining.pop(0)
        tree.update(_cells_in(ctx, first[2], shrink=first[2].shrink))
    ok = True
    while remaining:
        # pick the pad closest to the tree's bounding box centre
        tj = [j for (_, j, _) in tree]
        ti = [i for (_, _, i) in tree]
        cxy = (sum(ti) / len(ti) * RES, ctx.gy0 + sum(tj) / len(tj) * RES)
        remaining.sort(key=lambda p: (p[2].params[0] - cxy[0]) ** 2 + (p[2].params[1] - cxy[1]) ** 2)
        ref, num, sh, pad = remaining.pop(0)
        if sh.params[1] > (ctx.ny - 1) * RES + ctx.gy0:
            continue  # outside the routing area (probe section): connected by hand routes
        tgt = _cells_in(ctx, sh, shrink=sh.shrink)
        tgt = [c for c in tgt if c[0] in sh.layers]
        if any(c in tree for c in tgt):
            continue
        # target cells must be passable for this net
        path = None
        for margin in ((6.0, 20.0, 200.0) if not big else (200.0,)):
            xs = [i for (_, _, i) in tree] + [i for (_, _, i) in tgt]
            ys = [j for (_, j, _) in tree] + [j for (_, j, _) in tgt]
            m = int(margin / RES)
            win = (max(min(xs) - m, 0), max(min(ys) - m, 0), min(max(xs) + m, ctx.nx - 1), min(max(ys) + m, ctx.ny - 1))
            path = astar(ctx, nid, w, clr, list(tree), tgt, win)
            if path:
                break
        if not path and w > 0.2:
            for margin in (20.0, 200.0):
                xs = [i for (_, _, i) in tree] + [i for (_, _, i) in tgt]
                ys = [j for (_, j, _) in tree] + [j for (_, j, _) in tgt]
                m = int(margin / RES)
                win = (max(min(xs) - m, 0), max(min(ys) - m, 0), min(max(xs) + m, ctx.nx - 1),
                       min(max(ys) + m, ctx.ny - 1))
                path = astar(ctx, nid, 0.2, clr, list(tree), tgt, win)
                if path:
                    w_used = 0.2
                    break
        else:
            w_used = w
        if not path:
            ok = False
            continue
        commit(ctx, board, net, nid, w_used if path else w, path)
        N = ctx.nx * ctx.ny
        for s in path:
            L, rem = divmod(s, N)
            j, i = divmod(rem, ctx.nx)
            tree.add((L, j, i))
        tree.update(tgt)
    return ok


def fanout_ground(ctx, board, quiet=False):
    """Give every small SMD GND pad a via (short stub) to the bottom ground plane."""
    gnd = board.FindNet("GND")
    nid = ctx.netcode("GND")
    clr = ctx.clr_of("GND")
    count = 0
    for ref, num, sh, pad in ctx.net_pads.get("GND", []):
        if pad.HasHole() or 0 not in sh.layers or 1 in sh.layers:
            continue
        if sh.kind == "rect" and (sh.params[2] * sh.params[3] * 4) > 3.0:
            continue  # big pads (EP, probe strips) are stitched by their own vias / the pour
        if ref.startswith("PRB") or sh.params[1] > (ctx.ny - 1) * RES or (ref == "U1" and num in ("2", "8")):
            continue
        src = _cells_in(ctx, sh, shrink=sh.shrink)
        best = None
        cx, cy = sh.params[0], sh.params[1]
        vF = ctx.maps[(0, "via", clr)]
        vB = ctx.maps[(1, "via", clr)]
        for r in np.arange(0.4, 2.2, 0.1):
            for ang in range(0, 360, 15):
                x = cx + r * math.cos(math.radians(ang))
                y = cy + r * math.sin(math.radians(ang))
                i, j = int(round(x / RES)), int(round((y - ctx.gy0) / RES))
                if not (0 <= i < ctx.nx and 0 <= j < ctx.ny):
                    continue
                if vF[j, i] in (-1, nid) and vB[j, i] in (-1, nid):
                    # stub must be clear too
                    path = astar(ctx, nid, 0.3, clr, src, [(0, j, i)],
                                 (max(i - 30, 0), max(j - 30, 0), min(i + 30, ctx.nx - 1), min(j + 30, ctx.ny - 1)))
                    if path and len(path) < 30:
                        best = (path, i * RES, ctx.gy0 + j * RES)
                        break
            if best:
                break
        if not best:
            if not quiet:
                print(f"  - no GND fan-out via for {ref}.{num} (connected through pour/EP)")
            continue
        path, x, y = best
        if len(path) > 1:
            commit(ctx, board, "GND", nid, 0.3, path)
        add_via(ctx, board, gnd, nid, x, y, clr)
        count += 1
    if not quiet:
        print("GND fan-out vias:", count)


def finish_ground(board, origin, rect, slot=None):
    """GND pours (both layers) over rect=(x1, y1, x2, y2) board-local, stitching vias, fill."""
    rx1, ry1, rx2, ry2 = rect
    ctx = board_ctx[0]
    gnd = board.FindNet("GND")
    ox, oy = origin
    for lay in LAYERS:
        z = pcbnew.ZONE(board)
        z.SetLayer(lay)
        z.SetNet(gnd)
        ol = z.Outline()
        ol.NewOutline()
        for (x, y) in [(rx1, ry1), (rx2, ry1), (rx2, ry2), (rx1, ry2)]:
            ol.Append(MM(ox + x), MM(oy + y))
        z.SetLocalClearance(MM(0.3))
        z.SetMinThickness(MM(0.25))
        z.SetThermalReliefGap(MM(0.3))
        z.SetThermalReliefSpokeWidth(MM(0.4))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        z.SetIsFilled(False)
        z.SetZoneName("GND_" + ("TOP" if lay == pcbnew.F_Cu else "BOT"))
        board.Add(z)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    # stitching vias where both pours exist and the via grid allows it
    nid = ctx.netcode("GND")
    clr = ctx.clr_of("GND")
    vF = ctx.maps[(0, "via", clr)]
    vB = ctx.maps[(1, "via", clr)]
    zones = list(board.Zones())
    added = 0
    pitch = 2.5
    y = 1.2
    while y < ry2 - 1.0:
        x = 1.2
        while x < (ctx.nx - 1) * RES - 1.0:
            i, j = int(round(x / RES)), int(round(y / RES))
            if 0 <= j < ctx.ny and vF[j, i] in (-1, nid) and vB[j, i] in (-1, nid):
                p = pcbnew.VECTOR2I(MM(ox + x), MM(oy + y))
                inside = all(z.GetFilledPolysList(z.GetLayer()).Contains(p) for z in zones)
                if inside:
                    add_via(ctx, board, gnd, nid, x, y, clr)
                    added += 1
            x += pitch
        y += pitch
    filler.Fill(board.Zones())
    # every filled island must touch a GND via / plated hole, otherwise drop a via into it
    for _round in range(3):
        fixed = 0
        holes = [(TOMM(v.GetPosition().x) - ox, TOMM(v.GetPosition().y) - oy) for v in board.GetTracks()
                 if isinstance(v, pcbnew.PCB_VIA) and v.GetNetname() == "GND"]
        for fp in _fps(board):
            for pad in fp.Pads():
                if pad.HasHole() and pad.GetNetname() == "GND":
                    holes.append((TOMM(pad.GetPosition().x) - ox, TOMM(pad.GetPosition().y) - oy))
        for z in board.Zones():
            polys = z.GetFilledPolysList(z.GetLayer())
            for k in range(polys.OutlineCount()):
                ol = polys.Outline(k)
                if any(ol.PointInside(pcbnew.VECTOR2I(MM(ox + hx), MM(oy + hy))) for hx, hy in holes):
                    continue
                bb = ol.BBox()
                xa, ya = TOMM(bb.GetX()) - ox, TOMM(bb.GetY()) - oy
                xb, yb = xa + TOMM(bb.GetWidth()), ya + TOMM(bb.GetHeight())
                done = False
                yy = ya + 0.4
                while yy < yb - 0.3 and not done:
                    xx = xa + 0.4
                    while xx < xb - 0.3 and not done:
                        i, j = int(round(xx / RES)), int(round(yy / RES))
                        if 0 <= i < ctx.nx and 0 <= j < ctx.ny and vF[j, i] in (-1, nid) and vB[j, i] in (-1, nid):
                            ok = all(ol.PointInside(pcbnew.VECTOR2I(MM(ox + xx + dx), MM(oy + yy + dy)))
                                     for dx, dy in ((0.35, 0), (-0.35, 0), (0, 0.35), (0, -0.35), (0, 0)))
                            other = [zz for zz in board.Zones() if zz.GetLayer() != z.GetLayer()]
                            ok = ok and all(zz.GetFilledPolysList(zz.GetLayer()).Contains(
                                pcbnew.VECTOR2I(MM(ox + xx), MM(oy + yy))) for zz in other)
                            if ok:
                                add_via(ctx, board, gnd, nid, round(xx, 2), round(yy, 2), clr)
                                fixed += 1
                                done = True
                        xx += 0.1
                    yy += 0.1
        if not fixed:
            break
        filler.Fill(board.Zones())
        added += fixed
    print("stitching vias:", added)
