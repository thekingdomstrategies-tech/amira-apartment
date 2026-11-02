#!/usr/bin/env python3
"""Build index.html and plan.html, and the plan images they show, from the architect's PDFs and tools/model.py.

Every sheet (as built, option 1, option 2; empty and furnished) is rendered (pdftoppm), turned so the room names read
upright, moved onto the original's frame by its facade band (as tools/extract_walls.py does), and cropped at 2 px per
cm, so the drawings, the clickable rooms and the 3D model share one set of coordinates.

Usage: python3 tools/build_pages.py   ->  index.html, plan.html, img/plan-<sheet>-<empty|furnished>.jpg, img/plan-thumb.jpg
"""
import html, json, os, subprocess, sys, tempfile

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model  # noqa: E402
from extract_walls import CM_PER_PT, X0, Y0, X1, Y1, parse_svg, facade_offset  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PX_PER_CM = 2
NAME = 'Creektown Apartment'
ZONE = {'pub': 'Living', 'cir': 'Circulation', 'pri': 'Bedrooms', 'wetz': 'Wet rooms', 'ser': 'Service'}
DRAWINGS = ('furnished', 'empty')
PDF_OF = {'furnished': '%s_with_furn.pdf', 'empty': '%s_empty.pdf'}


def render_plans():
    """{plan key: {furnished: path, empty: path}}, every sheet on the original's frame."""
    os.makedirs(os.path.join(ROOT, 'img'), exist_ok=True)
    W, H = round((X1 - X0) * CM_PER_PT), round((Y1 - Y0) * CM_PER_PT)
    dpi = 300; k = dpi / 72
    out = {}
    with tempfile.TemporaryDirectory() as td:
        for key in model.ORDER:
            sheet = model.LAYOUTS[key]['sheet']
            out[key] = {}
            for dr in DRAWINGS:
                pdf = os.path.join(ROOT, 'source', PDF_OF[dr] % sheet)
                base = os.path.join(td, '%s-%s' % (sheet, dr))
                subprocess.run(['pdftocairo', '-svg', pdf, base + '.svg'], check=True)
                dx, dy = facade_offset(parse_svg(base + '.svg'))            # turned pt
                subprocess.run(['pdftoppm', '-r', str(dpi), '-png', '-singlefile', pdf, base], check=True)
                im = Image.open(base + '.png').convert('L').rotate(90, expand=True)     # anticlockwise: names upright
                box = [round((X0 - dx) * k), round((Y0 - dy) * k), round((X1 - dx) * k), round((Y1 - dy) * k)]
                im = im.crop(box).resize((W * PX_PER_CM, H * PX_PER_CM), Image.LANCZOS)
                fn = 'img/plan-%s-%s.jpg' % (sheet, dr)
                im.save(os.path.join(ROOT, fn), quality=78, optimize=True, progressive=True)
                out[key][dr] = fn
                if key == 'existing' and dr == 'furnished':
                    th = im.resize((800, int(800 * im.size[1] / im.size[0])), Image.LANCZOS)
                    th.save(os.path.join(ROOT, 'img', 'plan-thumb.jpg'), quality=80)
    return out, W, H


CSS = r'''
/* Creek Town brand (from the compound brochure): forest and leaf green on white, Poppins, heavy uppercase headings,
   a widely spaced light wordmark, large faded section numerals, square edges. */
:root{--forest:#1C3B28;--forest-2:#24492F;--leaf:#5A8C5B;--panel:#4C7D4D;--leaf-ink:#3E6E40;--lime:#8DBA6A;
  --paper:#FFFFFF;--sheet:#F3F4F2;--grey:#EDEDED;--ink:#404040;--ink2:#5C5F60;--muted:#6B6E6F;--line:#DADBDC;--head:#111111;--link:var(--leaf-ink);
  --on-dark:#FFFFFF;--on-dark2:rgba(255,255,255,.78);--hl:rgba(90,140,91,.16);--num:rgba(90,140,91,.28);
  --font:"Poppins","Helvetica Neue",Arial,sans-serif}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){color-scheme:dark;--forest:#132A1C;--forest-2:#1A3524;--leaf:#6FA26F;--panel:#2E5534;--leaf-ink:#9CCB80;--lime:#9CCB80;
  --paper:#0E1711;--sheet:#15231A;--grey:#1A2B20;--ink:#D3D9D3;--ink2:#B4BDB5;--muted:#8E998F;--line:#26382C;--head:#FFFFFF;--link:#9CCB80;
  --hl:rgba(156,203,128,.16);--num:rgba(156,203,128,.22)}}
:root[data-theme="dark"]{color-scheme:dark;--forest:#132A1C;--forest-2:#1A3524;--leaf:#6FA26F;--panel:#2E5534;--leaf-ink:#9CCB80;--lime:#9CCB80;
  --paper:#0E1711;--sheet:#15231A;--grey:#1A2B20;--ink:#D3D9D3;--ink2:#B4BDB5;--muted:#8E998F;--line:#26382C;--head:#FFFFFF;--link:#9CCB80;
  --hl:rgba(156,203,128,.16);--num:rgba(156,203,128,.22)}
*{box-sizing:border-box}[hidden]{display:none!important}
body{margin:0;background:var(--paper);color:var(--ink);font:400 15.5px/1.75 var(--font);font-variant-numeric:lining-nums tabular-nums}
a{color:var(--link)}img{max-width:100%}
.wrap{max-width:1200px;margin:0 auto;padding-inline:24px}
.eyebrow{font:600 11px/1.2 var(--font);letter-spacing:.2em;text-transform:uppercase;color:var(--leaf-ink)}
h1,h2,h3{font-family:var(--font);margin:0;text-wrap:balance;color:var(--head)}
/* running header, as on every brochure spread: name left, place right */
.bar .wrap{display:flex;justify-content:space-between;align-items:center;gap:12px;padding-block:20px;font:600 11px var(--font);letter-spacing:.12em;text-transform:uppercase}
.bar a{text-decoration:none;margin-left:24px}
/* the cover: forest green, the wordmark centred-left */
.hero{background:var(--forest);color:var(--on-dark)}
.hero .bar{color:var(--on-dark2)}.hero .bar a{color:var(--on-dark);opacity:.85}.hero .bar a:hover{opacity:1;color:var(--lime)}
.hero .copy{padding-block:clamp(56px,10vw,132px) clamp(56px,8vw,96px);display:grid;gap:20px;justify-items:start}
.wm{display:grid;gap:10px;color:var(--on-dark)}
.wm .w1{font:300 clamp(34px,6.4vw,86px)/1 var(--font);letter-spacing:.32em;text-transform:uppercase;margin-right:-.32em}
.wm .w1 b{display:inline-block;font-weight:600;letter-spacing:.06em;font-size:.52em;vertical-align:.18em}
.wm .w2{font:400 clamp(12px,1.3vw,15px)/1 var(--font);letter-spacing:.42em;text-transform:uppercase;color:var(--on-dark2)}
.hero .eyebrow{color:var(--lime)}
.hero p{margin:0;max-width:58ch;font-size:clamp(15px,1.4vw,18px);font-weight:300;color:var(--on-dark2)}
.cta{display:flex;flex-wrap:wrap;gap:12px;margin-top:10px}
.btn{display:inline-flex;align-items:center;gap:8px;font:600 12px var(--font);letter-spacing:.12em;text-transform:uppercase;padding:14px 22px;text-decoration:none}
.btn.solid{background:#fff;color:var(--forest)}.btn.ghost{border:1.5px solid rgba(255,255,255,.7);color:#fff}
.btn:hover{filter:brightness(1.06)}
.btn:focus-visible,.card:focus-visible{outline:3px solid var(--lime);outline-offset:3px}
/* key facts on a leaf-green panel */
.factsband{background:var(--panel);color:#fff}
.facts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr))}
.facts div{padding:24px 20px 24px 0;display:grid;gap:4px;align-content:start;border-right:1px solid rgba(255,255,255,.28)}
.facts div+div{padding-left:22px}.facts div:last-child{border-right:0}
.facts span{font:600 10.5px var(--font);letter-spacing:.18em;text-transform:uppercase;color:#fff;opacity:.9}
.facts b{font:700 16px/1.3 var(--font);color:#fff;text-transform:uppercase;letter-spacing:.01em}
.facts small{font-size:12.5px;line-height:1.5;color:#fff}
main{display:grid;gap:88px;padding-block:76px 92px;counter-reset:sec}
main>section{display:grid;gap:28px;counter-increment:sec}
/* section heads: a large faded numeral beside a heavy uppercase title, as the brochure's "01 ABOUT US" */
.sh{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px 40px;align-items:end}
.sh .eyebrow{grid-column:1/-1}
.sh h2{display:flex;align-items:baseline;gap:.35em;font:700 clamp(26px,3.4vw,42px)/1.05 var(--font);text-transform:uppercase;letter-spacing:-.005em}
.sh h2::before{content:counter(sec,decimal-leading-zero);font:300 2.1em/.8 var(--font);color:var(--num);letter-spacing:-.04em}
.sh p{margin:0;max-width:56ch;color:var(--ink2)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px}
.card{display:grid;grid-template-rows:auto 1fr;background:var(--sheet);color:inherit;text-decoration:none;transition:transform .25s ease,box-shadow .25s ease}
.card:hover{transform:translateY(-4px);box-shadow:0 14px 30px rgba(17,17,17,.12)}
.card .thumb{aspect-ratio:4/3;overflow:hidden;background:var(--grey)}.card .thumb img{width:100%;height:100%;object-fit:cover;display:block}
.card .body{padding:18px 18px 22px;display:grid;gap:6px;align-content:start;border-top:4px solid var(--leaf)}
.card .n{font:600 10.5px var(--font);letter-spacing:.18em;text-transform:uppercase;color:var(--leaf-ink)}
.card h3{font:700 17px/1.25 var(--font);text-transform:uppercase}.card p{margin:0;font-size:13.5px;line-height:1.6;color:var(--ink2)}
.list{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 48px}
.list li{display:grid;gap:2px;padding:16px 0;border-top:1px solid var(--line)}
.list b{font:600 14.5px/1.4 var(--font);color:var(--head)}.list span{font-size:14px;color:var(--ink2)}
table{width:100%;border-collapse:collapse;font-size:14px;background:var(--paper)}
th,td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--line)}
th{font:600 10.5px var(--font);letter-spacing:.14em;text-transform:uppercase;color:var(--muted);border-bottom:2px solid var(--head)}
td.n,th.n{text-align:right}tfoot td{font-weight:700;color:var(--head);text-transform:uppercase;font-size:13px;letter-spacing:.04em}
tbody tr{cursor:pointer}tbody tr:hover,tbody tr.on{background:var(--hl)}
footer{background:var(--forest);color:rgba(255,255,255,.75)}
footer .wrap{padding-block:28px 36px;display:flex;flex-wrap:wrap;gap:8px 28px;font:500 11px var(--font);letter-spacing:.14em;text-transform:uppercase}
footer a{color:inherit}
/* plan page */
.top{background:var(--paper);border-bottom:1px solid var(--line)}.top .bar a{color:var(--head)}.top .bar .here{border-bottom:2px solid var(--leaf);padding-bottom:3px}
.ptitle{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:end;gap:16px}
.ptitle h1{font:700 clamp(28px,4vw,48px)/1.05 var(--font);text-transform:uppercase}
.seg{display:inline-flex;border:1px solid var(--line);background:var(--paper)}
.seg button{appearance:none;border:0;background:none;font:600 11px var(--font);letter-spacing:.1em;text-transform:uppercase;padding:11px 14px;color:var(--ink2);cursor:pointer}
.seg button[aria-pressed="true"]{background:var(--forest);color:#fff}
.seg button:focus-visible{outline:2px solid var(--lime);outline-offset:-2px}
.sheet{background:#fff;border:1px solid var(--line);padding:clamp(6px,1.5vw,18px);position:relative}
.sheet svg{display:block;width:100%;height:auto}
.room{fill:transparent;stroke:none;cursor:pointer;transition:fill .15s}
.room:hover,.room.on{fill:rgba(90,140,91,.30)}
.room:focus-visible{outline:none;fill:rgba(90,140,91,.40);stroke:#5A8C5B;stroke-width:4}
.wall{fill:#1C3B28}.facade{fill:#9AA79B}.mfloor{fill:#F3F4F2}.mlbl{font:700 22px var(--font);letter-spacing:.06em;text-transform:uppercase;fill:#111;text-anchor:middle;pointer-events:none}
.mdim{font:500 18px var(--font);fill:#76797A;text-anchor:middle;pointer-events:none}
.tip{position:absolute;pointer-events:none;background:var(--forest);color:#fff;font:500 13px/1.4 var(--font);padding:7px 10px;white-space:nowrap;transform:translate(-50%,calc(-100% - 10px))}
.tip b{font-weight:600}
.note{margin:0;font-size:13.5px;color:var(--ink2);max-width:80ch;border-left:3px solid var(--leaf);padding-left:14px}
.segs{display:flex;flex-wrap:wrap;gap:10px}
.seg small{font-weight:500;letter-spacing:.02em;text-transform:none;opacity:.8}
/* the three plans: leaf-green cards, as the brochure's unit-type panels */
.opts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}
.opt{background:var(--panel);color:#fff;padding:22px 22px 20px;display:grid;gap:10px;align-content:start}
.opt .n{font:600 10.5px var(--font);letter-spacing:.18em;text-transform:uppercase;color:#fff;opacity:.9}
.opt h3{font:700 21px/1.15 var(--font);text-transform:uppercase;color:#fff}
.opt .dims{margin:0;font:600 12.5px var(--font);letter-spacing:.04em;color:#fff}
.opt ul{margin:0;padding-left:18px;font-size:13.5px;line-height:1.6;color:#fff;display:grid;gap:6px}
.opt .go{margin:6px 0 0;display:flex;gap:18px;font:600 11.5px var(--font);letter-spacing:.12em;text-transform:uppercase}
.opt .go a{color:#fff;text-decoration:none;border-bottom:2px solid rgba(255,255,255,.8);padding-bottom:2px}
.opt .go a:hover{border-color:#fff}
.opt:first-child{background:var(--forest)}
.cmp tbody tr{cursor:default}.cmp tbody tr:hover{background:none}
@media (max-width:900px){.opts{grid-template-columns:minmax(0,1fr)}.facts{grid-template-columns:repeat(2,minmax(0,1fr))}.facts div{border-right:0;padding-left:0!important;border-bottom:1px solid rgba(255,255,255,.28)}
  .facts div:nth-child(odd){padding-right:16px}.sh{grid-template-columns:1fr}.list{grid-template-columns:1fr}}
@media (max-width:640px){.wrap{padding-inline:16px}.hero .bar nav a{margin-left:14px}.bar .wrap>span{display:none}
  th,td{padding:8px 8px}.hide-s{display:none}.seg button{padding:10px 10px;letter-spacing:.06em}.wm .w1{letter-spacing:.2em}}
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
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap">
<style>%(css)s</style>
</head>
'''

FOOT = '''<footer><div class="wrap"><span>%s</span><span>Drawings: the architect's plans, 2 Sep 2026</span>
<span>Built on the <a href="https://github.com/kamelshenouda/azad">AZAD</a> site and 3D viewer</span></div></footer>
''' % NAME


def area(r):
    return (r[2] - r[0]) * (r[3] - r[1]) / 1e4


def schedule(key):
    """Rooms of a plan as the pages list them, with net areas from the model; the terrace last.
    Returns (rows, net inside, outdoor)."""
    zone = {}
    for n, r, zn in model.LAYOUTS[key]['rooms']:
        zone.setdefault(n, zn)
    rows = []
    for n, rects in model.room_rects(key).items():
        r = rects[0]
        rows.append(dict(n=n, r=r, extra=rects[1:], zone=ZONE[zone[n]] if n in zone else 'Outdoor',
                         w=(r[2] - r[0]) / 100, d=(r[3] - r[1]) / 100, a=sum(area(q) for q in rects)))
    return (rows, sum(r['a'] for r in rows if r['zone'] != 'Outdoor'),
            sum(r['a'] for r in rows if r['zone'] == 'Outdoor'))


def counts(key):
    names = list(model.room_rects(key))
    beds = [n for n in names if n.startswith(('Master bedroom', 'Bedroom'))]
    baths = [n for n in names if 'bath' in n.lower()]
    return len(beds), len(baths)


PLAN_BODY = r'''<body>
<header class="top"><div class="bar"><div class="wrap"><a href="index.html" style="margin:0">← %(name)s</a>
<nav aria-label="Site"><a class="here" href="plan.html" aria-current="page">Plan</a><a href="3d.html" id="to3d">3D</a></nav></div></div></header>
<div class="wrap"><main>
<section>
  <div class="ptitle"><div><div class="eyebrow">The architect's plans, to scale</div><h1 id="ptitle">Plan</h1></div>
  <div class="segs">
  <div class="seg" id="plans" role="group" aria-label="Plan">%(plans)s</div>
  <div class="seg" id="draw" role="group" aria-label="Drawing">
    <button type="button" data-k="furnished" aria-pressed="true">Furnished</button>
    <button type="button" data-k="empty" aria-pressed="false">Empty</button>
    <button type="button" data-k="model" aria-pressed="false">Model</button>
  </div></div></div>
  <div class="sheet" id="sheet">
    <svg viewBox="0 0 %(vw)d %(vh)d" role="img" aria-label="Floor plan of the apartment; each room can be selected">
      <image id="bg" href="%(furn)s" x="0" y="0" width="%(vw)d" height="%(vh)d"/>
      %(models)s
      %(overlays)s
    </svg>
    <div class="tip" id="tip" hidden></div>
  </div>
  <p class="note">Furnished and Empty are the architect's two sheets for each plan, turned so the room names read upright. Model is what the 3D walkthrough is built from: the walls traced from the empty sheet, at 1:50, to the centimetre. Hover or tap a room for its size, or <a id="walk" href="3d.html">walk through this plan in 3D</a>.</p>
</section>
<section>
  <div class="sh"><div class="eyebrow">Room schedule</div><h2>Every room, measured</h2>
  <p>Net floor areas between finished walls, from the model. Open spaces are split only to give each part its size; a + marks a room in more than one piece, with its total area.</p></div>
  %(tables)s
</section>
</main></div>
%(foot)s
<script>
(function(){
  var D=%(data)s, P='existing', V='furnished';
  var bg=document.getElementById('bg'), tip=document.getElementById('tip'), sheet=document.getElementById('sheet');
  function store(k,v){try{localStorage.setItem(k,v)}catch(e){}} function read(k){try{return localStorage.getItem(k)}catch(e){return null}}
  function each(sel,f){[].forEach.call(document.querySelectorAll(sel),f);}
  function hide(el,h){ if(h)el.setAttribute('hidden',''); else el.removeAttribute('hidden'); }   // SVG elements ignore .hidden
  function on(i,el){
    each('.rooms[data-p="'+P+'"] rect',function(r){r.classList.toggle('on',+r.getAttribute('data-i')===i);});
    each('.sched[data-p="'+P+'"] tbody tr',function(t){t.classList.toggle('on',+t.getAttribute('data-i')===i);});
    if(i<0||!el){tip.hidden=true;return;} var r=D[P].rooms[i], b=el.getBoundingClientRect(), s=sheet.getBoundingClientRect();
    tip.innerHTML='<b>'+r.n+'</b> · '+r.d+' · '+r.a; tip.style.left=(b.left+b.width/2-s.left)+'px'; tip.style.top=(b.top+b.height/2-s.top)+'px'; tip.hidden=false; }
  function render(){
    each('#plans button',function(b){b.setAttribute('aria-pressed',b.getAttribute('data-p')===P?'true':'false');});
    each('#draw button',function(b){b.setAttribute('aria-pressed',b.getAttribute('data-k')===V?'true':'false');});
    each('.mdl',function(g){hide(g,V!=='model'||g.getAttribute('data-p')!==P);});
    each('.rooms',function(g){hide(g,g.getAttribute('data-p')!==P);});
    each('.sched',function(t){hide(t,t.getAttribute('data-p')!==P);});
    bg.style.display=V==='model'?'none':''; if(V!=='model')bg.setAttribute('href',D[P].img[V]);
    document.getElementById('ptitle').textContent=D[P].name;
    var u='3d.html?plan='+P; document.getElementById('walk').href=u; document.getElementById('to3d').href=u;
    on(-1); store('creektown-plan-view',V); store('creektown-plan',P);
    try{ history.replaceState(null,'',P==='existing'?location.pathname:'?plan='+P); }catch(e){}
  }
  each('#plans button',function(b){b.addEventListener('click',function(){P=b.getAttribute('data-p');render();});});
  each('#draw button',function(b){b.addEventListener('click',function(){V=b.getAttribute('data-k');render();});});
  var q=/[?&]plan=(\w+)/.exec(location.search), p0=(q&&q[1])||read('creektown-plan'), v0=read('creektown-plan-view');
  if(p0&&D[p0])P=p0; if(v0&&/^(furnished|empty|model)$/.test(v0))V=v0;
  each('.rooms rect',function(el){ var i=+el.getAttribute('data-i');
    el.addEventListener('mouseenter',function(){on(i,el);}); el.addEventListener('mouseleave',function(){on(-1);});
    el.addEventListener('focus',function(){on(i,el);}); el.addEventListener('blur',function(){on(-1);});
    el.addEventListener('click',function(){on(i,el);}); });
  each('.sched tbody tr',function(t){ var i=+t.getAttribute('data-i');
    t.addEventListener('mouseenter',function(){ on(i,document.querySelector('.rooms[data-p="'+P+'"] rect[data-i="'+i+'"]')); });
    t.addEventListener('mouseleave',function(){on(-1);}); });
  render();
})();
</script>
</body>
</html>
'''

SCHED = '''<table class="sched" data-p="%(key)s"%(hidden)s><thead><tr><th>Room</th><th class="hide-s">Zone</th><th class="n">Size, m</th><th class="n">Area, m²</th></tr></thead>
  <tbody>%(trs)s</tbody>
  <tfoot><tr><td>Inside, net</td><td class="hide-s"></td><td></td><td class="n">%(total).1f</td></tr>
  <tr><td>With the terrace</td><td class="hide-s"></td><td></td><td class="n">%(total2).1f</td></tr></tfoot></table>'''


def plan_page(imgs, W, H):
    k = PX_PER_CM

    def rect_el(r, i, label):
        return '<rect class="room" data-i="%d" x="%g" y="%g" width="%g" height="%g" tabindex="0" role="button" aria-label="%s"/>' % (
            i, r[0] * k, r[1] * k, (r[2] - r[0]) * k, (r[3] - r[1]) * k, html.escape(label))

    models, overlays, tables, data, totals = [], [], [], {}, {}
    for key in model.ORDER:
        lay = model.LAYOUTS[key]
        rows, total, outdoor = schedule(key)
        totals[key] = total
        hidden = '' if key == 'existing' else ' hidden=""'
        ov = []
        for i, rm in enumerate(rows):
            lab = '%s, %.2f by %.2f m, %.1f square metres' % (rm['n'], rm['w'], rm['d'], rm['a'])
            ov += [rect_el(r, i, lab) for r in [rm['r']] + rm['extra']]
        overlays.append('<g class="rooms" data-p="%s"%s>%s</g>' % (key, hidden, ''.join(ov)))
        g = ['<g class="mdl" data-p="%s" hidden="">' % key, '<rect class="mfloor" x="0" y="0" width="%d" height="%d"/>' % (W * k, H * k)]
        for w in model.walls_of(key):
            g.append('<rect class="%s" x="%g" y="%g" width="%g" height="%g"/>' % (
                'wall' if w[4] == 'wall' else 'facade', w[0] * k, w[1] * k, (w[2] - w[0]) * k, (w[3] - w[1]) * k))
        measured = set()
        for lab, rn, x, y in lay['labels']:
            g.append('<text class="mlbl" x="%g" y="%g">%s</text>' % (x * k, y * k, html.escape(lab)))
            rm = next((r for r in rows if r['n'] == rn), None)
            if rm and rn not in measured:   # a second label for one room (the dressing area) carries no size
                measured.add(rn)
                g.append('<text class="mdim" x="%g" y="%g">%.2f × %.2f</text>' % (x * k, y * k + 26, rm['w'], rm['d']))
        g.append('</g>')
        models.append(''.join(g))
        trs = ''.join('<tr data-i="%d"><td>%s</td><td class="hide-s">%s</td><td class="n">%.2f × %.2f%s</td><td class="n">%.1f</td></tr>' % (
            i, html.escape(r['n']), r['zone'], r['w'], r['d'], ' +' if r['extra'] else '', r['a']) for i, r in enumerate(rows))
        tables.append(SCHED % dict(key=key, hidden=hidden, trs=trs, total=total, total2=total + outdoor))
        data[key] = dict(rooms=[dict(n=r['n'], d='%.2f × %.2f m' % (r['w'], r['d']), a='%.1f m²' % r['a']) for r in rows],
                         img=imgs[key], name=lay['name'])

    plans = ''.join('<button type="button" data-p="%s" aria-pressed="%s">%s <small>%s</small></button>' % (
        key, 'true' if key == 'existing' else 'false', *model.LAYOUTS[key]['button']) for key in model.ORDER)
    body = PLAN_BODY % dict(name=NAME, vw=W * k, vh=H * k, furn=imgs['existing']['furnished'], models='\n      '.join(models),
                            overlays='\n      '.join(overlays), tables='\n  '.join(tables), plans=plans, foot=FOOT,
                            data=json.dumps(data, ensure_ascii=False))
    page = HEAD % dict(title='%s · Plan' % NAME, css=CSS,
                       desc='The architect\'s plans of the Creektown apartment: as built and two layout options, furnished and empty, with every room measured.') + body
    open(os.path.join(ROOT, 'plan.html'), 'w', encoding='utf-8').write(page)
    return totals


OPTIONS = {
    'existing': ('As handed over', [
        'Three bedrooms, the master with a dressing area and its own bathroom.',
        'Two more bathrooms off the corridor, a closed kitchen and a maid\'s room.',
        'One open reception, living and dining space onto the terrace.',
    ]),
    'o1': ('A bigger master suite', [
        'The master bedroom moves to bedroom 1 and opens into a dressing area, which leads to the master bathroom.',
        'A galley kitchen takes the old master bedroom: two runs facing each other, open to the corridor, with a breakfast table.',
        'The two corridor bathrooms become one, with a shower and the washing machine.',
        'The old kitchen opens into the living area and takes the dining table; the maid\'s room becomes storage.',
        'Bedroom 2 is entered from a wider corridor, which takes in its old entry.',
    ]),
    'o2': ('A family kitchen', [
        'The bedrooms stay; the master bedroom door moves along the corridor and its dressing becomes an L of wardrobes.',
        'Bedroom 2 is entered from a wider corridor, its old entry now a cupboard; it is drawn as a sitting room or study.',
        'The two corridor bathrooms become one, with a shower and the washing machine.',
        'The kitchen takes in the maid\'s room and opens onto the dining area, with an island and three stools.',
    ]),
}

INDEX_BODY = '''<body>
<header class="hero">
  <div class="bar"><div class="wrap"><span>About %(tot)d m² inside + terrace</span><nav aria-label="Site"><a href="plan.html">Plan</a><a href="3d.html">3D</a></nav></div></div>
  <div class="copy wrap">
    <div class="eyebrow">Creek Town · New Cairo · interior architecture</div>
    <h1 class="wm" aria-label="Creektown Apartment, New Cairo"><span class="w1">Creektown <b>Apartment</b></span><span class="w2">New Cairo</span></h1>
    <p>Amira's new apartment: three bedrooms, a maid's room and an open reception, living and dining onto a terrace, and the architect's two options for reworking it. Measured from the drawings and built as a 3D model you can walk through with the real sun.</p>
    <div class="cta"><a class="btn solid" href="plan.html">See the plans</a><a class="btn ghost" href="3d.html">Walk through them</a></div>
  </div>
</header>
<div class="factsband"><div class="wrap"><div class="facts" aria-label="Key facts">
  <div><span>Size</span><b>About %(tot).0f m² net + %(ter).1f m² terrace</b><small>Floor area between walls, from the drawings at 1:50</small></div>
  <div><span>As built</span><b>Master suite · %(nb)d bedrooms in all</b><small>3 bathrooms · maid's room · kitchen</small></div>
  <div><span>Options</span><b>Two bedrooms or three</b><small>Option 1 trades a bedroom for a master suite and a galley kitchen; option 2 opens up the kitchen</small></div>
  <div><span>Status</span><b>Choosing the layout</b><small>As built and both options, each with the architect's furniture</small></div>
</div></div></div>
<div class="wrap"><main>
<section>
  <div class="sh"><div class="eyebrow">The project</div><h2>Explore</h2><p>Every view is drawn from the same centimetre model, traced from the architect's plans.</p></div>
  <div class="cards">
    <a class="card" href="plan.html"><div class="thumb"><img src="img/plan-thumb.jpg" alt="The furnished floor plan" loading="lazy"></div><div class="body"><div class="n">01 · Plan</div><h3>Layouts, to scale</h3><p>As built and both options: the architect's sheets, furnished and empty, and the traced model; every room measured.</p></div></a>
    <a class="card" href="3d.html"><div class="thumb"><img src="img/3d-thumb.jpg" alt="The 3D model from above" loading="lazy"></div><div class="body"><div class="n">02 · 3D</div><h3>Walk it freely</h3><p>Switch between the three plans, from above or standing in any room; furnished or empty; the sun at any hour; true size on screen or in a VR headset.</p></div></a>
  </div>
</section>
<section>
  <div class="sh"><div class="eyebrow">The layout</div><h2>Three plans</h2><p>The architect's two options rework the inside of the same shell: the facade, windows, terrace and front door stay as built.</p></div>
  <div class="opts">%(cards)s</div>
  <table class="cmp"><thead><tr><th>Room, m²</th>%(cmp_head)s</tr></thead><tbody>%(cmp_rows)s</tbody>
  <tfoot><tr><td>Inside, net</td>%(cmp_foot)s</tr></tfoot></table>
  <p class="note">Open spaces are split only to give each part its size, so an area moves when a neighbouring wall comes down: in option 1 the dining area takes in the old kitchen, and in both options the corridor takes in bedroom 2's old entry.</p>
</section>
<section>
  <div class="sh"><div class="eyebrow">As built</div><h2>Room by room</h2><p>As drawn. Sizes are between finished walls.</p></div>
  <ul class="list">%(rooms)s</ul>
</section>
<section>
  <div class="sh"><div class="eyebrow">Before the design</div><h2>Still to confirm</h2><p>The drawings don't say these, so the model uses a stand-in until they are checked on site or with the architect.</p></div>
  <ul class="list">
    <li><b>Which way it faces</b><span>The sheets have no north arrow. The 3D sun assumes the window wall (the top of the plan) faces due south; one compass reading on site fixes it.</span></li>
    <li><b>Ceiling height</b><span>Taken as 2.80 m to the slab. Any beams and dropped ceilings still need measuring.</span></li>
    <li><b>Window sills and heads</b><span>Main windows from 0.90 to 2.25 m, bathroom and kitchen windows higher. The terrace has full-height sliding doors.</span></li>
    <li><b>The concrete band outside</b><span>Drawn on the facade outside the bedrooms and the reception; shown in 3D as a low planter or parapet, to be confirmed.</span></li>
    <li><b>Option 1: dressing area and kitchen</b><span>The empty sheet draws no wall between them, and no door to the master bathroom. The 3D model puts a partition where the furnished sheet draws a line, and leaves the bathroom doorway open.</span></li>
    <li><b>Doors and chairs the sheets leave out</b><span>Option 1's bathroom door has no swing drawn, so it is hinged on the vanity side; dining chairs are added where the options draw the table alone.</span></li>
  </ul>
</section>
</main></div>
%(foot)s
</body>
</html>
'''


def index_page(totals):
    rows, total, terrace = schedule('existing')
    beds = [r for r in rows if r['zone'] == 'Bedrooms']
    room_items = ''.join('<li><b>%s · %.2f × %.2f m</b><span>%s</span></li>' % (html.escape(r['n']), r['w'], r['d'], html.escape(DESC[r['n']]))
                         for r in rows if r['n'] in DESC)
    cards = []
    for key in model.ORDER:
        lay = model.LAYOUTS[key]
        nb, nbath = counts(key)
        head, pts = OPTIONS[key]
        cards.append('<article class="opt"><div class="n">%s · %s</div><h3>%s</h3><p class="dims">%d bedrooms · %d bathrooms · %.0f m² net</p>'
                     '<ul>%s</ul><p class="go"><a href="plan.html?plan=%s">Plan</a><a href="3d.html?plan=%s">3D</a></p></article>' % (
                         lay['button'][0], lay['button'][1], head, nb, nbath, totals[key],
                         ''.join('<li>%s</li>' % html.escape(t) for t in pts), key, key))
    names, areas = [], {}
    for key in model.ORDER:
        areas[key] = {}
        for r in schedule(key)[0]:
            if r['zone'] == 'Outdoor': continue
            areas[key][r['n']] = r['a']
            if r['n'] not in names: names.append(r['n'])
    cmp_rows = ''.join('<tr><td>%s</td>%s</tr>' % (html.escape(n), ''.join(
        '<td class="n">%s</td>' % ('%.1f' % areas[key][n] if n in areas[key] else '–') for key in model.ORDER)) for n in names)
    body = INDEX_BODY % dict(
        tot=total, ter=terrace, nb=len(beds), rooms=room_items, cards=''.join(cards), cmp_rows=cmp_rows, foot=FOOT,
        cmp_head=''.join('<th class="n">%s</th>' % model.LAYOUTS[key]['button'][0] for key in model.ORDER),
        cmp_foot=''.join('<td class="n">%.1f</td>' % totals[key] for key in model.ORDER))
    page = HEAD % dict(title=NAME, css=CSS,
                       desc='Amira\'s Creektown apartment in New Cairo: the plans to scale, as built and two layout options, and a 3D walkthrough with the real sun.') + body
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
    totals = plan_page(imgs, W, H)
    index_page(totals)
    print('index.html, plan.html and %d images; net inside: %s' % (
        sum(len(v) for v in imgs.values()) + 1, ', '.join('%s %.1f m²' % (k, v) for k, v in totals.items())))


if __name__ == '__main__':
    main()
