"""Clean wall outlines for the zoned plan.

The walls are traced from the architect's PDF cell by cell, so they arrive as many small rectangles: hairline gaps of a
few centimetres between pieces, small chips, notches and steps where two traced strips do not quite line up. This turns
them into clean, straight wall shapes, on a 1 cm grid:

  1. close gaps and notches up to GAP cm (doors and windows are 60 cm and more, so they stay open);
  2. drop slivers thinner than SLIVER cm and loose chips smaller than CHIP cm²;
  3. straighten: break the shape into rectangles and snap every edge to the most common face nearby (within SNAP cm),
     so a wall face that wobbles by a few centimetres becomes one straight line;
  4. close and open once more, then hand back the rectangles.

Openings (doors, windows) are wider than GAP, so they stay open.
"""
import numpy as np
from scipy import ndimage as nd

GAP, SLIVER, CHIP, SNAP = 9, 4, 400, 7


def _mask(rects, W, H):
    m = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in rects:
        a, b = max(0, int(round(y0))), min(H, int(round(y1)))
        c, d = max(0, int(round(x0))), min(W, int(round(x1)))
        if a < b and c < d: m[a:b, c:d] = True
    return m


def _rects(m):
    """Greedy rectangles covering a mask: rows first, then grown downwards."""
    m = m.copy(); out = []
    H, W = m.shape
    ys, xs = np.nonzero(m)
    for y, x in zip(ys, xs):
        if not m[y, x]: continue
        x1 = x
        while x1 < W and m[y, x1]: x1 += 1
        y1 = y + 1
        while y1 < H and m[y1, x:x1].all(): y1 += 1
        m[y:y1, x:x1] = False
        out.append([int(x), int(y), int(x1), int(y1)])
    return out


def _snap(vals):
    """{value: weight} -> {value: snapped value}: each cluster within SNAP cm goes to its heaviest member."""
    keys = sorted(vals)
    out, group = {}, []
    for v in keys + [None]:
        if v is not None and (not group or v - group[-1] <= SNAP):
            group.append(v); continue
        best = max(group, key=lambda k: vals[k])
        for k in group: out[k] = best
        group = [v] if v is not None else []
    return out


def _clean(m):
    k = lambda n: np.ones((n, n), bool)
    m = nd.binary_closing(m, k(GAP))
    m = nd.binary_opening(m, k(SLIVER))
    lab, n = nd.label(m)
    if n:
        sizes = nd.sum(np.ones_like(lab), lab, range(n + 1))
        keep = sizes >= CHIP; keep[0] = False
        m = keep[lab]
    return m


def clean(rects, W, H, clear=()):
    """rects: [x0, y0, x1, y1] in cm -> cleaned, straightened rects. clear: footprints (doors, windows) kept open."""
    m = _clean(_mask(rects, W, H))
    rs = _rects(m)
    # straighten: snap the x edges and the y edges, each weighted by how long the edge runs
    xw, yw = {}, {}
    for x0, y0, x1, y1 in rs:
        for x in (x0, x1): xw[x] = xw.get(x, 0) + (y1 - y0)
        for y in (y0, y1): yw[y] = yw.get(y, 0) + (x1 - x0)
    sx, sy = _snap(xw), _snap(yw)
    snapped = []
    for x0, y0, x1, y1 in rs:   # a thin wall keeps its own thickness: its two faces are never snapped together
        a, b = (sx[x0], sx[x1]) if sx[x1] > sx[x0] else (x0, x1)
        c, d = (sy[y0], sy[y1]) if sy[y1] > sy[y0] else (y0, y1)
        snapped.append([a, c, b, d])
    rs = snapped
    m = _clean(_mask(rs, W, H))
    if clear: m &= ~_mask(clear, W, H)   # an opening never shrinks
    return _rects(m)


def path(rects, k):
    """One SVG path for all the rectangles (one shape, so no hairline seams between pieces)."""
    return ''.join('M%g %gh%gv%gh%gz' % (x0 * k, y0 * k, (x1 - x0) * k, (y1 - y0) * k, -(x1 - x0) * k) for x0, y0, x1, y1 in rects)


def _runs(m, axis):
    """For each wall cell: the length of its run along `axis`, and its distance to the run's two ends."""
    a = m if axis == 1 else m.T
    L = np.zeros(a.shape, np.int32); d0 = np.zeros(a.shape, np.int32); d1 = np.zeros(a.shape, np.int32)
    for i in range(a.shape[0]):
        row = a[i]
        if not row.any(): continue
        edges = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        starts, ends = np.nonzero(edges == 1)[0], np.nonzero(edges == -1)[0]
        for s, e in zip(starts, ends):
            n = e - s
            L[i, s:e] = n; d0[i, s:e] = np.arange(n); d1[i, s:e] = np.arange(n)[::-1]
    return (L, d0, d1) if axis == 1 else (L.T, d0.T, d1.T)


def thin(rects, W, H, share=.4, max_cut=5, min_core=4):
    """The walls drawn thinner: each wall loses `share` of its thickness (at most max_cut cm a side), centred, and
    only across its thickness, so wall ends, and the doors and windows between them, stay where they are."""
    m = _mask(rects, W, H)
    hL, hd0, hd1 = _runs(m, 1)        # along x
    vL, vd0, vd1 = _runs(m, 0)        # along y
    horiz = hL >= vL                  # a cell of a wall running along x: its thickness is its run along y
    t = np.where(horiz, vL, hL)
    near = np.where(horiz, np.minimum(vd0, vd1), np.minimum(hd0, hd1))
    cut = np.minimum(max_cut, np.maximum(0, np.minimum(np.round(t * share / 2), (t - min_core) // 2)))
    core = m & (near >= cut)
    return _rects(core)
