#!/usr/bin/env python3
"""Build index.html and plan.html, and the plan images they show, from the architect's PDFs and tools/model.py.

The two PDFs are rendered (pdftoppm), turned so the room names read upright, and cropped to the model's frame at
2 px per cm, so the drawings, the clickable rooms and the 3D model share one set of coordinates.

Usage: python3 tools/build_pages.py   ->  index.html, plan.html, img/plan-*.jpg, img/plan-thumb.jpg
"""
import html, json, os, subprocess, sys, tempfile

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model  # noqa: E402
from extract_walls import CM_PER_PT, X0, Y0, X1, Y1  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PX_PER_CM = 2
# the furnished sheet is plotted 16 cm right and 9 cm lower than the empty one (found by cross-correlating the two)
FURN_SHIFT = (16, 9)
NAME = 'Creektown Apartment'
ZONE = {'pub': 'Living', 'cir': 'Circulation', 'pri': 'Bedrooms', 'wetz': 'Wet rooms', 'ser': 'Service'}


def render_plans():
    os.makedirs(os.path.join(ROOT, 'img'), exist_ok=True)
    W, H = round((X1 - X0) * CM_PER_PT), round((Y1 - Y0) * CM_PER_PT)
    dpi = 300; k = dpi / 72
    out = {}
    with tempfile.TemporaryDirectory() as td:
        for key, pdf, shift in (('empty', 'original_empty.pdf', (0, 0)), ('furnished', 'original_with_furn.pdf', FURN_SHIFT)):
            base = os.path.join(td, key)
            subprocess.run(['pdftoppm', '-r', str(dpi), '-png', '-singlefile', os.path.join(ROOT, 'source', pdf), base], check=True)
            im = Image.open(base + '.png').convert('L').rotate(90, expand=True)     # anticlockwise: names upright
            # crop in sheet points, shifted so the furnished sheet lands on the empty one
            sx, sy = shift[0] / CM_PER_PT, shift[1] / CM_PER_PT
            box = [int((X0 - sx) * k), int((Y0 - sy) * k), int((X1 - sx) * k), int((Y1 - sy) * k)]
            im = im.crop(box).resize((W * PX_PER_CM, H * PX_PER_CM), Image.LANCZOS)
            fn = 'img/plan-%s.jpg' % key
            im.save(os.path.join(ROOT, fn), quality=78, optimize=True, progressive=True)
            out[key] = fn
            if key == 'furnished':
                th = im.crop((0, 0, im.size[0], im.size[1])).resize((800, int(800 * im.size[1] / im.size[0])), Image.LANCZOS)
                th.save(os.path.join(ROOT, 'img', 'plan-thumb.jpg'), quality=80)
    return out, W, H


CSS = r'''
:root{--olive:#7B7258;--olive-deep:#6A624B;--navy:#0C3B5C;--gold:#B79565;--grey:#E3E3E3;--charcoal:#403F41;
  --paper:#F1F0EC;--sheet:#FFFFFF;--ink:#23252A;--ink2:#55585E;--muted:#7A7C80;--line:#D9D8D3;--head:var(--navy);--link:var(--navy);
  --on-olive:#FFFFFF;--on-olive2:rgba(255,255,255,.78);--hl:rgba(183,149,101,.28);--font:"Montserrat","Helvetica Neue",Arial,sans-serif}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){color-scheme:dark;--olive:#4A4535;--olive-deep:#3E3A2C;--navy:#9DB8CF;--gold:#CDAE7E;--grey:#26272A;--charcoal:#141416;
  --paper:#18191B;--sheet:#1F2023;--ink:#ECEBE6;--ink2:#C3C3BE;--muted:#9A9A95;--line:#34353A;--head:#E9E6DD;--link:#CDAE7E;--hl:rgba(205,174,126,.3)}}
:root[data-theme="dark"]{color-scheme:dark;--olive:#4A4535;--olive-deep:#3E3A2C;--navy:#9DB8CF;--gold:#CDAE7E;--grey:#26272A;--charcoal:#141416;
  --paper:#18191B;--sheet:#1F2023;--ink:#ECEBE6;--ink2:#C3C3BE;--muted:#9A9A95;--line:#34353A;--head:#E9E6DD;--link:#CDAE7E;--hl:rgba(205,174,126,.3)}
*{box-sizing:border-box}[hidden]{display:none!important}
body{margin:0;background:var(--paper);color:var(--ink);font:400 16px/1.7 var(--font);font-variant-numeric:lining-nums tabular-nums}
a{color:var(--link)}img{max-width:100%}
.wrap{max-width:1200px;margin:0 auto;padding-inline:24px}
.eyebrow{font:600 11.5px/1.2 var(--font);letter-spacing:.24em;text-transform:uppercase;color:var(--gold)}
h1,h2,h3{font-family:var(--font);margin:0;text-wrap:balance;color:var(--head)}
.bar .wrap{display:flex;justify-content:space-between;align-items:center;gap:12px;padding-block:22px;font:500 11.5px var(--font);letter-spacing:.2em;text-transform:uppercase}
.bar a{text-decoration:none;margin-left:22px}
.hero{background:var(--olive);color:var(--on-olive)}
.hero .bar{color:var(--on-olive2)}.hero .bar a{color:var(--on-olive);opacity:.85}.hero .bar a:hover{opacity:1;color:var(--gold)}
.hero .copy{padding-block:clamp(48px,9vw,120px) clamp(48px,7vw,88px);display:grid;gap:18px;justify-items:start}
.hero h1{color:var(--on-olive);font:300 clamp(44px,8vw,104px)/.98 var(--font);letter-spacing:-.02em}.hero h1 b{font-weight:600}
.hero .rule{width:88px;height:2px;background:var(--gold)}
.hero p{margin:0;max-width:58ch;font-size:clamp(16px,1.5vw,19px);font-weight:300;color:var(--on-olive2)}
.cta{display:flex;flex-wrap:wrap;gap:12px;margin-top:8px}
.btn{display:inline-flex;align-items:center;gap:8px;font:600 12.5px var(--font);letter-spacing:.14em;text-transform:uppercase;padding:14px 20px;text-decoration:none}
.btn.solid{background:#fff;color:#4A4535}.btn.ghost{border:1.5px solid var(--gold);color:#fff}
.btn:focus-visible,.card:focus-visible{outline:3px solid var(--gold);outline-offset:3px}
.factsband{background:var(--grey)}
.facts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr))}
.facts div{padding:22px 20px 22px 0;display:grid;gap:4px;align-content:start;border-right:1px solid var(--line)}
.facts div+div{padding-left:22px}.facts div:last-child{border-right:0}
.facts span{font:600 10.5px var(--font);letter-spacing:.22em;text-transform:uppercase;color:var(--muted)}
.facts b{font:500 16.5px/1.3 var(--font);color:var(--navy)}.facts small{font-size:12.5px;line-height:1.45;color:var(--ink2)}
main{display:grid;gap:80px;padding-block:72px 88px}
section{display:grid;gap:28px}
.sh{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px 40px;align-items:end}
.sh .eyebrow{grid-column:1/-1}.sh h2{font:300 clamp(30px,4vw,50px)/1.05 var(--font);letter-spacing:-.01em}.sh p{margin:0;max-width:56ch;color:var(--ink2)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px}
.card{display:grid;grid-template-rows:auto 1fr;background:var(--sheet);color:inherit;text-decoration:none;border-top:3px solid var(--gold);box-shadow:0 1px 0 var(--line);transition:transform .25s ease,box-shadow .25s ease}
.card:hover{transform:translateY(-4px);box-shadow:0 14px 30px rgba(35,37,42,.12)}
.card .thumb{aspect-ratio:4/3;overflow:hidden;background:var(--grey)}.card .thumb img{width:100%;height:100%;object-fit:cover;display:block}
.card .body{padding:16px 16px 20px;display:grid;gap:6px;align-content:start}
.card .n{font:600 10.5px var(--font);letter-spacing:.22em;text-transform:uppercase;color:var(--gold)}
.card h3{font:600 17px/1.25 var(--font)}.card p{margin:0;font-size:13.5px;line-height:1.55;color:var(--ink2)}
.list{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 48px}
.list li{display:grid;gap:2px;padding:16px 0;border-top:1px solid var(--line)}
.list b{font:600 15px/1.35 var(--font);color:var(--head)}.list span{font-size:14.5px;color:var(--ink2)}
table{width:100%;border-collapse:collapse;font-size:14.5px;background:var(--sheet)}
th,td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--line)}
th{font:600 10.5px var(--font);letter-spacing:.18em;text-transform:uppercase;color:var(--muted)}
td.n,th.n{text-align:right}tfoot td{font-weight:600;color:var(--head)}
tbody tr{cursor:pointer}tbody tr:hover,tbody tr.on{background:var(--hl)}
footer{background:var(--charcoal);color:rgba(255,255,255,.7)}
footer .wrap{padding-block:26px 34px;display:flex;flex-wrap:wrap;gap:8px 28px;font:500 11px var(--font);letter-spacing:.16em;text-transform:uppercase}
footer a{color:inherit}
/* plan page */
.top{background:var(--sheet);border-bottom:1px solid var(--line)}.top .bar a{color:var(--link)}.top .bar .here{border-bottom:2px solid var(--gold)}
.ptitle{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:end;gap:16px}
.ptitle h1{font:300 clamp(32px,4.4vw,54px)/1.05 var(--font)}
.seg{display:inline-flex;border:1px solid var(--line);background:var(--sheet)}
.seg button{appearance:none;border:0;background:none;font:600 11.5px var(--font);letter-spacing:.14em;text-transform:uppercase;padding:11px 14px;color:var(--ink2);cursor:pointer}
.seg button[aria-pressed="true"]{background:var(--navy);color:var(--paper)}
.seg button:focus-visible{outline:2px solid var(--gold);outline-offset:-2px}
.sheet{background:#fff;box-shadow:0 1px 0 var(--line);padding:clamp(6px,1.5vw,18px);position:relative}
.sheet svg{display:block;width:100%;height:auto}
.room{fill:transparent;stroke:none;cursor:pointer;transition:fill .15s}
.room:hover,.room.on{fill:rgba(183,149,101,.30)}
.room:focus-visible{outline:none;fill:rgba(183,149,101,.40);stroke:#B79565;stroke-width:4}
.wall{fill:#3A3B3F}.facade{fill:#9C9A94}.mfloor{fill:#F4F2EE}.mlbl{font:600 22px var(--font);letter-spacing:.12em;text-transform:uppercase;fill:#3A3B3F;text-anchor:middle;pointer-events:none}
.mdim{font:500 18px var(--font);fill:#7A7C80;text-anchor:middle;pointer-events:none}
.tip{position:absolute;pointer-events:none;background:var(--ink);color:var(--paper);font:500 13px/1.4 var(--font);padding:7px 10px;border-radius:4px;white-space:nowrap;transform:translate(-50%,calc(-100% - 10px))}
.tip b{font-weight:600}
.note{margin:0;font-size:14px;color:var(--ink2);max-width:80ch;border-left:3px solid var(--gold);padding-left:14px}
@media (max-width:900px){.facts{grid-template-columns:repeat(2,minmax(0,1fr))}.facts div{border-right:0;padding-left:0!important;border-bottom:1px solid var(--line)}
  .facts div:nth-child(odd){padding-right:16px}.sh{grid-template-columns:1fr}.list{grid-template-columns:1fr}}
@media (max-width:640px){.wrap{padding-inline:16px}.hero .bar nav a{margin-left:14px}.bar .wrap>span{display:none}
  th,td{padding:8px 8px}.hide-s{display:none}.seg button{padding:10px 10px;letter-spacing:.08em}}
@media (prefers-reduced-motion:reduce){.card{transition:none}}
'''

HEAD = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>%(title)s</title>
<meta name="description" content="%(desc)s">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300..700&display=swap">
<style>%(css)s</style>
</head>
'''

FOOT = '''<footer><div class="wrap"><span>%s</span><span>Drawings: the architect's plan, 2 Sep 2026</span>
<span>Built on the <a href="https://github.com/kamelshenouda/azad">AZAD</a> site and 3D viewer</span></div></footer>
''' % NAME


def area(r):
    return (r[2] - r[0]) * (r[3] - r[1]) / 1e4


def schedule():
    """Rooms as the plan page and the overview list them, with net areas from the model."""
    rows = []
    for n, r, zn in model.ROOMS:
        if n == 'Bedroom 2 entry': continue
        a = area(r) + (area(dict((q[0], q[1]) for q in model.ROOMS)['Bedroom 2 entry']) if n == 'Bedroom 2' else 0)
        rows.append(dict(n=n, r=r, zone=ZONE[zn], w=(r[2] - r[0]) / 100, d=(r[3] - r[1]) / 100, a=a,
                         extra=[q[1] for q in model.ROOMS if q[0] == 'Bedroom 2 entry'] if n == 'Bedroom 2' else []))
    tn, tr = model.TERRACE
    terrace = dict(n=tn, r=tr, zone='Outdoor', w=(tr[2] - tr[0]) / 100, d=(tr[3] - tr[1]) / 100, a=area(tr), extra=[])
    return rows, terrace


def plan_page(imgs, W, H):
    rows, terrace = schedule()
    walls = json.load(open(os.path.join(ROOT, 'data', 'walls.json')))['rects']
    total = sum(r['a'] for r in rows)
    k = PX_PER_CM

    def rect_el(r, cls, i, label):
        return '<rect class="%s" data-i="%d" x="%g" y="%g" width="%g" height="%g" tabindex="0" role="button" aria-label="%s"/>' % (
            cls, i, r[0] * k, r[1] * k, (r[2] - r[0]) * k, (r[3] - r[1]) * k, html.escape(label))

    allrooms = rows + [terrace]
    overlay = []
    for i, rm in enumerate(allrooms):
        lab = '%s, %.2f by %.2f m, %.1f square metres' % (rm['n'], rm['w'], rm['d'], rm['a'])
        overlay.append(rect_el(rm['r'], 'room', i, lab))
        for e in rm['extra']: overlay.append(rect_el(e, 'room', i, lab))
    model_g = ['<g id="mdl" hidden="">', '<rect class="mfloor" x="0" y="0" width="%d" height="%d"/>' % (W * k, H * k)]
    for w in walls:
        model_g.append('<rect class="%s" x="%g" y="%g" width="%g" height="%g"/>' % (
            'wall' if w[4] == 'wall' else 'facade', w[0] * k, w[1] * k, (w[2] - w[0]) * k, (w[3] - w[1]) * k))
    for lab, rn, x, y in model.LABELS:
        rm = next((r for r in allrooms if r['n'] == rn), None)
        model_g.append('<text class="mlbl" x="%g" y="%g">%s</text>' % (x * k, y * k, html.escape(lab)))
        if rm: model_g.append('<text class="mdim" x="%g" y="%g">%.2f × %.2f</text>' % (x * k, y * k + 26, rm['w'], rm['d']))
    model_g.append('</g>')

    trs = ''.join('<tr data-i="%d"><td>%s</td><td class="hide-s">%s</td><td class="n">%.2f × %.2f</td><td class="n">%.1f</td></tr>' % (
        i, html.escape(r['n']), r['zone'], r['w'], r['d'], r['a']) for i, r in enumerate(allrooms))
    data = json.dumps([dict(n=r['n'], z=r['zone'], d='%.2f × %.2f m' % (r['w'], r['d']), a='%.1f m²' % r['a']) for r in allrooms])

    body = '''<body>
<header class="top"><div class="bar"><div class="wrap"><a href="index.html" style="margin:0">← %(name)s</a>
<nav aria-label="Site"><a class="here" href="plan.html" aria-current="page">Plan</a><a href="3d.html">3D</a></nav></div></div></header>
<div class="wrap"><main>
<section>
  <div class="ptitle"><div><div class="eyebrow">The architect's plan, to scale</div><h1>Plan</h1></div>
  <div class="seg" role="group" aria-label="Drawing">
    <button type="button" data-k="furnished" aria-pressed="true">Furnished</button>
    <button type="button" data-k="empty" aria-pressed="false">Empty</button>
    <button type="button" data-k="model" aria-pressed="false">Model</button>
  </div></div>
  <div class="sheet" id="sheet">
    <svg viewBox="0 0 %(vw)d %(vh)d" role="img" aria-label="Floor plan of the apartment; each room can be selected">
      <image id="bg" href="%(furn)s" x="0" y="0" width="%(vw)d" height="%(vh)d"/>
      %(model)s
      <g id="rooms">%(overlay)s</g>
    </svg>
    <div class="tip" id="tip" hidden></div>
  </div>
  <p class="note">Furnished and Empty are the architect's two sheets, turned so the room names read upright. Model is what the 3D walkthrough is built from: the walls traced from the empty sheet, at 1:50, to the centimetre. Hover or tap a room for its size.</p>
</section>
<section>
  <div class="sh"><div class="eyebrow">Room schedule</div><h2>Every room, measured</h2>
  <p>Net floor areas between finished walls, from the model. The reception, living and dining are one open space on the drawing; they are split here only to give each part its size.</p></div>
  <table id="sched"><thead><tr><th>Room</th><th class="hide-s">Zone</th><th class="n">Size, m</th><th class="n">Area, m²</th></tr></thead>
  <tbody>%(trs)s</tbody>
  <tfoot><tr><td>Inside, net</td><td class="hide-s"></td><td></td><td class="n">%(total).1f</td></tr>
  <tr><td>With the terrace</td><td class="hide-s"></td><td></td><td class="n">%(total2).1f</td></tr></tfoot></table>
</section>
</main></div>
%(foot)s
<script>
(function(){
  var R=%(data)s, IM={furnished:'%(furn)s',empty:'%(empty)s'};
  var bg=document.getElementById('bg'), mdl=document.getElementById('mdl'), tip=document.getElementById('tip'), sheet=document.getElementById('sheet');
  function store(k,v){try{localStorage.setItem(k,v)}catch(e){}} function read(k){try{return localStorage.getItem(k)}catch(e){return null}}
  var segs=[].slice.call(document.querySelectorAll('.seg button'));
  function show(k){ segs.forEach(function(b){b.setAttribute('aria-pressed',b.getAttribute('data-k')===k?'true':'false');});
    if(k==='model')mdl.removeAttribute('hidden'); else mdl.setAttribute('hidden',''); bg.style.display=k==='model'?'none':''; if(IM[k])bg.setAttribute('href',IM[k]); store('creektown-plan-view',k); }
  segs.forEach(function(b){b.addEventListener('click',function(){show(b.getAttribute('data-k'));});});
  var k0=read('creektown-plan-view'); if(k0&&/^(furnished|empty|model)$/.test(k0))show(k0);
  var rects=[].slice.call(document.querySelectorAll('#rooms rect')), trs=[].slice.call(document.querySelectorAll('#sched tbody tr'));
  function on(i,el){ rects.forEach(function(r){r.classList.toggle('on',+r.getAttribute('data-i')===i);}); trs.forEach(function(t){t.classList.toggle('on',+t.getAttribute('data-i')===i);});
    if(i<0||!el){tip.hidden=true;return;} var r=R[i], b=el.getBoundingClientRect(), s=sheet.getBoundingClientRect();
    tip.innerHTML='<b>'+r.n+'</b> · '+r.d+' · '+r.a; tip.style.left=(b.left+b.width/2-s.left)+'px'; tip.style.top=(b.top+b.height/2-s.top)+'px'; tip.hidden=false; }
  rects.forEach(function(el){ var i=+el.getAttribute('data-i');
    el.addEventListener('mouseenter',function(){on(i,el);}); el.addEventListener('mouseleave',function(){on(-1);});
    el.addEventListener('focus',function(){on(i,el);}); el.addEventListener('blur',function(){on(-1);});
    el.addEventListener('click',function(){on(i,el);}); });
  trs.forEach(function(t){ var i=+t.getAttribute('data-i'); t.addEventListener('mouseenter',function(){ on(i,rects.filter(function(r){return +r.getAttribute('data-i')===i;})[0]); });
    t.addEventListener('mouseleave',function(){on(-1);}); });
})();
</script>
</body>
</html>
''' % dict(name=NAME, vw=W * k, vh=H * k, furn=imgs['furnished'], empty=imgs['empty'], model='\n      '.join(model_g),
           overlay=''.join(overlay), trs=trs, total=total, total2=total + terrace['a'], foot=FOOT, data=data)
    page = HEAD % dict(title='%s · Plan' % NAME, desc='The architect\'s plan of the Creektown apartment, furnished and empty, with every room measured.', css=CSS) + body
    open(os.path.join(ROOT, 'plan.html'), 'w', encoding='utf-8').write(page)
    return total, terrace['a']


def index_page(total, terrace):
    rows, _ = schedule()
    beds = [r for r in rows if r['zone'] == 'Bedrooms']
    room_items = ''.join('<li><b>%s · %.2f × %.2f m</b><span>%s</span></li>' % (html.escape(n), r['w'], r['d'], html.escape(t))
                         for n, t, r in [(r['n'], DESC.get(r['n'], ''), r) for r in rows] if t)
    body = '''<body>
<header class="hero">
  <div class="bar"><div class="wrap"><span>About %(tot)d m² inside + terrace</span><nav aria-label="Site"><a href="plan.html">Plan</a><a href="3d.html">3D</a></nav></div></div>
  <div class="copy wrap">
    <div class="eyebrow">Creek Town · New Cairo · interior architecture</div>
    <h1><b>Creektown</b> Apartment</h1>
    <div class="rule" aria-hidden="true"></div>
    <p>Amira's new apartment: three bedrooms, a maid's room and an open reception, living and dining onto a terrace. Measured from the architect's drawings and built as a 3D model you can walk through with the real sun.</p>
    <div class="cta"><a class="btn solid" href="plan.html">See the plan</a><a class="btn ghost" href="3d.html">Walk through it</a></div>
  </div>
</header>
<div class="factsband"><div class="wrap"><div class="facts" aria-label="Key facts">
  <div><span>Size</span><b>About %(tot).0f m² net + %(ter).1f m² terrace</b><small>Floor area between walls, from the drawing at 1:50</small></div>
  <div><span>Rooms</span><b>Master suite · %(nb)d bedrooms in all</b><small>3 bathrooms · maid's room · kitchen</small></div>
  <div><span>Living</span><b>One open space, %(liv).0f m²</b><small>Reception, living and dining for six, onto the terrace</small></div>
  <div><span>Status</span><b>As built, with the architect's furniture</b><small>Ready for layout options and finishes</small></div>
</div></div></div>
<div class="wrap"><main>
<section>
  <div class="sh"><div class="eyebrow">The project</div><h2>Explore</h2><p>Every view is drawn from the same centimetre model, traced from the architect's plan.</p></div>
  <div class="cards">
    <a class="card" href="plan.html"><div class="thumb"><img src="img/plan-thumb.jpg" alt="The furnished floor plan" loading="lazy"></div><div class="body"><div class="n">01 · Plan</div><h3>Layout, to scale</h3><p>The architect's sheets, furnished and empty, and the traced model; every room measured.</p></div></a>
    <a class="card" href="3d.html"><div class="thumb"><img src="img/3d-thumb.jpg" alt="The 3D model from above" loading="lazy"></div><div class="body"><div class="n">02 · 3D</div><h3>Walk it freely</h3><p>From above or standing in any room; furnished or empty; doors open or closed; the sun at any hour; true size on screen or in a VR headset.</p></div></a>
  </div>
</section>
<section>
  <div class="sh"><div class="eyebrow">The spaces</div><h2>Room by room</h2><p>As drawn. Sizes are between finished walls.</p></div>
  <ul class="list">%(rooms)s</ul>
</section>
<section>
  <div class="sh"><div class="eyebrow">Before the design</div><h2>Still to confirm</h2><p>The drawings don't say these, so the model uses a stand-in until they are checked on site.</p></div>
  <ul class="list">
    <li><b>Which way it faces</b><span>The sheets have no north arrow. The 3D sun assumes the window wall (the top of the plan) faces due south; one compass reading on site fixes it.</span></li>
    <li><b>Ceiling height</b><span>Taken as 2.80 m to the slab. Any beams and dropped ceilings still need measuring.</span></li>
    <li><b>Window sills and heads</b><span>Main windows from 0.90 to 2.25 m, bathroom and kitchen windows higher. The terrace has full-height sliding doors.</span></li>
    <li><b>The concrete band outside</b><span>Drawn on the facade outside the bedrooms and the reception; shown in 3D as a low planter or parapet, to be confirmed.</span></li>
  </ul>
</section>
</main></div>
%(foot)s
</body>
</html>
''' % dict(tot=total, ter=terrace, nb=len(beds), liv=sum(r['a'] for r in rows if r['n'] in ('Reception', 'Living', 'Dining')),
           rooms=room_items, foot=FOOT)
    page = HEAD % dict(title=NAME, desc='Amira\'s Creektown apartment in New Cairo: the plan to scale and a 3D walkthrough with the real sun.', css=CSS) + body
    open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8').write(page)


DESC = {
    'Master bedroom': 'A king bed on the far wall between two windows\' light, a walk-in dressing area behind a partition, and its own bathroom.',
    'Master bathroom': 'Vanity under the window wall, WC, and a full-length bath.',
    'Bedroom 1': 'A double bed against the outside wall under the window, and a full-width wardrobe.',
    'Bedroom 2': 'Two single beds with a shared bedside table, a wardrobe, and its own small entry from the corridor.',
    'Kitchen': 'Hob on the run along the corridor wall, the sink under the window, and an opening to the dining area.',
    'Maid\'s room': 'Off the kitchen, with its own window.',
    'Reception': 'A three-seat sofa, two armchairs under the window, and a two-seat sofa round a coffee table.',
    'Living': 'TV wall, sofa and a lounge chair, next to the terrace doors.',
    'Dining': 'A table for six, between the kitchen and the living area.',
}


def main():
    imgs, W, H = render_plans()
    total, terrace = plan_page(imgs, W, H)
    index_page(total, terrace)
    print('index.html, plan.html and %d images; %.1f m² inside, %.1f m² terrace' % (len(imgs) + 1, total, terrace))


if __name__ == '__main__':
    main()
