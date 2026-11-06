"""The compound round E07 for the high-quality renders: what the terrace looks out on.

The brochure's own pictures of the apartment buildings (pages 45 and 53) set the look: light grey rendered walls,
charcoal recessed bays, a white band at every floor, tall dark-framed windows with pale curtains behind, a deep
balcony bay in the middle of each side with glass railings, slatted charcoal panels at the corners, a set-back top
floor. Every block is the same floor plate, so one block is built and placed 29 times (Cycles instances it).

The ground comes from the masterplan (tools/compound_map.py -> data/ground.png, data/compound.json): lawn, paved paths
and pool decks, the lagoon pools, the roads. Hedges ring each block; trees stand where the masterplan draws a canopy
(Poly Haven's CC0 jacaranda and a small olive-like tree), and date palms, built here leaflet by leaflet, line the decks.
"""
import json, math, os, random

import bpy, bmesh
from mathutils import Vector, Matrix

import model

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, '.assets')
CM = .01
GROUND = -model.ELEV * CM            # the garden, m, relative to the apartment's floor
STOREY = model.STOREY * CM
FLOORS = model.FLOOR_NO + 1          # ground + five: E07 and its neighbours are the same height
PLATE = (31.6, 23.0)               # an apartment block's floor plate, m (tools/surroundings.py)
HAZE = ('#C9D3DD', .11, 900)         # the horizon's colour and brightness (the photographed sky's), and the distance (m)
                                     # over which the air thickens


def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4) for v in c) + (1,)


# ---------------------------------------------------------------- materials
class M:
    def __init__(self):
        self.m = {}

    def __getitem__(self, k):
        if k not in self.m:
            self.m[k] = getattr(self, 'make_' + k)()
        return self.m[k]

    @staticmethod
    def new(name):
        m = bpy.data.materials.new('cmp ' + name)
        m.use_nodes = True
        nt = m.node_tree
        for n in list(nt.nodes):
            if n.type != 'OUTPUT_MATERIAL':
                nt.nodes.remove(n)
        return m, nt, nt.nodes['Material Output']

    @staticmethod
    def haze(nt, shader, out):
        """Mix toward the horizon's colour with distance, as the old massing did."""
        N, L = nt.nodes.new, nt.links.new
        cam = N('ShaderNodeCameraData')
        dv = N('ShaderNodeMath'); dv.operation = 'DIVIDE'; L(cam.outputs['View Distance'], dv.inputs[0]); dv.inputs[1].default_value = -HAZE[2]
        ex = N('ShaderNodeMath'); ex.operation = 'EXPONENT'; L(dv.outputs[0], ex.inputs[0])
        f = N('ShaderNodeMath'); f.operation = 'SUBTRACT'; f.inputs[0].default_value = 1; L(ex.outputs[0], f.inputs[1])
        em = N('ShaderNodeEmission'); em.inputs['Color'].default_value = lin(HAZE[0]); em.inputs['Strength'].default_value = HAZE[1]
        mx = N('ShaderNodeMixShader'); L(f.outputs[0], mx.inputs[0]); L(shader, mx.inputs[1]); L(em.outputs[0], mx.inputs[2])
        L(mx.outputs[0], out.inputs['Surface'])

    @staticmethod
    def tex(nt, name, kind, vec, noncolor=False):
        p = os.path.join(ASSETS, 'tex', name, kind + '.jpg')
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(p, check_existing=True)
        if noncolor:
            n.image.colorspace_settings.name = 'Non-Color'
        n.interpolation = 'Cubic'
        nt.links.new(vec, n.inputs['Vector'])
        return n

    def render(self, name, tint, size=2.0, rough=.88, bump=.25):
        """Rendered (plastered) wall: the photo plaster's light and dark, tinted; world-space so instances differ."""
        m, nt, out = self.new(name)
        N, L = nt.nodes.new, nt.links.new
        tc = N('ShaderNodeTexCoord')
        mp = N('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / size,) * 3
        L(tc.outputs['UV'], mp.inputs['Vector'])
        d = self.tex(nt, 'white_plaster_02', 'diff', mp.outputs[0])
        bw = N('ShaderNodeRGBToBW'); L(d.outputs['Color'], bw.inputs['Color'])
        mr = N('ShaderNodeMapRange'); mr.inputs['From Max'].default_value = .75; mr.inputs['To Min'].default_value = .82
        mr.clamp = False; L(bw.outputs['Val'], mr.inputs['Value'])
        # weathering: a faint, large mottle, a little darker low down and where rain runs off the slabs
        nz = N('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = .15; nz.inputs['Detail'].default_value = 4
        L(tc.outputs['Object'], nz.inputs['Vector'])
        mo = N('ShaderNodeMapRange'); mo.inputs['From Min'].default_value = .35; mo.inputs['From Max'].default_value = .65
        mo.inputs['To Min'].default_value = .94; mo.inputs['To Max'].default_value = 1.03; L(nz.outputs['Fac'], mo.inputs['Value'])
        m1 = N('ShaderNodeMath'); m1.operation = 'MULTIPLY'; L(mr.outputs['Result'], m1.inputs[0]); L(mo.outputs['Result'], m1.inputs[1])
        mx = N('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1
        mx.inputs[6].default_value = lin(tint); L(m1.outputs[0], mx.inputs[7])
        b = N('ShaderNodeBsdfPrincipled'); L(mx.outputs[2], b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = rough
        bp = N('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump; bp.inputs['Distance'].default_value = .002
        L(bw.outputs['Val'], bp.inputs['Height']); L(bp.outputs['Normal'], b.inputs['Normal'])
        self.haze(nt, b.outputs[0], out)
        return m

    def make_wall(self):
        return self.render('wall', '#D9DAD7')

    def make_slab(self):
        return self.render('slab', '#F0EFEB', rough=.8)

    def make_dark(self):
        return self.render('dark', '#45464A', rough=.75)

    def make_roof(self):
        return self.render('roof', '#BDBAB2', size=3, rough=.95, bump=.5)

    def make_louvre(self):
        """Charcoal aluminium slats, 12 cm apart, standing proud of a dark backing: stripes, their shading and a sheen."""
        m, nt, out = self.new('louvre')
        N, L = nt.nodes.new, nt.links.new
        tc = N('ShaderNodeTexCoord')
        sep = N('ShaderNodeSeparateXYZ'); L(tc.outputs['Object'], sep.inputs[0])
        ad = N('ShaderNodeMath'); ad.operation = 'ADD'; L(sep.outputs['X'], ad.inputs[0]); L(sep.outputs['Y'], ad.inputs[1])
        w = N('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = 'X'; w.wave_profile = 'SAW'
        w.inputs['Scale'].default_value = 1
        cx = N('ShaderNodeCombineXYZ'); mul = N('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 1 / .12
        L(ad.outputs[0], mul.inputs[0]); L(mul.outputs[0], cx.inputs['X']); L(cx.outputs[0], w.inputs['Vector'])
        g = N('ShaderNodeMath'); g.operation = 'GREATER_THAN'; g.inputs[1].default_value = .35; L(w.outputs['Fac'], g.inputs[0])
        col = N('ShaderNodeMix'); col.data_type = 'RGBA'; L(g.outputs[0], col.inputs['Factor'])
        col.inputs[6].default_value = lin('#1C1D20'); col.inputs[7].default_value = lin('#3E4044')
        b = N('ShaderNodeBsdfPrincipled'); L(col.outputs[2], b.inputs['Base Color'])
        b.inputs['Metallic'].default_value = .5; b.inputs['Roughness'].default_value = .42
        bp = N('ShaderNodeBump'); bp.inputs['Strength'].default_value = .8; bp.inputs['Distance'].default_value = .02
        L(w.outputs['Fac'], bp.inputs['Height']); L(bp.outputs['Normal'], b.inputs['Normal'])
        self.haze(nt, b.outputs[0], out)
        return m

    def make_frame(self):
        m, nt, out = self.new('frame')
        b = nt.nodes.new('ShaderNodeBsdfPrincipled'); b.inputs['Base Color'].default_value = lin('#2B2D30')
        b.inputs['Metallic'].default_value = .6; b.inputs['Roughness'].default_value = .38
        self.haze(nt, b.outputs[0], out)
        return m

    def make_window(self):
        """Glazing with the room behind it: a coat of glass over a pale curtain, a sheer, or the dark of a room,
        chosen per pane from its position (so every window, and every block, differs)."""
        m, nt, out = self.new('window')
        N, L = nt.nodes.new, nt.links.new
        geo = N('ShaderNodeNewGeometry')
        sc = N('ShaderNodeVectorMath'); sc.operation = 'SCALE'; sc.inputs['Scale'].default_value = 1 / 1.4
        L(geo.outputs['Position'], sc.inputs[0])
        fl = N('ShaderNodeVectorMath'); fl.operation = 'FLOOR'; L(sc.outputs[0], fl.inputs[0])
        wn = N('ShaderNodeTexWhiteNoise'); wn.noise_dimensions = '3D'; L(fl.outputs[0], wn.inputs['Vector'])
        ramp = N('ShaderNodeValToRGB'); L(wn.outputs['Value'], ramp.inputs['Fac'])
        e = ramp.color_ramp.elements
        e[0].position = 0; e[0].color = lin('#17191C')
        e[1].position = .42; e[1].color = lin('#262A2E')
        for pos, c in ((.45, '#9C968C'), (.7, '#C9C3B8'), (.9, '#DCD6CB')):
            x = e.new(pos); x.color = lin(c)
        ramp.color_ramp.interpolation = 'CONSTANT'
        # the curtain hangs in folds: vertical stripes in its brightness
        tc = N('ShaderNodeTexCoord')
        wv = N('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'X'; wv.inputs['Scale'].default_value = 9
        L(tc.outputs['Object'], wv.inputs['Vector'])
        fm = N('ShaderNodeMapRange'); fm.inputs['To Min'].default_value = .8; fm.inputs['To Max'].default_value = 1.05
        L(wv.outputs['Fac'], fm.inputs['Value'])
        mx = N('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1
        L(ramp.outputs['Color'], mx.inputs[6]); L(fm.outputs['Result'], mx.inputs[7])
        b = N('ShaderNodeBsdfPrincipled'); L(mx.outputs[2], b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = .85; b.inputs['Specular IOR Level'].default_value = 0
        b.inputs['Coat Weight'].default_value = 1; b.inputs['Coat Roughness'].default_value = .02; b.inputs['Coat IOR'].default_value = 1.52
        b.inputs['Coat Tint'].default_value = lin('#D8E2E4')
        self.haze(nt, b.outputs[0], out)
        return m

    def make_railglass(self):
        m, nt, out = self.new('railglass')
        g = nt.nodes.new('ShaderNodeBsdfPrincipled'); g.inputs['Base Color'].default_value = lin('#DCE9E6')
        g.inputs['Transmission Weight'].default_value = 1; g.inputs['Roughness'].default_value = .02; g.inputs['IOR'].default_value = 1.5
        # thin glass: no refraction offset, so light passes straight through
        tp = nt.nodes.new('ShaderNodeBsdfTransparent'); tp.inputs['Color'].default_value = lin('#D5E3E0')
        gl = nt.nodes.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = .02
        fr = nt.nodes.new('ShaderNodeFresnel'); fr.inputs['IOR'].default_value = 1.5
        mx = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(fr.outputs[0], mx.inputs[0]); nt.links.new(tp.outputs[0], mx.inputs[1]); nt.links.new(gl.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs['Surface'])
        return m

    def make_hedge(self):
        """Clipped box hedge: leaf-sized cells of light and dark green, deeply bumped."""
        m, nt, out = self.new('hedge')
        N, L = nt.nodes.new, nt.links.new
        tc = N('ShaderNodeTexCoord')
        vo = N('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 22; L(tc.outputs['Object'], vo.inputs['Vector'])
        nz = N('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = .6; nz.inputs['Detail'].default_value = 3
        L(tc.outputs['Object'], nz.inputs['Vector'])
        r = N('ShaderNodeValToRGB'); L(vo.outputs['Color'], r.inputs['Fac'])
        r.color_ramp.elements[0].color = lin('#22361A'); r.color_ramp.elements[1].color = lin('#4F6B2E')
        mx = N('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = .5
        L(r.outputs['Color'], mx.inputs[6]); L(nz.outputs['Color'], mx.inputs[7])
        b = N('ShaderNodeBsdfPrincipled'); L(mx.outputs[2], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .7
        b.inputs['Subsurface Weight'].default_value = .15
        bp = N('ShaderNodeBump'); bp.inputs['Strength'].default_value = 1; bp.inputs['Distance'].default_value = .05
        L(vo.outputs['Distance'], bp.inputs['Height']); L(bp.outputs['Normal'], b.inputs['Normal'])
        self.haze(nt, b.outputs[0], out)
        return m

    def make_palm_leaf(self):
        m, nt, out = self.new('palm leaf')
        N, L = nt.nodes.new, nt.links.new
        oi = N('ShaderNodeObjectInfo')
        att = N('ShaderNodeAttribute'); att.attribute_name = 'age'
        r = N('ShaderNodeValToRGB'); L(att.outputs['Fac'], r.inputs['Fac'])
        e = r.color_ramp.elements
        e[0].color = lin('#6E8A3E'); e[1].position = .85; e[1].color = lin('#46602B')
        x = e.new(1); x.color = lin('#8C7A4A')
        hue = N('ShaderNodeHueSaturation'); L(r.outputs['Color'], hue.inputs['Color'])
        hm = N('ShaderNodeMapRange'); hm.inputs['To Min'].default_value = .47; hm.inputs['To Max'].default_value = .53
        L(oi.outputs['Random'], hm.inputs['Value']); L(hm.outputs['Result'], hue.inputs['Hue'])
        b = N('ShaderNodeBsdfPrincipled'); L(hue.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = .45; b.inputs['Specular IOR Level'].default_value = .45
        t = N('ShaderNodeBsdfTranslucent'); L(hue.outputs['Color'], t.inputs['Color'])
        mx = N('ShaderNodeMixShader'); mx.inputs[0].default_value = .25
        L(b.outputs[0], mx.inputs[1]); L(t.outputs[0], mx.inputs[2])
        self.haze(nt, mx.outputs[0], out)
        return m

    def make_palm_trunk(self):
        """The trunk's ring of old leaf bases: bands round it, broken up, grey-brown."""
        m, nt, out = self.new('palm trunk')
        N, L = nt.nodes.new, nt.links.new
        tc = N('ShaderNodeTexCoord')
        w = N('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = 'Z'; w.inputs['Scale'].default_value = 4.5
        w.inputs['Distortion'].default_value = 3; w.inputs['Detail'].default_value = 3
        L(tc.outputs['Object'], w.inputs['Vector'])
        r = N('ShaderNodeValToRGB'); L(w.outputs['Fac'], r.inputs['Fac'])
        r.color_ramp.elements[0].color = lin('#4A3F33'); r.color_ramp.elements[1].color = lin('#9A8B76')
        b = N('ShaderNodeBsdfPrincipled'); L(r.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .9
        bp = N('ShaderNodeBump'); bp.inputs['Strength'].default_value = 1; bp.inputs['Distance'].default_value = .03
        L(w.outputs['Fac'], bp.inputs['Height']); L(bp.outputs['Normal'], b.inputs['Normal'])
        self.haze(nt, b.outputs[0], out)
        return m

    def make_ground(self):
        """Lawn, paving, road and pool, from the masterplan map."""
        m, nt, out = self.new('ground')
        N, L = nt.nodes.new, nt.links.new
        uv = N('ShaderNodeUVMap'); uv.uv_map = 'map'
        img = N('ShaderNodeTexImage'); img.image = bpy.data.images.load(os.path.join(ROOT, 'data', 'ground.png'), check_existing=True)
        img.image.colorspace_settings.name = 'Non-Color'; img.image.alpha_mode = 'CHANNEL_PACKED'
        img.interpolation = 'Cubic'; img.extension = 'CLIP'
        L(uv.outputs['UV'], img.inputs['Vector'])
        sp = N('ShaderNodeSeparateColor'); L(img.outputs['Color'], sp.inputs['Color'])
        Wt, Pv, Rd, Dp = sp.outputs['Red'], sp.outputs['Green'], sp.outputs['Blue'], img.outputs['Alpha']
        tc = N('ShaderNodeTexCoord')

        def surface(tex, size, tint, keep, rough, nstr, big=None):
            mp = N('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / size,) * 3
            L(tc.outputs['Object'], mp.inputs['Vector'])
            d = self.tex(nt, tex, 'diff', mp.outputs[0])
            bw = N('ShaderNodeRGBToBW'); L(d.outputs['Color'], bw.inputs['Color'])
            mr = N('ShaderNodeMapRange'); mr.inputs['From Max'].default_value = .45; mr.inputs['To Min'].default_value = 1 - keep
            mr.clamp = False; L(bw.outputs['Val'], mr.inputs['Value'])
            mx = N('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1
            mx.inputs[6].default_value = lin(tint); L(mr.outputs['Result'], mx.inputs[7])
            col = mx.outputs[2]
            if big:     # large patches: the lawn is never one even green
                nz = N('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = .04; nz.inputs['Detail'].default_value = 5
                L(tc.outputs['Object'], nz.inputs['Vector'])
                r = N('ShaderNodeValToRGB'); L(nz.outputs['Fac'], r.inputs['Fac'])
                r.color_ramp.elements[0].position = .3; r.color_ramp.elements[0].color = lin(big[0])
                r.color_ramp.elements[1].position = .7; r.color_ramp.elements[1].color = lin(big[1])
                m2 = N('ShaderNodeMix'); m2.data_type = 'RGBA'; m2.blend_type = 'MULTIPLY'; m2.inputs['Factor'].default_value = 1
                L(col, m2.inputs[6]); L(r.outputs['Color'], m2.inputs[7]); col = m2.outputs[2]
            b = N('ShaderNodeBsdfPrincipled'); L(col, b.inputs['Base Color']); b.inputs['Roughness'].default_value = rough
            nm = N('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = nstr
            nt_ = self.tex(nt, tex, 'nor', mp.outputs[0], True)
            L(nt_.outputs['Color'], nm.inputs['Color']); L(nm.outputs['Normal'], b.inputs['Normal'])
            return b.outputs[0]

        lawn = surface('leafy_grass', 1.6, '#5F8A3A', .7, .9, 1, big=('#CFD9B8', '#FFFFFF'))
        pave = surface('concrete_pavers_02', 1.8, '#C9B795', .55, .7, .8)
        road = surface('asphalt_02', 4, '#55565A', .6, .8, .6)
        # the pools: clear water over pale tiles, turquoise in the shallows, deeper blue in the middle, a ripple on top
        col = N('ShaderNodeMix'); col.data_type = 'RGBA'; L(Dp, col.inputs['Factor'])
        col.inputs[6].default_value = lin('#62C9D3'); col.inputs[7].default_value = lin('#1F86A9')
        cv = N('ShaderNodeTexVoronoi'); cv.feature = 'DISTANCE_TO_EDGE'; cv.inputs['Scale'].default_value = .9
        L(tc.outputs['Object'], cv.inputs['Vector'])
        cm = N('ShaderNodeMapRange'); cm.inputs['From Max'].default_value = .09; cm.inputs['To Min'].default_value = 1.35
        cm.inputs['To Max'].default_value = 1; L(cv.outputs['Distance'], cm.inputs['Value'])
        cmx = N('ShaderNodeMix'); cmx.data_type = 'RGBA'; cmx.blend_type = 'MULTIPLY'; cmx.inputs['Factor'].default_value = 1
        L(col.outputs[2], cmx.inputs[6]); L(cm.outputs['Result'], cmx.inputs[7])
        wb = N('ShaderNodeBsdfPrincipled'); L(cmx.outputs[2], wb.inputs['Base Color'])
        wb.inputs['Roughness'].default_value = .03; wb.inputs['Specular IOR Level'].default_value = .5; wb.inputs['IOR'].default_value = 1.33
        wb.inputs['Coat Weight'].default_value = 1; wb.inputs['Coat Roughness'].default_value = .01; wb.inputs['Coat IOR'].default_value = 1.33
        rz = N('ShaderNodeTexNoise'); rz.inputs['Scale'].default_value = 1.2; rz.inputs['Detail'].default_value = 6; rz.inputs['Roughness'].default_value = .6
        L(tc.outputs['Object'], rz.inputs['Vector'])
        wbp = N('ShaderNodeBump'); wbp.inputs['Strength'].default_value = .25; wbp.inputs['Distance'].default_value = .02
        L(rz.outputs['Fac'], wbp.inputs['Height']); L(wbp.outputs['Normal'], wb.inputs['Coat Normal'])
        # a white stone coping round each pool, where the map's water fades out
        cp = N('ShaderNodeMath'); cp.operation = 'PINGPONG'; cp.inputs[1].default_value = .5; L(Wt, cp.inputs[0])
        cpm = N('ShaderNodeMath'); cpm.operation = 'GREATER_THAN'; cpm.inputs[1].default_value = .3; L(cp.outputs[0], cpm.inputs[0])
        cb = N('ShaderNodeBsdfPrincipled'); cb.inputs['Base Color'].default_value = lin('#EEE9DE'); cb.inputs['Roughness'].default_value = .6

        def mixs(fac, a, b):
            x = N('ShaderNodeMixShader'); L(fac, x.inputs[0]); L(a, x.inputs[1]); L(b, x.inputs[2])
            return x.outputs[0]

        s = mixs(Pv, lawn, pave)
        s = mixs(Rd, s, road)
        wcl = N('ShaderNodeMath'); wcl.operation = 'GREATER_THAN'; wcl.inputs[1].default_value = .5; L(Wt, wcl.inputs[0])
        s = mixs(wcl.outputs[0], s, wb.outputs[0])
        s = mixs(cpm.outputs[0], s, cb.outputs[0])
        self.haze(nt, s, out)
        return m


# ---------------------------------------------------------------- geometry helpers
class Mesh:
    """Boxes by material, in metres, gathered into one object per material."""
    def __init__(self):
        self.bm = {}

    def box(self, x0, y0, z0, x1, y1, z1, m):
        if x1 - x0 <= 1e-4 or y1 - y0 <= 1e-4 or z1 - z0 <= 1e-4:
            return
        bm = self.bm.setdefault(m, bmesh.new())
        v = [bm.verts.new(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
        for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            bm.faces.new([v[i] for i in f])

    def objects(self, mats, coll, name, uvs=True):
        out = []
        for m, bm in self.bm.items():
            me = bpy.data.meshes.new('%s %s' % (name, m))
            bm.to_mesh(me); bm.free()
            if uvs:
                uvl = me.uv_layers.new(name='UVMap')
                for p in me.polygons:
                    ax = max(range(3), key=lambda i: abs(p.normal[i]))
                    for li in p.loop_indices:
                        co = me.vertices[me.loops[li].vertex_index].co
                        uvl.data[li].uv = [(co.y, co.z), (co.x, co.z), (co.x, co.y)][ax]
            me.materials.append(mats[m])
            ob = bpy.data.objects.new(me.name, me); coll.objects.link(ob); out.append(ob)
        self.bm = {}
        return out


# ---------------------------------------------------------------- an apartment block (Model A), centred, long side on X
def side_layout(L, long_side):
    """Bays along one side, from one corner to the other: (kind, start, end) in m from the corner."""
    c, bw = 2.4, (7.0 if long_side else 3.6)
    rest = (L - 2 * c - bw) / 2
    n = max(1, round(rest / 3.3)); w = rest / n
    bays = [('louvre', 0, c)]
    x = c
    for _ in range(n):
        bays.append(('win', x, x + w)); x += w
    bays.append(('loggia', x, x + bw)); x += bw
    for _ in range(n):
        bays.append(('win', x, x + w)); x += w
    bays.append(('louvre', x, L))
    return bays


def block(mats, coll):
    X, Y = PLATE[0] / 2, PLATE[1] / 2
    H, h = FLOORS * STOREY, STOREY
    D = 1.5                       # how deep the loggias go
    g = Mesh()
    sides = []                    # (origin, along, out, length, long?)
    sides.append((Vector((-X, -Y, 0)), Vector((1, 0, 0)), Vector((0, -1, 0)), 2 * X, True))
    sides.append((Vector((X, Y, 0)), Vector((-1, 0, 0)), Vector((0, 1, 0)), 2 * X, True))
    sides.append((Vector((X, -Y, 0)), Vector((0, 1, 0)), Vector((1, 0, 0)), 2 * Y, False))
    sides.append((Vector((-X, Y, 0)), Vector((0, -1, 0)), Vector((-1, 0, 0)), 2 * Y, False))

    def put(o, al, ou, a0, a1, d0, d1, z0, z1, m):
        """A box on a side: a0..a1 along it, d0..d1 out from its wall plane (negative: in), z0..z1 up."""
        p = [o + al * a + ou * d for a in (a0, a1) for d in (d0, d1)]
        xs, ys = [q.x for q in p], [q.y for q in p]
        g.box(min(xs), min(ys), z0, max(xs), max(ys), z1, m)

    # the core, notched by the loggias; round each window the wall is cut back to a 15 cm reveal
    g.box(-X + D, -Y + D, 0, X - D, Y - D, H, 'wall')
    for o, al, ou, Ls, lg in sides:
        for kind, a0, a1 in side_layout(Ls, lg):
            q0, q1 = (a0, a1) if lg else (max(a0, D), min(a1, Ls - D))     # the long sides own the corners
            if q1 - q0 < .01 or kind == 'loggia':
                if kind == 'loggia':
                    put(o, al, ou, a0, a1, -D, -D + .02, 0, H, 'dark')         # the loggia's back wall
                continue
            if kind == 'louvre':
                put(o, al, ou, q0, q1, -D, 0, 0, H, 'louvre'); continue
            w = a1 - a0; ww = min(1.8, w * .55); m0 = a0 + (w - ww) / 2; m1 = m0 + ww
            for f in range(FLOORS):
                z = f * h; s0, s1 = z + (.9 if f else .3), z + 2.45
                put(o, al, ou, q0, m0 - .06, -D, 0, z, z + h, 'wall'); put(o, al, ou, m1 + .06, q1, -D, 0, z, z + h, 'wall')
                put(o, al, ou, m0 - .06, m1 + .06, -D, 0, z, s0 - .06, 'wall'); put(o, al, ou, m0 - .06, m1 + .06, -D, 0, s1 + .06, z + h, 'wall')
                put(o, al, ou, m0 - .06, m1 + .06, -D, -.16, s0 - .06, s1 + .06, 'wall')
    for o, al, ou, Ls, lg in sides:
        bays = side_layout(Ls, lg)
        for kind, a0, a1 in bays:
            w = a1 - a0
            for f in range(FLOORS):
                z = f * h
                if kind == 'win':
                    ww = min(1.8, w * .55); m0 = a0 + (w - ww) / 2; m1 = m0 + ww
                    s0, s1 = z + (.9 if f else .3), z + 2.45
                    put(o, al, ou, m0, m1, -.16, -.14, s0, s1, 'window')                  # glass, set in
                    for q0, q1, z0, z1 in ((m0 - .06, m0, s0, s1), (m1, m1 + .06, s0, s1), (m0 - .06, m1 + .06, s0 - .06, s0),
                                           (m0 - .06, m1 + .06, s1, s1 + .06), ((m0 + m1) / 2 - .03, (m0 + m1) / 2 + .03, s0, s1)):
                        put(o, al, ou, q0, q1, -.16, -.1, z0, z1, 'frame')
                    put(o, al, ou, m0 - .1, m1 + .1, -.16, .04, s0 - .1, s0 - .04, 'slab')     # the sill
                    if w > 3:   # a dark panel beside each window, as on the brochure's elevations
                        put(o, al, ou, m1 + .12, m1 + .5, 0, .015, z + .2, z + h - .2, 'dark')
                elif kind == 'loggia':
                    # sliding doors at the back, the floor slab running out, a glass railing at the front
                    put(o, al, ou, a0 + .3, a1 - .3, -D + .02, -D + .05, z + .2, z + 2.6, 'window')
                    for q in (a0 + .3, (a0 + a1) / 2, a1 - .3):
                        put(o, al, ou, q - .03, q + .03, -D + .02, -D + .08, z + .2, z + 2.6, 'frame')
                    if f:
                        put(o, al, ou, a0, a1, -D, .3, z - .11, z + .11, 'slab')
                        put(o, al, ou, a0 + .05, a1 - .05, .18, .2, z + .11, z + 1.15, 'railglass')
                        put(o, al, ou, a0 + .05, a1 - .05, .17, .21, z + 1.11, z + 1.16, 'frame')
                    else:   # the entrance lobby
                        put(o, al, ou, a0 + .3, a1 - .3, -D + .05, -D + .07, .15, 2.9, 'window')
        # white fins framing the loggia and the corners, full height
        for kind, a0, a1 in bays:
            if kind != 'win':
                for a in (a0, a1):
                    if .01 < a < Ls - .01:
                        put(o, al, ou, a - .12, a + .12, -D * (kind == 'loggia'), .3, 0, H + .1, 'slab')
    # a white band at every floor and the roof's coping; a dark plinth
    for f in range(1, FLOORS + 1):
        z = f * h
        t = .45 if f == FLOORS else .22
        g.box(-X - .3, -Y - .3, z - t / 2, X + .3, -Y + D, z + t / 2, 'slab')
        g.box(-X - .3, Y - D, z - t / 2, X + .3, Y + .3, z + t / 2, 'slab')
        g.box(-X - .3, -Y + D, z - t / 2, -X + D, Y - D, z + t / 2, 'slab')
        g.box(X - D, -Y + D, z - t / 2, X + .3, Y - D, z + t / 2, 'slab')
    g.box(-X - .02, -Y - .02, -.3, X + .02, Y + .02, .3, 'dark')
    g.box(-X + D, -Y + D, H, X - D, Y - D, H + .02, 'roof')
    # the set-back top floor, with its own windows and coping
    k = .62
    px, py = X * k, Y * k
    g.box(-px, -py, H, px, py, H + h, 'wall')
    for o, al, ou, Ls in ((Vector((-px, -py, 0)), Vector((1, 0, 0)), Vector((0, -1, 0)), 2 * px),
                          (Vector((px, py, 0)), Vector((-1, 0, 0)), Vector((0, 1, 0)), 2 * px),
                          (Vector((px, -py, 0)), Vector((0, 1, 0)), Vector((1, 0, 0)), 2 * py),
                          (Vector((-px, py, 0)), Vector((0, -1, 0)), Vector((-1, 0, 0)), 2 * py)):
        n = max(2, round(Ls / 3.6))
        for i in range(n):
            c = (i + .5) * Ls / n
            put(o, al, ou, c - .8, c + .8, -.02, .02, H + .25, H + 2.5, 'window')
            put(o, al, ou, c - .86, c + .86, .02, .05, H + 2.5, H + 2.56, 'frame')
    g.box(-px - .25, -py - .25, H + h - .1, px + .25, py + .25, H + h + .3, 'slab')
    g.box(-px, -py, H + h + .3, px, py, H + h + .32, 'roof')
    return g.objects(mats, coll, 'block')


# ---------------------------------------------------------------- a date palm
def palm(mats, coll, seed, height):
    rnd = random.Random(seed)
    tr = bmesh.new()
    lean = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)).normalized() * rnd.uniform(.2, .7)
    rings, seg = 30, 12
    vs = []
    for j in range(rings + 1):
        t = j / rings
        c = lean * t * t + Vector((0, 0, height * t))
        r = .3 - .08 * t + (.12 * (t - .93) / .07 if t > .93 else 0) + (.12 * (1 - t / .05) if t < .05 else 0)
        vs.append([tr.verts.new(c + Vector((math.cos(2 * math.pi * i / seg) * r, math.sin(2 * math.pi * i / seg) * r, 0))) for i in range(seg)])
    for a, b in zip(vs, vs[1:]):
        for i in range(seg):
            tr.faces.new([a[i], a[(i + 1) % seg], b[(i + 1) % seg], b[i]])
    top = lean + Vector((0, 0, height))
    me = bpy.data.meshes.new('palm trunk'); tr.to_mesh(me); tr.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mats['palm_trunk'])
    ob = bpy.data.objects.new('palm trunk', me); coll.objects.link(ob)

    lf = bmesh.new()
    age = lf.verts.layers.float.new('age')
    n = rnd.randint(20, 26)
    for i in range(n):
        a = i / n
        az = i * 2.39996 + rnd.uniform(-.15, .15)
        el = math.radians(65 - 105 * a + rnd.uniform(-8, 8))        # young fronds up, old ones hanging
        Lf = rnd.uniform(3.4, 4.2) * (1 - .15 * abs(a - .5))
        sag = .12 + .34 * a
        d0 = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
        side0 = Vector((-math.sin(az), math.cos(az), 0))
        steps = 72
        prev = None
        pts = []
        for k in range(steps + 1):
            s = Lf * k / steps
            pts.append(top + d0 * s + Vector((0, 0, -sag * s * s)))
        for k in range(4, steps + 1):
            p = pts[k]; tng = (pts[k] - pts[k - 1]).normalized()
            up = tng.cross(side0).normalized()
            if up.z < 0:
                up = -up
            u = k / steps
            ln0 = (.15 + .55 * math.sin(math.pi * min(1, u * 1.1)) ** .7) * (1 - .3 * u)
            for sgn in (-1, 1):
                if rnd.random() < .07:       # a leaflet torn off here and there
                    continue
                ln = ln0 * rnd.uniform(.8, 1.15)
                sd = tng.cross(up).normalized() * sgn
                dirv = (sd * .8 + up * rnd.uniform(.15, .5) + tng * rnd.uniform(.25, .45)).normalized()
                tip = p + dirv * ln + Vector((0, 0, -rnd.uniform(.3, .6) * ln))
                mid = p + dirv * ln * .5 + Vector((0, 0, -.05 * ln))
                wv = tng * .03
                q = [lf.verts.new(v) for v in (p - wv, p + wv, mid + wv, mid - wv)]
                t2 = lf.verts.new(tip)
                lf.faces.new(q); lf.faces.new([q[3], q[2], t2])
                for v in q + [t2]:
                    v[age] = min(1, a * 1.05 + rnd.uniform(-.05, .05)) if a < .9 else 1
        # the rachis itself
        for k in range(steps):
            p, q = pts[k], pts[k + 1]
            w = .03 * (1 - k / steps) + .008
            sd = side0 * w
            f = [lf.verts.new(v) for v in (p - sd, p + sd, q + sd, q - sd)]
            lf.faces.new(f)
            for v in f:
                v[age] = min(1, a)
    me = bpy.data.meshes.new('palm fronds'); lf.to_mesh(me); lf.free()
    me.materials.append(mats['palm_leaf'])
    ob = bpy.data.objects.new('palm fronds', me); coll.objects.link(ob)


# ---------------------------------------------------------------- the imported trees
def import_tree(coll, name, tint=None):
    path = os.path.join(ASSETS, 'models', name, name + '.gltf')
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
    if tint:
        done = set()
        for o in new:
            for i, s in enumerate(getattr(o, 'material_slots', [])):
                if s.material and s.material.name not in done and 'leaves' in s.material.name.lower():
                    m = s.material.copy(); s.material = m; done.add(m.name)
                    nt = m.node_tree
                    b = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
                    lk = b.inputs['Base Color'].links
                    if lk:
                        src = lk[0].from_socket
                        hs = nt.nodes.new('ShaderNodeHueSaturation'); hs.inputs['Hue'].default_value = tint[0]
                        hs.inputs['Saturation'].default_value = tint[1]; hs.inputs['Value'].default_value = tint[2]
                        nt.links.new(src, hs.inputs['Color']); nt.links.new(hs.outputs[0], b.inputs['Base Color'])
    # the model's base at the origin
    bpy.context.view_layer.update()
    zs = [(o.matrix_world @ Vector(c)).z for o in new if o.type == 'MESH' for c in o.bound_box]
    roots = [o for o in new if o.parent is None]
    for o in roots:
        o.location.z -= min(zs)
    return coll


# ---------------------------------------------------------------- the ground
def ground(mats, scene):
    d = json.load(open(os.path.join(ROOT, 'data', 'compound.json')))
    ax0, ay0, ax1, ay1 = d['map_plan']          # plan cm of the map's (0, 0) and (W, H) corners
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('map')
    R = 3000      # out to 3 km
    xs = [-R, min(ax0, ax1) * CM, max(ax0, ax1) * CM, R]
    ys = [-R, -max(ay0, ay1) * CM, -min(ay0, ay1) * CM, R]
    vv = {}
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            vv[i, j] = bm.verts.new((x, y, GROUND))
    for i in range(3):
        for j in range(3):
            f = bm.faces.new([vv[i, j], vv[i + 1, j], vv[i + 1, j + 1], vv[i, j + 1]])
            for lp in f.loops:
                x, y = lp.vert.co.x / CM, -lp.vert.co.y / CM           # plan cm
                lp[uvl].uv = ((x - ax0) / (ax1 - ax0), 1 - (y - ay0) / (ay1 - ay0))
    me = bpy.data.meshes.new('compound ground'); bm.to_mesh(me); bm.free()
    me.materials.append(mats['ground'])
    ob = bpy.data.objects.new('compound ground', me); scene.collection.objects.link(ob)
    return d


def hedges(mats, scene, d):
    g = Mesh()
    t, hgt, gap = .7, 1.1, 2.6
    z0 = GROUND
    for x0, y0, x1, y1 in d['hedges']:
        X0, X1, Y0, Y1 = x0 * CM, x1 * CM, -y1 * CM, -y0 * CM
        cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
        for a, b in ((X0, cx - gap / 2), (cx + gap / 2, X1)):
            g.box(a, Y0, z0, b, Y0 + t, z0 + hgt, 'hedge'); g.box(a, Y1 - t, z0, b, Y1, z0 + hgt, 'hedge')
        for a, b in ((Y0 + t, cy - gap / 2), (cy + gap / 2, Y1 - t)):
            g.box(X0, a, z0, X0 + t, b, z0 + hgt, 'hedge'); g.box(X1 - t, a, z0, X1, b, z0 + hgt, 'hedge')
    for ob in g.objects(mats, scene.collection, 'hedges'):
        bv = ob.modifiers.new('round', 'BEVEL'); bv.width = .18; bv.segments = 3
        for p in ob.data.polygons:
            p.use_smooth = True


# ---------------------------------------------------------------- all of it
def instance(scene, coll, loc, rot=0, scale=1, name='inst'):
    e = bpy.data.objects.new(name, None)
    e.instance_type = 'COLLECTION'; e.instance_collection = coll
    e.location = loc; e.rotation_euler = (0, 0, rot); e.scale = (scale,) * 3
    scene.collection.objects.link(e)
    return e


def protos(name):
    c = bpy.data.collections.new(name)
    return c


def build(scene):
    mats = M()
    d = ground(mats, scene)
    hedges(mats, scene, d)
    # the blocks
    bc = protos('block'); block(mats, bc)
    for b in model.SURROUND['blocks']:
        cx, cy = (b[0] + b[2]) / 2 * CM, -(b[1] + b[3]) / 2 * CM
        rot = 0 if (b[2] - b[0]) > (b[3] - b[1]) else math.pi / 2
        instance(scene, bc, (cx, cy, GROUND), rot, name='block')
    # trees
    kinds = {
        'broad': [import_tree(protos('jacaranda'), 'jacaranda_tree')],
        'olive': [import_tree(protos('olive'), 'island_tree_02')],
        'flower': [import_tree(protos('jacaranda autumn'), 'jacaranda_tree', tint=(.42, 1.3, 1.25))],
    }
    pal = []
    for i in range(4):
        c = protos('palm %d' % i); palm(mats, c, 100 + i, 7.5 + 1.3 * i); pal.append(c)
    kinds['palm'] = pal
    kinds['shrub'] = [import_tree(protos('shrubs'), 'searsia_lucida')]
    kinds['bed'] = [import_tree(protos('bougainvillea'), 'searsia_lucida', tint=(.08, 1.7, 1.15))]
    base = {'broad': .36, 'flower': .3, 'olive': 1.55, 'palm': 1, 'shrub': 1, 'bed': 1}
    rnd = random.Random(5)
    for x, y, k, s in d['trees'] + d.get('shrubs', []):
        c = rnd.choice(kinds[k])
        instance(scene, c, (x * CM, -y * CM, GROUND), rnd.uniform(0, 2 * math.pi), base[k] * s, name='tree ' + k)
    print('compound: %d blocks, %d trees' % (len(model.SURROUND['blocks']), len(d['trees'])), flush=True)
