"""High-quality renders, on top of render_cycles: photo-scanned textures, a real sky, soft furnishings, sheer curtains,
plants and props, and a photographic finish (bloom, vignette).

    python3 tools/fetch_assets.py                       # once: the CC0 Poly Haven textures, sky and models
    <venv>/bin/python tools/render_hq.py --only living --times day --res 1920x1200 --samples 384

The furniture is still Amira's own, measured; only its finish and the styling around it are added here.
"""
import argparse, math, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_cycles as rc
from render_cycles import bpy, bmesh, Vector, CM, lin, model
import addon_utils
import numpy as np
from render_views import RENDERS, EXPOSURE, HQ_VIEWS, HQ_EXPOSURE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, '.assets')
HDRI = 'kloofendal_48d_partly_cloudy_puresky'
DAY_EV = 4.0          # the photographed sky is far dimmer than Blender's physical one: a longer exposure

# ---------------------------------------------------------------- materials from photo textures
# key: (texture, tile size in m, tint or None, how much of the photo's light/dark to keep, roughness range,
#       normal strength, sheen, coat)
PBR = {
    'wall':      ('white_plaster_02', 1.6, '#EEE6D7', .25, (.82, .95), .35, 0, 0),
    'wallpaint': ('white_plaster_02', 1.6, '#EEE6D7', .25, (.82, .95), .35, 0, 0),
    'ceiling':   ('white_plaster_02', 2.0, '#F6F3EE', .10, (.88, .97), .15, 0, 0),
    'cap':       ('white_plaster_02', 2.0, '#F1EEE8', .15, (.85, .95), .2, 0, 0),
    'oak':       ('oak_veneer_01', .9, None, 1, (.32, .5), .4, 0, .25),
    'oakdark':   ('oak_veneer_01', .9, '#5A3E26', .9, (.3, .45), .4, 0, .25),
    'beige':     ('rough_linen', .22, '#CDBFAA', .45, (.85, 1), .8, .35, 0),
    'fabric':    ('rough_linen', .22, '#E0D6C6', .45, (.85, 1), .8, .35, 0),
    'linen':     ('rough_linen', .2, '#EEE8DD', .45, (.85, 1), .8, .35, 0),
    'taupe':     ('rough_linen', .12, '#7C6C5A', .5, (.88, 1), .9, .4, 0),
    'sgrey':     ('rough_linen', .12, '#8E8B85', .5, (.88, 1), .9, .4, 0),
    'pouf':      ('wool_boucle', .1, '#705F4E', .6, (.9, 1), 1, .4, 0),
    'throw':     ('wool_boucle', .1, '#EAE2D4', .5, (.9, 1), 1, .4, 0),
    'throwrust': ('wool_boucle', .1, '#A25E3E', .5, (.9, 1), 1, .4, 0),
    'throwsage': ('wool_boucle', .1, '#8C9A82', .5, (.9, 1), 1, .4, 0),
    'book_a':    ('rough_linen', .08, '#3B3833', .3, (.55, .8), .3, 0, 0),
    'book_b':    ('rough_linen', .08, '#C9B593', .3, (.55, .8), .3, 0, 0),
    'mustard':   ('velour_velvet', .25, '#B59A52', .5, (.6, .85), .6, .8, 0),
    'wine':      ('velour_velvet', .25, '#7A1E28', .5, (.6, .85), .6, .8, 0),
    'rug':       ('curly_teddy_natural', .35, '#DCD0BA', .55, (.95, 1), 1.2, .5, 0),
}
SOFT = {'beige', 'fabric', 'linen', 'taupe', 'sgrey', 'pouf', 'mustard', 'wine', 'throw', 'throwrust', 'throwsage'}


def tex_path(name, m):
    return os.path.join(ASSETS, 'tex', name, m + '.jpg')


def image(path, noncolor=False):
    img = bpy.data.images.load(path, check_existing=True)
    if noncolor:
        img.colorspace_settings.name = 'Non-Color'
    return img


MEANS = {}


def mean_luma(path):
    """The photo's mean brightness, so a tint keeps its colour and only takes the texture's light and dark."""
    if path not in MEANS:
        img = image(path)
        a = np.empty(img.size[0] * img.size[1] * 4, np.float32); img.pixels.foreach_get(a)
        a = a.reshape(-1, 4)[::7]
        MEANS[path] = float((a[:, 0] * .2126 + a[:, 1] * .7152 + a[:, 2] * .0722).mean())
    return MEANS[path]


def make_pbr(mats, k):
    name, size, tint, keep, (r0, r1), nstr, sheen, coat = PBR[k]
    m, nt, out = mats.new(k)
    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = 'UVMap'
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / size, 1 / size, 1)
    nt.links.new(uv.outputs['UV'], mp.inputs['Vector'])

    def tex(map_, noncolor):
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = image(tex_path(name, map_), noncolor)
        n.interpolation = 'Cubic'
        nt.links.new(mp.outputs[0], n.inputs['Vector'])
        return n

    b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    d = tex('diff', False)
    if tint:
        bw = nt.nodes.new('ShaderNodeRGBToBW'); nt.links.new(d.outputs['Color'], bw.inputs['Color'])
        mu = mean_luma(tex_path(name, 'diff'))
        mr = nt.nodes.new('ShaderNodeMapRange')       # 1 at the photo's mean, more or less around it
        mr.inputs['From Min'].default_value = 0; mr.inputs['From Max'].default_value = mu
        mr.inputs['To Min'].default_value = 1 - keep; mr.inputs['To Max'].default_value = 1
        mr.clamp = False
        nt.links.new(bw.outputs['Val'], mr.inputs['Value'])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
        mx.inputs['Factor'].default_value = 1
        mx.inputs[6].default_value = lin(tint)
        nt.links.new(mr.outputs['Result'], mx.inputs[7])
        nt.links.new(mx.outputs[2], b.inputs['Base Color'])
    else:
        nt.links.new(d.outputs['Color'], b.inputs['Base Color'])
    if os.path.exists(tex_path(name, 'rough')):
        r = tex('rough', True)
        rr = nt.nodes.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = r0; rr.inputs['To Max'].default_value = r1
        nt.links.new(r.outputs['Color'], rr.inputs['Value']); nt.links.new(rr.outputs['Result'], b.inputs['Roughness'])
    else:
        b.inputs['Roughness'].default_value = (r0 + r1) / 2
    if nstr and os.path.exists(tex_path(name, 'nor')):
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.uv_map = 'UVMap'; nm.inputs['Strength'].default_value = nstr
        nt.links.new(tex('nor', True).outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    if sheen:
        b.inputs['Sheen Weight'].default_value = sheen; b.inputs['Sheen Roughness'].default_value = .45
        b.inputs['Specular IOR Level'].default_value = .25
    if coat:
        b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = .12
    nt.links.new(b.outputs[0], out.inputs['Surface'])
    return m


def make_porcelain(mats):
    """120 x 60 polished porcelain: a pale marble photo for the stone's life, the joints drawn on top."""
    m, nt, out = mats.new('porcelain')
    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = 'UVMap'
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / 1.2, 1 / 1.2, 1)
    nt.links.new(uv.outputs['UV'], mp.inputs['Vector'])
    d = nt.nodes.new('ShaderNodeTexImage'); d.image = image(tex_path('marble_01', 'diff')); nt.links.new(mp.outputs[0], d.inputs['Vector'])
    bw = nt.nodes.new('ShaderNodeRGBToBW'); nt.links.new(d.outputs['Color'], bw.inputs['Color'])
    mu = mean_luma(tex_path('marble_01', 'diff'))
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Max'].default_value = mu; mr.inputs['To Min'].default_value = .82; mr.clamp = False
    nt.links.new(bw.outputs['Val'], mr.inputs['Value'])
    br = nt.nodes.new('ShaderNodeTexBrick'); br.offset = 0; br.squash = 1
    br.inputs['Scale'].default_value = 1; br.inputs['Brick Width'].default_value = 1.2; br.inputs['Row Height'].default_value = .6
    br.inputs['Mortar Size'].default_value = .0025; br.inputs['Mortar Smooth'].default_value = .3
    br.inputs['Color1'].default_value = lin('#EAE4DA'); br.inputs['Color2'].default_value = lin('#E4DDD1'); br.inputs['Mortar'].default_value = lin('#B9AF9F')
    tc = nt.nodes.new('ShaderNodeTexCoord'); nt.links.new(tc.outputs['Object'], br.inputs['Vector'])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1
    nt.links.new(br.outputs['Color'], mx.inputs[6]); nt.links.new(mr.outputs['Result'], mx.inputs[7])
    b = nt.nodes.new('ShaderNodeBsdfPrincipled'); nt.links.new(mx.outputs[2], b.inputs['Base Color'])
    rr = nt.nodes.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = .07; rr.inputs['To Max'].default_value = .5
    inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1
    nt.links.new(br.outputs['Fac'], inv.inputs[1]); nt.links.new(inv.outputs[0], rr.inputs['Value'])
    nt.links.new(rr.outputs['Result'], b.inputs['Roughness'])
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .4; bump.inputs['Distance'].default_value = .0015
    nt.links.new(br.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Specular IOR Level'].default_value = .55
    nt.links.new(b.outputs[0], out.inputs['Surface'])
    return m


def make_context(mats):
    """The neighbours: sand-coloured rendered blocks, a window every 3.2 m on every 3.1 m floor, glass that
    catches the sky, a little haze with distance; at night some of the windows are lit."""
    m, nt, out = mats.new('context')
    N = nt.nodes.new; L = nt.links.new
    uv = N('ShaderNodeUVMap'); uv.uv_map = 'UVMap'
    sep = N('ShaderNodeSeparateXYZ'); L(uv.outputs['UV'], sep.inputs[0])

    def math_(op, a, b=None):
        n = N('ShaderNodeMath'); n.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L(v, n.inputs[i])
        return n.outputs[0]

    U, V = sep.outputs['X'], sep.outputs['Y']
    cu, cv = math_('DIVIDE', U, 3.2), math_('DIVIDE', V, 3.1)
    fu, fv = math_('FRACT', cu), math_('FRACT', cv)
    wu = math_('MULTIPLY', math_('GREATER_THAN', fu, .2), math_('LESS_THAN', fu, .8))
    wv = math_('MULTIPLY', math_('GREATER_THAN', fv, .3), math_('LESS_THAN', fv, .82))
    geo = N('ShaderNodeNewGeometry'); gz = N('ShaderNodeSeparateXYZ'); L(geo.outputs['Normal'], gz.inputs[0])
    vert = math_('LESS_THAN', math_('ABSOLUTE', gz.outputs['Z']), .5)
    win = math_('MULTIPLY', math_('MULTIPLY', wu, wv), vert)
    # the walls
    d = nt.nodes.new('ShaderNodeTexImage'); d.image = image(tex_path('white_plaster_02', 'diff'))
    mp = N('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / 3, 1 / 3, 1); L(uv.outputs['UV'], mp.inputs['Vector']); L(mp.outputs[0], d.inputs['Vector'])
    bw = N('ShaderNodeRGBToBW'); L(d.outputs['Color'], bw.inputs['Color'])
    mr = N('ShaderNodeMapRange'); mr.inputs['From Max'].default_value = mean_luma(tex_path('white_plaster_02', 'diff'))
    mr.inputs['To Min'].default_value = .8; mr.clamp = False; L(bw.outputs['Val'], mr.inputs['Value'])
    wall = N('ShaderNodeMix'); wall.data_type = 'RGBA'; wall.blend_type = 'MULTIPLY'; wall.inputs['Factor'].default_value = 1
    wall.inputs[6].default_value = lin('#D9C9AC'); L(mr.outputs['Result'], wall.inputs[7])
    col = N('ShaderNodeMix'); col.data_type = 'RGBA'; L(win, col.inputs['Factor'])
    L(wall.outputs[2], col.inputs[6]); col.inputs[7].default_value = lin('#2A333B')
    b = N('ShaderNodeBsdfPrincipled'); L(col.outputs[2], b.inputs['Base Color'])
    rr = N('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = .85; rr.inputs['To Max'].default_value = .06
    L(win, rr.inputs['Value']); L(rr.outputs['Result'], b.inputs['Roughness'])
    sp = N('ShaderNodeMapRange'); sp.inputs['To Min'].default_value = .4; sp.inputs['To Max'].default_value = 1
    L(win, sp.inputs['Value']); L(sp.outputs['Result'], b.inputs['Specular IOR Level'])
    if mats.night:      # about four windows in ten lit, each its own warmth
        cell = N('ShaderNodeCombineXYZ'); L(math_('FLOOR', cu), cell.inputs['X']); L(math_('FLOOR', cv), cell.inputs['Y'])
        wn = N('ShaderNodeTexWhiteNoise'); wn.noise_dimensions = '3D'; L(cell.outputs[0], wn.inputs['Vector'])
        lit = math_('MULTIPLY', math_('GREATER_THAN', wn.outputs['Value'], .6), win)
        warm = N('ShaderNodeValToRGB'); L(wn.outputs['Value'], warm.inputs['Fac'])
        warm.color_ramp.elements[0].color = lin('#FFB86A'); warm.color_ramp.elements[1].color = lin('#FFE2B8')
        L(warm.outputs['Color'], b.inputs['Emission Color']); L(math_('MULTIPLY', lit, 2.5), b.inputs['Emission Strength'])
    # haze: mix toward the horizon's colour with distance
    cam = N('ShaderNodeCameraData')
    f = math_('SUBTRACT', 1, math_('EXPONENT', math_('DIVIDE', cam.outputs['View Distance'], -900)))
    if mats.night:
        f = math_('MULTIPLY', f, .3)
    hz = N('ShaderNodeEmission'); hz.inputs['Color'].default_value = lin('#C8D2DC' if not mats.night else '#1A2030')
    hz.inputs['Strength'].default_value = 1.4 if not mats.night else .3
    mx = N('ShaderNodeMixShader'); L(f, mx.inputs[0]); L(b.outputs[0], mx.inputs[1]); L(hz.outputs[0], mx.inputs[2])
    L(mx.outputs[0], out.inputs['Surface'])
    return m


def make_sheer(mats):
    m, nt, out = mats.new('sheer')
    tr = nt.nodes.new('ShaderNodeBsdfTranslucent'); tr.inputs['Color'].default_value = lin('#F6F1E8')
    df = nt.nodes.new('ShaderNodeBsdfDiffuse'); df.inputs['Color'].default_value = lin('#F3EEE5')
    tp = nt.nodes.new('ShaderNodeBsdfTransparent')
    a = nt.nodes.new('ShaderNodeMixShader'); a.inputs[0].default_value = .5
    nt.links.new(tr.outputs[0], a.inputs[1]); nt.links.new(df.outputs[0], a.inputs[2])
    b = nt.nodes.new('ShaderNodeMixShader'); b.inputs[0].default_value = .5      # half the light passes straight through
    nt.links.new(a.outputs[0], b.inputs[1]); nt.links.new(tp.outputs[0], b.inputs[2])
    nt.links.new(b.outputs[0], out.inputs['Surface'])
    return m


_make = rc.Mats.make


def make_hq(self, k):
    if k in PBR and os.path.exists(tex_path(PBR[k][0], 'diff')):
        return make_pbr(self, k)
    if k == 'porcelain':
        return make_porcelain(self)
    if k == 'sheer':
        return make_sheer(self)
    if k == 'context':
        return make_context(self)
    return _make(self, k)


# ---------------------------------------------------------------- geometry: UVs everywhere, soft furnishings
def box_uvs(me):
    """A planar projection per face (metres), so the photo textures sit at their real size on every box."""
    uvl = me.uv_layers.new(name='UVMap')
    me.calc_loop_triangles()
    for poly in me.polygons:
        n = poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            u, v = [(co.y, co.z), (co.x, co.z), (co.x, co.y)][ax]
            uvl.data[li].uv = (u, v)


class HQGeo(rc.Geo):
    def __init__(self):
        super().__init__()
        self.soft = []

    def box(self, b, m):
        if m in SOFT:
            self.soft.append((b, m))
        else:
            super().box(b, m)

    def link(self, mats, scene):
        for m, bm in self.bm.items():
            me = bpy.data.meshes.new(m)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(me); bm.free()
            box_uvs(me)
            me.materials.append(mats.get(m))
            scene.collection.objects.link(bpy.data.objects.new(m, me))
        self.bm = {}
        for i, (b, m) in enumerate(self.soft):
            soft_box(scene, mats, b, m, i)


def soft_box(scene, mats, b, m, i):
    """An upholstered piece: the measured box, its edges rounded and the faces a little full, like a cushion."""
    x0, y0, z0, x1, y1, z1 = b
    dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
    if min(dx, dy, dz) <= 0:
        return
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    me = bpy.data.meshes.new('soft'); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('soft %s %d' % (m, i), me)
    ob.location = ((x0 + x1) / 2 * CM, -(y0 + y1) / 2 * CM, (z0 + z1) / 2 * CM)
    ob.scale = (dx * CM, dy * CM, dz * CM)
    scene.collection.objects.link(ob)
    # the modifiers work in the object's own space: apply the scale first so the rounding is even
    me.transform(ob.matrix_basis.to_3x3().to_4x4()); ob.scale = (1, 1, 1)
    small = min(dx, dy, dz)
    bv = ob.modifiers.new('round', 'BEVEL'); bv.width = min(small * .42, 6) * CM; bv.segments = 3; bv.limit_method = 'NONE'
    ss = ob.modifiers.new('soft', 'SUBSURF'); ss.levels = ss.render_levels = 2
    if small >= 8 and max(dx, dy) >= 30:             # cushions and seats: a little fuller in the middle
        cast = ob.modifiers.new('full', 'CAST'); cast.factor = .12; cast.cast_type = 'SPHERE'
        cast.use_x = cast.use_y = True; cast.use_z = small < 25
    for p in me.polygons:
        p.use_smooth = True
    box_uvs(me)
    me.materials.append(mats.get(m))


# ---------------------------------------------------------------- the sky
def hdri_sun_dir(img):
    w, h = img.size
    a = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(a)
    lum = a.reshape(h, w, 4)[..., :3].sum(-1)
    y, x = np.unravel_index(np.argmax(lum), lum.shape)
    u, v = (x + .5) / w, (y + .5) / h
    az = math.pi - 2 * math.pi * u              # Cycles: u = (pi - atan2(y, x)) / 2 pi; rows count up from the bottom
    el = math.pi * (v - .5)
    return Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)))


def world_hdri(scene, az, alt):
    w = bpy.data.worlds.new('day'); scene.world = w
    nt = w.node_tree
    bg = [n for n in nt.nodes if n.type == 'BACKGROUND'][0]
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = image(os.path.join(ASSETS, 'hdri', HDRI + '.hdr'))
    s = hdri_sun_dir(env.image)
    d = rc.plan_direction(az, alt)
    rot = math.atan2(s.y, s.x) - math.atan2(d.y, d.x)       # turn the photo so its sun stands where Cairo's does
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Rotation'].default_value = (0, 0, rot)
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs[0], env.inputs['Vector'])
    nt.links.new(env.outputs['Color'], bg.inputs[0]); bg.inputs[1].default_value = 1.0
    print('HDRI sun at %.0f deg, turned %.0f deg' % (math.degrees(math.asin(s.z)), math.degrees(rot)))


# ---------------------------------------------------------------- props
def import_model(scene, name, at, rot=0, scale=1, fit_h=None):
    """A Poly Haven model, its base at `at` (plan cm, height cm), turned `rot` degrees about the vertical."""
    path = os.path.join(ASSETS, 'models', name, name + '.gltf')
    if not os.path.exists(path):
        print('missing model', name); return None
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None]
    root = bpy.data.objects.new('prop ' + name, None); scene.collection.objects.link(root)
    for o in roots:
        o.parent = root
    if fit_h:
        bpy.context.view_layer.update()
        zs = [(o.matrix_world @ Vector(c)).z for o in new if o.type == 'MESH' for c in o.bound_box]
        scale = fit_h * CM / (max(zs) - min(zs))
    root.scale = (scale,) * 3
    root.rotation_euler = (0, 0, math.radians(rot))
    root.location = (at[0] * CM, -at[1] * CM, at[2] * CM)
    return root


def take_plants(L):
    """The viewer's plants (a ball of leaves on a pot) give way to real plant models."""
    plants, keep = [], []
    for it in L['items']:
        if it['t'] == 's' and it.get('m') == 'leaf':
            plants.append((it['c'], it['z'] + it['r'] * it.get('sy', 1)))
    centres = {tuple(c) for c, _ in plants}
    for it in L['items']:
        if it['t'] == 's' and it.get('m') == 'leaf':
            continue
        if it['t'] == 'c' and tuple(it['c']) in centres:
            continue
        keep.append(it)
    L['items'] = keep
    return plants


def all_curtains(g, lay):
    """Sheer curtains, drawn to the sides, on the windows of the bedrooms and the living rooms."""
    rooms = lay['rooms']

    def kind(x, y):
        for n, (a, b, c, d), k in rooms:
            if a <= x <= c and b <= y <= d:
                return k
        return None
    for n, r, axis, sill, head, panes in model.windows_of(lay) + [(n, r, a, 0, 230, 2) for n, r, a in model.SLIDERS]:
        x0, y0, x1, y1 = r
        if axis == 'x':
            cx = (x0 + x1) / 2
            side = 1 if kind(cx, y1 + 30) else -1
            if kind(cx, y1 + 30 if side > 0 else y0 - 30) not in ('pri', 'pub'):
                continue
            curtains(g, x0, x1, y1 if side > 0 else y0, side=side)
        else:
            cy = (y0 + y1) / 2
            side = 1 if kind(x1 + 30, cy) else -1
            if kind(x1 + 30 if side > 0 else x0 - 30, cy) not in ('pri', 'pub'):
                continue
            curtains(g, y0, y1, x1 if side > 0 else x0, side=side, axis='y')


def curtains(g, x0, x1, y, z1=270, side=1, axis='x'):
    """Sheer curtains drawn to both sides of a window, on a slim black rod, `side` toward the room. For a window in a
    wall along y, x0/x1 are its y extent and y the wall face's x."""
    def P(u, w, z):                        # along the wall, out from it, height -> Blender
        return ((u * CM, -w * CM, z * CM) if axis == 'x' else (w * CM, -u * CM, z * CM))
    r0, r1 = y + side * 5, y + side * 7
    rod = [x0 - 15, min(r0, r1), z1 - 4, x1 + 15, max(r0, r1), z1 - 2]
    g.box(rod if axis == 'x' else [rod[1], rod[0], rod[2], rod[4], rod[3], rod[5]], 'black')
    for a, b in ((x0 - 12, x0 + 40), (x1 - 40, x1 + 12)):
        bm = g._bm('sheer')
        n = int((b - a) / 1.2)
        top, bot = [], []
        for i in range(n + 1):
            u = a + (b - a) * i / n
            w = y + side * (10 + 3.5 * math.sin(2 * math.pi * (u - a) / 11))
            top.append(bm.verts.new(P(u, w, z1 - 6)))
            bot.append(bm.verts.new(P(u, w + side * .6, 1)))
        for i in range(n):
            bm.faces.new([bot[i], bot[i + 1], top[i + 1], top[i]])


PROPS = {   # plan cm; rotation in degrees about the vertical
    'o3': [
        ('wooden_bowl_01', (1200, 231, 44.2), 0, .9, None),
        ('ceramic_vase_03', (1176, 288, 38), 0, .8, None),
        ('potted_plant_04', (1207, 288, 38), 30, 1.1, None),
        ('book_encyclopedia_set_01', (1536, 540, 62), 90, .8, None),
        ('ceramic_vase_01', (1536, 400, 50), 0, .9, None),
    ],
}


def artwork(seed, w=600, h=840):
    """An abstract print in the room's warm palette: soft organic shapes and a charcoal line, on a paper ground."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32) / w
    img = np.ones((h, w, 3), np.float32) * np.array(lin('#EDE6DA')[:3], np.float32)
    pal = [lin(c)[:3] for c in ('#B5562F', '#D9B88F', '#8C6A4F', '#C98F6A', '#3A3532')]
    def blob(cx, cy, r, col, soft=.004):
        a = np.arctan2(yy - cy, xx - cx)
        rr = r * (1 + .12 * np.sin(3 * a + rng.uniform(0, 6)) + .06 * np.sin(5 * a + rng.uniform(0, 6)))
        d = np.hypot(xx - cx, yy - cy) - rr
        m = np.clip(.5 - d / soft, 0, 1)[..., None]
        return img * (1 - m) + np.array(col, np.float32) * m
    H = h / w                                                       # the canvas is 1 wide and H high
    k = min(1, H)
    for i in range(3):
        img = blob(rng.uniform(.3, .7), rng.uniform(.3, .7) * H, rng.uniform(.16, .28) * k, pal[(seed + i) % 4])
    t = np.linspace(0, 1, 4000)                                     # one charcoal brush line
    cx, cy, r = rng.uniform(.35, .65), rng.uniform(.4, .6) * H, rng.uniform(.2, .32) * k
    px, py = cx + r * np.cos(t * 4 + seed), cy + r * .8 * np.sin(t * 4 + seed)
    line = np.zeros((h, w), np.float32)
    ix, iy = (px * w).astype(int), (py * w).astype(int)
    ok = (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h); line[iy[ok], ix[ok]] = 1
    from scipy.ndimage import gaussian_filter, maximum_filter
    line = np.clip(gaussian_filter(maximum_filter(line, 5), 1.2) * 3, 0, 1)[..., None]
    img = img * (1 - line) + np.array(pal[4], np.float32) * line
    img *= (1 + (rng.standard_normal((h, w, 1)).astype(np.float32) * .015))   # paper grain
    im = bpy.data.images.new('art%d' % seed, w, h)
    rgba = np.concatenate([np.clip(img, 0, 1), np.ones((h, w, 1), np.float32)], -1)[::-1]
    im.pixels.foreach_set(rgba.ravel()); im.pack()
    return im


def hang_print(scene, mats, g, wall, uc, zc, w, h, seed, axis='y', side=1):
    """A print framed in black with a white mat. axis 'y': on a wall along y at x = wall, facing +x (side 1) or -x;
    axis 'x': on a wall along x at y = wall, facing +y (side 1) or -y. uc is its centre along the wall."""
    f, mat = 2.5, 6

    def bx(u0, u1, d0, d1, z0, z1):           # d: distance out from the wall
        w0, w1 = sorted((wall + side * d0, wall + side * d1))
        g.box([w0, u0, z0, w1, u1, z1] if axis == 'y' else [u0, w0, z0, u1, w1, z1], 'black' if d1 > 2 else 'white')

    def P(u, d, z):
        ww = wall + side * d
        return (ww * CM, -u * CM, z * CM) if axis == 'y' else (u * CM, -ww * CM, z * CM)
    u0, u1, z0, z1 = uc - w / 2, uc + w / 2, zc - h / 2, zc + h / 2
    for a, b, c, d in ((u0, u0 + f, z0, z1), (u1 - f, u1, z0, z1), (u0, u1, z0, z0 + f), (u0, u1, z1 - f, z1)):
        bx(a, b, 0, 3, c, d)
    bx(u0 + f, u1 - f, 0, 1.5, z0 + f, z1 - f)
    m, nt, out = mats.new('art%d' % seed)
    a0, a1, c0, c1 = u0 + f + mat, u1 - f - mat, z0 + f + mat, z1 - f - mat
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = artwork(seed, 600, int(600 * (c1 - c0) / (a1 - a0)))
    b = nt.nodes.new('ShaderNodeBsdfPrincipled'); b.inputs['Roughness'].default_value = .8
    nt.links.new(t.outputs['Color'], b.inputs['Base Color']); nt.links.new(b.outputs[0], out.inputs['Surface'])
    # the picture reads left to right as seen from the room
    left, right = (a1, a0) if (axis == 'y') == (side > 0) else (a0, a1)
    me = bpy.data.meshes.new('art')
    me.from_pydata([P(left, 1.6, c0), P(right, 1.6, c0), P(right, 1.6, c1), P(left, 1.6, c1)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name='UVMap')
    for i, c in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[i].uv = c
    me.materials.append(m)
    scene.collection.objects.link(bpy.data.objects.new('art', me))

def pillow(scene, mats, c, w, h, t, yaw, tilt, m, i):
    """A throw pillow: a subdivided box, plump in the middle, leaning back by `tilt` degrees; faces +x before `yaw`."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    me = bpy.data.meshes.new('pillow'); bm.to_mesh(me); bm.free()
    for v in me.vertices:
        v.co.x *= t * CM; v.co.y *= w * CM; v.co.z *= h * CM
    box_uvs(me)
    ob = bpy.data.objects.new('pillow %d' % i, me); scene.collection.objects.link(ob)
    bv = ob.modifiers.new('round', 'BEVEL'); bv.width = t * .35 * CM; bv.segments = 2
    ss = ob.modifiers.new('soft', 'SUBSURF'); ss.levels = ss.render_levels = 2
    cast = ob.modifiers.new('plump', 'CAST'); cast.factor = .1; cast.use_z = cast.use_y = True; cast.use_x = False
    for p in me.polygons:
        p.use_smooth = True
    ob.rotation_euler = (0, math.radians(-tilt), math.radians(yaw))
    ob.location = (c[0] * CM, -c[1] * CM, c[2] * CM)
    me.materials.append(mats.get(m))


def rbox(scene, mats, c, size, yaw, m, bevel=.2):
    """A box turned `yaw` degrees, its base at c: books and the like."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    me = bpy.data.meshes.new('rbox'); bm.to_mesh(me); bm.free()
    for v in me.vertices:
        v.co.x *= size[0] * CM; v.co.y *= size[1] * CM; v.co.z = (v.co.z + .5) * size[2] * CM
    box_uvs(me)
    ob = bpy.data.objects.new('rbox ' + m, me); scene.collection.objects.link(ob)
    bv = ob.modifiers.new('edge', 'BEVEL'); bv.width = bevel * CM; bv.segments = 2
    ob.rotation_euler = (0, 0, math.radians(yaw)); ob.location = (c[0] * CM, -c[1] * CM, c[2] * CM)
    me.materials.append(mats.get(m))


def dress(scene, mats, key):
    """The soft touches a stylist would add, on Amira's own pieces."""
    if key != 'o3':
        return
    pillow(scene, mats, (1031, 250, 71), 44, 44, 13, 4, 14, 'mustard', 1)          # the beige sofa
    pillow(scene, mats, (1029, 205, 69), 40, 40, 12, -8, 16, 'linen', 2)
    soft_box(scene, mats, [1032, 322, 55, 1074, 366, 61], 'throw', 99)             # a folded throw on its seat
    rbox(scene, mats, (1200, 232, 38), (30, 23, 3.4), 8, 'book_a')                 # books on the coffee table
    rbox(scene, mats, (1201, 231, 41.4), (26, 20, 2.8), -5, 'book_b')
    pillow(scene, mats, (187, 668, 78), 62, 50, 16, 90, 14, 'linen', 3)           # the master bed: big pillows behind,
    pillow(scene, mats, (267, 668, 78), 62, 50, 16, 90, 14, 'linen', 4)
    soft_box(scene, mats, [149, 497, 57, 305, 548, 62], 'throwrust', 98)           # a throw across its foot
    soft_box(scene, mats, [312, 848, 52, 428, 888, 56], 'throwsage', 97)           # bedroom 2: a throw, a cushion
    pillow(scene, mats, (370, 1030, 72), 42, 42, 13, 90, 15, 'mustard', 5)


def add_props(scene, key, plants):
    for c, top in plants:
        import_model(scene, 'potted_plant_02', (c[0], c[1], 0), 20, fit_h=top)
    for name, at, rot, s, fit in PROPS.get(key, []):
        import_model(scene, name, at, rot, s, fit)


# ---------------------------------------------------------------- the photographic finish
def to_srgb(x):
    x = np.clip(x, 0, None)
    return np.where(x <= .0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - .055)


def to_linear(x):
    return np.where(x <= .04045, x / 12.92, np.power((x + .055) / 1.055, 2.4))


def load_display(path):
    """An image's pixels as display (sRGB) values: Blender hands a 16-bit PNG back linearised."""
    img = bpy.data.images.load(path)
    w, h = img.size
    a = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)
    if img.is_float:
        a[..., :3] = to_srgb(a[..., :3])
    bpy.data.images.remove(img)
    return a


def finish(path_png, path_jpg):
    a = load_display(path_png)
    h, w = a.shape[:2]
    rgb = to_linear(a[..., :3])                   # the glow is light, so it is added in linear
    from scipy.ndimage import gaussian_filter
    lum = rgb @ np.array([.2126, .7152, .0722], np.float32)
    hi = np.clip(lum - .82, 0, None)[..., None] * rgb / np.maximum(lum[..., None], 1e-4)
    glow = sum(gaussian_filter(hi, (s * w / 1000, s * w / 1000, 0)) * k for s, k in ((4, .35), (16, .25), (48, .2)))
    rgb = rgb + glow * .6
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r2 = ((xx - w / 2) / (w / 2)) ** 2 * .8 + ((yy - h / 2) / (h / 2)) ** 2 * .6
    rgb = rgb * (1 - .16 * np.clip(r2, 0, 1.4))[..., None]
    a[..., :3] = np.clip(to_srgb(rgb), 0, 1)
    out = bpy.data.images.new('out', w, h)
    out.pixels.foreach_set(a.ravel())
    out.filepath_raw = path_jpg; out.file_format = 'JPEG'
    bpy.context.scene.render.image_settings.quality = 92
    out.save_render(path_jpg) if hasattr(out, 'save_render') else out.save()
    bpy.data.images.remove(out)


# ---------------------------------------------------------------- exposure
def auto_ev(scene, ev, target=.40):
    """A quick small render, then the exposure that brings its median to a photographer's middle grey."""
    r, c = scene.render, scene.cycles
    keep = (r.resolution_x, r.resolution_y, c.samples, r.filepath)
    r.resolution_x, r.resolution_y, c.samples = 240, 150, 12
    tmp = os.path.join(bpy.app.tempdir or '/tmp', 'ev.png'); r.filepath = tmp
    scene.view_settings.exposure = ev
    bpy.ops.render.render(write_still=True)
    a = load_display(tmp).reshape(-1, 4)
    med = float(np.median(a[:, 0] * .2126 + a[:, 1] * .7152 + a[:, 2] * .0722))
    r.resolution_x, r.resolution_y, c.samples, r.filepath = keep
    return ev + max(-2.5, min(2.5, 2.2 * math.log2(target / max(med, .02)))), med


# ---------------------------------------------------------------- the scene
def build_scene(key, night):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable('cycles', default_set=True)
    addon_utils.enable('io_scene_gltf2', default_set=True)
    scene = bpy.context.scene
    L = model.build(key)
    plants = take_plants(L)
    lay = model.LAYOUTS[key]
    mats = rc.Mats(night)
    g = HQGeo()
    rc.build_flat(L, g); rc.build_fittings(key, g); rc.build_lights_geo(L, g); rc.build_surroundings(g)
    all_curtains(g, lay)
    if key == 'o3':
        hang_print(scene, mats, g, 972, 219, 152, 50, 70, 3)      # a pair of prints over the sofa
        hang_print(scene, mats, g, 972, 281, 152, 50, 70, 8)
        hang_print(scene, mats, g, 683, 227, 168, 80, 56, 5, axis="x", side=-1)     # one over the master bed
    g.link(mats, scene)
    add_props(scene, key, plants)
    dress(scene, mats, key)
    if night:
        rc.world_night(scene); rc.lights_night(L, scene)
    else:
        az, alt = rc.sun_position(rc.DAY, rc.SITE['lat'], rc.SITE['lon'])
        world_hdri(scene, az, alt); rc.portals(scene, lay)
    return scene


def main():
    rc.Mats.make = make_hq
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', default='o3')
    ap.add_argument('--only', default='')
    ap.add_argument('--times', default='day,night')
    ap.add_argument('--res', default='1920x1200')
    ap.add_argument('--samples', type=int, default=384)
    ap.add_argument('--out', default=os.path.join(ROOT, 'renders'))
    ap.add_argument('--ev', type=float, default=0, help='extra exposure, in stops, for trials')
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    res = tuple(int(v) for v in a.res.split('x'))
    only = set(a.only.split(',')) if a.only else None
    os.makedirs(a.out, exist_ok=True)
    for t in a.times.split(','):
        night = t == 'night'
        views = [v for v in RENDERS if t in v[6] and (not only or v[0] in only)]
        if not views:
            continue
        scene = build_scene(a.plan, night)
        rc.setup(scene, res, a.samples)
        scene.cycles.adaptive_threshold = .01
        scene.render.image_settings.file_format = 'PNG'; scene.render.image_settings.color_depth = '16'
        for v in views:
            key = v[0]
            pos, look, lens = HQ_VIEWS.get(key, v[3:6])
            if key not in HQ_VIEWS and key != 'terrace':
                pos = [pos[0], pos[1], min(pos[2], 125)]          # a photographer's eye height
            k = '%s-%s' % (key, t)
            cam = rc.camera(scene, pos, look, lens, *res)
            if night:
                scene.view_settings.exposure = .6 + a.ev + HQ_EXPOSURE.get(k, EXPOSURE.get(k, 0))
            else:
                ev, med = auto_ev(scene, DAY_EV)
                scene.view_settings.exposure = ev + a.ev + HQ_EXPOSURE.get(k, 0)
                print('EXPOSURE %s: median %.2f at %.1f -> %.2f' % (k, med, DAY_EV, scene.view_settings.exposure), flush=True)
            png = os.path.join(a.out, k + '.png')
            scene.render.filepath = png
            t0 = time.time()
            bpy.ops.render.render(write_still=True)
            finish(png, os.path.join(a.out, k + '.jpg')); os.remove(png)
            print('RENDERED %s in %.0fs' % (k, time.time() - t0), flush=True)
            bpy.data.objects.remove(cam)


if __name__ == '__main__':
    main()
