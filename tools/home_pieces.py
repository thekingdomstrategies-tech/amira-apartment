"""Amira's own furniture, drawn from her photos (Nov 2026), for Option 3.

Every piece is built from boxes (the viewer merges them by material), at the sizes she gave:

  - the kitchen: grey painted frame-and-panel doors, arched on the wall units, glass doors with glazing bars, bar
    handles, drawer stacks, a speckled grey granite worktop (photos of her kitchen);
  - the mahogany wall unit, re-used as the master wardrobe: raised-panel doors, a carved band of diamonds, upper
    cupboards, fluted trims, a cornice and brass handles; its dressing table with drawers and a framed mirror;
  - the mahogany bed with its panelled headboard and footboard;
  - the 2.00 sofa (taupe, rolled arms, loose cushions), the 1.40 sofa (grey, rolled arms, a white throw), the two
    poufs, and the new 2.80 sofa from the showroom (beige, three pieces, white piping);
  - the black upright piano.

A face is one side of a cabinet run: `u` runs along it, `z` up, and `t` is the distance out from its plane.
"""


class Face:
    def __init__(self, F, axis, plane, out, f='built'):
        """axis: 'x' if the face looks along x (its plane is x = plane), 'y' if along y; out: +1 or -1."""
        self.F, self.axis, self.p, self.d, self.f = F, axis, plane, out, f

    def rect(self, u0, u1, z0, z1, t0, t1, m):
        a, b = self.p + self.d * t0, self.p + self.d * t1
        lo, hi = min(a, b), max(a, b)
        u0, u1 = min(u0, u1), max(u0, u1)
        if self.axis == 'x':
            self.F.box([lo, u0, z0, hi, u1, z1], m, f=self.f)
        else:
            self.F.box([u0, lo, z0, u1, hi, z1], m, f=self.f)


GAP = .3        # between doors and drawers
DARK = {'mahog': 'mahogd', 'kgrey': 'kgreyd'}   # the shadowed groove round a raised panel


def handle_v(fc, u, z0, z1, t, m='steel'):
    fc.rect(u - .6, u + .6, z0, z1, t, t + 1.6, m)


def handle_h(fc, u0, u1, z, t, m='steel'):
    fc.rect(u0, u1, z - .6, z + .6, t, t + 1.6, m)


RISE, STRIPS = 5, 18     # the arched heads: how far the arch rises, and the strips that draw its curve


def _arc(u, uc, half):
    """0 at the ends of the arch, 1 at its crown: a circular segment."""
    k = (u - uc) / half
    return max(0., 1 - k * k) ** .5


def arch_strips(fc, u0, u1, z_base, z_top_extra, t0, t1, m, grow=0.):
    """A curved head drawn as thin vertical strips: from z_base up to z_base + RISE * arc(u) + z_top_extra. The strips
    take the finish's unbevelled twin (m + 'a'), so they read as one curved surface."""
    m = m + 'a' if m in ('kgrey', 'kgreyd', 'mahog', 'mahogd') else m
    uc, half = (u0 + u1) / 2, (u1 - u0) / 2 + grow
    n = STRIPS
    for i in range(n):
        a, b = u0 + (u1 - u0) * i / n, u0 + (u1 - u0) * (i + 1) / n
        h = RISE * _arc((a + b) / 2, uc, half) + z_top_extra
        if h > .05:
            fc.rect(a, b, z_base, z_base + h, t0, t1, m)


def panel_door(fc, u0, u1, z0, z1, m, hinge='l', arch=False, hz=None, hm='steel', knob=False):
    """A frame-and-panel door: the slab, its raised panel (with an arched head if asked), and a handle on the side
    away from the hinge (hinge: 'l' / 'r' along u, or None for no handle). hz: the handle's height, z0..z1 centre if
    not given."""
    u0, u1, z0, z1 = u0 + GAP, u1 - GAP, z0 + GAP, z1 - GAP
    fc.rect(u0, u1, z0, z1, 0, 2, m)
    w, h = u1 - u0, z1 - z0
    mg = min(7, w * .16, h * .16)
    top = z1 - mg - (RISE if arch else 0)
    if m in DARK:
        fc.rect(u0 + mg - 1.2, u1 - mg + 1.2, z0 + mg - 1.2, top + 1.2, 2, 2.15, DARK[m])
        if arch:
            arch_strips(fc, u0 + mg - 1.2, u1 - mg + 1.2, top + 1.2, 0, 2, 2.15, DARK[m], grow=1.2)
    fc.rect(u0 + mg, u1 - mg, z0 + mg, top, 2, 2.8, m)
    if arch:     # the arched head, a smooth curve
        arch_strips(fc, u0 + mg, u1 - mg, top, 0, 2, 2.8, m)
    if hinge:
        u = u1 - 3.5 if hinge == 'l' else u0 + 3.5
        zc = hz if hz is not None else (z0 + z1) / 2
        if knob:
            fc.rect(u - 1.1, u + 1.1, zc - 3, zc + 3, 2.8, 4.4, hm)
        else:
            handle_v(fc, u, zc - 6, zc + 6, 2.8, hm)


def glass_door(fc, u0, u1, z0, z1, m, hinge='l', arch=True, cols=2, rows=3, hz=None):
    """A glazed door: a 4.5 cm frame, the glass, and glazing bars (cols x rows panes)."""
    u0, u1, z0, z1 = u0 + GAP, u1 - GAP, z0 + GAP, z1 - GAP
    s = 4.5
    fc.rect(u0, u0 + s, z0, z1, 0, 2.2, m); fc.rect(u1 - s, u1, z0, z1, 0, 2.2, m)
    fc.rect(u0, u1, z0, z0 + s, 0, 2.2, m)
    gz1 = z1 - s - (RISE + 1 if arch else 0)     # the glass's top at the sides; an arch rises RISE above it
    if arch:     # the top rail, its lower edge arched: strips from the curve up to the rail
        uc, half, n = (u0 + u1) / 2, (u1 - u0 - 2 * s) / 2, STRIPS
        for i in range(n):
            a, b = u0 + s + 2 * half * i / n, u0 + s + 2 * half * (i + 1) / n
            fc.rect(a, b, gz1 + RISE * _arc((a + b) / 2, uc, half), z1, 0, 2.2, m + 'a')
    else:
        fc.rect(u0, u1, gz1, z1, 0, 2.2, m)
    fc.F.box(_g(fc, u0 + s, u1 - s, z0 + s, gz1 + (RISE if arch else 0), .9, 1.3), 'glass', g='glass', f=fc.f)
    for i in range(1, cols):
        u = u0 + s + (u1 - u0 - 2 * s) * i / cols
        fc.rect(u - .6, u + .6, z0 + s, gz1, 1, 1.9, m)
    for j in range(1, rows):
        z = z0 + s + (gz1 - z0 - s) * j / rows
        fc.rect(u0 + s, u1 - s, z - .6, z + .6, 1, 1.9, m)
    if hinge:
        u = u1 - 2.2 if hinge == 'l' else u0 + 2.2
        zc = hz if hz is not None else (z0 + z1) / 2
        handle_v(fc, u, zc - 6, zc + 6, 2.2)


def _g(fc, u0, u1, z0, z1, t0, t1):
    a, b = fc.p + fc.d * t0, fc.p + fc.d * t1
    lo, hi = min(a, b), max(a, b)
    return [lo, u0, z0, hi, u1, z1] if fc.axis == 'x' else [u0, lo, z0, u1, hi, z1]


def drawer(fc, u0, u1, z0, z1, m, hm='steel', knob=False):
    u0, u1, z0, z1 = u0 + GAP, u1 - GAP, z0 + GAP, z1 - GAP
    fc.rect(u0, u1, z0, z1, 0, 2, m)
    uc, zc = (u0 + u1) / 2, z1 - min(5, (z1 - z0) / 2)
    if knob:
        for u in ((uc,) if u1 - u0 < 50 else (u0 + (u1 - u0) * .25, u1 - (u1 - u0) * .25)):
            fc.rect(u - 3.5, u + 3.5, zc - 1, zc + 1, 2, 3.6, hm)
    else:
        hw = min(8, (u1 - u0) / 2 - 5)
        handle_h(fc, uc - hw, uc + hw, zc, 2)


def drawers(fc, u0, u1, z0, z1, n, m, **kw):
    for i in range(n):
        drawer(fc, u0, u1, z0 + (z1 - z0) * i / n, z0 + (z1 - z0) * (i + 1) / n, m, **kw)


# ---------------------------------------------------------------- the kitchen
KG, GR = 'kgrey', 'granite'


class Run:
    """A kitchen run along y (u = y) against a wall at x = wall, its fronts at x = front (60 deep)."""

    def __init__(self, F, wall, front):
        self.F, self.wall, self.front = F, wall, front
        self.out = 1 if front > wall else -1
        self.fc = Face(F, 'x', front, self.out)

    def x(self, depth):     # the x range from the wall out to `depth`
        a, b = self.wall, self.wall + self.out * depth
        return min(a, b), max(a, b)

    def carcass(self, u0, u1, z0, z1, depth=58):
        x0, x1 = self.x(depth)
        self.F.box([x0, u0, z0, x1, u1, z1], KG, f='built')

    def base(self, u0, u1, doors=(), drawers_=0):
        """A base unit: kick, carcass, worktop; doors: hinge sides ('l','r') of its doors, across the width."""
        x0, x1 = self.x(53)
        self.F.box([x0, u0, 0, x1, u1, 10], 'black', f='built')        # the kick, set back
        self.carcass(u0, u1, 10, 88)
        if drawers_:
            drawers(self.fc, u0, u1, 10, 88, drawers_, KG)
        elif doors:
            n = len(doors)
            for i, hg in enumerate(doors):
                panel_door(self.fc, u0 + (u1 - u0) * i / n, u0 + (u1 - u0) * (i + 1) / n, 10, 88, KG, hinge=hg, hz=78)
        self.worktop(u0, u1)

    def worktop(self, u0, u1):
        x0, x1 = self.x(62.5)
        self.F.box([x0, u0, 88, x1, u1, 92], GR, f='built')

    def wall_unit(self, u0, u1, z0=145, z1=215, doors=('l', 'r'), glass=False):
        x0, x1 = self.x(33)
        self.F.box([x0, u0, z0, x1, u1, z1], KG, f='built')
        fc = Face(self.F, 'x', self.wall + self.out * 33, self.out)
        n = len(doors)
        for i, hg in enumerate(doors):
            a, b = u0 + (u1 - u0) * i / n, u0 + (u1 - u0) * (i + 1) / n
            if glass:
                glass_door(fc, a, b, z0, z1, KG, hinge=hg, hz=z0 + 12)
            else:
                panel_door(fc, a, b, z0, z1, KG, hinge=hg, arch=True, hz=z0 + 12)
        cx0, cx1 = self.x(36.5)
        self.F.box([cx0, u0, z1, cx1, u1, z1 + 5], KG, f='built')    # the cornice


def kitchen_left(F, x_wall=647, x_front=707):
    """The left run, on the dressing-area wall, from the window: dishwasher 70, sink 100, oven tower 65 (oven, microwave
    above), fridge 90 with the lift-up unit over it, glass cabinet 80."""
    r = Run(F, x_wall, x_front)
    fc = r.fc
    # dishwasher 70, its door in the grey, with the wall unit 70 above
    x0, x1 = r.x(53); F.box([x0, 88, 0, x1, 156, 10], 'black', f='built')
    r.carcass(88, 156, 10, 88); panel_door(fc, 88, 156, 10, 88, KG, hinge=None)
    handle_h(fc, 104, 140, 82, 2.8)
    r.worktop(88, 156); r.wall_unit(88, 156, doors=('l', 'r'))
    F.piece('Dishwasher', [x0, 88, 0, x1, 156, 92], '70 cm, behind a grey door; the 70 wall unit above')
    # sink unit 100, the glazed wall unit above it
    r.base(156, 256, doors=('l', 'r'))
    F.box([x_wall + 10, 170, 87, x_wall + 50, 242, 92.5], 'steel', f='built')
    F.box([x_wall + 4, 202, 92, x_wall + 8, 210, 118], 'steel', f='built')       # the tap
    F.box([x_wall + 4, 202, 114, x_wall + 22, 210, 118], 'steel', f='built')
    r.wall_unit(156, 256, doors=('l', 'r'), glass=True)
    F.piece('Sink unit', [x0, 156, 0, x1, 256, 92], '100 cm, the glass wall unit above')
    # the oven tower 65: plinth, drawer, built-in oven, microwave, a tall door above
    r.carcass(256, 321, 10, 215); F.box([x0, 256, 0, x1, 321, 10], 'black', f='built')
    drawer(fc, 256, 321, 10, 30, KG)
    fc.rect(258, 319, 31, 89, 0, 1.6, 'black'); handle_h(fc, 262, 315, 84, 1.6)       # the oven
    fc.rect(262, 315, 36, 76, 1.6, 1.8, 'glass')
    fc.rect(258, 319, 92, 130, 0, 1.6, 'black'); fc.rect(262, 300, 96, 126, 1.6, 1.8, 'glass')   # the microwave
    panel_door(fc, 256, 321, 132, 215, KG, hinge='r', hz=142)
    cx0, cx1 = r.x(61.5); F.box([cx0, 256, 215, cx1, 321, 220], KG, f='built')
    F.piece('Oven tower', [x0, 256, 0, x1, 321, 220], '65 cm: built-in oven, microwave above')
    # the new fridge 90 x 70, with the lift-up unit 80 over it
    fx0, fx1 = r.x(70)
    F.box([fx0, 324, 0, fx1, 408, 182], 'steel', f='built')
    ff = Face(F, 'x', x_wall + r.out * 70, r.out)
    ff.rect(324.5, 365.6, 1, 181, 0, .4, 'steel'); ff.rect(366.4, 407.5, 1, 181, 0, .4, 'steel')
    handle_v(ff, 362.5, 95, 150, .4, 'steel'); handle_v(ff, 369.5, 95, 150, .4, 'steel')
    r.carcass(321, 411, 185, 215, depth=58)
    panel_door(fc, 321, 411, 185, 215, KG, hinge=None); handle_h(fc, 350, 382, 190, 2.8)
    F.box([cx0, 321, 215, cx1, 411, 220], KG, f='built')
    F.piece('Fridge', [fx0, 321, 0, fx1, 411, 215], 'new, 90 x 70, the lift-up unit 80 above')
    # the glass cabinet 80: drawers below, two glazed doors above
    r.carcass(411, 486, 10, 215); F.box([x0, 411, 0, x1, 486, 10], 'black', f='built')
    drawers(fc, 411, 486, 10, 95, 4, KG)
    F.box([x0, 412, 96, x1, 485, 97], KG, f='built')
    glass_door(fc, 411, 448.5, 97, 215, KG, hinge='l', hz=108); glass_door(fc, 448.5, 486, 97, 215, KG, hinge='r', hz=108)
    F.box([cx0, 411, 215, cx1, 486, 220], KG, f='built')
    F.piece('Glass cabinet', [x0, 411, 0, x1, 486, 220], '80 cm, from her kitchen')


def kitchen_right(F, hob_trial_v='i-trial', hob_design_v='i-design', x_wall=959, x_front=899):
    """The right run, on the reception wall, from the window: tall unit 60, base 90, the hob 95 (or 60), base 90, a 5
    filler, the small counter 70 with the 45 drawer unit under it, facing the corridor."""
    r = Run(F, x_wall, x_front)
    fc = r.fc
    x0, x1 = r.x(58)
    # the tall unit in the window corner
    r.carcass(88, 148, 10, 215); F.box([x0, 88, 0, x1, 148, 10], 'black', f='built')
    panel_door(fc, 88, 148, 10, 120, KG, hinge='l', hz=100); panel_door(fc, 88, 148, 120, 215, KG, hinge='l', arch=True, hz=130)
    cx0, cx1 = r.x(61.5); F.box([cx0, 88, 215, cx1, 148, 220], KG, f='built')
    F.piece('Tall unit', [x0, 88, 0, x1, 148, 220], '60 cm')
    # base 90 with the wall unit 90 above
    r.base(148, 238, doors=('l', 'r')); r.wall_unit(148, 238)
    # the hob: base 90 + 5, the wall unit 90 above a hood
    r.base(238, 333, drawers_=3)
    F.box([x_wall - 52, 240, 92, x_wall - 8, 331, 93], 'black', v=hob_design_v, f='built')         # built-in hob, 95 cm
    F.box([x_wall - 52, 255, 92, x_wall - 8, 315, 93], 'black', v=hob_trial_v, f='built')          # or a 60 cm hob
    hx0, hx1 = r.x(50); F.box([hx0, 243, 150, hx1, 328, 160], 'steel', f='built')                  # the hood
    r.wall_unit(238, 333, z0=160)
    F.piece('Hob', [x0, 238, 88, x1, 333, 93], 'built-in, 95 or 60 cm (the Hob switch in View); the hood under the 90 wall unit')
    # base 90, filler 5
    r.base(333, 423, doors=('l', 'r')); r.wall_unit(333, 428)
    r.carcass(423, 428, 10, 88); r.worktop(423, 428)
    # the small counter 70 with stools; the 45 drawer unit under it, opening to the corridor
    r.worktop(428, 498)
    F.box([x_wall - 45, 438, 0, x_wall, 498, 10], 'black', f='built')
    F.box([x_wall - 45, 438, 10, x_wall, 496, 88], KG, f='built')
    fy = Face(F, 'y', 496, +1)
    drawers(fy, x_wall - 45, x_wall, 10, 88, 5, KG)
    F.piece('Drawer unit', [x_wall - 45, 438, 0, x_wall, 498, 88], '45 cm, faces the corridor, under the small counter')
    r.wall_unit(428, 498)
    F.piece('Kitchen', [647, 88, 0, 959, 498, 220], 'her kitchen units re-used: grey painted, arched and glazed doors, granite worktop')


# ---------------------------------------------------------------- the mahogany wall unit, as the master wardrobe
MH = 'mahog'


def frieze(fc, u0, u1, z0, z1):
    """The carved band: a row of diamonds (small stepped pyramids)."""
    fc.rect(u0, u1, z0, z1, 0, 2.4, MH)
    n = max(1, round((u1 - u0) / 9))
    w = (u1 - u0) / n
    zc = (z0 + z1) / 2
    for i in range(n):
        c = u0 + w * (i + .5)
        fc.rect(c - w * .36, c + w * .36, zc - 3.2, zc + 3.2, 2.4, 3.2, MH)
        fc.rect(c - w * .2, c + w * .2, zc - 1.8, zc + 1.8, 3.2, 4, MH)


def flutes(fc, u0, u1, z0, z1):
    fc.rect(u0, u1, z0, z1, 0, 2, MH)
    w = u1 - u0
    if w >= 6:
        for k in (.3, .5, .7):
            fc.rect(u0 + w * k - .6, u0 + w * k + .6, z0 + 6, z1 - 6, 2, 2.8, MH)


def wall_unit_section(fc, u0, u1, door, z_top=272, hinge='l'):
    """One section of the wall unit: a 60 cm door below and above it, trim (fluted) filling the rest of the width."""
    trim = (u1 - u0) - door
    du0, du1 = (u0, u0 + door) if hinge == 'l' else (u1 - door, u1)
    panel_door(fc, du0, du1, 0, 200, MH, hinge=hinge, hz=105, hm='brass', knob=True)
    frieze(fc, u0, u1, 200, 212)
    panel_door(fc, du0, du1, 212, z_top - 8, MH, hinge=hinge, hz=222, hm='brass', knob=True)
    if trim > .5:
        tu0, tu1 = (du1, u1) if hinge == 'l' else (u0, du0)
        flutes(fc, tu0, tu1, 0, 200); flutes(fc, tu0, tu1, 212, z_top - 8)
    fc.rect(u0, u1, z_top - 8, z_top - 3, 0, 2.5, MH); fc.rect(u0, u1, z_top - 3, z_top, 0, 4, MH)   # the cornice


def master_wardrobe(F):
    """In the dressing area: 70 | 60 along the window wall, the corner, then 60, 60, 60, 70, 80 down the kitchen
    wall; seven of the wall unit's eight 60 cm doors, trims filling the rest."""
    Z = 272
    F.box([440, 88, 0, 632, 146, Z], 'mahogd', f='built')     # the top run's carcass and the corner
    F.box([574, 146, 0, 632, 486, Z], 'mahogd', f='built')    # the column's carcass
    top = Face(F, 'y', 146, +1)
    wall_unit_section(top, 440, 510, 60, Z, 'l')               # 70
    wall_unit_section(top, 510, 572, 60, Z, 'r')               # 60 (with a 2 cm trim)
    flutes(top, 572, 574, 0, Z - 8)
    col = Face(F, 'x', 574, -1)
    u = 148
    for w, hg in ((60, 'l'), (60, 'r'), (60, 'l'), (70, 'r'), (80, 'l')):
        wall_unit_section(col, u, u + w, 60, Z, hg)
        u += w
    flutes(col, 146, 148, 0, Z - 8); flutes(col, 478, 486, 0, Z - 8)
    F.piece('Wardrobe', [440, 88, 0, 632, 486, Z], 'her mahogany wall unit: 70 | 60, the corner, then 60, 60, 60, 70, 80; seven 60 cm doors, fluted trims')


def dressing_table(F, x0=262, x1=390, y_wall=318, depth=45):
    """The wall unit's dressing table, 128: a top on two drawer pedestals; the 60 x 93 mirror to its right; the hanging
    TV 42 to its left."""
    y1 = y_wall + depth
    F.box([x0, y_wall, 72, x1, y1, 76], MH, f='loose')
    fc = Face(F, 'y', y1 - 2, +1, f='loose')
    for a, b in ((x0, x0 + 38), (x1 - 38, x1)):
        F.box([a, y_wall, 0, b, y1 - 2, 72], MH, f='loose')
        drawers(fc, a, b, 4, 72, 3, MH, hm='brass', knob=True)
    F.box([x0 + 38, y_wall, 62, x1 - 38, y1 - 2, 72], MH, f='loose')
    drawer(Face(F, 'y', y1 - 2, +1, f='loose'), x0 + 38, x1 - 38, 62, 72, MH, hm='brass', knob=True)
    F.piece('Dressing table', [x0, y_wall, 0, x1, y1, 76], 'from her wall unit, 128 cm, drawers either side')
    # the mirror 60 x 93 in a mahogany frame, on the wall to the right
    mx0, mx1, mz0, mz1 = 370, 430, 95, 188
    F.box([mx0, y_wall, mz0, mx1, y_wall + 2.5, mz1], MH, f='loose')
    F.box([mx0 + 4, y_wall + 2.5, mz0 + 4, mx1 - 4, y_wall + 2.8, mz1 - 4], 'mirror', f='loose')
    F.piece('Mirror', [mx0, y_wall, mz0, mx1, y_wall + 3, mz1], '60 x 93, framed')
    F.box([222, y_wall, 100, 262, y_wall + 4, 160], 'black', f='loose'); F.piece('Hanging TV', [222, y_wall, 100, 262, y_wall + 4, 160], '42 cm')


def mahogany_bed(F, x0, y0, x1, y1, n='Master bed'):
    """Her mahogany bed (photo): the headboard on the far (y1) side, panelled between posts, a lower footboard,
    side rails, the mattress, and burgundy pillows."""
    L = dict(f='loose')
    for x in (x0, x1 - 7):
        F.box([x, y1 - 7, 0, x + 7, y1, 118], MH, **L)            # headboard posts
        F.box([x, y0, 0, x + 7, y0 + 7, 62], MH, **L)             # footboard posts
    F.box([x0 + 7, y1 - 5, 30, x1 - 7, y1 - 1, 110], MH, **L)     # the headboard panel
    hf = Face(F, 'y', y1 - 5, -1, f='loose')
    for a, b in ((x0 + 12, (x0 + x1) / 2 - 3), ((x0 + x1) / 2 + 3, x1 - 12)):
        hf.rect(a, b, 60, 102, 0, 1, MH); hf.rect(a + 5, b - 5, 65, 97, 1, 1.8, MH)
    F.box([x0 + 4, y1 - 6, 110, x1 - 4, y1, 114], MH, **L)        # its top rail
    F.box([x0 + 7, y0, 22, x1 - 7, y0 + 4, 56], MH, **L)          # the footboard
    ff = Face(F, 'y', y0, -1, f='loose')
    ff.rect(x0 + 14, x1 - 14, 28, 50, 0, 1, MH)
    F.box([x0 + 2, y0 + 1, 56, x1 - 2, y0 + 6, 60], MH, **L)
    F.box([x0, y0 + 7, 18, x0 + 4, y1 - 7, 38], MH, **L); F.box([x1 - 4, y0 + 7, 18, x1, y1 - 7, 38], MH, **L)   # side rails
    F.box([x0 + 4, y0 + 4, 18, x1 - 4, y1 - 6, 34], 'oakdark', **L)
    F.box([x0 + 5, y0 + 6, 34, x1 - 5, y1 - 8, 56], 'linen', **L)  # the mattress and bedding
    F.box([x0 + 3, y0 + 5, 40, x1 - 3, y1 - 60, 58], 'linen', **L)  # the quilt, falling over the sides
    for a, b in ((x0 + 10, (x0 + x1) / 2 - 2), ((x0 + x1) / 2 + 2, x1 - 10)):
        F.box([a, y1 - 52, 56, b, y1 - 12, 70], 'wine', **L)
    F.piece(n, [x0, y0, 0, x1, y1, 118], 'her mahogany bed, 1.60 x 2.00')


# ---------------------------------------------------------------- sofas and poufs
class Frame:
    """A sofa's own frame: u along its length, v from the front (0) to the back (depth)."""

    def __init__(self, F, x0, y0, x1, y1, back):
        self.F, self.back = F, back
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.L = (x1 - x0) if back in 'tb' else (y1 - y0)
        self.D = (y1 - y0) if back in 'tb' else (x1 - x0)

    def box(self, u0, u1, v0, v1, z0, z1, m):
        b = self.back
        if b == 'b':
            r = [self.x0 + u0, self.y0 + v0, z0, self.x0 + u1, self.y0 + v1, z1]
        elif b == 't':
            r = [self.x0 + u0, self.y1 - v1, z0, self.x0 + u1, self.y1 - v0, z1]
        elif b == 'r':
            r = [self.x0 + v0, self.y0 + u0, z0, self.x0 + v1, self.y0 + u1, z1]
        else:
            r = [self.x1 - v1, self.y0 + u0, z0, self.x1 - v0, self.y0 + u1, z1]
        self.F.box(r, m, f='loose')


def rolled_sofa(F, n, x0, y0, x1, y1, back, m, seats, accents='mustard', throw=False, mt=None):
    """The traditional sofas she has (photos): a skirted base, rolled arms, loose seat and back cushions."""
    s = Frame(F, x0, y0, x1, y1, back)
    L, D, A = s.L, s.D, 22
    s.box(1, L - 1, 2, D - 1, 3, 20, m)                         # the skirted base
    s.box(A, L - A, 0, D - 18, 18, 40, m)                       # the deck
    s.box(0, L, D - 20, D, 18, 80, m)                           # the back
    for a, b in ((0, A), (L - A, L)):
        s.box(a, b, 0, D - 4, 18, 58, m)                        # the arms
        s.box(a - 1.5, b + 1.5, -1, D - 8, 50, 66, m)           # their roll
    w = (L - 2 * A) / seats
    for i in range(seats):
        s.box(A + w * i + .6, A + w * (i + 1) - .6, -1, D - 20, 40, 53, m)
        s.box(A + w * i + .6, A + w * (i + 1) - .6, D - 34, D - 18, 46, 78, m)
    if throw:
        s.box(A, L - A, -2.5, D - 22, 53, 54, 'linen'); s.box(A, L - A, -3, -2, 30, 54, 'linen')
    if accents:
        s.box(A + 4, A + 42, D - 44, D - 32, 50, 86, accents); s.box(L - A - 42, L - A - 4, D - 44, D - 32, 50, 86, accents)
    F.piece(n, [x0, y0, 0, x1, y1, 80], mt)


def showroom_sofa(F, n, x0, y0, x1, y1, back, mt=None):
    """The new 2.80 sofa from the showroom (photo): beige, three pieces with arms on the end ones, deep seats, loose
    back cushions, white piping along the edges."""
    m, P = 'beige', 'piping'
    s = Frame(F, x0, y0, x1, y1, back)
    L, D, A = s.L, s.D, 20
    s.box(0, L, 3, D - 2, 0, 12, 'black')                       # the recliner's base, set back
    s.box(A, L - A, 0, D - 16, 12, 42, m)
    s.box(0, L, D - 18, D, 12, 72, m)
    for a, b in ((0, A), (L - A, L)):
        s.box(a, b, 0, D - 2, 12, 60, m)
        s.box(a, b, -.4, 1, 59.4, 60.6, P)                      # piping round the arm fronts and tops
        s.box(a - .3, a + .9, 0, D - 2, 59.4, 60.6, P); s.box(b - .9, b + .3, 0, D - 2, 59.4, 60.6, P)
    w = (L - 2 * A) / 3
    for i in range(3):
        a, b = A + w * i + .5, A + w * (i + 1) - .5
        s.box(a, b, -1, D - 18, 42, 55, m)
        s.box(a, b, -1.6, -.4, 54.4, 55.6, P)                   # piping on the seat's front edge
        s.box(a + 2, b - 2, D - 40, D - 16, 50, 86, m)          # the back cushions
        s.box(a + 2, b - 2, D - 40.6, D - 39.4, 85.2, 86.4, P)
    s.box(A + 8, A + 48, D - 50, D - 38, 54, 84, 'taupe'); s.box(L - A - 48, L - A - 8, D - 50, D - 38, 54, 84, 'linen')
    F.piece(n, [x0, y0, 0, x1, y1, 86], mt)


def pouf(F, x0, y0, x1, y1, h=42):
    F.box([x0 + 1, y0 + 1, 4, x1 - 1, y1 - 1, h - 6], 'pouf', f='loose')
    F.box([x0, y0, h - 8, x1, y1, h], 'pouf', f='loose')        # the padded top, a little wider
    for x, y in ((x0 + 3, y0 + 3), (x1 - 7, y0 + 3), (x0 + 3, y1 - 7), (x1 - 7, y1 - 7)):
        F.box([x, y, 0, x + 4, y + 4, 4], 'oakdark', f='loose')
    F.piece('Pouf', [x0, y0, 0, x1, y1, h], '45 x 45, her own')


# ---------------------------------------------------------------- the piano
def upright_piano(F, x0, y0, x1, y1):
    """Black upright, against the y1 wall, the keyboard facing y0."""
    P, L = 'piano', dict(f='loose')
    F.box([x0 + 4, y0 + 26, 0, x1 - 4, y1, 66], P, **L)          # the lower case, set back
    F.box([x0 + 4, y0 + 30, 66, x1 - 4, y1, 128], P, **L)        # the upper case
    for a in (x0, x1 - 4):
        F.box([a, y0, 0, a + 4, y1, 80], P, **L)                 # the cheeks, down to the toe blocks
        F.box([a, y0 + 30, 80, a + 4, y1, 128], P, **L)
        F.box([a - .5, y0, 0, a + 4.5, y0 + 5, 6], 'brass', **L)  # castors
    F.box([x0 + 4, y0, 66, x1 - 4, y0 + 30, 72], P, **L)          # the key bed
    F.box([x0 + 4, y0 + 1, 72, x1 - 4, y0 + 17, 74.5], 'keys', **L)
    F.box([x0 + 4, y0 + 17, 72, x1 - 4, y0 + 30, 84], P, **L)     # the fallboard, open
    F.box([x0, y0 + 28, 128, x1, y1, 130], P, **L)                # the lid
    F.box([x0 + 20, y0 + 30.5, 92, x1 - 20, y0 + 32, 116], P, **L)  # the music desk
    for x in (x0 + 45, x0 + 75):
        F.box([x, y0 + 10, 4, x + 4, y0 + 18, 8], 'brass', **L)    # pedals
    F.piece('Piano', [x0, y0, 0, x1, y1, 130], 'her black upright, 1.50 x 70')
