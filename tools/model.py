"""The Creektown apartment as a 3D model, in the data format of the AZAD walkthrough (kamelshenouda/azad).

Everything is in plan centimetres: x to the right, y down, z up from the finished floor, on the turned sheet used by
tools/extract_walls.py. Walls come from data/walls.json (the architect's PDF); the openings, rooms and furniture below
were read off source/original_empty.pdf and source/original_with_furn.pdf on a 1 cm grid.

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

# ---------------------------------------------------------------- openings
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
DOORS = [
    # name,              rect,                    axis, hinge end, swing (+1/-1 across the wall), leaf material
    ('Master bedroom door', [613, 480, 699, 508],  'x', 0, -1, 'white'),
    ('Bedroom 1 door',      [418, 511, 448, 595],  'y', 1, -1, 'white'),
    ('Bedroom 2 door',      [447, 600, 531, 626],  'x', 1, +1, 'white'),
    ('Bathroom door',       [568, 600, 642, 626],  'x', 0, +1, 'white'),
    ('Guest bath door',     [821, 600, 894, 626],  'x', 0, +1, 'white'),
    ('Master bath door',    [418, 152, 448, 234],  'y', 0, -1, 'white'),
    ('Maid\'s room door',   [1125, 954, 1203, 980], 'x', 1, +1, 'white'),
    ('Front door',          [1257, 1058, 1366, 1098], 'x', 0, -1, 'oakdark'),
]
OPENINGS = [  # no leaf
    ('Kitchen opening', [1205, 850, 1242, 940], 'y', DOOR_HEAD),
]

# ---------------------------------------------------------------- rooms (interior, cm) and their floor zone
# zones: pub (reception), cir (circulation), pri (bedrooms), wetz (wet rooms), ser (service)
ROOMS = [
    ('Master bathroom', [252, 62, 430, 305],  'wetz'),
    ('Master bedroom',  [438, 88, 962, 492],  'pri'),
    ('Bedroom 1',       [67, 318, 428, 686],  'pri'),
    ('Bedroom 2',       [67, 694, 430, 1062], 'pri'),
    ('Bedroom 2 entry', [440, 618, 548, 792], 'pri'),
    ('Corridor',        [440, 498, 1218, 610], 'cir'),
    ('Bathroom 1',      [552, 618, 798, 790], 'wetz'),
    ('Guest bathroom',  [810, 618, 966, 790], 'wetz'),
    ('Kitchen',         [978, 618, 1216, 962], 'ser'),
    ('Maid\'s room',    [978, 972, 1216, 1132], 'ser'),
    ('Reception',       [972, 66, 1300, 480], 'pub'),
    ('Living',          [1300, 192, 1562, 480], 'pub'),
    ('Dining',          [1218, 480, 1562, 888], 'pub'),
    ('Entrance',        [1230, 888, 1380, 1064], 'cir'),
]
TERRACE = ('Terrace', [1340, 40, 1560, 172])
FLOOR_M = {'pub': 'porcelain', 'cir': 'porcelain', 'pri': 'oakfloor', 'wetz': 'stone', 'ser': 'porcelain'}

# where the labels sit and how the rooms read on the plan (the open space is one room on the architect's sheet)
LABELS = [  # label, the room it measures, where it sits
    ('Master bath', 'Master bathroom', 340, 185), ('Master bedroom', 'Master bedroom', 700, 300),
    ('Bedroom 1', 'Bedroom 1', 250, 500), ('Bedroom 2', 'Bedroom 2', 250, 880), ('Corridor', 'Corridor', 700, 555),
    ('Bathroom 1', 'Bathroom 1', 675, 705), ('Guest bath', 'Guest bathroom', 888, 705), ('Kitchen', 'Kitchen', 1097, 790),
    ('Maid\'s room', 'Maid\'s room', 1097, 1050), ('Reception', 'Reception', 1135, 270), ('Living', 'Living', 1430, 330),
    ('Dining', 'Dining', 1430, 655), ('Entrance', 'Entrance', 1305, 975), ('Terrace', 'Terrace', 1450, 105),
]


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


def build():
    walls = json.load(open(os.path.join(ROOT, 'data', 'walls.json')))['rects']
    solid = [dict(r=w[:4], kind=w[4]) for w in walls]
    items, pieces = [], []

    def box(b, m, **kw):
        it = dict(t='b', b=[round(v, 1) for v in b], m=m); it.update(kw); items.append(it); return it

    # every opening cuts the walls it crosses; what lies inside keeps a sill and a lintel
    cuts = ([(n, r, a, s, h, 'win', p) for n, r, a, s, h, p in WINDOWS]
            + [(n, r, a, 0, WIN_HEAD, 'slide', 0) for n, r, a in SLIDERS]
            + [(n, r, a, 0, DOOR_HEAD + (10 if n == 'Front door' else 0), 'door', 0) for n, r, a, *_ in DOORS]
            + [(n, r, a, 0, h, 'open', 0) for n, r, a, h in OPENINGS])
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
    for n, o, axis, hinge, swing, m in DOORS:
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
    rooms = []
    for n, r, zn in ROOMS:
        box([r[0], r[1], 0, r[2], r[3], 1], FLOOR_M[zn], g='floor', zn=zn)
        box([r[0], r[1], H - 1, r[2], r[3], H], 'ceiling', g='ceiling')
    tn, tr = TERRACE
    box([tr[0], tr[1], 0, tr[2], tr[3], 1], 'oak', g='floor')
    rect = dict((n, r) for n, r, _ in ROOMS); rect[tn] = tr
    for n, rn, x, y in LABELS:
        r = rect[rn]
        rooms.append(dict(n=n, at=[x, y], r=r, d='%.2f × %.2f' % ((r[2] - r[0]) / 100, (r[3] - r[1]) / 100)))
    furn, extra = furniture(box)
    items += extra
    lights = lighting()
    labels = [[n, x, y] for n, _, x, y in LABELS]
    outline = [[195, 10], [1590, 10], [1590, 915], [1410, 915], [1410, 1150], [950, 1150], [950, 815], [455, 815],
               [455, 1160], [10, 1160], [10, 262], [195, 262]]
    return dict(items=items, labels=labels, rooms=rooms, pieces=pieces + furn, lights=lights, garden=[[0, 0], [0, 0], [0, 0]],
                site=[-150, -150, 1750, 1320], name='As built · architect\'s furniture', outline=outline)


def furniture(box):
    """The architect's furniture layout (source/original_with_furn.pdf), as simple blocks."""
    P = []
    def piece(n, b, mt=None):
        d = dict(n=n, b=b)
        if mt: d['mt'] = mt
        P.append(d)
    L = dict(f='loose'); B = dict(f='built')

    def bed(n, x0, y0, x1, y1, head):   # head: 'l','r','t','b' — the side the headboard is on
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
        piece(n, [x0, y0, 0, x1, y1, 105], 'upholstered bed')

    def wardrobe(n, x0, y0, x1, y1):
        box([x0, y0, 0, x1, y1, 240], 'white', **B)
        piece(n, [x0, y0, 0, x1, y1, 240], 'built-in wardrobe')

    def sofa(n, x0, y0, x1, y1, back):   # back: side of the backrest
        box([x0, y0, 0, x1, y1, 42], 'fabric', **L)
        bk = {'l': [x0, y0, 0, x0 + 20, y1, 80], 'r': [x1 - 20, y0, 0, x1, y1, 80], 't': [x0, y0, 0, x1, y0 + 20, 80], 'b': [x0, y1 - 20, 0, x1, y1, 80]}[back]
        box(bk, 'fabric', **L)
        if back in 'lr':
            box([x0, y0, 0, x1, y0 + 16, 62], 'fabric', **L); box([x0, y1 - 16, 0, x1, y1, 62], 'fabric', **L)
        else:
            box([x0, y0, 0, x0 + 16, y1, 62], 'fabric', **L); box([x1 - 16, y0, 0, x1, y1, 62], 'fabric', **L)
        piece(n, [x0, y0, 0, x1, y1, 80], 'fabric sofa')

    def table(n, x0, y0, x1, y1, h=75, m='oak'):
        box([x0, y0, h - 4, x1, y1, h], m, **L)
        for x, y in ((x0 + 4, y0 + 4), (x1 - 8, y0 + 4), (x0 + 4, y1 - 8), (x1 - 8, y1 - 8)):
            box([x, y, 0, x + 4, y + 4, h - 4], 'oakdark', **L)
        piece(n, [x0, y0, 0, x1, y1, h], 'oak')

    def chair(cx, cy, facing):
        box([cx - 22, cy - 22, 0, cx + 22, cy + 22, 46], 'fabric', **L)
        b = {'l': [cx + 18, cy - 22, 46, cx + 22, cy + 22, 88], 'r': [cx - 22, cy - 22, 46, cx - 18, cy + 22, 88],
             't': [cx - 22, cy + 18, 46, cx + 22, cy + 22, 88], 'b': [cx - 22, cy - 22, 46, cx + 22, cy - 18, 88]}[facing]
        box(b, 'fabric', **L)

    def items_c(cx, cy, r, h):   # a round side table: top and stem
        box_list.append(dict(t='c', c=[cx, cy], r=r, z=[h - 3, h], m='oak', f='loose'))
        box_list.append(dict(t='c', c=[cx, cy], r=3, z=[0, h - 3], m='black', f='loose'))

    box_list = []

    # master bedroom: king bed on the right wall, dressing behind a partition on the left
    bed('Master bed', 752, 196, 956, 372, 'r')
    for y in (146, 380):
        box([912, y, 0, 956, y + 44, 50], 'oak', **L)
    box([591, 194, 0, 606, 480, 240], 'white', **B); piece('Dressing partition', [591, 194, 0, 606, 480, 240])
    wardrobe('Dressing wardrobes', 442, 244, 502, 480)
    box([472, 110, 0, 530, 168, 45], 'fabric', **L); piece('Ottoman', [472, 110, 0, 530, 168, 45])
    # bedroom 1: double bed against the left wall, wardrobe along the wall to bedroom 2
    bed('Bed', 70, 384, 274, 548, 'l')
    for y in (342, 552):
        box([70, y, 0, 112, y + 34, 50], 'oak', **L)
    wardrobe('Wardrobe', 70, 626, 400, 686)
    # bedroom 2: two single beds, headboards to the bottom wall, wardrobe on the top wall
    bed('Single bed', 118, 868, 221, 1058, 'b')
    bed('Single bed', 279, 868, 382, 1058, 'b')
    box([228, 1016, 0, 272, 1056, 50], 'oak', **L)
    wardrobe('Wardrobe', 72, 696, 308, 756)
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
    bed('Single bed', 994, 1044, 1172, 1130, 'l')
    # reception: a three-seat sofa on the left, two armchairs under the window, a two-seat sofa, coffee table
    sofa('Sofa, 3 seats', 984, 157, 1059, 396, 'l')
    sofa('Sofa, 2 seats', 1059, 400, 1216, 475, 'b')
    for x0 in (1073, 1184):
        box([x0, 82, 0, x0 + 75, 154, 42], 'fabric', **L); box([x0, 82, 0, x0 + 75, 98, 78], 'fabric', **L)
        piece('Armchair', [x0, 82, 0, x0 + 75, 154, 78], 'fabric')
    box([1126, 214, 0, 1194, 332, 38], 'oak', **L); piece('Coffee table', [1126, 214, 0, 1194, 332, 38])
    box_list.append(dict(t='c', c=[1095, 285], r=95, z=[1, 2], m='rug', f='loose'))
    items_c(1018, 118, 26, 50)
    # living: TV wall, lounge chair, sofa facing it
    box([1300, 168, 0, 1316, 346, 50], 'oakdark', **B); box([1306, 190, 80, 1310, 330, 155], 'black', **L)
    piece('TV unit', [1300, 168, 0, 1316, 346, 155])
    sofa('Sofa', 1469, 279, 1548, 436, 'r')
    box([1408, 196, 0, 1484, 272, 42], 'fabric', **L); box([1408, 196, 0, 1484, 210, 78], 'fabric', **L); piece('Lounge chair', [1408, 196, 0, 1484, 272, 78])
    items_c(1495, 238, 25, 50)
    box([1398, 321, 0, 1441, 368, 40], 'oak', **L); piece('Side table', [1398, 321, 0, 1441, 368, 40])
    # dining: table for six
    table('Dining table', 1378, 574, 1478, 744)
    for y in (615, 690): chair(1356, y, 'r'); chair(1500, y, 'l')
    chair(1428, 552, 't'); chair(1428, 766, 'b')
    box_list.append(dict(t='l', c=[1428, 615], z=170, st='dome'))
    box_list.append(dict(t='l', c=[1428, 705], z=170, st='dome'))
    # terrace: two chairs and a small table
    for x in (1390, 1490):
        box([x, 70, 0, x + 50, 120, 42], 'fabric', **L)
    items_c(1460, 140, 22, 55)

    return P, box_list


def lighting():
    L = []
    for n, r, zn in ROOMS:
        w, d = r[2] - r[0], r[3] - r[1]
        if zn == 'pri':
            L.append(dict(k='ceil', p=[(r[0] + r[2]) / 2, (r[1] + r[3]) / 2]))
            continue
        nx, ny = max(1, round(w / 150)), max(1, round(d / 150))
        for i in range(nx):
            for j in range(ny):
                L.append(dict(k='down', p=[round(r[0] + w * (i + .5) / nx), round(r[1] + d * (j + .5) / ny)]))
    L += [dict(k='shelf', pts=[[982, 652], [1212, 652]]), dict(k='lamp', p=[1520, 250]), dict(k='lamp', p=[1035, 120]),
          dict(k='ext', p=[1450, 60])]
    return L


# ---------------------------------------------------------------- viewpoints (eye height 165 cm)
EYE, SIT = 165, 120
VIEWS = [   # z: zoom below 1 widens the view beyond true size, as AZAD's room views do
    ('overview', 'Overview', dict(pos=[1750, 1900, 1350], look=[800, 600, 0], mode='overview', msg='Overview. Drag to orbit.')),
    ('entrance', 'Front door', dict(pos=[1310, 1050, EYE], look=[1330, 600, 120], z=.6, msg='Just inside the front door, wider than life: the dining area ahead, the kitchen on the left. Press 1:1 for true size.')),
    ('dining', 'Dining', dict(pos=[1240, 870, EYE], look=[1440, 620, 85], z=.55, msg='By the dining table for six, wider than life. Press 1:1 for true size.')),
    ('reception', 'Reception', dict(pos=[1290, 470, EYE], look=[1040, 170, 95], z=.55, msg='Across the reception to the window and the three-seat sofa, wider than life. Press 1:1 for true size.')),
    ('living', 'Living', dict(pos=[1530, 470, EYE], look=[1310, 230, 100], z=.55, msg='The living area, facing the TV wall, wider than life. Press 1:1 for true size.')),
    ('terrace', 'Terrace', dict(pos=[1450, 330, EYE], look=[1450, 60, 110], z=.6, msg='From the living area out to the terrace, wider than life. Press 1:1 for true size.')),
    ('kitchen', 'Kitchen', dict(pos=[1190, 940, EYE], look=[1040, 650, 95], z=.55, msg='The kitchen, wider than life: hob on the far wall, sink under the window. Press 1:1 for true size.')),
    ('corridor', 'Corridor', dict(pos=[960, 555, EYE], look=[440, 555, 120], z=.7, msg='Down the bedroom corridor.')),
    ('master', 'Master bedroom', dict(pos=[640, 470, EYE], look=[900, 250, 90], z=.55, msg='Master bedroom from the door, wider than life. Press 1:1 for true size.')),
    ('bed1', 'Bedroom 1', dict(pos=[415, 670, EYE], look=[110, 400, 90], z=.55, msg='Bedroom 1 from the wardrobe corner, wider than life. Press 1:1 for true size.')),
    ('bed2', 'Bedroom 2', dict(pos=[400, 760, EYE], look=[150, 1000, 80], z=.55, msg='Bedroom 2, wider than life. Press 1:1 for true size.')),
    ('bath', 'Bathroom', dict(pos=[590, 640, EYE], look=[720, 780, 90], z=.5, msg='Bathroom 1, wider than life. Press 1:1 for true size.')),
]


def all_data(azad_all):
    """The ALL object the viewer reads, keeping AZAD's furniture catalogue, textures and lighting scenes."""
    L = build()
    outline = L.pop('outline')
    return dict(
        layouts={'existing': L}, default='existing', art={}, changes=[], ba={},
        tex=azad_all.get('tex', {}),
        scenes=[["Day", "Ceiling lights off, kitchen under-cupboard light on."],
                ["Cooking", "Kitchen downlights 100 %, under-cupboard light 100 %."],
                ["Dinner / hosting", "Dining pendants 60 %, reception 50 %, kitchen 20 %."],
                ["Film", "Everything off except a low wash in the living area."],
                ["Night path", "Corridor downlights 5 %, everything else off."],
                ["All off", "One press by the front door as you leave."]],
        preview=False, fcat=azad_all.get('fcat', []), fin=[], furnish={}, context=[]), outline


if __name__ == '__main__':
    d, _ = all_data({})
    L = d['layouts']['existing']
    print(len(L['items']), 'items,', len(L['rooms']), 'rooms,', len(L['lights']), 'lights')
