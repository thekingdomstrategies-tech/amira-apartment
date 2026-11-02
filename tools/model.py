"""The Creektown apartment as a 3D model, in the data format of the AZAD walkthrough (kamelshenouda/azad).

Three plans, each from one pair of the architect's 1:50 sheets in source/:
  existing  As built (original_empty.pdf, original_with_furn.pdf)
  o1        Option 1, two bedrooms (option_1_empty.pdf, option_1_with_furn.pdf)
  o2        Option 2, three bedrooms (option_2_empty.pdf, option_2_with_furn.pdf)

Everything is in plan centimetres: x to the right, y down, z up from the finished floor, on the turned sheet used by
tools/extract_walls.py, which also moves every option sheet onto the original's frame. Walls come from
data/walls_<sheet>.json; the openings, rooms and furniture below were read off the sheets on a 1 cm grid.

An item is a box {"t":"b","b":[x0,y0,z0,x1,y1,z1],"m":material}, a cylinder {"t":"c","c":[x,y],"r":r,"z":[z0,z1]},
or a pendant {"t":"l"}. "g" marks walls, floors, ceilings and glass; "f" marks furniture ("loose") and joinery
("built") so the Furniture switch can hide them; "v" ties a piece to a switch state (doors open or closed).
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = 280          # floor to slab, cm (the AZAD viewer's ceiling height; to be confirmed on site)
DOOR_HEAD = 210
WIN_HEAD = 225
PARAPET = 95     # the concrete facade band outside the windows is drawn as a planter/parapet, not a full wall

# ---------------------------------------------------------------- openings in the facade: the same on every sheet
# rect: the opening's footprint, generous across the wall so it takes the whole thickness
# axis: 'x' if the wall runs along x (the opening spans x), 'y' if it runs along y
WINDOWS = [
    # name,               rect,                    axis, sill, head, panes
    ('Master bedroom window', [718, 52, 902, 92],    'x', 90, WIN_HEAD, 2),
    ('Reception window',      [1053, 30, 1242, 76],  'x', 90, WIN_HEAD, 2),
    ('Master bath window',    [220, 166, 258, 236],  'y', 150, 210, 1),
    ('Bedroom 1 window',      [82, 288, 219, 326],   'x', 90, WIN_HEAD, 2),
    ('Bedroom 2 window',      [34, 828, 74, 1006],   'y', 90, WIN_HEAD, 2),
    ('Bathroom window',       [669, 784, 739, 822],  'x', 150, 210, 1),
    ('Guest bath window',     [815, 784, 885, 822],  'x', 150, 210, 1),
    ('Kitchen window',        [944, 838, 984, 937],  'y', 105, 210, 1),
    ('Maid\'s room window',   [944, 986, 984, 1046], 'y', 105, 210, 1),
]
SLIDERS = [  # sliding glass doors: name, rect, axis
    ('Terrace doors', [1358, 170, 1546, 194], 'x'),
]
FRONT_DOOR = ('Front door', [1257, 1058, 1366, 1098], 'x', 0, -1, 'oakdark')
TERRACE = ('Terrace', [1340, 40, 1560, 172])
FLOOR_M = {'pub': 'porcelain', 'cir': 'porcelain', 'pri': 'oakfloor', 'wetz': 'stone', 'ser': 'porcelain'}
OUTLINE = [[195, 10], [1590, 10], [1590, 915], [1410, 915], [1410, 1150], [950, 1150], [950, 815], [455, 815],
           [455, 1160], [10, 1160], [10, 262], [195, 262]]

# ---------------------------------------------------------------- the three plans
# doors: name, rect, axis, hinge end (0 = low end, 1 = high end), swing (+1/-1 across the wall), leaf material
# openings: name, rect, axis, head height (no leaf)
# extra_walls: partitions the empty sheet draws without hatching, so the tracer leaves them out: rect, height
# rooms: name, interior rect, floor zone (pub reception, cir circulation, pri bedrooms, wetz wet rooms, ser service);
#   a name may repeat for an L-shaped room: its first rect is the one the viewer names and measures
# labels: label, the room it measures, where it sits
LAYOUTS = {}

LAYOUTS['existing'] = dict(
    name='As built · architect\'s furniture', button=('As built', 'with furniture'),
    title='The apartment as drawn by the architect, with the furniture layout',
    sheet='original',
    doors=[
        ('Master bedroom door', [613, 480, 699, 508],  'x', 0, -1, 'white'),
        ('Bedroom 1 door',      [418, 511, 448, 595],  'y', 1, -1, 'white'),
        ('Bedroom 2 door',      [447, 600, 531, 626],  'x', 1, +1, 'white'),
        ('Bathroom door',       [568, 600, 642, 626],  'x', 0, +1, 'white'),
        ('Guest bath door',     [821, 600, 894, 626],  'x', 0, +1, 'white'),
        ('Master bath door',    [418, 152, 448, 234],  'y', 0, -1, 'white'),
        ('Maid\'s room door',   [1125, 954, 1203, 980], 'x', 1, +1, 'white'),
        FRONT_DOOR,
    ],
    openings=[('Kitchen opening', [1205, 850, 1242, 940], 'y', DOOR_HEAD)],
    extra_walls=[],
    rooms=[
        ('Master bathroom', [252, 62, 430, 305],  'wetz'),
        ('Master bedroom',  [438, 88, 962, 492],  'pri'),
        ('Bedroom 1',       [67, 318, 428, 686],  'pri'),
        ('Bedroom 2',       [67, 694, 430, 1062], 'pri'),
        ('Bedroom 2',       [440, 618, 548, 792], 'pri'),     # its entry from the corridor
        ('Corridor',        [440, 498, 1218, 610], 'cir'),
        ('Bathroom 1',      [552, 618, 798, 790], 'wetz'),
        ('Guest bathroom',  [810, 618, 966, 790], 'wetz'),
        ('Kitchen',         [978, 618, 1216, 962], 'ser'),
        ('Maid\'s room',    [978, 972, 1216, 1132], 'ser'),
        ('Reception',       [972, 66, 1300, 480], 'pub'),
        ('Living',          [1300, 192, 1562, 480], 'pub'),
        ('Dining',          [1218, 480, 1562, 888], 'pub'),
        ('Entrance',        [1230, 888, 1380, 1064], 'cir'),
    ],
    labels=[
        ('Master bath', 'Master bathroom', 340, 185), ('Master bedroom', 'Master bedroom', 700, 300),
        ('Bedroom 1', 'Bedroom 1', 250, 500), ('Bedroom 2', 'Bedroom 2', 250, 880), ('Corridor', 'Corridor', 700, 555),
        ('Bathroom 1', 'Bathroom 1', 675, 705), ('Guest bath', 'Guest bathroom', 888, 705), ('Kitchen', 'Kitchen', 1097, 790),
        ('Maid\'s room', 'Maid\'s room', 1097, 1050), ('Reception', 'Reception', 1135, 270), ('Living', 'Living', 1430, 330),
        ('Dining', 'Dining', 1430, 655), ('Entrance', 'Entrance', 1305, 975), ('Terrace', 'Terrace', 1450, 105),
    ],
    shelf=[[982, 652], [1212, 652]], lamps=[[1520, 250], [1035, 120]],
)

LAYOUTS['o1'] = dict(
    name='Option 1 · two bedrooms', button=('Option 1', '2 bedrooms'),
    title='Option 1: the master bedroom moves to bedroom 1 with a dressing area, a kitchen where the master was, one shared bathroom, storage in the maid\'s room',
    sheet='option_1',
    doors=[
        ('Master bedroom door', [454, 480, 548, 506],  'x', 1, -1, 'white'),
        ('Bedroom 2 door',      [418, 700, 448, 786],  'y', 0, -1, 'white'),
        ('Bathroom door',       [814, 600, 900, 626],  'x', 1, +1, 'white'),   # no swing drawn: hinged on the vanity side
        ('Storage door',        [1205, 972, 1242, 1052], 'y', 1, -1, 'white'),
        FRONT_DOOR,
    ],
    # the sheet draws no leaf here: the master bathroom opens straight into the dressing area
    openings=[('Master bath opening', [418, 163, 448, 242], 'y', DOOR_HEAD)],
    extra_walls=[
        ([548, 486, 572, 498], H),         # the jamb beside the master bedroom door
        ([570, 88, 576, 488], H),          # dressing area | kitchen: a line on the furnished sheet only (to confirm)
    ],
    rooms=[
        ('Master bathroom', [252, 62, 430, 305],  'wetz'),
        ('Master bedroom',  [67, 318, 430, 686],  'pri'),
        ('Master bedroom',  [440, 88, 570, 490],  'pri'),     # the dressing area
        ('Kitchen',         [576, 88, 962, 490],  'ser'),
        ('Bedroom 2',       [67, 694, 430, 1062], 'pri'),
        ('Corridor',        [440, 498, 1218, 610], 'cir'),
        ('Corridor',        [440, 610, 625, 792], 'cir'),
        ('Bathroom',        [635, 618, 966, 790], 'wetz'),
        ('Storage',         [978, 972, 1216, 1132], 'ser'),
        ('Reception',       [972, 66, 1300, 480], 'pub'),
        ('Living',          [1300, 192, 1562, 612], 'pub'),
        ('Living',          [1218, 480, 1300, 612], 'pub'),
        ('Dining',          [978, 612, 1562, 888], 'pub'),
        ('Dining',          [978, 888, 1230, 962], 'pub'),
        ('Entrance',        [1230, 888, 1380, 1064], 'cir'),
    ],
    labels=[
        ('Master bath', 'Master bathroom', 340, 185), ('Master bedroom', 'Master bedroom', 250, 450),
        ('Dressing', 'Master bedroom', 505, 300), ('Kitchen', 'Kitchen', 810, 300), ('Bedroom 2', 'Bedroom 2', 250, 880),
        ('Corridor', 'Corridor', 800, 555), ('Bathroom', 'Bathroom', 800, 705), ('Storage', 'Storage', 1097, 1090),
        ('Reception', 'Reception', 1135, 270), ('Living', 'Living', 1430, 540), ('Dining', 'Dining', 1250, 700),
        ('Entrance', 'Entrance', 1305, 975), ('Terrace', 'Terrace', 1450, 105),
    ],
    shelf=[[900, 150], [900, 390]], lamps=[[1040, 120]],
)

LAYOUTS['o2'] = dict(
    name='Option 2 · three bedrooms', button=('Option 2', '3 bedrooms'),
    title='Option 2: three bedrooms, one shared bathroom, and a large kitchen with an island that takes in the maid\'s room and opens to the dining area',
    sheet='option_2',
    doors=[
        ('Master bedroom door', [641, 480, 729, 508],  'x', 0, -1, 'white'),
        ('Bedroom 1 door',      [418, 511, 448, 595],  'y', 1, -1, 'white'),
        ('Bedroom 2 door',      [418, 700, 448, 786],  'y', 0, -1, 'white'),
        ('Bathroom door',       [810, 600, 896, 626],  'x', 0, +1, 'white'),
        ('Master bath door',    [418, 153, 448, 232],  'y', 1, -1, 'white'),
        FRONT_DOOR,
    ],
    openings=[],
    extra_walls=[
        ([645, 606, 806, 618], H),         # the bathroom's corridor wall, drawn without hatching
    ],
    rooms=[
        ('Master bathroom', [252, 62, 430, 305],  'wetz'),
        ('Master bedroom',  [438, 88, 962, 492],  'pri'),
        ('Bedroom 1',       [67, 318, 428, 686],  'pri'),
        ('Bedroom 2',       [67, 694, 430, 1062], 'pri'),
        ('Corridor',        [440, 498, 1218, 610], 'cir'),
        ('Corridor',        [440, 610, 625, 792], 'cir'),
        ('Bathroom',        [635, 618, 966, 790], 'wetz'),
        ('Kitchen',         [978, 620, 1228, 1132], 'ser'),
        ('Reception',       [972, 66, 1300, 480], 'pub'),
        ('Living',          [1300, 192, 1562, 480], 'pub'),
        ('Dining',          [1228, 480, 1562, 888], 'pub'),
        ('Entrance',        [1230, 888, 1380, 1064], 'cir'),
    ],
    labels=[
        ('Master bath', 'Master bathroom', 340, 185), ('Master bedroom', 'Master bedroom', 700, 300),
        ('Bedroom 1', 'Bedroom 1', 250, 500), ('Bedroom 2', 'Bedroom 2', 250, 880), ('Corridor', 'Corridor', 700, 555),
        ('Bathroom', 'Bathroom', 800, 705), ('Kitchen', 'Kitchen', 1060, 960), ('Reception', 'Reception', 1135, 270),
        ('Living', 'Living', 1430, 330), ('Dining', 'Dining', 1430, 655), ('Entrance', 'Entrance', 1305, 975),
        ('Terrace', 'Terrace', 1450, 105),
    ],
    shelf=[[982, 652], [1226, 652]], lamps=[[1035, 120]],
)

ORDER = ['existing', 'o1', 'o2']


def _sub(r, o):
    """r minus o (both [x0,y0,x1,y1]): up to four rectangles."""
    out = []
    if o[0] > r[0]: out.append([r[0], r[1], min(o[0], r[2]), r[3]])
    if o[2] < r[2]: out.append([max(o[2], r[0]), r[1], r[2], r[3]])
    xa, xb = max(r[0], o[0]), min(r[2], o[2])
    if xa < xb:
        if o[1] > r[1]: out.append([xa, r[1], xb, min(o[1], r[3])])
        if o[3] < r[3]: out.append([xa, max(o[3], r[1]), xb, r[3]])
    return [q for q in out if q[2] - q[0] > .5 and q[3] - q[1] > .5]


def _hit(r, o):
    return r[0] < o[2] and r[2] > o[0] and r[1] < o[3] and r[3] > o[1]


def _inter(r, o):
    return [max(r[0], o[0]), max(r[1], o[1]), min(r[2], o[2]), min(r[3], o[3])]


def walls_of(key):
    """The traced walls of a plan, plus the partitions its sheet draws without hatching."""
    lay = LAYOUTS[key]
    walls = json.load(open(os.path.join(ROOT, 'data', 'walls_%s.json' % lay['sheet'])))['rects']
    return [w[:4] + [w[4]] for w in walls] + [list(r) + ['wall'] for r, _ in lay['extra_walls']]


def room_rects(key):
    """{room name: [rect, ...]} in the order the plan lists them, plus the terrace."""
    out = {}
    for n, r, _ in LAYOUTS[key]['rooms']:
        out.setdefault(n, []).append(r)
    out[TERRACE[0]] = [TERRACE[1]]
    return out


def build(key):
    lay = LAYOUTS[key]
    solid = [dict(r=w[:4], kind=w[4]) for w in walls_of(key)]
    items, pieces = [], []

    def box(b, m, **kw):
        it = dict(t='b', b=[round(v, 1) for v in b], m=m); it.update(kw); items.append(it); return it

    doors, openings = lay['doors'], lay['openings']
    # every opening cuts the walls it crosses; what lies inside keeps a sill and a lintel
    cuts = ([(n, r, a, s, h, 'win', p) for n, r, a, s, h, p in WINDOWS]
            + [(n, r, a, 0, WIN_HEAD, 'slide', 0) for n, r, a in SLIDERS]
            + [(n, r, a, 0, DOOR_HEAD + (10 if n == 'Front door' else 0), 'door', 0) for n, r, a, *_ in doors]
            + [(n, r, a, 0, h, 'open', 0) for n, r, a, h in openings])
    spans = {}
    for n, o, axis, sill, head, kind, _ in cuts:
        keep, inside = [], []
        for w in solid:
            if w['kind'] == 'wall' and _hit(w['r'], o):
                keep += [dict(r=q, kind='wall') for q in _sub(w['r'], o)]
                inside.append(_inter(w['r'], o))
            else:
                keep.append(w)
        solid = keep
        for q in inside:
            if sill > 0: box([q[0], q[1], 0, q[2], q[3], sill], 'wall', g='wall')
            box([q[0], q[1], head, q[2], q[3], H], 'wall', g='wall')
        if inside:   # the wall's true thickness across the opening
            if axis == 'x': t0, t1 = min(q[1] for q in inside), max(q[3] for q in inside)
            else: t0, t1 = min(q[0] for q in inside), max(q[2] for q in inside)
        else:
            t0, t1 = (o[1], o[3]) if axis == 'x' else (o[0], o[2])
        spans[n] = (t0, t1)
        if kind != 'win':   # a threshold, so the floor runs through
            a0, a1 = (o[0], o[2]) if axis == 'x' else (o[1], o[3])
            box([a0, t0, 0, a1, t1, 1] if axis == 'x' else [t0, a0, 0, t1, a1, 1], 'porcelain', g='floor', zn='cir')

    for w in solid:
        r = w['r']
        if w['kind'] == 'facade':
            box([r[0], r[1], 0, r[2], r[3], PARAPET], 'wall', g='wall')
        else:
            box([r[0], r[1], 0, r[2], r[3], H], 'wall', g='wall')
        pieces.append(dict(n='Facade band' if w['kind'] == 'facade' else 'Wall', b=[r[0], r[1], 0, r[2], r[3], PARAPET if w['kind'] == 'facade' else H]))

    # windows: an aluminium frame round one or two panes, in the middle of the wall
    def frame_and_glass(n, o, axis, sill, head, panes, t0, t1, mt, kind='win'):
        a0, a1 = (o[0], o[2]) if axis == 'x' else (o[1], o[3])
        mid = (t0 + t1) / 2
        def B(u0, u1, z0, z1, d=3.5):
            return [u0, mid - d, z0, u1, mid + d, z1] if axis == 'x' else [mid - d, u0, z0, mid + d, u1, z1]
        for z0, z1 in ((sill, sill + 5), (head - 5, head)):
            box(B(a0, a1, z0, z1), 'frame')
        box(B(a0, a0 + 5, sill, head), 'frame'); box(B(a1 - 5, a1, sill, head), 'frame')
        step = (a1 - a0) / panes
        for k in range(panes):
            u0, u1 = a0 + k * step, a0 + (k + 1) * step
            if k: box(B(u0 - 2.5, u0 + 2.5, sill, head), 'frame')
            box(B(u0 + 3, u1 - 3, sill + 5, head - 5, .8), 'glass', g='glass')
        # the viewer lights a room from pieces named Window / Terrace doors
        pieces.append(dict(n='Terrace doors' if kind == 'slide' else 'Window', b=B(a0, a1, sill, head), mt=n + ' · ' + mt))

    for n, o, axis, sill, head, panes in WINDOWS:
        frame_and_glass(n, o, axis, sill, head, panes, *spans[n], 'aluminium, dark grey')
    for n, o, axis in SLIDERS:
        frame_and_glass(n, o, axis, 0, WIN_HEAD, 2, *spans[n], 'sliding, aluminium, dark grey', 'slide')

    # doors: a 4 cm leaf, open at 90 degrees or closed in the wall (the Doors switch)
    for n, o, axis, hinge, swing, m in doors:
        t0, t1 = spans[n]
        a0, a1 = (o[0], o[2]) if axis == 'x' else (o[1], o[3])
        a0 += 3; a1 -= 3   # frame
        head = DOOR_HEAD + (10 if n == 'Front door' else 0)
        L = a1 - a0
        mid = (t0 + t1) / 2
        hp = a0 if hinge == 0 else a1            # hinge position along the wall
        face = t1 if swing > 0 else t0           # the face the leaf swings past
        # frame (architrave) on both jambs
        for u0, u1 in ((a0 - 3, a0), (a1, a1 + 3)):
            box([u0, t0 - 1, 0, u1, t1 + 1, head] if axis == 'x' else [t0 - 1, u0, 0, t1 + 1, u1, head], 'white', v=None)
        box([a0 - 3, t0 - 1, head, a1 + 3, t1 + 1, head + 4] if axis == 'x' else [t0 - 1, a0 - 3, head, t1 + 1, a1 + 3, head + 4], 'white')
        # closed
        box([a0, mid - 2, 0, a1, mid + 2, head - 1] if axis == 'x' else [mid - 2, a0, 0, mid + 2, a1, head - 1], m, v='d-closed')
        # open: perpendicular to the wall at the hinge, into the room it swings to
        u0, u1 = (hp, hp + 4) if hinge == 0 else (hp - 4, hp)
        v0, v1 = (face, face + swing * L) if swing > 0 else (face + swing * L, face)
        box([u0, v0, 0, u1, v1, head - 1] if axis == 'x' else [v0, u0, 0, v1, u1, head - 1], m, v='d-open')
        # handle
        hx = a1 - 8 if hinge == 0 else a0 + 8
        box([hx - 1, mid - 5, 102, hx + 1, mid + 5, 104] if axis == 'x' else [mid - 5, hx - 1, 102, mid + 5, hx + 1, 104], 'black', v='d-closed')
        pieces.append(dict(n=n, b=[a0, mid - 2, 0, a1, mid + 2, head] if axis == 'x' else [mid - 2, a0, 0, mid + 2, a1, head],
                           mt='painted wood' if m == 'white' else 'oak veneer, dark'))

    # floors and ceilings
    for n, r, zn in lay['rooms']:
        box([r[0], r[1], 0, r[2], r[3], 1], FLOOR_M[zn], g='floor', zn=zn)
        box([r[0], r[1], H - 1, r[2], r[3], H], 'ceiling', g='ceiling')
    tn, tr = TERRACE
    box([tr[0], tr[1], 0, tr[2], tr[3], 1], 'oak', g='floor')
    rects = room_rects(key)
    rooms, named = [], set()
    for n, rn, x, y in lay['labels']:
        if rn in named: continue   # a second label for the same room (the dressing area) names it on the plan only
        named.add(rn)
        r = rects[rn][0]
        rooms.append(dict(n=n, at=[x, y], r=r, d='%.2f × %.2f' % ((r[2] - r[0]) / 100, (r[3] - r[1]) / 100)))
    furn, extra = FURNITURE[key](Furnisher(box))
    items += extra
    return dict(items=items, labels=[[n, x, y] for n, _, x, y in lay['labels']], rooms=rooms, pieces=pieces + furn,
                lights=lighting(lay), garden=[[0, 0], [0, 0], [0, 0]], site=[-150, -150, 1750, 1320], name=lay['name'])


class Furnisher:
    """Simple furniture blocks: each helper adds the boxes and names the piece for the viewer's click card."""

    def __init__(self, box):
        self.box, self.P, self.extra = box, [], []
        self.L, self.B = dict(f='loose'), dict(f='built')

    def done(self):
        return self.P, self.extra

    def piece(self, n, b, mt=None):
        d = dict(n=n, b=b)
        if mt: d['mt'] = mt
        self.P.append(d)

    def bed(self, n, x0, y0, x1, y1, head):   # head: 'l','r','t','b', the side the headboard is on
        box, L = self.box, self.L
        box([x0, y0, 0, x1, y1, 30], 'oak', **L)
        box([x0 + 2, y0 + 2, 30, x1 - 2, y1 - 2, 52], 'linen', **L)
        if head in 'lr':
            hx0, hx1 = (x0, x0 + 8) if head == 'l' else (x1 - 8, x1)
            box([hx0, y0, 0, hx1, y1, 105], 'fabric', **L)
            px0, px1 = (x0 + 10, x0 + 50) if head == 'l' else (x1 - 50, x1 - 10)
            box([px0, y0 + 8, 52, px1, (y0 + y1) / 2 - 3, 64], 'linen', **L); box([px0, (y0 + y1) / 2 + 3, 52, px1, y1 - 8, 64], 'linen', **L)
        else:
            hy0, hy1 = (y0, y0 + 8) if head == 't' else (y1 - 8, y1)
            box([x0, hy0, 0, x1, hy1, 105], 'fabric', **L)
            py0, py1 = (y0 + 10, y0 + 50) if head == 't' else (y1 - 50, y1 - 10)
            box([x0 + 8, py0, 52, x1 - 8, py1, 64], 'linen', **L)
        self.piece(n, [x0, y0, 0, x1, y1, 105], 'upholstered bed')

    def bedside(self, x0, y0, x1, y1):
        self.box([x0, y0, 0, x1, y1, 50], 'oak', **self.L)

    def wardrobe(self, n, x0, y0, x1, y1, h=240):
        self.box([x0, y0, 0, x1, y1, h], 'white', **self.B)
        self.piece(n, [x0, y0, 0, x1, y1, h], 'built-in wardrobe')

    def sofa(self, n, x0, y0, x1, y1, back):   # back: side of the backrest
        box, L = self.box, self.L
        box([x0, y0, 0, x1, y1, 42], 'fabric', **L)
        bk = {'l': [x0, y0, 0, x0 + 20, y1, 80], 'r': [x1 - 20, y0, 0, x1, y1, 80], 't': [x0, y0, 0, x1, y0 + 20, 80], 'b': [x0, y1 - 20, 0, x1, y1, 80]}[back]
        box(bk, 'fabric', **L)
        if back in 'lr':
            box([x0, y0, 0, x1, y0 + 16, 62], 'fabric', **L); box([x0, y1 - 16, 0, x1, y1, 62], 'fabric', **L)
        else:
            box([x0, y0, 0, x0 + 16, y1, 62], 'fabric', **L); box([x1 - 16, y0, 0, x1, y1, 62], 'fabric', **L)
        self.piece(n, [x0, y0, 0, x1, y1, 80], 'fabric sofa')

    def armchair(self, n, x0, y0, x1, y1, back):
        self.box([x0, y0, 0, x1, y1, 42], 'fabric', **self.L)
        bk = {'l': [x0, y0, 0, x0 + 14, y1, 78], 'r': [x1 - 14, y0, 0, x1, y1, 78], 't': [x0, y0, 0, x1, y0 + 16, 78], 'b': [x0, y1 - 14, 0, x1, y1, 78]}[back]
        self.box(bk, 'fabric', **self.L)
        self.piece(n, [x0, y0, 0, x1, y1, 78], 'fabric')

    def table(self, n, x0, y0, x1, y1, h=75, m='oak'):
        box, L = self.box, self.L
        box([x0, y0, h - 4, x1, y1, h], m, **L)
        for x, y in ((x0 + 4, y0 + 4), (x1 - 8, y0 + 4), (x0 + 4, y1 - 8), (x1 - 8, y1 - 8)):
            box([x, y, 0, x + 4, y + 4, h - 4], 'oakdark', **L)
        self.piece(n, [x0, y0, 0, x1, y1, h], 'oak')

    def block(self, n, r, h, m='oak', built=False, mt=None):   # r: [x0,y0,x1,y1] on the floor, h: height
        b = [r[0], r[1], 0, r[2], r[3], h]
        self.box(b, m, **(self.B if built else self.L))
        self.piece(n, b, mt)

    def chair(self, cx, cy, facing):
        box, L = self.box, self.L
        box([cx - 22, cy - 22, 0, cx + 22, cy + 22, 46], 'fabric', **L)
        b = {'l': [cx + 18, cy - 22, 46, cx + 22, cy + 22, 88], 'r': [cx - 22, cy - 22, 46, cx - 18, cy + 22, 88],
             't': [cx - 22, cy + 18, 46, cx + 22, cy + 22, 88], 'b': [cx - 22, cy - 22, 46, cx + 22, cy - 18, 88]}[facing]
        box(b, 'fabric', **L)

    def stool(self, cx, cy, h=65):
        self.extra.append(dict(t='c', c=[cx, cy], r=18, z=[h - 5, h], m='fabric', f='loose'))
        self.extra.append(dict(t='c', c=[cx, cy], r=3, z=[0, h - 5], m='black', f='loose'))

    def side_table(self, cx, cy, r, h):   # round: top and stem
        self.extra.append(dict(t='c', c=[cx, cy], r=r, z=[h - 3, h], m='oak', f='loose'))
        self.extra.append(dict(t='c', c=[cx, cy], r=3, z=[0, h - 3], m='black', f='loose'))

    def rug(self, cx, cy, r):
        self.extra.append(dict(t='c', c=[cx, cy], r=r, z=[1, 2], m='rug', f='loose'))

    def pendant(self, cx, cy):
        self.extra.append(dict(t='l', c=[cx, cy], z=170, st='dome'))

    def vanity(self, x0, y0, x1, y1):
        self.box([x0 + 2, y0 + 2, 0, x1 - 2, y1, 85], 'white', **self.B); self.box([x0, y0, 85, x1, y1, 88], 'travertine', **self.B)
        self.piece('Vanity', [x0, y0, 0, x1, y1, 88], 'basin on a stone top')

    def wc(self, x0, y0, x1, y1, back):
        self.box([x0, y0, 0, x1, y1, 40], 'ceramic', **self.B)
        bk = {'l': [x0 - 2, y0 + 4, 40, x0 + 14, y1 - 4, 80], 'b': [x0 + 2, y1 - 12, 40, x1 - 2, y1, 80], 't': [x0 + 2, y0, 40, x1 - 2, y0 + 12, 80]}[back]
        self.box(bk, 'ceramic', **self.B)
        self.piece('WC', [x0, y0, 0, x1, y1, 80])

    def bath(self, x0, y0, x1, y1):
        self.box([x0, y0, 0, x1, y1, 55], 'ceramic', **self.B)
        self.piece('Bath', [x0, y0, 0, x1, y1, 55], 'bath')

    def shower(self, x0, y0, x1, y1, screen):   # screen: [x0,y0,x1,y1] of the glass
        self.box([x0, y0, 0, x1, y1, 5], 'stone', **self.B)
        self.box(screen[:2] + [5] + screen[2:] + [200], 'glass', **self.B)
        self.piece('Shower', [x0, y0, 0, x1, y1, 200], 'tray and glass screen')

    def counter(self, x0, y0, x1, y1, uppers=None):
        self.box([x0, y0, 0, x1, y1, 88], 'white', **self.B); self.box([x0, y0, 88, x1, y1, 92], 'quartz', **self.B)
        if uppers: self.box(uppers[:2] + [145] + uppers[2:] + [215], 'white', **self.B)

    def hob(self, x0, y0, x1, y1):
        self.box([x0, y0, 92, x1, y1, 93], 'black', **self.B)

    def sink(self, x0, y0, x1, y1):
        self.box([x0, y0, 86, x1, y1, 92], 'steel', **self.B)

    def fridge(self, x0, y0, x1, y1):
        self.box([x0, y0, 0, x1, y1, 215], 'steel', **self.B)
        self.piece('Fridge', [x0, y0, 0, x1, y1, 215], 'tall unit')

    def tv(self, x0, y0, x1, y1, screen):
        self.box([x0, y0, 0, x1, y1, 50], 'oakdark', **self.B); self.box(screen, 'black', **self.L)
        self.piece('TV unit', [x0, y0, 0, x1, y1, screen[5]])

    def terrace(self):
        for x in (1390, 1490):
            self.box([x, 70, 0, x + 50, 120, 42], 'fabric', **self.L)
        self.side_table(1460, 140, 22, 55)


def furnish_existing(F):
    """source/original_with_furn.pdf"""
    box, L, B, piece = F.box, F.L, F.B, F.piece
    # master bedroom: king bed on the right wall, dressing behind a partition on the left
    F.bed('Master bed', 752, 196, 956, 372, 'r')
    for y in (146, 380):
        box([912, y, 0, 956, y + 44, 50], 'oak', **L)
    box([591, 194, 0, 606, 480, 240], 'white', **B); piece('Dressing partition', [591, 194, 0, 606, 480, 240])
    F.wardrobe('Dressing wardrobes', 442, 244, 502, 480)
    box([472, 110, 0, 530, 168, 45], 'fabric', **L); piece('Ottoman', [472, 110, 0, 530, 168, 45])
    # bedroom 1: double bed against the left wall, wardrobe along the wall to bedroom 2
    F.bed('Bed', 70, 384, 274, 548, 'l')
    for y in (342, 552):
        box([70, y, 0, 112, y + 34, 50], 'oak', **L)
    F.wardrobe('Wardrobe', 70, 626, 400, 686)
    # bedroom 2: two single beds, headboards to the bottom wall, wardrobe on the top wall
    F.bed('Single bed', 118, 868, 221, 1058, 'b')
    F.bed('Single bed', 279, 868, 382, 1058, 'b')
    box([228, 1016, 0, 272, 1056, 50], 'oak', **L)
    F.wardrobe('Wardrobe', 72, 696, 308, 756)
    # master bathroom: vanity on the top wall, WC on the left, bath along the bottom
    box([258, 66, 0, 428, 118, 85], 'white', **B); box([256, 64, 85, 430, 120, 88], 'travertine', **B)
    box([310, 70, 88, 360, 110, 100], 'ceramic', **B); piece('Vanity', [256, 64, 0, 430, 120, 100], 'basin on a stone top')
    box([256, 172, 0, 292, 214, 40], 'ceramic', **B); box([254, 176, 40, 270, 210, 80], 'ceramic', **B); piece('WC', [254, 172, 0, 292, 214, 80])
    box([256, 236, 0, 428, 303, 55], 'ceramic', **B); piece('Bath', [256, 236, 0, 428, 303, 55], '1.70 m bath')
    # bathroom 1: basin counter, WC, bath on the right
    box([554, 720, 0, 654, 788, 85], 'white', **B); box([554, 718, 85, 654, 788, 88], 'travertine', **B); piece('Vanity', [554, 718, 0, 654, 788, 88])
    box([682, 742, 0, 718, 788, 40], 'ceramic', **B); box([684, 776, 40, 716, 788, 80], 'ceramic', **B); piece('WC', [682, 742, 0, 718, 788, 80])
    box([726, 622, 0, 796, 788, 55], 'ceramic', **B); piece('Bath', [726, 622, 0, 796, 788, 55], '1.70 m bath')
    # guest bathroom
    box([906, 620, 0, 964, 690, 85], 'white', **B); box([904, 620, 85, 964, 692, 88], 'travertine', **B); piece('Vanity', [904, 620, 0, 964, 692, 88])
    box([832, 742, 0, 868, 788, 40], 'ceramic', **B); box([834, 776, 40, 866, 788, 80], 'ceramic', **B); piece('WC', [832, 742, 0, 868, 788, 80])
    # kitchen: a run on the top wall with the hob, a run on the window wall with the sink, a tall fridge
    box([980, 620, 0, 1214, 680, 88], 'white', **B); box([980, 620, 88, 1214, 682, 92], 'quartz', **B)
    box([1060, 630, 92, 1140, 668, 93], 'black', **B)
    box([980, 620, 145, 1214, 655, 215], 'white', **B)
    box([980, 680, 0, 1040, 958, 88], 'white', **B); box([980, 680, 88, 1042, 958, 92], 'quartz', **B)
    box([990, 852, 86, 1030, 916, 92], 'steel', **B)
    box([1150, 682, 0, 1214, 750, 215], 'steel', **B)
    piece('Kitchen', [980, 620, 0, 1214, 958, 215], 'white lacquer, quartz worktop')
    # maid's room: single bed along the bottom wall
    F.bed('Single bed', 994, 1044, 1172, 1130, 'l')
    # reception: a three-seat sofa on the left, two armchairs under the window, a two-seat sofa, coffee table
    F.sofa('Sofa, 3 seats', 984, 157, 1059, 396, 'l')
    F.sofa('Sofa, 2 seats', 1059, 400, 1216, 475, 'b')
    for x0 in (1073, 1184):
        box([x0, 82, 0, x0 + 75, 154, 42], 'fabric', **L); box([x0, 82, 0, x0 + 75, 98, 78], 'fabric', **L)
        piece('Armchair', [x0, 82, 0, x0 + 75, 154, 78], 'fabric')
    box([1126, 214, 0, 1194, 332, 38], 'oak', **L); piece('Coffee table', [1126, 214, 0, 1194, 332, 38])
    F.rug(1095, 285, 95)
    F.side_table(1018, 118, 26, 50)
    # living: TV wall, lounge chair, sofa facing it
    box([1300, 168, 0, 1316, 346, 50], 'oakdark', **B); box([1306, 190, 80, 1310, 330, 155], 'black', **L)
    piece('TV unit', [1300, 168, 0, 1316, 346, 155])
    F.sofa('Sofa', 1469, 279, 1548, 436, 'r')
    box([1408, 196, 0, 1484, 272, 42], 'fabric', **L); box([1408, 196, 0, 1484, 210, 78], 'fabric', **L); piece('Lounge chair', [1408, 196, 0, 1484, 272, 78])
    F.side_table(1495, 238, 25, 50)
    box([1398, 321, 0, 1441, 368, 40], 'oak', **L); piece('Side table', [1398, 321, 0, 1441, 368, 40])
    # dining: table for six
    F.table('Dining table', 1378, 574, 1478, 744)
    for y in (615, 690): F.chair(1356, y, 'r'); F.chair(1500, y, 'l')
    F.chair(1428, 552, 't'); F.chair(1428, 766, 'b')
    F.pendant(1428, 615); F.pendant(1428, 705)
    F.terrace()
    return F.done()


def furnish_o1(F):
    """source/option_1_with_furn.pdf"""
    # master bedroom (bedroom 1 on the as-built plan): bed on the wall to bedroom 2, dressing area behind
    F.bed('Master bed', 160, 480, 320, 682, 'b')
    F.bedside(72, 630, 150, 682); F.bedside(328, 630, 400, 682)
    F.wardrobe('Dressing wardrobes', 512, 160, 570, 480)
    # master bathroom: shower under the window wall, WC on the left, vanity along the bottom
    F.shower(256, 66, 428, 150, [256, 148, 428, 150])
    F.wc(254, 172, 292, 214, 'l')
    F.vanity(256, 248, 428, 303)
    # kitchen: two runs facing each other, open to the corridor; a breakfast table at the open end
    F.counter(645, 92, 730, 330); F.sink(660, 175, 715, 245)
    F.fridge(645, 330, 730, 415); F.counter(645, 415, 730, 488)
    F.counter(898, 92, 960, 400, uppers=[925, 92, 960, 400]); F.hob(903, 240, 955, 330)
    F.piece('Kitchen', [645, 92, 0, 960, 488, 215], 'two runs, white lacquer, quartz worktop')
    F.table('Breakfast table', 795, 420, 890, 488)
    F.stool(815, 405); F.stool(865, 405)
    # bedroom 2: one bed against the far wall, a desk under the window wall, wardrobe on the top wall
    F.bed('Bed', 298, 842, 418, 1056, 'b')
    F.table('Desk', 80, 990, 230, 1056)
    F.bedside(238, 1000, 290, 1056)
    F.wardrobe('Wardrobe', 72, 696, 308, 756)
    # corridor: a tall cupboard in the old bedroom 2 entry
    F.wardrobe('Cupboard', 552, 608, 620, 780, h=220)
    # the shared bathroom: shower, washing machine, WC, vanity
    F.shower(638, 622, 735, 788, [733, 622, 735, 788])
    F.block('Washing machine', [740, 728, 800, 788], 85, 'white', built=True)
    F.wc(832, 742, 868, 788, 'b')
    F.vanity(905, 620, 964, 780)
    # storage in the maid's room, a sideboard where the kitchen was
    F.wardrobe('Storage shelves', 980, 976, 1214, 1020, h=220)
    F.block('Sideboard', [995, 900, 1215, 958], 90, 'white', built=True)
    # reception: a corner sofa round the coffee table, a two-seat sofa facing it
    F.sofa('Corner sofa', 985, 175, 1060, 415, 'l')
    F.sofa('Corner sofa', 1060, 92, 1245, 170, 't')
    F.block('Coffee table', [1130, 240, 1210, 395], 38, mt='oak')
    F.rug(1150, 300, 100)
    F.sofa('Sofa, 2 seats', 1110, 448, 1260, 520, 'b')
    F.block('Side table', [1050, 452, 1095, 495], 50)
    F.block('Ottoman', [1320, 262, 1365, 305], 42, 'fabric'); F.block('Ottoman', [1320, 320, 1365, 365], 42, 'fabric')
    # living: TV on the right-hand wall, a sofa facing back across the room, a console by the entrance
    F.tv(1528, 210, 1556, 390, [1530, 225, 80, 1534, 375, 155])
    F.sofa('Sofa', 1470, 540, 1545, 745, 'r')
    F.side_table(1390, 625, 28, 45)
    F.block('Console', [1395, 818, 1545, 878], 80, mt='oak')
    # dining: the table between the kitchen windows and the living area (the sheet draws no chairs)
    F.table('Dining table', 1068, 665, 1170, 825)
    for y in (700, 790): F.chair(1046, y, 'r'); F.chair(1192, y, 'l')
    F.pendant(1119, 705); F.pendant(1119, 785)
    F.terrace()
    return F.done()


def furnish_o2(F):
    """source/option_2_with_furn.pdf"""
    # master bedroom: king bed on the right wall, an L of wardrobes on the left
    F.bed('Master bed', 752, 190, 952, 350, 'r')
    F.bedside(910, 140, 955, 182); F.bedside(910, 358, 955, 400)
    F.wardrobe('Wardrobes', 442, 240, 500, 480)
    F.wardrobe('Wardrobes', 500, 425, 630, 480)
    F.block('Dressing table', [585, 225, 625, 350], 75)
    # master bathroom: as built
    F.vanity(256, 64, 430, 120)
    F.wc(254, 172, 292, 214, 'l')
    F.bath(256, 236, 428, 303)
    # bedroom 1: as built
    F.bed('Bed', 70, 384, 274, 548, 'l')
    F.bedside(70, 342, 112, 376); F.bedside(70, 552, 112, 586)
    F.wardrobe('Wardrobe', 70, 626, 400, 686)
    # bedroom 2: a sitting room or study: sofa, armchair, side table, wardrobes
    F.wardrobe('Wardrobe', 72, 696, 308, 756)
    F.wardrobe('Tall cupboard', 358, 800, 428, 955, h=220)
    F.armchair('Armchair', 75, 880, 150, 950, 'l')
    F.sofa('Sofa', 175, 975, 330, 1056, 'b')
    F.block('Side table', [90, 978, 145, 1040], 50)
    # corridor: a tall cupboard in the old bedroom 2 entry
    F.wardrobe('Cupboard', 548, 608, 620, 780, h=220)
    # the shared bathroom: bath or shower, washing machine, WC, vanity
    F.shower(638, 622, 735, 788, [733, 622, 735, 788])
    F.block('Washing machine', [740, 718, 800, 788], 85, 'white', built=True)
    F.wc(832, 742, 868, 788, 'b')
    F.vanity(905, 625, 964, 700)
    # kitchen: a run on the corridor wall with the hob, a run under the windows with the sink, an island with stools
    F.counter(980, 622, 1226, 685, uppers=[980, 622, 1226, 657]); F.hob(1072, 632, 1165, 678)
    F.counter(980, 685, 1040, 1060); F.sink(987, 850, 1032, 915)
    F.fridge(980, 1062, 1040, 1128)
    F.box([1130, 775, 0, 1225, 940, 88], 'white', **F.B); F.box([1128, 773, 88, 1228, 942, 92], 'quartz', **F.B)
    F.piece('Island', [1128, 773, 0, 1228, 942, 92], 'white lacquer, quartz top')
    for y in (800, 857, 914): F.stool(1250, y)
    F.piece('Kitchen', [980, 622, 0, 1226, 1128, 215], 'white lacquer, quartz worktop')
    # reception: as built, with the TV on a low unit facing the sofas
    F.sofa('Sofa, 3 seats', 985, 155, 1060, 395, 'l')
    F.armchair('Armchair', 1073, 85, 1138, 160, 't'); F.armchair('Armchair', 1162, 85, 1237, 160, 't')
    F.side_table(1018, 118, 26, 50)
    F.block('Coffee table', [1125, 215, 1190, 330], 38)
    F.rug(1130, 280, 95)
    F.tv(1050, 455, 1285, 498, [1120, 470, 75, 1220, 474, 140])
    # living: sofa on the right wall, ottomans, a lounge chair
    F.sofa('Sofa', 1475, 210, 1550, 360, 'r')
    F.block('Ottoman', [1300, 240, 1345, 285], 42, 'fabric'); F.block('Ottoman', [1300, 300, 1345, 345], 42, 'fabric')
    F.block('Side table', [1418, 265, 1455, 320], 50)
    F.armchair('Lounge chair', 1440, 375, 1510, 445, 'r')
    # dining: the table on the right, chairs added (the sheet draws the table only)
    F.table('Dining table', 1388, 560, 1480, 720)
    for y in (600, 680): F.chair(1366, y, 'r'); F.chair(1502, y, 'l')
    F.pendant(1434, 600); F.pendant(1434, 680)
    F.block('Console', [1390, 818, 1540, 878], 80)
    F.terrace()
    return F.done()


FURNITURE = {'existing': furnish_existing, 'o1': furnish_o1, 'o2': furnish_o2}


def lighting(lay):
    L = []
    for n, r, zn in lay['rooms']:
        w, d = r[2] - r[0], r[3] - r[1]
        if zn == 'pri':
            L.append(dict(k='ceil', p=[(r[0] + r[2]) / 2, (r[1] + r[3]) / 2]))
            continue
        nx, ny = max(1, round(w / 150)), max(1, round(d / 150))
        for i in range(nx):
            for j in range(ny):
                L.append(dict(k='down', p=[round(r[0] + w * (i + .5) / nx), round(r[1] + d * (j + .5) / ny)]))
    L.append(dict(k='shelf', pts=lay['shelf']))
    L += [dict(k='lamp', p=p) for p in lay['lamps']]
    L.append(dict(k='ext', p=[1450, 60]))
    return L


# ---------------------------------------------------------------- viewpoints (eye height 165 cm)
EYE, SIT = 165, 120
TRUE = ' Press 1:1 for true size.'
VIEWS = [   # key, button, view, plans it belongs to (None: all); z below 1 widens the view, as AZAD's room views do
    ('overview', 'Overview', dict(pos=[1750, 1900, 1350], look=[800, 600, 0], mode='overview', msg='Overview. Drag to orbit.'), None),
    ('entrance', 'Front door', dict(pos=[1310, 1050, EYE], look=[1330, 600, 120], z=.6, msg='Just inside the front door, wider than life.' + TRUE), None),
    ('dining', 'Dining', dict(pos=[1240, 870, EYE], look=[1440, 620, 85], z=.55, msg='By the dining table for six, wider than life.' + TRUE), ['existing']),
    ('dining1', 'Dining', dict(pos=[1330, 900, EYE], look=[1100, 720, 85], z=.55, msg='Towards the dining table and the kitchen windows, wider than life.' + TRUE), ['o1']),
    ('dining2', 'Dining', dict(pos=[1280, 870, EYE], look=[1440, 620, 85], z=.55, msg='By the dining table, with the kitchen island behind you, wider than life.' + TRUE), ['o2']),
    ('reception', 'Reception', dict(pos=[1290, 470, EYE], look=[1040, 170, 95], z=.55, msg='Across the reception to the window and the sofa, wider than life.' + TRUE), None),
    ('living', 'Living', dict(pos=[1530, 470, EYE], look=[1310, 230, 100], z=.55, msg='The living area, wider than life.' + TRUE), ['existing', 'o2']),
    ('living1', 'Living', dict(pos=[1300, 600, EYE], look=[1545, 300, 100], z=.55, msg='The living area and the TV wall, wider than life.' + TRUE), ['o1']),
    ('terrace', 'Terrace', dict(pos=[1450, 330, EYE], look=[1450, 60, 110], z=.6, msg='From the living area out to the terrace, wider than life.' + TRUE), None),
    ('kitchen', 'Kitchen', dict(pos=[1190, 940, EYE], look=[1040, 650, 95], z=.55, msg='The kitchen, wider than life: hob on the far wall, sink under the window.' + TRUE), ['existing']),
    ('kitchen1', 'Kitchen', dict(pos=[810, 570, EYE], look=[810, 150, 95], z=.55, msg='From the corridor into the kitchen, wider than life: the sink run on the left, the hob on the right.' + TRUE), ['o1']),
    ('kitchen2', 'Kitchen', dict(pos=[1340, 990, EYE], look=[1050, 720, 90], z=.55, msg='Across the island into the kitchen, wider than life.' + TRUE), ['o2']),
    ('corridor', 'Corridor', dict(pos=[960, 555, EYE], look=[440, 555, 120], z=.7, msg='Down the bedroom corridor.'), None),
    ('master', 'Master bedroom', dict(pos=[640, 470, EYE], look=[900, 250, 90], z=.55, msg='Master bedroom from the door, wider than life.' + TRUE), ['existing']),
    ('master1', 'Master bedroom', dict(pos=[505, 330, EYE], look=[230, 600, 80], z=.55, msg='From the dressing area into the master bedroom, wider than life.' + TRUE), ['o1']),
    ('master2', 'Master bedroom', dict(pos=[690, 470, EYE], look=[900, 250, 90], z=.55, msg='Master bedroom from the door, wider than life.' + TRUE), ['o2']),
    ('bed1', 'Bedroom 1', dict(pos=[415, 670, EYE], look=[110, 400, 90], z=.55, msg='Bedroom 1 from the wardrobe corner, wider than life.' + TRUE), ['existing', 'o2']),
    ('bed2', 'Bedroom 2', dict(pos=[400, 760, EYE], look=[150, 1000, 80], z=.55, msg='Bedroom 2, wider than life.' + TRUE), None),
    ('bath', 'Bathroom', dict(pos=[590, 640, EYE], look=[720, 780, 90], z=.5, msg='Bathroom 1, wider than life.' + TRUE), ['existing']),
    ('bath1', 'Bathroom', dict(pos=[845, 635, EYE], look=[680, 770, 90], z=.5, msg='The shared bathroom from the door, wider than life.' + TRUE), ['o1']),
    ('bath2', 'Bathroom', dict(pos=[895, 745, EYE], look=[660, 690, 90], z=.5, msg='The shared bathroom, wider than life: the shower at the far end.' + TRUE), ['o2']),
]


def all_data(azad_all):
    """The ALL object the viewer reads, keeping AZAD's furniture catalogue, textures and lighting scenes."""
    return dict(
        layouts={k: build(k) for k in ORDER}, default='existing', art={}, changes=[], ba={},
        tex=azad_all.get('tex', {}),
        scenes=[["Day", "Ceiling lights off, kitchen under-cupboard light on."],
                ["Cooking", "Kitchen downlights 100 %, under-cupboard light 100 %."],
                ["Dinner / hosting", "Dining pendants 60 %, reception 50 %, kitchen 20 %."],
                ["Film", "Everything off except a low wash in the living area."],
                ["Night path", "Corridor downlights 5 %, everything else off."],
                ["All off", "One press by the front door as you leave."]],
        preview=False, fcat=azad_all.get('fcat', []), fin=[], furnish={}, context=[]), OUTLINE


if __name__ == '__main__':
    d, _ = all_data({})
    for k in ORDER:
        L = d['layouts'][k]
        print('%-8s %4d items, %2d rooms, %2d lights  %s' % (k, len(L['items']), len(L['rooms']), len(L['lights']), L['name']))
