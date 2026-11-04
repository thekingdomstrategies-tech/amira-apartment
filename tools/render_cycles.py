"""Photoreal renders of a plan, path-traced in Blender Cycles from the same centimetre model as the plan page and the
3D walkthrough (tools/model.py), with the compound round it, the real sun and sky by day, and the flat's own lights at
night.

Usage (Python with Blender's `bpy` module, e.g. `pip install bpy==5.2.3 scipy` in a venv):

    python tools/render_cycles.py                          # every view of RENDERS, day and night, into renders/
    python tools/render_cycles.py --only living,kitchen    # some of them
    python tools/render_cycles.py --res 960x600 --samples 64 --out /tmp/test   # a quick pass

Plan coordinates are cm, x right, y down, z up; Blender's are metres with Y = -y. The top of the plan faces south
(SITE facing 180), so in Blender +Y is south and +X west.
"""
import argparse, math, os, sys, time, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import bpy, bmesh, addon_utils
from mathutils import Vector
import model

CM = .01
SITE = dict(lat=30.0740, lon=31.4870, facing=180)
DAY = datetime.datetime(2026, 11, 15, 13, 30)      # local time, Cairo (UTC+2)
UTC_OFFSET = 2

from render_views import RENDERS, EXPOSURE, DAY_LABEL, NIGHT_LABEL

# ---------------------------------------------------------------- colours
def lin(h):
    """sRGB hex -> linear RGBA."""
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v / 12.92) if v <= .04045 else ((v + .055) / 1.055) ** 2.4) for v in c) + (1,)


class Mats:
    def __init__(self, night):
        self.night, self.m = night, {}

    def get(self, k):
        if k in ('kgreya', 'kgreyda', 'mahoga', 'mahogda'):      # the arch strips' twins: the same finish here
            k = k[:-1]
        if k not in self.m:
            self.m[k] = self.make(k)
        return self.m[k]

    # -- node helpers
    def new(self, k):
        m = bpy.data.materials.new(k)
        m.use_nodes = True
        nt = m.node_tree
        for n in list(nt.nodes):
            if n.type != 'OUTPUT_MATERIAL':
                nt.nodes.remove(n)
        return m, nt, nt.nodes['Material Output']

    def bsdf(self, nt, out, color, rough=.5, metal=0., sheen=0., coat=0., spec=.5, bevel=0., bump=None):
        b = nt.nodes.new('ShaderNodeBsdfPrincipled')
        self.inp(nt, b, 'Base Color', color)
        b.inputs['Roughness'].default_value = rough
        b.inputs['Metallic'].default_value = metal
        if sheen:
            b.inputs['Sheen Weight'].default_value = sheen
            b.inputs['Sheen Roughness'].default_value = .5
        if coat:
            b.inputs['Coat Weight'].default_value = coat
            b.inputs['Coat Roughness'].default_value = .05
        b.inputs['Specular IOR Level'].default_value = spec
        normal = None
        if bevel:
            bv = nt.nodes.new('ShaderNodeBevel'); bv.inputs['Radius'].default_value = bevel; bv.samples = 6
            normal = bv
        if bump is not None:
            bm = nt.nodes.new('ShaderNodeBump'); bm.inputs['Strength'].default_value = bump[1]; bm.inputs['Distance'].default_value = bump[2]
            nt.links.new(bump[0], bm.inputs['Height'])
            if normal:
                nt.links.new(normal.outputs['Normal'], bm.inputs['Normal'])
            normal = bm
        if normal:
            nt.links.new(normal.outputs['Normal'], b.inputs['Normal'])
        nt.links.new(b.outputs[0], out.inputs['Surface'])
        return b

    def inp(self, nt, node, name, v):
        if isinstance(v, tuple):
            node.inputs[name].default_value = v
        else:
            nt.links.new(v, node.inputs[name])

    def coord(self, nt):
        tc = nt.nodes.new('ShaderNodeTexCoord')
        return tc.outputs['Object']

    def noise(self, nt, scale, detail=4, rough=.5, vec=None):
        n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail; n.inputs['Roughness'].default_value = rough
        nt.links.new(vec or self.coord(nt), n.inputs['Vector'])
        return n

    def ramp(self, nt, fac, stops):
        r = nt.nodes.new('ShaderNodeValToRGB')
        cr = r.color_ramp
        cr.elements[0].position, cr.elements[0].color = stops[0][0], lin(stops[0][1])
        cr.elements[1].position, cr.elements[1].color = stops[-1][0], lin(stops[-1][1])
        for p, c in stops[1:-1]:
            e = cr.elements.new(p); e.color = lin(c)
        nt.links.new(fac, r.inputs['Fac'])
        return r.outputs['Color']

    def wood(self, nt, cols, scale=4., stretch=(1, 1, 12), rings=True):
        """Wood grain: stretched noise and wave bands in object space (metres)."""
        mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = stretch
        nt.links.new(self.coord(nt), mp.inputs['Vector'])
        w = nt.nodes.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = 'Z'
        w.inputs['Scale'].default_value = scale; w.inputs['Distortion'].default_value = 6; w.inputs['Detail'].default_value = 3
        nt.links.new(mp.outputs[0], w.inputs['Vector'])
        n = self.noise(nt, 40, 6, .6, mp.outputs[0])
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'FLOAT'; mix.inputs['Factor'].default_value = .35
        nt.links.new(w.outputs['Fac'], mix.inputs['A']); nt.links.new(n.outputs['Fac'], mix.inputs['B'])
        return self.ramp(nt, mix.outputs['Result'], cols), mix.outputs['Result']

    def make(self, k):
        m, nt, out = self.new(k)
        C = lin
        if k in ('wall', 'wallpaint'):
            n = self.noise(nt, 3, 3)
            col = self.ramp(nt, n.outputs['Fac'], [(.35, '#EEE5D4'), (.65, '#F5EEE1')])
            self.bsdf(nt, out, col, .9, bump=(self.noise(nt, 300, 2).outputs['Fac'], .04, .002))
        elif k == 'ceiling':
            self.bsdf(nt, out, C('#F7F4EF'), .95)
        elif k == 'cap':
            self.bsdf(nt, out, C('#F3F0EA'), .8)
        elif k == 'porcelain':     # 120 x 60 tiles, 2 mm joints, softly polished
            br = nt.nodes.new('ShaderNodeTexBrick'); br.offset = 0; br.squash = 1
            br.inputs['Scale'].default_value = 1; br.inputs['Brick Width'].default_value = 1.2; br.inputs['Row Height'].default_value = .6
            br.inputs['Mortar Size'].default_value = .002; br.inputs['Mortar Smooth'].default_value = .2
            br.inputs['Color1'].default_value = C('#ECE7DE'); br.inputs['Color2'].default_value = C('#E6E0D5'); br.inputs['Mortar'].default_value = C('#BDB4A6')
            nt.links.new(self.coord(nt), br.inputs['Vector'])
            n = self.noise(nt, 2.5, 5)
            mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = .12
            nt.links.new(br.outputs['Color'], mix.inputs['A']); nt.links.new(n.outputs['Color'], mix.inputs['B'])
            b = self.bsdf(nt, out, mix.outputs['Result'], .14, spec=.6)
            rr = self.ramp(nt, br.outputs['Fac'], [(0, '#FFFFFF'), (1, '#262626')])
            nt.links.new(rr, b.inputs['Roughness'])
        elif k == 'oakfloor':      # planks 20 x 120
            br = nt.nodes.new('ShaderNodeTexBrick'); br.offset = .5; br.offset_frequency = 1
            br.inputs['Scale'].default_value = 1; br.inputs['Brick Width'].default_value = 1.2; br.inputs['Row Height'].default_value = .2
            br.inputs['Mortar Size'].default_value = .0015
            br.inputs['Color1'].default_value = C('#C9A57A'); br.inputs['Color2'].default_value = C('#B8915F'); br.inputs['Mortar'].default_value = C('#6B4E31')
            nt.links.new(self.coord(nt), br.inputs['Vector'])
            g, f = self.wood(nt, [(.2, '#A57E52'), (.8, '#D8B88E')], 6, (1, 30, 1))
            mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = .55
            nt.links.new(br.outputs['Color'], mix.inputs['A']); nt.links.new(g, mix.inputs['B'])
            self.bsdf(nt, out, mix.outputs['Result'], .35, coat=.3)
        elif k in ('oak', 'oakdark'):
            cols = [(.15, '#A8814F'), (.85, '#D6B385')] if k == 'oak' else [(.15, '#4E3520'), (.85, '#7A5634')]
            g, f = self.wood(nt, cols)
            self.bsdf(nt, out, g, .45, bevel=.003, bump=(f, .05, .001))
        elif k in ('mahog', 'mahogd'):
            cols = [(.1, '#3A120A'), (.55, '#5E2216'), (.9, '#7A3220')] if k == 'mahog' else [(.1, '#22090A'), (.9, '#3A140C')]
            g, f = self.wood(nt, cols, 5, (1, 1, 10))
            self.bsdf(nt, out, g, .32, coat=.45, bevel=.003, bump=(f, .03, .001))
        elif k in ('kgrey', 'kgreyd'):
            n = self.noise(nt, 60, 3)
            col = self.ramp(nt, n.outputs['Fac'], [(.3, '#8A9491' if k == 'kgrey' else '#5D6664'), (.7, '#929C99' if k == 'kgrey' else '#646D6B')])
            self.bsdf(nt, out, col, .38, coat=.15, bevel=.002)
        elif k == 'granite':
            v = nt.nodes.new('ShaderNodeTexVoronoi'); v.inputs['Scale'].default_value = 420
            nt.links.new(self.coord(nt), v.inputs['Vector'])
            n = self.noise(nt, 160, 6, .7)
            mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'FLOAT'; mix.inputs['Factor'].default_value = .5
            nt.links.new(v.outputs['Distance'], mix.inputs['A']); nt.links.new(n.outputs['Fac'], mix.inputs['B'])
            col = self.ramp(nt, mix.outputs['Result'], [(.28, '#2A2A2C'), (.36, '#6F6F6D'), (.5, '#9E9E9A'), (.62, '#C9C9C5'), (.7, '#EDEDEA')])
            self.bsdf(nt, out, col, .18, spec=.6, bevel=.004)
        elif k in ('quartz', 'travertine', 'stone', 'cstone'):
            base = {'quartz': ('#D8D7D3', '#E8E7E3'), 'travertine': ('#D6C7AE', '#E4D6BF'), 'stone': ('#CFC2AC', '#DDD1BC'), 'cstone': ('#DFC8A1', '#E8D4B0')}[k]
            n = self.noise(nt, 12, 6)
            self.bsdf(nt, out, self.ramp(nt, n.outputs['Fac'], [(.35, base[0]), (.65, base[1])]), .3, bevel=.003)
        elif k in ('white', 'front'):
            self.bsdf(nt, out, C('#F2F1EC'), .35, coat=.1, bevel=.002)
        elif k == 'ceramic':
            self.bsdf(nt, out, C('#F8F8F6'), .08, coat=.6, bevel=.008)
        elif k == 'black':
            self.bsdf(nt, out, C('#18191B'), .35, metal=.2, bevel=.002)
        elif k == 'piano':
            self.bsdf(nt, out, C('#0A0A0C'), .1, coat=1, bevel=.004)
        elif k == 'keys':          # white keys 2.35 cm with black joints
            w = nt.nodes.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = 'X'; w.wave_profile = 'SAW'
            w.inputs['Scale'].default_value = 1 / .0235 / 6.2832 * 6.2832; w.inputs['Distortion'].default_value = 0
            nt.links.new(self.coord(nt), w.inputs['Vector'])
            self.bsdf(nt, out, self.ramp(nt, w.outputs['Fac'], [(0, '#1A1A1A'), (.06, '#F4F2EC'), (1, '#F4F2EC')]), .25, coat=.5)
        elif k == 'steel':
            self.bsdf(nt, out, C('#C8CBCD'), .22, metal=1, bevel=.002)
        elif k == 'frame':
            self.bsdf(nt, out, C('#2B2C2E'), .4, metal=.6)
        elif k == 'brass':
            self.bsdf(nt, out, C('#C09456'), .25, metal=1)
        elif k == 'mirror':
            self.bsdf(nt, out, C('#F2F4F5'), .01, metal=1)
        elif k == 'glass':        # thin glass: the light passes straight through, with a reflection on top
            tr = nt.nodes.new('ShaderNodeBsdfTransparent'); gl = nt.nodes.new('ShaderNodeBsdfGlossy')
            gl.inputs['Roughness'].default_value = .02
            fr = nt.nodes.new('ShaderNodeFresnel'); fr.inputs['IOR'].default_value = 1.5
            # the reflection only on the side a ray comes in by: from inside the pane Fresnel would give total internal
            # reflection, and the glass would go black
            geo = nt.nodes.new('ShaderNodeNewGeometry')
            mm = nt.nodes.new('ShaderNodeMath'); mm.operation = 'SUBTRACT'; mm.inputs[0].default_value = 1
            nt.links.new(geo.outputs['Backfacing'], mm.inputs[1])
            k = nt.nodes.new('ShaderNodeMath'); k.operation = 'MULTIPLY'
            nt.links.new(fr.outputs[0], k.inputs[0]); nt.links.new(mm.outputs[0], k.inputs[1])
            mx = nt.nodes.new('ShaderNodeMixShader')
            nt.links.new(k.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(gl.outputs[0], mx.inputs[2])
            nt.links.new(mx.outputs[0], out.inputs['Surface'])
        elif k in ('linen', 'fabric', 'taupe', 'sgrey', 'pouf', 'beige', 'mustard', 'wine', 'piping'):
            col = {'linen': '#F1EDE5', 'fabric': '#E2D8C8', 'taupe': '#7A6A58', 'sgrey': '#8F8C86', 'pouf': '#6E5E4E',
                   'beige': '#CFC2AF', 'mustard': '#B39853', 'wine': '#7A1E28', 'piping': '#F6F3EC'}[k]
            n = self.noise(nt, 900, 2)
            rad = {'linen': .02, 'fabric': .03, 'piping': .003, 'wine': .04, 'mustard': .04}.get(k, .035)
            self.bsdf(nt, out, C(col), .95, sheen=.2, spec=.2, bevel=rad, bump=(n.outputs['Fac'], .15, .001))
        elif k == 'rug':
            n = self.noise(nt, 18, 6, .7)
            col = self.ramp(nt, n.outputs['Fac'], [(.3, '#D9CDB6'), (.7, '#E8DECB')])
            self.bsdf(nt, out, col, 1, sheen=.4, bump=(self.noise(nt, 700, 2).outputs['Fac'], .3, .002))
        elif k == 'leaf':
            n = self.noise(nt, 14, 5)
            self.bsdf(nt, out, self.ramp(nt, n.outputs['Fac'], [(.3, '#3C5A2C'), (.7, '#6A8A48')]), .6, bump=(n.outputs['Fac'], .6, .02))
        elif k == 'rattan':
            w = nt.nodes.new('ShaderNodeTexWave'); w.inputs['Scale'].default_value = 60; w.inputs['Distortion'].default_value = 2
            nt.links.new(self.coord(nt), w.inputs['Vector'])
            b = self.bsdf(nt, out, self.ramp(nt, w.outputs['Fac'], [(.3, '#8C6230'), (.7, '#C99A5C')]), .7)
            if self.night:
                b.inputs['Emission Color'].default_value = C('#FFB46A'); b.inputs['Emission Strength'].default_value = .6
        elif k == 'shade':        # floor-lamp shades: linen that glows at night
            b = self.bsdf(nt, out, C('#EFE6D6'), .9, sheen=.3)
            b.inputs['Transmission Weight'].default_value = .3
            if self.night:
                b.inputs['Emission Color'].default_value = C('#FFD9A8'); b.inputs['Emission Strength'].default_value = 3
        elif k == 'downlight':
            b = self.bsdf(nt, out, C('#FFFFFF'), .3)
            if self.night:
                b.inputs['Emission Color'].default_value = C('#FFE2B8'); b.inputs['Emission Strength'].default_value = 40
        elif k == 'led':
            b = self.bsdf(nt, out, C('#FFF4DE'), .5)
            b.inputs['Emission Color'].default_value = C('#FFE3BC'); b.inputs['Emission Strength'].default_value = 25 if self.night else 4
        elif k == 'context':      # the other buildings: rendered walls with darker window bands
            w = nt.nodes.new('ShaderNodeTexWave'); w.bands_direction = 'Z'; w.wave_profile = 'SAW'
            w.inputs['Scale'].default_value = 1 / 3.1 * 1.0; w.inputs['Distortion'].default_value = 0
            mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1, 1, 1)
            nt.links.new(self.coord(nt), mp.inputs['Vector']); nt.links.new(mp.outputs[0], w.inputs['Vector'])
            col = self.ramp(nt, w.outputs['Fac'], [(0, '#E7DFD2'), (.55, '#E7DFD2'), (.56, '#5D6570'), (.9, '#5D6570'), (.91, '#E7DFD2')])
            b = self.bsdf(nt, out, col, .7)
            if self.night:
                win = self.ramp(nt, w.outputs['Fac'], [(0, '#000000'), (.55, '#000000'), (.56, '#FFC88A'), (.9, '#FFC88A'), (.91, '#000000')])
                nn = self.noise(nt, .08, 1)
                mk = nt.nodes.new('ShaderNodeMix'); mk.data_type = 'RGBA'; mk.blend_type = 'MULTIPLY'; mk.inputs['Factor'].default_value = 1
                th = self.ramp(nt, nn.outputs['Fac'], [(.48, '#000000'), (.52, '#FFFFFF')])
                nt.links.new(win, mk.inputs['A']); nt.links.new(th, mk.inputs['B'])
                nt.links.new(mk.outputs['Result'], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = 1.2
        elif k == 'grass':
            n = self.noise(nt, .6, 6, .6)
            self.bsdf(nt, out, self.ramp(nt, n.outputs['Fac'], [(.3, '#55703A'), (.7, '#7D9157')]), 1)
        elif k == 'water':
            self.bsdf(nt, out, C('#4FA7C6'), .03, spec=.8)
        elif k == 'pave':
            n = self.noise(nt, 4, 5)
            self.bsdf(nt, out, self.ramp(nt, n.outputs['Fac'], [(.3, '#B9B1A3'), (.7, '#CEC7BA')]), .85)
        elif k == 'asphalt':
            self.bsdf(nt, out, C('#56585A'), .85)
        elif k == 'trunk':
            self.bsdf(nt, out, C('#6A5038'), .9)
        elif k == 'shutter':
            self.bsdf(nt, out, C('#4E5154'), .5, metal=.3)
        else:
            self.bsdf(nt, out, C('#D8D4CC'), .6)
        return m


# ---------------------------------------------------------------- geometry, merged by material
class Geo:
    def __init__(self):
        self.bm = {}

    def _bm(self, m):
        if m not in self.bm:
            self.bm[m] = bmesh.new()
        return self.bm[m]

    def box(self, b, m):
        x0, y0, z0, x1, y1, z1 = b
        if x1 - x0 <= 0 or y1 - y0 <= 0 or z1 - z0 <= 0:
            return
        bm = self._bm(m)
        X0, X1 = x0 * CM, x1 * CM
        Y0, Y1 = -y1 * CM, -y0 * CM
        Z0, Z1 = z0 * CM, z1 * CM
        v = [bm.verts.new(p) for p in ((X0, Y0, Z0), (X1, Y0, Z0), (X1, Y1, Z0), (X0, Y1, Z0),
                                        (X0, Y0, Z1), (X1, Y0, Z1), (X1, Y1, Z1), (X0, Y1, Z1))]
        for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            bm.faces.new([v[i] for i in f])

    def cyl(self, cx, cy, r, z0, z1, m, seg=32, cap=True, open_=False):
        bm = self._bm(m)
        X, Y = cx * CM, -cy * CM
        lo, hi = [], []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            px, py = X + r * CM * math.cos(a), Y + r * CM * math.sin(a)
            lo.append(bm.verts.new((px, py, z0 * CM))); hi.append(bm.verts.new((px, py, z1 * CM)))
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new([lo[i], lo[j], hi[j], hi[i]])
        if cap and not open_:
            bm.faces.new(list(reversed(lo))); bm.faces.new(hi)

    def sphere(self, cx, cy, cz, r, sy, m, top_half=False, us=32, vs=16):
        """A UV sphere built vertex by vertex (bmesh's operator slows down as the mesh grows)."""
        bm = self._bm(m)
        X, Y, Z, R = cx * CM, -cy * CM, cz * CM, r * CM
        j0 = vs // 2 if top_half else 0
        rings = []
        for j in range(j0, vs + 1):
            th = math.pi * j / vs            # 0 at the bottom pole, pi at the top
            z, rr = -math.cos(th) * R * sy, math.sin(th) * R
            if rr < 1e-9:
                rings.append([bm.verts.new((X, Y, Z + z))])
            else:
                rings.append([bm.verts.new((X + rr * math.cos(2 * math.pi * i / us), Y + rr * math.sin(2 * math.pi * i / us), Z + z)) for i in range(us)])
        for a, b in zip(rings, rings[1:]):
            if len(a) == 1:
                for i in range(us):
                    bm.faces.new([a[0], b[(i + 1) % us], b[i]])
            elif len(b) == 1:
                for i in range(us):
                    bm.faces.new([a[i], a[(i + 1) % us], b[0]])
            else:
                for i in range(us):
                    bm.faces.new([a[i], a[(i + 1) % us], b[(i + 1) % us], b[i]])

    def prism(self, pts, z0, z1, m):
        bm = self._bm(m)
        lo = [bm.verts.new((x * CM, -y * CM, z0 * CM)) for x, y in pts]
        hi = [bm.verts.new((x * CM, -y * CM, z1 * CM)) for x, y in pts]
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new([lo[i], lo[j], hi[j], hi[i]])
        try:
            bm.faces.new(list(reversed(lo))); bm.faces.new(hi)
        except ValueError:
            pass

    def link(self, mats, scene):
        for m, bm in self.bm.items():
            me = bpy.data.meshes.new(m)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(me); bm.free()
            me.materials.append(mats.get(m))
            ob = bpy.data.objects.new(m, me)
            scene.collection.objects.link(ob)


SKIP_V = {'d-closed', 'sh-closed', 'sh-half', 'i-trial'}   # doors open, shutters up, the 95 cm hob


def build_flat(L, g):
    xs = [p[0] for p in model.OUTLINE]; ys = [p[1] for p in model.OUTLINE]
    g.prism(model.OUTLINE, model.H - .5, model.H + 25, 'ceiling')        # the slab over the flat: no light leaks at the wall heads
    for it in L['items']:
        if it.get('v') in SKIP_V:
            continue
        t, m = it['t'], it.get('m', 'white')
        if t == 'b':
            g.box(it['b'], m)
        elif t == 'c':
            g.cyl(it['c'][0], it['c'][1], it['r'], it['z'][0], it['z'][1], m, 40 if it['r'] > 12 else 24)
        elif t == 's':
            g.sphere(it['c'][0], it['c'][1], it['z'], it['r'], it.get('sy', 1), m)
        elif t == 'p':
            g.prism(it['p'], it['z'][0], it['z'][1], m)
        elif t == 'l':      # a woven dome pendant on a cord
            cx, cy, z = it['c'][0], it['c'][1], it['z']
            g.sphere(cx, cy, z, 23, .92, 'rattan', top_half=True)
            g.cyl(cx, cy, .4, z + 21, model.H, 'black', 8)
            g.cyl(cx, cy, 3, z + 20, z + 22, 'black', 16)


def build_lights_geo(L, g):
    """The light fittings the viewer adds itself: recessed downlights, ceiling discs, floor lamps, the LED strip."""
    H = model.H
    for l in L['lights']:
        k = l['k']
        if k == 'down':
            g.cyl(l['p'][0], l['p'][1], 4.2, H - .6, H - .1, 'downlight', 24)
            g.cyl(l['p'][0], l['p'][1], 5.2, H - .3, H - .05, 'white', 24)
        elif k == 'ceil':
            g.cyl(l['p'][0], l['p'][1], 22, H - 6, H - .1, 'shade', 40)
        elif k == 'lamp':
            x, y = l['p']
            g.cyl(x, y, 14, 0, 2, 'black', 32); g.cyl(x, y, 1, 2, 142, 'black', 12)
            g.cyl(x, y, 21, 140, 172, 'shade', 40, open_=True)
        elif k == 'shelf':
            (x0, y0), (x1, y1) = l['pts']
            g.box([x0 - 2, min(y0, y1), 143.6, x0 + 1, max(y0, y1), 144.2], 'led')


def build_surroundings(g):
    ground = -model.ELEV
    g.box([-30000, -30000, ground - 5, 40000, 40000, ground], 'grass')
    for c in model.CONTEXT:
        if c['name'] == 'the floors below':
            g.prism(c['p'], c['z'][0], c['z'][1], 'cap')
        else:
            g.prism(c['p'], c['z'][0], c['z'][1], 'context')
    S = model.SURROUND
    for r in S['roads']:
        g.box([r[0], r[1], ground, r[2], r[3], ground + 2], 'asphalt')
    for r in S['water']:
        g.box([r[0], r[1], ground, r[2], r[3], ground + 3], 'water')
    for x, y, kind, s in S['trees']:
        if kind == 'palm':
            g.cyl(x, y, 18 * s, ground, ground + 700 * s, 'trunk', 10)
            g.sphere(x, y, ground + 720 * s, 260 * s, .45, 'leaf', us=14, vs=8)
        else:
            g.cyl(x, y, 16 * s, ground, ground + 220 * s, 'trunk', 10)
            g.sphere(x, y, ground + 380 * s, 260 * s, .85, 'leaf', us=14, vs=8)


# ---------------------------------------------------------------- light
def sun_position(when_local, lat, lon, utc=UTC_OFFSET):
    """Solar azimuth (degrees from north, clockwise) and altitude, NOAA's approximations."""
    t = when_local - datetime.timedelta(hours=utc)
    n = t.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1 + (t.hour - 12) / 24)
    eot = 229.18 * (.000075 + .001868 * math.cos(g) - .032077 * math.sin(g) - .014615 * math.cos(2 * g) - .040849 * math.sin(2 * g))
    dec = .006918 - .399912 * math.cos(g) + .070257 * math.sin(g) - .006758 * math.cos(2 * g) + .000907 * math.sin(2 * g) \
        - .002697 * math.cos(3 * g) + .00148 * math.sin(3 * g)
    tst = t.hour * 60 + t.minute + eot + 4 * lon
    ha = math.radians(tst / 4 - 180)
    la = math.radians(lat)
    cz = math.sin(la) * math.sin(dec) + math.cos(la) * math.cos(dec) * math.cos(ha)
    alt = math.asin(max(-1, min(1, cz)))
    az = math.degrees(math.atan2(math.sin(ha), math.cos(ha) * math.sin(la) - math.tan(dec) * math.cos(la))) + 180
    return az % 360, math.degrees(alt)


def plan_direction(az_deg, alt_deg, facing=SITE['facing']):
    """A compass direction as a Blender vector. The plan's top faces `facing` (180: south)."""
    # the plan's up (-y_plan, +Y in Blender) points to `facing`; rotate the compass by that
    a = math.radians(az_deg - facing)
    h = math.radians(alt_deg)
    # in Blender with +Y = the plan's top (facing) and +X = facing + 90 clockwise ... the plan's right is facing + 90
    return Vector((math.sin(a) * math.cos(h), math.cos(a) * math.cos(h), math.sin(h)))


def world_day(scene, az, alt):
    w = bpy.data.worlds.new('day'); scene.world = w
    nt = w.node_tree
    bg = [n for n in nt.nodes if n.type == 'BACKGROUND'][0]
    sky = nt.nodes.new('ShaderNodeTexSky'); sky.sky_type = 'MULTIPLE_SCATTERING'; sky.sun_disc = False
    d = plan_direction(az, alt)
    sky.sun_elevation = math.radians(alt)
    sky.sun_rotation = math.atan2(d.x, d.y)       # Blender's sky: rotation r puts the sun at (sin r, cos r)
    sky.altitude = 120; sky.air_density = 1.2; sky.aerosol_density = 2.5
    nt.links.new(sky.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = .8
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 4.2; sun.angle = math.radians(.6)
    sun.color = (1, .95, .88)
    ob = bpy.data.objects.new('sun', sun); scene.collection.objects.link(ob)
    ob.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()


def world_night(scene):
    w = bpy.data.worlds.new('night'); scene.world = w
    nt = w.node_tree
    bg = [n for n in nt.nodes if n.type == 'BACKGROUND'][0]
    grad = nt.nodes.new('ShaderNodeTexGradient'); grad.gradient_type = 'LINEAR'
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Rotation'].default_value = (0, -math.pi / 2, 0)
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs[0], grad.inputs['Vector'])
    r = nt.nodes.new('ShaderNodeValToRGB')
    r.color_ramp.elements[0].position = .45; r.color_ramp.elements[0].color = lin('#3B2E2A')
    r.color_ramp.elements[1].position = .62; r.color_ramp.elements[1].color = lin('#0E1626')
    nt.links.new(grad.outputs['Fac'], r.inputs['Fac']); nt.links.new(r.outputs['Color'], bg.inputs[0])
    bg.inputs[1].default_value = .35


def lights_night(L, scene):
    H = model.H
    col = (1, .82, .62)

    def add(name, kind, pos, energy, size=.05, rot=None, spot=None):
        li = bpy.data.lights.new(name, kind); li.energy = energy; li.color = col
        if kind == 'POINT':
            li.shadow_soft_size = size
        if kind == 'SPOT':
            li.spot_size, li.spot_blend = spot; li.shadow_soft_size = size
        if kind == 'AREA':
            li.shape = 'RECTANGLE'; li.size, li.size_y = size
        ob = bpy.data.objects.new(name, li); ob.location = pos
        if rot:
            ob.rotation_euler = rot
        scene.collection.objects.link(ob)

    for i, l in enumerate(L['lights']):
        k = l['k']
        if k == 'down':
            add('down%d' % i, 'SPOT', (l['p'][0] * CM, -l['p'][1] * CM, (H - 1.5) * CM), 32, .03, None, (math.radians(95), .6))
        elif k == 'ceil':
            add('ceil%d' % i, 'POINT', (l['p'][0] * CM, -l['p'][1] * CM, (H - 14) * CM), 45, .12)
        elif k == 'lamp':
            add('lamp%d' % i, 'POINT', (l['p'][0] * CM, -l['p'][1] * CM, 1.58), 55, .08)
        elif k == 'shelf':
            (x0, y0), (x1, y1) = l['pts']
            add('shelf', 'AREA', (x0 * CM, -(y0 + y1) / 2 * CM, 1.43), 30, (.03, abs(y1 - y0) * CM))
    for i, it in enumerate([it for it in L['items'] if it['t'] == 'l']):
        add('pend%d' % i, 'POINT', (it['c'][0] * CM, -it['c'][1] * CM, (it['z'] + 8) * CM), 70, .09)


def portals(scene, lay):
    """Sky portals at the windows and terrace doors: they guide the daylight in, so there is less noise."""
    wins = model.windows_of(lay) + [(n, r, a, 0, 230, 2) for n, r, a in model.SLIDERS]
    rooms = [r[1] for r in lay['rooms']]

    def inside(x, y):
        return any(a <= x <= c and b <= y <= d for a, b, c, d in rooms)

    for n, r, axis, sill, head, panes in wins:
        x0, y0, x1, y1 = r
        cx, cy, cz = (x0 + x1) / 2, (y0 + y1) / 2, (sill + head) / 2
        li = bpy.data.lights.new('portal ' + n, 'AREA'); li.cycles.is_portal = True; li.shape = 'RECTANGLE'
        # an area light shines along its own -Z: turn it to face into the room
        if axis == 'x':     # a window in a wall running along x: the room is on one side in y
            li.size, li.size_y = (x1 - x0) * CM, (head - sill) * CM
            rot = (-math.pi / 2, 0, 0) if inside(cx, y1 + 30) else (math.pi / 2, 0, 0)
        else:
            li.size, li.size_y = (head - sill) * CM, (y1 - y0) * CM
            rot = (0, -math.pi / 2, 0) if inside(x1 + 30, cy) else (0, math.pi / 2, 0)
        ob = bpy.data.objects.new('portal ' + n, li); ob.location = (cx * CM, -cy * CM, cz * CM); ob.rotation_euler = rot
        scene.collection.objects.link(ob)


# ---------------------------------------------------------------- cameras
def camera(scene, pos, look, lens, w, h):
    """A level camera (vertical lines stay vertical), shifted to frame the target, as architectural photos are."""
    cam = bpy.data.cameras.new('cam'); cam.lens = lens; cam.sensor_width = 36; cam.sensor_fit = 'HORIZONTAL'
    cam.clip_start = .05; cam.clip_end = 500
    ob = bpy.data.objects.new('cam', cam); scene.collection.objects.link(ob); scene.camera = ob
    p = Vector((pos[0] * CM, -pos[1] * CM, pos[2] * CM)); t = Vector((look[0] * CM, -look[1] * CM, look[2] * CM))
    d = t - p
    yaw = math.atan2(d.y, d.x)
    flat = math.hypot(d.x, d.y)
    pitch = math.atan2(d.z, flat)
    ob.location = p
    ob.rotation_euler = (math.pi / 2, 0, yaw - math.pi / 2)
    if abs(pitch) < math.radians(35):
        cam.shift_y = max(-.3, min(.3, math.tan(pitch) * lens / 36))
    else:
        ob.rotation_euler = (math.pi / 2 + pitch, 0, yaw - math.pi / 2)
    return ob


# ---------------------------------------------------------------- the scene and the render
def setup(scene, res, samples):
    scene.render.engine = 'CYCLES'
    c = scene.cycles
    c.device = 'CPU'; c.samples = samples; c.use_adaptive_sampling = True; c.adaptive_threshold = .015
    c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'
    try:
        c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    except Exception:
        pass
    c.max_bounces = 10; c.diffuse_bounces = 5; c.glossy_bounces = 4; c.transmission_bounces = 8; c.transparent_max_bounces = 12
    c.sample_clamp_indirect = 6; c.blur_glossy = 1; c.caustics_reflective = False; c.caustics_refractive = False
    c.use_light_tree = True
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'JPEG'; scene.render.image_settings.quality = 90
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - Punchy'
    except Exception:
        pass
    scene.render.threads_mode = 'AUTO'


def build_scene(key, night):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable('cycles', default_set=True)
    scene = bpy.context.scene
    L = model.build(key)
    lay = model.LAYOUTS[key]
    mats = Mats(night)
    g = Geo()
    build_flat(L, g); build_lights_geo(L, g); build_surroundings(g)
    g.link(mats, scene)
    if night:
        world_night(scene); lights_night(L, scene)
    else:
        az, alt = sun_position(DAY, SITE['lat'], SITE['lon'])
        world_day(scene, az, alt); portals(scene, lay)
    return scene


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', default='o3')
    ap.add_argument('--only', default='')
    ap.add_argument('--times', default='day,night')
    ap.add_argument('--res', default='1920x1200')
    ap.add_argument('--samples', type=int, default=256)
    ap.add_argument('--out', default=os.path.join(ROOT, 'renders'))
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
        setup(scene, res, a.samples)
        for key, title, cap, pos, look, lens, times in views:
            scene.view_settings.exposure = (.6 if night else 1.6) + EXPOSURE.get('%s-%s' % (key, t), 0)
            cam = camera(scene, pos, look, lens, *res)
            scene.render.filepath = os.path.join(a.out, '%s-%s.jpg' % (key, t))
            t0 = time.time()
            bpy.ops.render.render(write_still=True)
            print('RENDERED %s-%s in %.0fs' % (key, t, time.time() - t0), flush=True)
            bpy.data.objects.remove(cam)


if __name__ == '__main__':
    main()
