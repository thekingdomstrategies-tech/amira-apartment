#!/usr/bin/env python3
"""Extract the as-built walls of the Creektown apartment from the architect's vector PDF.

The DWG cannot be read without extra tooling, but source/original_empty.pdf is a 1:50 plot of the same drawing on A3,
with every line still a vector. This script turns it into axis-aligned wall rectangles in plan centimetres:

  1. pdftocairo turns the PDF into SVG paths (poppler-utils).
  2. The paths are sorted by pen: wall outlines (0.54 pt grey), columns (1.44 pt), wall hatching, and the filled
     concrete facade band.
  3. Every x and y used by an outline cuts the plan into a grid of cells. A cell that holds hatching is wall; a cell
     inside the facade fill is facade. Hairline gaps between wall cells are closed.
  4. Neighbouring cells are merged greedily into rectangles.

Plan coordinates: the sheet is turned 90 degrees anticlockwise so the room names read upright (as in the furnished
plan), x to the right, y down, in cm, origin near the top-left corner of the drawing. 1 pt on the sheet = 1.764 cm.

Usage: python3 tools/extract_walls.py  ->  data/walls.json
"""
import json, os, re, subprocess, sys, tempfile

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(ROOT, 'source', 'original_empty.pdf')
OUT = os.path.join(ROOT, 'data', 'walls.json')

CM_PER_PT = 0.3528 * 50 / 10      # 1:50 on the sheet: 1 pt = 0.3528 mm = 1.764 cm
X0, Y0, X1, Y1 = 185, 85, 1095, 800   # the drawing's window on the turned sheet, in pt
SHEET_W = 842                     # A3 portrait width in pt (the sheet is turned, so this becomes its height)
TERRACE = (1338, 58, 1560, 158)   # the terrace decking is hatched like a wall; it is floor, so it is left out (cm)


def parse_svg(fn):
    """Every <path> as polylines in sheet points, with its pen."""
    s = open(fn).read()
    out = []
    for m in re.finditer(r'<path ([^>]*)/>', s):
        a = m.group(1)
        g = lambda k: (re.search(k + r'="([^"]*)"', a) or [None, None])[1]
        M = [float(x) for x in re.findall(r'[-\d.e]+', g('transform'))] if g('transform') else [1, 0, 0, 1, 0, 0]
        T = lambda x, y: (M[0] * x + M[2] * y + M[4], M[1] * x + M[3] * y + M[5])
        toks = re.findall(r'[MLCZ]|[-\d.e]+', g('d') or '')
        subs, cur, i, cmd = [], [], 0, None
        while i < len(toks):
            t = toks[i]
            if t in 'MLCZ':
                cmd = t; i += 1
            if cmd == 'Z':
                if cur:
                    cur.append(cur[0]); subs.append(cur); cur = []
                cmd = None; continue
            if cmd == 'M':
                if cur: subs.append(cur)
                cur = [T(float(toks[i]), float(toks[i + 1]))]; i += 2; cmd = 'L'
            elif cmd == 'L':
                cur.append(T(float(toks[i]), float(toks[i + 1]))); i += 2
            elif cmd == 'C':
                p = [T(float(toks[i + k]), float(toks[i + k + 1])) for k in (0, 2, 4)]
                p0 = cur[-1]
                for j in range(1, 9):
                    u = j / 8
                    cur.append(tuple((1 - u) ** 3 * p0[c] + 3 * (1 - u) ** 2 * u * p[0][c] + 3 * (1 - u) * u * u * p[1][c] + u ** 3 * p[2][c] for c in (0, 1)))
                i += 6
            else:
                i += 1
        if cur: subs.append(cur)
        out.append(dict(fill=g('fill'), stroke=g('stroke') or '', sw=g('stroke-width'), subs=subs))
    return out


def turn(p):          # sheet point -> turned sheet point (anticlockwise, so the text reads upright)
    return (p[1], SHEET_W - p[0])


def cm(v, o):
    return (v - o) * CM_PER_PT


def main():
    with tempfile.TemporaryDirectory() as td:
        svg = os.path.join(td, 'plan.svg')
        subprocess.run(['pdftocairo', '-svg', PDF, svg], check=True)
        P = parse_svg(svg)

    is_outline = lambda p: p['sw'] in ('0.54', '1.44')
    is_hatch = lambda p: (p['sw'] == '0.06' and p['stroke'].startswith('rgb(49')) or (p['sw'] == '0.24' and p['stroke'].startswith('rgb(76'))
    is_facade = lambda p: bool(p['fill']) and p['fill'].startswith('rgb(78')

    K = 4    # raster: 4 px per pt
    W, H = (X1 - X0) * K, (Y1 - Y0) * K

    def raster(sel, fill=False):
        im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
        for p in P:
            if not sel(p): continue
            for s in p['subs']:
                q = [((turn(x)[0] - X0) * K, (turn(x)[1] - Y0) * K) for x in s]
                if fill and len(q) > 2: d.polygon(q, fill=255)
                elif len(q) > 1: d.line(q, fill=255, width=1)
        return np.array(im) > 0

    hatch = raster(is_hatch)
    facade = raster(is_facade, fill=True)

    xs, ys = set(), set()
    for p in P:
        if not (is_outline(p) or is_facade(p)): continue
        for s in p['subs']:
            for a, b in zip(s, s[1:]):
                A, B = turn(a), turn(b)
                if abs(A[0] - B[0]) < .3: xs.add(round((A[0] + B[0]) / 2, 1))
                if abs(A[1] - B[1]) < .3: ys.add(round((A[1] + B[1]) / 2, 1))

    def merge(v):
        v = sorted(v); o = [v[0]]
        for a in v[1:]:
            if a - o[-1] > .6: o.append(a)
        return o
    xs, ys = merge(xs), merge(ys)
    nx, ny = len(xs) - 1, len(ys) - 1

    G = np.zeros((ny, nx), int)      # 0 room, 1 wall, 2 facade
    for i in range(nx):
        for j in range(ny):
            x0, x1, y0, y1 = xs[i], xs[i + 1], ys[j], ys[j + 1]
            cx, cy = cm((x0 + x1) / 2, X0), cm((y0 + y1) / 2, Y0)
            if TERRACE[0] < cx < TERRACE[2] and TERRACE[1] < cy < TERRACE[3]: continue
            a = hatch[int((y0 - Y0) * K) + 1:int((y1 - Y0) * K) - 1, int((x0 - X0) * K) + 1:int((x1 - X0) * K) - 1]
            if facade[int(((y0 + y1) / 2 - Y0) * K), int(((x0 + x1) / 2 - X0) * K)]: G[j, i] = 2
            elif a.size and a.mean() > .04 and min(x1 - x0, y1 - y0) * CM_PER_PT < 106: G[j, i] = 1

    for _ in range(2):     # close hairline gaps (under 4 cm) between wall cells
        for j in range(ny):
            for i in range(nx):
                if G[j, i]: continue
                w, h = (xs[i + 1] - xs[i]) * CM_PER_PT, (ys[j + 1] - ys[j]) * CM_PER_PT
                if w < 4 and 0 < i < nx - 1 and G[j, i - 1] and G[j, i + 1]: G[j, i] = G[j, i - 1]
                elif h < 4 and 0 < j < ny - 1 and G[j - 1, i] and G[j + 1, i]: G[j, i] = G[j - 1, i]

    used = np.zeros_like(G, bool); rects = []
    for t in (1, 2):
        for j in range(ny):
            for i in range(nx):
                if G[j, i] != t or used[j, i]: continue
                i2 = i
                while i2 + 1 < nx and G[j, i2 + 1] == t and not used[j, i2 + 1]: i2 += 1
                j2 = j
                while j2 + 1 < ny and all(G[j2 + 1, k] == t and not used[j2 + 1, k] for k in range(i, i2 + 1)): j2 += 1
                used[j:j2 + 1, i:i2 + 1] = True
                r = [round(cm(xs[i], X0)), round(cm(ys[j], Y0)), round(cm(xs[i2 + 1], X0)), round(cm(ys[j2 + 1], Y0))]
                if r[2] - r[0] >= 1 and r[3] - r[1] >= 1:
                    rects.append(r + ['wall' if t == 1 else 'facade'])
    # the two grey facade strips drawn as dotted concrete without a fill (left and top-left of the bedrooms)
    rects += [[10, 262, 40, 1122, 'facade'], [195, 10, 217, 137, 'facade']]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({'source': 'source/original_empty.pdf', 'units': 'cm', 'scale': '1:50 on A3', 'rects': rects},
              open(OUT, 'w'), indent=0)
    print('%d wall rectangles -> %s' % (len(rects), os.path.relpath(OUT, ROOT)))


if __name__ == '__main__':
    sys.exit(main())
