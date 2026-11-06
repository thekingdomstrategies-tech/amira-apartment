#!/usr/bin/env python3
"""The compound's ground and planting for the high-quality terrace render, read off the brochure's masterplan (page 7),
on the same crop and scale as tools/surroundings.py.

  data/ground.png      the ground, 2 px per masterplan px (13 cm): red the pools, green paving (paths, pool decks, the
                       aprons round the buildings), blue the roads, alpha the pools' depth (1 well inside the edge).
                       Lawn is what is left. Edges are smoothed, then anti-aliased.
  data/compound.json   trees where the masterplan draws a canopy (dark green, or the red-brown flowering ones), palms
                       along the pool decks, the hedges round each building, and the map's placement in plan cm.

Usage: python3 tools/compound_map.py
"""
import json, math, os, random, subprocess, sys, tempfile

import numpy as np
from PIL import Image
from scipy import ndimage as nd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import surroundings as su

ROOT = su.ROOT
UP = 2                      # output px per masterplan px


def masterplan():
    with tempfile.TemporaryDirectory() as td:
        base = os.path.join(td, 'mp')
        subprocess.run(['pdftoppm', '-r', '300', '-png', '-singlefile', '-f', str(su.PAGE), '-l', str(su.PAGE),
                        os.path.join(ROOT, 'source', 'creek_town_brochure.pdf'), base], check=True, stderr=subprocess.DEVNULL)
        im = Image.open(base + '.png').convert('RGB')
    k = im.size[0] / 1862
    return np.array(im.crop(tuple(round(v * k) for v in su.CROP))).astype(int)


def smooth(mask, sigma, up=UP):
    """A pixel mask as a smooth, anti-aliased field at `up` times the resolution."""
    f = nd.zoom(mask.astype(np.float32), up, order=1)
    f = nd.gaussian_filter(f, sigma * up)
    hard = f > .5
    return nd.gaussian_filter(hard.astype(np.float32), .6)


def blobs(mask, lo, hi):
    lab, n = nd.label(mask)
    out = []
    for i, sl in enumerate(nd.find_objects(lab)):
        part = lab[sl] == i + 1
        area = int(part.sum())
        if lo <= area <= hi:
            cy, cx = nd.center_of_mass(part)
            out.append((sl[1].start + cx, sl[0].start + cy, area))
    return out


def main():
    a = masterplan()
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    sat = mx - mn
    white = nd.binary_opening((R > 215) & (G > 215) & (B > 215), np.ones((3, 3)))
    roofs = su.keep_large(white, 1500)
    near_roof = nd.binary_dilation(roofs, iterations=4)

    blue = (B > 100) & (B > R + 30) & (B >= G - 10)
    water = nd.binary_fill_holes(nd.binary_closing(blue, np.ones((5, 5))))
    water = su.keep_large(nd.binary_opening(water, np.ones((3, 3))), 150)

    grey = (sat < 16) & (R > 45) & (R < 120)
    road = su.keep_large(nd.binary_opening(grey, np.ones((9, 9))), 3000)
    road = nd.binary_closing(road, np.ones((7, 7)))

    pale = ((sat < 30) & (mx > 125) & ~white) | ((R > G + 12) & (R > B + 20) & (R > 110))
    pale &= ~near_roof & ~water
    paths = su.keep_large(nd.binary_opening(pale, np.ones((2, 2))), 40)
    deck = nd.binary_dilation(water, iterations=8) & ~water            # a paved edge all round the pools
    apron = nd.binary_dilation(roofs, iterations=5) & ~roofs           # and round each building, inside its hedge
    paving = (paths | deck | apron | roofs) & ~water & ~road

    W = smooth(water, 2.2)
    P = smooth(paving, 1.6)
    Rd = smooth(road, 2.5)
    depth = np.clip(nd.distance_transform_edt(nd.zoom(water, UP, order=0)) / (12 * UP), 0, 1)
    depth = nd.gaussian_filter(depth, 2)
    P = np.minimum(P, 1 - W); Rd = np.minimum(Rd, 1 - W)
    img = np.dstack([W, P, Rd, depth])
    Image.fromarray((np.clip(img, 0, 1) * 255).round().astype(np.uint8), 'RGBA').save(os.path.join(ROOT, 'data', 'ground.png'), optimize=True)

    # trees where a canopy is drawn: dark green, or the red-brown flowering ones; not on roofs, pools or roads
    clear = ~(nd.binary_dilation(roofs, iterations=10) | nd.binary_dilation(water, iterations=3) | road)   # not the roofs' shadows
    darkg = (mx < 80) & (G >= R) & clear
    redb = (R > G + 25) & (R > B + 25) & (R > 90) & (R < 200) & (sat > 50) & clear
    rnd = random.Random(11)
    trees, spots = [], []

    def free(x, y, d, among=None):
        pts = spots if among is None else among
        return all((x - u) ** 2 + (y - v) ** 2 > (d / su.SCALE) ** 2 for u, v in pts)

    # palms first, along the pool decks about every 9 m, as the brochure's pool views have them
    edge = deck & ~nd.binary_dilation(water, iterations=3)
    ys, xs = np.nonzero(edge)
    order = list(range(len(xs))); rnd.shuffle(order)
    for i in order:
        x, y = int(xs[i]), int(ys[i])
        if not free(x, y, 900): continue
        spots.append((x, y)); px, py = su.to_plan(x, y)
        trees.append([round(px), round(py), 'palm', round(.85 + .35 * rnd.random(), 2)])
    # then a tree wherever a canopy is drawn; about one in four of the garden ones a palm
    for x, y, area in sorted(blobs(nd.binary_opening(darkg, np.ones((2, 2))), 12, 400), key=lambda t: -t[2]):
        if not free(x, y, 550): continue
        spots.append((x, y)); px, py = su.to_plan(x, y)
        r = math.sqrt(area / math.pi) * su.SCALE                    # the canopy's radius, cm
        kind = 'olive' if r < 180 else 'broad'
        if kind == 'olive' and rnd.random() < .25:
            trees.append([round(px), round(py), 'palm', round(.8 + .4 * rnd.random(), 2)]); continue
        trees.append([round(px), round(py), kind, round(min(1.6, max(.7, r / 260)) * (.9 + .2 * rnd.random()), 2)])
    for x, y, area in blobs(nd.binary_opening(redb, np.ones((2, 2))), 6, 400):
        if not free(x, y, 450): continue
        spots.append((x, y)); px, py = su.to_plan(x, y)
        trees.append([round(px), round(py), 'flower', round(.9 + .3 * rnd.random(), 2)])

    # shrubs and flowering beds along the lawn's edges, where it meets the paths and the pool decks, about every 5 m
    lawn = ~(paving | water | road | roofs)
    rim = lawn & nd.binary_dilation(paths | deck, iterations=2) & ~nd.binary_dilation(roofs, iterations=6)
    ys, xs = np.nonzero(rim)
    order = list(range(len(xs))); rnd.shuffle(order)
    shrubs, near = [], []
    for i in order:
        x, y = int(xs[i]), int(ys[i])
        if not free(x, y, 250) or not free(x, y, 500, near): continue
        near.append((x, y)); px, py = su.to_plan(x, y)
        shrubs.append([round(px), round(py), 'bed' if rnd.random() < .3 else 'shrub', round(.5 + .4 * rnd.random(), 2)])

    # a clipped hedge round every block, 1.4 m out from its walls, with a gap at the middle of each side
    hedges = []
    for b in su.json_blocks() if hasattr(su, 'json_blocks') else json.load(open(su.OUT))['blocks']:
        x0, y0, x1, y1 = b[0] - 140, b[1] - 140, b[2] + 140, b[3] + 140
        hedges.append([x0, y0, x1, y1])

    H, Wd = a.shape[:2]
    # the map's corners in plan cm: (0, 0) and (W, H) masterplan px
    c0, c1 = su.to_plan(0, 0), su.to_plan(Wd, H)
    data = dict(source='source/creek_town_brochure.pdf, page %d (masterplan)' % su.PAGE, ground='data/ground.png',
                map_plan=[c0[0], c0[1], c1[0], c1[1]], trees=trees, shrubs=shrubs, hedges=hedges)
    json.dump(data, open(os.path.join(ROOT, 'data', 'compound.json'), 'w'), separators=(',', ':'))
    kinds = {}
    for t in trees:
        kinds[t[2]] = kinds.get(t[2], 0) + 1
    print('ground %dx%d; trees %s; %d shrubs and beds; %d hedges' % (Wd * UP, H * UP, kinds, len(shrubs), len(hedges)))


if __name__ == '__main__':
    sys.exit(main())
