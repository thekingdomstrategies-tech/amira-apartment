#!/usr/bin/env python3
"""The surroundings of building E07 for the 3D view from the windows: read off the brochure's masterplan (page 7).

Unit E07-53 is on the 5th floor of E07, the building at the head of the middle apartment cluster's pool (the building
circled on the compound's model). Its pool side is the plan's top edge (the reception, master bedroom and terrace).
The masterplan is drawn with the Suez Road at the top and Rehab at the bottom, so roughly north up; the pool side of
E07 faces down the page, which the model takes as south (SITE.facing in tools/build_3d.py).

From the masterplan rendered at 300 dpi:
  buildings  white roofs; apartment blocks become E07-sized floor plates (two orientations), long roofs along the
             road are the shops (three storeys)
  pools      blue
  roads      wide dark grey
  trees      scattered on the lawn, away from buildings, pools and roads
Masterplan pixels map to plan centimetres by a half turn about E07's centre (the page's down is the plan's up), at
SCALE cm per pixel, set by E07's roof against its floor plate.

Usage: python3 tools/surroundings.py   ->  data/surroundings.json
"""
import json, math, os, random, subprocess, sys, tempfile

import numpy as np
from PIL import Image
from scipy import ndimage as nd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'surroundings.json')
PAGE = 7
CROP = (930, 330, 1520, 700)        # the apartment clusters, in points of the page rendered at 1862 px wide
E07 = (736.5, 252.0)                # E07's roof centre in the crop (px)
SCALE = 26.0                        # cm per px: E07's roof is 115 x 98 px for a floor plate of about 32 x 23 m
PLATE = (3160, 2300)                # an apartment block's floor plate, cm (two 165 m2 units side by side, two deep)
BUILDING_CENTRE = (1590, 1160)      # E07's centre in plan cm: its four units meet at the party wall x 1590, y 1160
STOREY, FLOORS_BELOW = 310, 5       # see tools/model.py
GROUND = -STOREY * FLOORS_BELOW


def to_plan(ix, iy):
    """Masterplan crop px -> plan cm: a half turn about E07 (the page's down is the plan's up)."""
    return (BUILDING_CENTRE[0] - (ix - E07[0]) * SCALE, BUILDING_CENTRE[1] - (iy - E07[1]) * SCALE)


def keep_large(mask, min_px):
    """Only the connected parts of a mask of at least min_px pixels."""
    lab, n = nd.label(mask)
    if not n: return mask
    sizes = nd.sum(np.ones_like(lab), lab, range(n + 1))
    keep = sizes >= min_px; keep[0] = False
    return keep[lab]


def runs(mask, step):
    """A mask as boxes: runs along each band of `step` rows, in plan cm [x0, y0, x1, y1]."""
    out = []
    H, W = mask.shape
    for y in range(0, H, step):
        band = mask[y:y + step].any(axis=0)
        x = 0
        while x < W:
            if band[x]:
                x0 = x
                while x < W and band[x]: x += 1
                a, b = to_plan(x0, y), to_plan(x, y + step)
                out.append([round(min(a[0], b[0])), round(min(a[1], b[1])), round(max(a[0], b[0])), round(max(a[1], b[1]))])
            x += 1
    return out


def main():
    with tempfile.TemporaryDirectory() as td:
        base = os.path.join(td, 'mp')
        subprocess.run(['pdftoppm', '-r', '300', '-png', '-singlefile', '-f', str(PAGE), '-l', str(PAGE),
                        os.path.join(ROOT, 'source', 'creek_town_brochure.pdf'), base], check=True, stderr=subprocess.DEVNULL)
        im = Image.open(base + '.png').convert('RGB')
    k = im.size[0] / 1862
    im = im.crop(tuple(round(v * k) for v in CROP))
    a = np.array(im).astype(int)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]

    white = nd.binary_opening((R > 215) & (G > 215) & (B > 215), np.ones((3, 3)))
    blue = (B > 140) & (B > R + 45) & (B >= G - 4)                # the pools' deep and light blues
    blue = nd.binary_fill_holes(nd.binary_closing(blue, np.ones((5, 5))))
    blue = keep_large(nd.binary_opening(blue, np.ones((3, 3))), 150)
    grey = (abs(R - G) < 14) & (abs(G - B) < 14) & (R > 45) & (R < 110)
    road = keep_large(nd.binary_opening(grey, np.ones((9, 9))), 3000)   # only long, wide grey: roads, not shadows
    green = (G > R + 12) & (G > B + 8)

    lab, n = nd.label(white)
    blocks, shops, taken = [], [], np.zeros_like(white)
    for i, sl in enumerate(nd.find_objects(lab)):
        part = lab[sl] == i + 1
        area = part.sum()
        if area < 1500: continue
        w, h = sl[1].stop - sl[1].start, sl[0].stop - sl[0].start
        cx, cy = (sl[1].start + sl[1].stop) / 2, (sl[0].start + sl[0].stop) / 2
        taken[sl] |= part
        if 6000 < area < 8000 and max(w, h) < 125:            # an apartment block
            if abs(cx - E07[0]) < 5 and abs(cy - E07[1]) < 5: continue   # E07 itself is modelled from the plan
            px, py = to_plan(cx, cy)
            dx, dy = (PLATE[0] / 2, PLATE[1] / 2) if w > h else (PLATE[1] / 2, PLATE[0] / 2)
            blocks.append([round(px - dx), round(py - dy), round(px + dx), round(py + dy)])
        else:                                                   # the shops along the road
            m = np.zeros_like(white); m[sl] = part
            shops += runs(m, 6)

    # trees on the lawn: a jittered grid, kept clear of buildings, pools and roads
    clear = nd.binary_dilation(taken | blue | road, np.ones((15, 15)))
    rnd = random.Random(7)
    trees, H, W = [], a.shape[0], a.shape[1]
    for gy in range(8, H - 8, 30):
        for gx in range(8, W - 8, 30):
            x, y = gx + rnd.randint(-9, 9), gy + rnd.randint(-9, 9)
            if not (0 <= x < W and 0 <= y < H) or clear[y, x] or not green[y, x]: continue
            if rnd.random() < .35: continue
            px, py = to_plan(x, y)
            trees.append([round(px), round(py), 'palm' if rnd.random() < .45 else 'round', round(.8 + .5 * rnd.random(), 2)])

    data = dict(source='source/creek_town_brochure.pdf, page %d (masterplan)' % PAGE, scale_cm_per_px=SCALE, ground=GROUND,
                blocks=blocks, shops=shops, water=runs(blue, 2), roads=runs(road, 6), trees=trees)
    json.dump(data, open(OUT, 'w'), separators=(',', ':'))
    print('%d blocks, %d shop boxes, %d water boxes, %d road boxes, %d trees -> %s' % (
        len(blocks), len(shops), len(data['water']), len(data['roads']), len(trees), os.path.relpath(OUT, ROOT)))


if __name__ == '__main__':
    sys.exit(main())
