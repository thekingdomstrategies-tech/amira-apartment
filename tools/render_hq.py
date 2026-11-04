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
    'taupe':     ('wool_boucle', .14, '#7C6C5A', .6, (.9, 1), 1, .4, 0),
    'sgrey':     ('wool_boucle', .14, '#8E8B85', .6, (.9, 1), 1, .4, 0),
    'pouf':      ('wool_boucle', .14, '#705F4E', .6, (.9, 1), 1, .4, 0),
    'mustard':   ('velour_velvet', .25, '#B59A52', .5, (.6, .85), .6, .8, 0),
    'wine':      ('velour_velvet', .25, '#7A1E28', .5, (.6, .85), .6, .8, 0),
    'rug':       ('curly_teddy_natural', .35, '#DCD0BA', .55, (.95, 1), 1.2, .5, 0),
}
SOFT = {'beige', 'fabric', 'linen', 'taupe', 'sgrey', 'pouf', 'mustard', 'wine'}


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


def curtains(g, x0, x1, y, z1=270, gap=0):
    """Sheer curtains drawn to both sides of a window in a wall along x, on a slim black rod."""
    g.box([x0 - 15, y - 1, z1 - 4, x1 + 15, y + 1, z1 - 2], 'black')
    for a, b in ((x0 - 12, x0 + 40), (x1 - 40, x1 + 12)):
        bm = g._bm('sheer')
        n = int((b - a) / 1.2)
        top, bot = [], []
        for i in range(n + 1):
            x = a + (b - a) * i / n
            yy = y + 4 + 3.5 * math.sin(2 * math.pi * (x - a) / 11)
            top.append(bm.verts.new((x * CM, -yy * CM, (z1 - 6) * CM)))
            bot.append(bm.verts.new((x * CM, -(yy + .6) * CM, 1 * CM)))
        for i in range(n):
            bm.faces.new([bot[i], bot[i + 1], top[i + 1], top[i]])


PROPS = {   # plan cm; rotation in degrees about the vertical
    'o3': [
        ('wooden_bowl_01', (1192, 222, 38), 0, 1, None),
        ('ceramic_vase_03', (1176, 288, 38), 0, .8, None),
        ('potted_plant_04', (1214, 282, 38), 30, 1.1, None),
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
    for i in range(3):
        img = blob(rng.uniform(.25, .75), rng.uniform(.3, 1.1), rng.uniform(.16, .3), pal[(seed + i) % 4])
    t = np.linspace(0, 1, 4000)                                     # one charcoal brush line
    cx, cy, r = rng.uniform(.3, .7), rng.uniform(.4, 1.0), rng.uniform(.2, .35)
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


def hang_print(scene, mats, g, x_wall, yc, zc, w, h, seed):
    """A print framed in black with a white mat, on a wall running along y, facing +x."""
    f, mat = 2.5, 6
    y0, y1, z0, z1 = yc - w / 2, yc + w / 2, zc - h / 2, zc + h / 2
    for b in ((y0, y0 + f, z0, z1), (y1 - f, y1, z0, z1), (y0, y1, z0, z0 + f), (y0, y1, z1 - f, z1)):
        g.box([x_wall, b[0], b[2], x_wall + 3, b[1], b[3]], 'black')
    g.box([x_wall, y0 + f, z0 + f, x_wall + 1.5, y1 - f, z1 - f], 'white')
    m, nt, out = mats.new('art%d' % seed)
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = artwork(seed)
    b = nt.nodes.new('ShaderNodeBsdfPrincipled'); b.inputs['Roughness'].default_value = .8
    nt.links.new(t.outputs['Color'], b.inputs['Base Color']); nt.links.new(b.outputs[0], out.inputs['Surface'])
    ay0, ay1, az0, az1 = y0 + f + mat, y1 - f - mat, z0 + f + mat, z1 - f - mat
    X = (x_wall + 1.6) * CM
    me = bpy.data.meshes.new('art')
    me.from_pydata([(X, -ay1 * CM, az0 * CM), (X, -ay0 * CM, az0 * CM), (X, -ay0 * CM, az1 * CM), (X, -ay1 * CM, az1 * CM)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name='UVMap')
    for i, c in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[i].uv = c
    me.materials.append(m)
    scene.collection.objects.link(bpy.data.objects.new('art', me))


def add_props(scene, key, plants):
    for c, top in plants:
        import_model(scene, 'potted_plant_02', (c[0], c[1], 0), 20, fit_h=top)
    for name, at, rot, s, fit in PROPS.get(key, []):
        import_model(scene, name, at, rot, s, fit)


# ---------------------------------------------------------------- the photographic finish
def finish(path_png, path_jpg):
    img = bpy.data.images.load(path_png)
    w, h = img.size
    a = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)
    rgb = a[..., :3]
    from scipy.ndimage import gaussian_filter
    lum = rgb @ np.array([.2126, .7152, .0722], np.float32)
    hi = np.clip(lum - .82, 0, None)[..., None] * rgb / np.maximum(lum[..., None], 1e-4)
    glow = sum(gaussian_filter(hi, (s * w / 1000, s * w / 1000, 0)) * k for s, k in ((4, .35), (16, .25), (48, .2)))
    rgb = rgb + glow * .6
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r2 = ((xx - w / 2) / (w / 2)) ** 2 * .8 + ((yy - h / 2) / (h / 2)) ** 2 * .6
    rgb = rgb * (1 - .16 * np.clip(r2, 0, 1.4))[..., None]
    a[..., :3] = np.clip(rgb, 0, 1)
    out = bpy.data.images.new('out', w, h)
    out.pixels.foreach_set(a.ravel())
    out.filepath_raw = path_jpg; out.file_format = 'JPEG'
    bpy.context.scene.render.image_settings.quality = 92
    out.save_render(path_jpg) if hasattr(out, 'save_render') else out.save()
    bpy.data.images.remove(img)


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
    if key == 'o3':
        curtains(g, 1358, 1546, 186)
        hang_print(scene, mats, g, 972, 219, 152, 50, 70, 3)      # a pair of prints over the sofa
        hang_print(scene, mats, g, 972, 281, 152, 50, 70, 8)
    g.link(mats, scene)
    add_props(scene, key, plants)
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
            k = '%s-%s' % (key, t)
            scene.view_settings.exposure = (.6 if night else DAY_EV) + a.ev + HQ_EXPOSURE.get(k, EXPOSURE.get(k, 0))
            cam = rc.camera(scene, pos, look, lens, *res)
            png = os.path.join(a.out, k + '.png')
            scene.render.filepath = png
            t0 = time.time()
            bpy.ops.render.render(write_still=True)
            finish(png, os.path.join(a.out, k + '.jpg')); os.remove(png)
            print('RENDERED %s in %.0fs' % (k, time.time() - t0), flush=True)
            bpy.data.objects.remove(cam)


if __name__ == '__main__':
    main()
