#!/usr/bin/env python3
"""Build index.html and plan.html, and the plan images they show, from the architect's PDFs and tools/model.py.

Every sheet (as built, option 1, option 2; empty and furnished) is rendered (pdftoppm), turned so the room names read
upright, moved onto the original's frame by its facade band (as tools/extract_walls.py does), and cropped at 2 px per
cm, so the drawings, the clickable rooms and the 3D model share one set of coordinates.

Usage: python3 tools/build_pages.py   ->  index.html, plan.html, img/plan-<sheet>-<empty|furnished>.jpg, img/plan-thumb.jpg
"""
import html, json, math, os, subprocess, sys, tempfile

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model  # noqa: E402
import clean_walls  # noqa: E402
from extract_walls import CM_PER_PT, X0, Y0, X1, Y1, parse_svg, facade_offset  # noqa: E402
from build_3d import SITE  # noqa: E402
SITE_FACING = SITE['facing']   # the bearing the top of the plan faces

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


HERO_PAGE = 53     # the brochure's apartment-building render, behind the overview's header


def hero_image():
    """The Creek Town apartment buildings (brochure page 53) for the header: the page's own labels taken out."""
    with tempfile.TemporaryDirectory() as td:
        base = os.path.join(td, 'hero')
        subprocess.run(['pdftoppm', '-r', '160', '-png', '-singlefile', '-f', str(HERO_PAGE), '-l', str(HERO_PAGE),
                        os.path.join(ROOT, 'source', 'creek_town_brochure.pdf'), base], check=True, stderr=subprocess.DEVNULL)
        im = Image.open(base + '.png').convert('RGB')
    W, H = im.size
    # the running header "CREEK TOWN" sits in the sky at the top left: cover it with the sky just right of it
    k = W / 2709
    box = tuple(round(v * k) for v in (70, 66, 236, 106))
    patch = im.crop((box[2] + 10, box[1], box[2] + 10 + (box[2] - box[0]), box[3]))
    im.paste(patch, box[:2])
    im = im.crop((0, 0, W, round(H * .905)))          # the page numbers along the bottom edge
    for w, q, name in ((2400, 74, 'hero-building.jpg'), (1200, 74, 'hero-building-s.jpg')):
        im.resize((w, round(w * im.size[1] / im.size[0])), Image.LANCZOS).save(
            os.path.join(ROOT, 'img', name), quality=q, optimize=True, progressive=True)


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
.hero{position:relative;overflow:hidden;isolation:isolate;background:var(--forest);color:var(--on-dark)}
/* the compound's apartment buildings (brochure page 53) under a forest-green gradient: the text side stays deep green,
   the buildings show through on the right; the photo drifts slowly and a soft light moves over it */
.hero-bg{position:absolute;inset:0 0 0 30%;z-index:-3;background:#1C3B28 url(img/hero-building.jpg) 46% 40%/cover no-repeat;
  transform-origin:50% 45%;animation:hero-drift 46s ease-in-out infinite alternate;will-change:transform;
  -webkit-mask-image:linear-gradient(90deg,transparent 0,#000 22%);mask-image:linear-gradient(90deg,transparent 0,#000 22%)}
@media (max-width:900px){.hero-bg{inset:0;background-image:url(img/hero-building-s.jpg);background-position:48% 40%;-webkit-mask-image:none;mask-image:none}}
.hero::before{content:"";position:absolute;inset:0;z-index:-2;
  background:linear-gradient(96deg,rgba(28,59,40,.98) 0%,rgba(28,59,40,.96) 33%,rgba(28,59,40,.72) 47%,rgba(28,59,40,.30) 68%,rgba(28,59,40,.08) 100%),
             linear-gradient(0deg,rgba(28,59,40,.9) 0%,rgba(28,59,40,0) 30%),
             linear-gradient(180deg,rgba(28,59,40,.55) 0%,rgba(28,59,40,0) 22%)}
.hero-light{position:absolute;inset:-25%;z-index:-1;pointer-events:none;mix-blend-mode:soft-light;
  background:radial-gradient(32% 40% at 72% 30%,rgba(255,238,205,.45),rgba(255,238,205,0) 70%),
             radial-gradient(30% 38% at 40% 78%,rgba(141,186,106,.45),rgba(141,186,106,0) 70%);
  animation:hero-light 26s ease-in-out infinite alternate}
@keyframes hero-drift{0%{transform:scale(1.06) translate3d(-1.2%,.6%,0)}100%{transform:scale(1.16) translate3d(1.6%,-1.4%,0)}}
@keyframes hero-light{0%{transform:translate3d(-7%,-3%,0) rotate(-4deg);opacity:.75}100%{transform:translate3d(7%,4%,0) rotate(6deg);opacity:1}}
.hero .copy>*{animation:hero-in .9s cubic-bezier(.2,.7,.2,1) both}
.hero .copy>:nth-child(2){animation-delay:.08s}.hero .copy>:nth-child(3){animation-delay:.16s}.hero .copy>:nth-child(4){animation-delay:.24s}
@keyframes hero-in{from{opacity:0;transform:translate3d(0,14px,0)}to{opacity:1;transform:none}}
@media (max-width:900px){.hero::before{background:linear-gradient(180deg,rgba(28,59,40,.82) 0%,rgba(28,59,40,.9) 45%,rgba(28,59,40,.97) 100%)}}
@media (prefers-reduced-motion:reduce){.hero-bg,.hero-light,.hero .copy>*{animation:none}.hero-bg{transform:scale(1.06)}}
.hero .bar{color:var(--on-dark2)}.hero .bar a{color:var(--on-dark);opacity:.85}.hero .bar a:hover{opacity:1;color:var(--lime)}
.hero .copy{padding-block:clamp(56px,10vw,132px) clamp(56px,8vw,96px);display:grid;gap:20px;justify-items:start}
.wm{display:grid;gap:10px;color:var(--on-dark);text-shadow:0 2px 28px rgba(8,22,14,.55)}
.wm .w1{font:300 clamp(34px,6.4vw,86px)/1 var(--font);letter-spacing:.32em;text-transform:uppercase;margin-right:-.32em}
.wm .w1 b{display:inline-block;font-weight:600;letter-spacing:.06em;font-size:.52em;vertical-align:.18em}
.wm .w2{font:400 clamp(12px,1.3vw,15px)/1 var(--font);letter-spacing:.42em;text-transform:uppercase;color:var(--on-dark2)}
.hero .eyebrow{color:var(--lime)}
.hero p{margin:0;max-width:50ch;font-size:clamp(15px,1.4vw,18px);font-weight:300;color:var(--on-dark2)}
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
.sheet{overflow:auto;-webkit-overflow-scrolling:touch}.sheetin{width:100%}
.pmeta{margin:6px 0 0;font:500 12.5px var(--font);letter-spacing:.04em;color:var(--muted)}.pmeta b{color:var(--head);font-weight:600}
.ztools{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;padding:12px 14px;background:var(--sheet);border:1px solid var(--line);border-bottom:0}
.zopt{display:flex;align-items:center;gap:8px}.zopt>span{font:600 10.5px var(--font);letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.zopt .seg button{padding:8px 11px}
.zbg{fill:#FBFAF8}.zroom,.zterr{stroke:none}.zterr{stroke:#8DAA7E;stroke-width:2;stroke-dasharray:8 6}
.zwall{fill:#1C3B28}.zwallbed{fill:#E4E7E2}.zfacade{fill:#C9CEC8}
.zwin{fill:#FFFFFF;stroke:#7F9BB0;stroke-width:1.5}.zwinl{stroke:#7F9BB0;stroke-width:1.5}
.zleaf{stroke:#3B4A41;stroke-width:2.5}.zswing{fill:none;stroke:#6E7A73;stroke-width:1.5;stroke-dasharray:6 5}
.zf{fill:rgba(255,255,255,.55);stroke:#9AA19C;stroke-width:1.4}.zrug{fill:none;stroke:#B9BFB9;stroke-width:1.2;stroke-dasharray:4 4}
.zdim line{stroke:#5E89A6;stroke-width:1.6}.zdim text{font:500 20px var(--font);fill:#4A7896;text-anchor:middle}
.zname{font:700 29px var(--font);letter-spacing:.06em;text-transform:uppercase;fill:#1F2421;text-anchor:middle;pointer-events:none}
.zsize,.zarea{font:500 23px var(--font);fill:#55605A;text-anchor:middle;pointer-events:none}
.zarea{display:none}.areas .zarea{display:inline}.nosizes .zsize{display:none}.nosizes.areas .zarea{transform:translateY(-28px)}
.nofurn .zfurn{display:none}.nodims .zdim{display:none}
.znorth circle{fill:#FFFFFF;stroke:#1F2421;stroke-width:2}.znorth path{fill:#1F2421}.znorth text{font:700 26px var(--font);fill:#1F2421;text-anchor:middle}
.zscale .zsb1{fill:#1F2421}.zscale .zsb0{fill:#FFFFFF;stroke:#1F2421;stroke-width:1.5}.zscale text{font:500 21px var(--font);fill:#55605A;text-anchor:middle}
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
</div></footer>
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
  <div class="ptitle"><div><div class="eyebrow">The architect's plans, to scale</div><h1 id="ptitle">Plan</h1>
  <p class="pmeta">Rooms <b id="parea"></b> m² · Top of the plan faces <b>%(facing)s</b></p></div>
  <div class="segs">
  <div class="seg" id="plans" role="group" aria-label="Plan">%(plans)s</div>
  <div class="seg" id="draw" role="group" aria-label="Drawing">
    <button type="button" data-k="zones" aria-pressed="true">Zones</button>
    <button type="button" data-k="furnished" aria-pressed="false">Furnished</button>
    <button type="button" data-k="empty" aria-pressed="false">Empty</button>
  </div></div></div>
  <div class="ztools" id="ztools">
    <div class="zopt" data-o="furn"><span>Furniture</span><div class="seg"><button type="button" data-v="1" aria-pressed="true">Shown</button><button type="button" data-v="0" aria-pressed="false">Hidden</button></div></div>
    <div class="zopt" data-o="sizes"><span>Room sizes</span><div class="seg"><button type="button" data-v="1" aria-pressed="true">On</button><button type="button" data-v="0" aria-pressed="false">Off</button></div></div>
    <div class="zopt" data-o="areas"><span>Areas</span><div class="seg"><button type="button" data-v="0" aria-pressed="true">Off</button><button type="button" data-v="1" aria-pressed="false">On</button></div></div>
    <div class="zopt" data-o="dims"><span>Dimensions</span><div class="seg"><button type="button" data-v="1" aria-pressed="true">On</button><button type="button" data-v="0" aria-pressed="false">Off</button></div></div>
    <div class="zopt zoomopt" data-o="zoom"><span>Zoom</span><div class="seg"><button type="button" data-v="1" aria-pressed="true">1×</button><button type="button" data-v="2" aria-pressed="false">2×</button><button type="button" data-v="3" aria-pressed="false">3×</button></div></div>
  </div>
  <div class="sheet" id="sheet"><div class="sheetin" id="sheetin">
    <svg viewBox="0 0 %(vw)d %(vh)d" role="img" aria-label="Floor plan of the apartment; each room can be selected">
      <image id="bg" href="%(furn)s" x="0" y="0" width="%(vw)d" height="%(vh)d"/>
      %(models)s
      %(overlays)s
    </svg>
  </div><div class="tip" id="tip" hidden></div></div>
  <p class="note">Zones is the plan as the 3D walkthrough is built: the walls traced from the architect's empty sheet at 1:50, to the centimetre, each room coloured by what it is. Furnished and Empty are the architect's own two sheets, turned so the room names read upright. Hover or tap a room for its size, or <a id="walk" href="3d.html">walk through this plan in 3D</a>.</p>
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
  var D=%(data)s, P='existing', V='zones', O={furn:'1',sizes:'1',areas:'0',dims:'1',zoom:'1'};
  var bg=document.getElementById('bg'), tip=document.getElementById('tip'), sheet=document.getElementById('sheet');
  function store(k,v){try{localStorage.setItem(k,v)}catch(e){}} function read(k){try{return localStorage.getItem(k)}catch(e){return null}}
  function each(sel,f){[].forEach.call(document.querySelectorAll(sel),f);}
  function hide(el,h){ if(h)el.setAttribute('hidden',''); else el.removeAttribute('hidden'); }   // SVG elements ignore .hidden
  function on(i,el){
    each('.rooms[data-p="'+P+'"] rect',function(r){r.classList.toggle('on',+r.getAttribute('data-i')===i);});
    each('.sched[data-p="'+P+'"] tbody tr',function(t){t.classList.toggle('on',+t.getAttribute('data-i')===i);});
    if(i<0||!el){tip.hidden=true;return;} var r=D[P].rooms[i], b=el.getBoundingClientRect(), s=sheet.getBoundingClientRect(); b={left:b.left+0,top:b.top+0,width:b.width,height:b.height};
    tip.innerHTML='<b>'+r.n+'</b> · '+r.d+' · '+r.a; tip.style.left=(b.left+b.width/2-s.left+sheet.scrollLeft)+'px'; tip.style.top=(b.top+b.height/2-s.top+sheet.scrollTop)+'px'; tip.hidden=false; }
  function render(){
    each('#plans button',function(b){b.setAttribute('aria-pressed',b.getAttribute('data-p')===P?'true':'false');});
    each('#draw button',function(b){b.setAttribute('aria-pressed',b.getAttribute('data-k')===V?'true':'false');});
    each('.zones',function(g){hide(g,V!=='zones'||g.getAttribute('data-p')!==P);});
    document.getElementById('ztools').hidden=false; each('.zopt:not(.zoomopt)',function(z){ z.hidden=V!=='zones'; });
    each('.zopt',function(z){ var k=z.getAttribute('data-o'); each('.zopt[data-o="'+k+'"] button',function(b){ b.setAttribute('aria-pressed',b.getAttribute('data-v')===O[k]?'true':'false'); }); });
    sheet.classList.toggle('nofurn',O.furn==='0'); sheet.classList.toggle('nosizes',O.sizes==='0'); sheet.classList.toggle('areas',O.areas==='1'); sheet.classList.toggle('nodims',O.dims==='0');
    document.getElementById('sheetin').style.width=(100*+O.zoom)+'%%'; sheet.classList.toggle('zoomed',O.zoom!=='1');
    document.getElementById('parea').textContent=D[P].area;
    each('.rooms',function(g){hide(g,g.getAttribute('data-p')!==P);});
    each('.sched',function(t){hide(t,t.getAttribute('data-p')!==P);});
    bg.style.display=V==='zones'?'none':''; if(V!=='zones')bg.setAttribute('href',D[P].img[V]);
    document.getElementById('ptitle').textContent=D[P].name;
    var u='3d.html?plan='+P; document.getElementById('walk').href=u; document.getElementById('to3d').href=u;
    on(-1); store('creektown-plan-view',V); store('creektown-plan',P); store('creektown-plan-opts',JSON.stringify(O));
    try{ history.replaceState(null,'',P==='existing'?location.pathname:'?plan='+P); }catch(e){}
  }
  each('#plans button',function(b){b.addEventListener('click',function(){P=b.getAttribute('data-p');render();});});
  each('#draw button',function(b){b.addEventListener('click',function(){V=b.getAttribute('data-k');render();});});
  each('.zopt button',function(b){b.addEventListener('click',function(){ O[b.closest('.zopt').getAttribute('data-o')]=b.getAttribute('data-v'); render(); });});
  try{ var o0=JSON.parse(read('creektown-plan-opts')||'{}'); Object.keys(O).forEach(function(k){ if(typeof o0[k]==='string')O[k]=o0[k]; }); }catch(e){}
  var q=/[?&]plan=(\w+)/.exec(location.search), p0=(q&&q[1])||read('creektown-plan'), v0=read('creektown-plan-view');
  if(p0&&D[p0])P=p0; if(v0&&/^(furnished|empty|zones)$/.test(v0))V=v0;
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



# ---------------------------------------------------------------- the zoned plan: the model drawn as an architect's
# coloured plan. Walls, windows and doors come from the 3D model itself (model.build), so it shows exactly what you walk.
ZONE_FILL = {'Kitchen': '#ECE8F3', 'Bathroom': '#DDEAF2', 'bath': '#DDEAF2', 'Terrace': '#E2EED9', 'Storage': '#F1EADB',
             "Maid's room": '#F1EADB', 'pri': '#E4EEE2', 'pub': '#F5EADD', 'cir': '#EDEBE7', 'wetz': '#DDEAF2', 'ser': '#F1EADB'}


def zone_fill(name, zone):
    if name in ZONE_FILL: return ZONE_FILL[name]
    if 'bath' in name.lower(): return ZONE_FILL['bath']
    if name == 'Master bedroom': return '#DDEBDC'
    return ZONE_FILL.get(zone, '#EEECE8')


def zones_svg(key, W, H):
    k = PX_PER_CM
    lay = model.LAYOUTS[key]
    built = model.build(key)
    rows, total, _ = schedule(key)
    zone_of = {}
    for n, r, zn in lay['rooms']:
        zone_of.setdefault(n, zn)
    f = lambda v: '%g' % round(v * k, 1)
    rect = lambda b, cls, extra='': '<rect class="%s" x="%s" y="%s" width="%s" height="%s"%s/>' % (
        cls, f(b[0]), f(b[1]), f(b[2] - b[0]), f(b[3] - b[1]), extra)
    g = ['<g class="zones" data-p="%s" hidden="">' % key, '<rect class="zbg" x="0" y="0" width="%d" height="%d"/>' % (W * k, H * k)]

    # the rooms, filled by what they are
    tr = model.TERRACE[1]
    g.append(rect(tr, 'zterr', ' fill="%s"' % ZONE_FILL['Terrace']))
    for n, r, zn in lay['rooms']:
        g.append(rect(r, 'zroom', ' fill="%s"' % zone_fill(n, zn)))

    # furniture, from above: the 3D model's pieces (legs and slivers left out), lowest first
    furn = []
    for it in built['items']:
        if not it.get('f'): continue
        if it['t'] == 'b':
            b = it['b']
            if min(b[3] - b[0], b[4] - b[1]) < 8 or b[5] - b[2] < 1.5: continue
            furn.append((b[5], rect([b[0], b[1], b[3], b[4]], 'zf')))
        elif it['t'] == 'c' and it['r'] >= 15:
            cls = 'zrug' if it['z'][1] <= 3 else 'zf'
            furn.append((it['z'][1], '<circle class="%s" cx="%s" cy="%s" r="%s"/>' % (cls, f(it['c'][0]), f(it['c'][1]), f(it['r']))))
    g.append('<g class="zfurn">' + ''.join(e for _, e in sorted(furn, key=lambda t: t[0])) + '</g>')

    # walls (full height) and the facade band, as the 3D model has them (openings already cut), cleaned into straight
    # shapes (tools/clean_walls.py) and drawn as one path each, so no seams show between the traced pieces
    walls = [[it['b'][0], it['b'][1], it['b'][3], it['b'][4]] for it in built['items']
             if it.get('g') == 'wall' and it['b'][2] == 0 and it['b'][5] >= 200]
    facade = [[it['b'][0], it['b'][1], it['b'][3], it['b'][4]] for it in built['items']
              if it.get('g') == 'wall' and it['b'][2] == 0 and it['b'][5] == model.PARAPET]
    clear = [o for _, o, *_ in lay['doors'] + lay['openings']] + [w[1] for w in model.WINDOWS] + [w[1] for w in model.SLIDERS]
    g.append('<path class="zfacade" d="%s"/>' % clean_walls.path(clean_walls.clean(facade, W, H), k))
    cw = clean_walls.clean(walls, W, H, clear)
    g.append('<path class="zwallbed" d="%s"/>' % clean_walls.path(cw, k))          # the wall's true footprint, pale
    g.append('<path class="zwall" d="%s"/>' % clean_walls.path(clean_walls.thin(cw, W, H), k))   # drawn thinner

    # windows and the terrace doors: a pale pane with a line along it
    for pc in built['pieces']:
        if pc['n'] not in ('Window', 'Terrace doors'): continue
        b = pc['b']; along_x = (b[3] - b[0]) > (b[4] - b[1])
        if along_x:
            cy = (b[1] + b[4]) / 2
            g.append(rect([b[0], cy - 6, b[3], cy + 6], 'zwin'))
            g.append('<line class="zwinl" x1="%s" y1="%s" x2="%s" y2="%s"/>' % (f(b[0]), f(cy), f(b[3]), f(cy)))
        else:
            cx = (b[0] + b[3]) / 2
            g.append(rect([cx - 6, b[1], cx + 6, b[4]], 'zwin'))
            g.append('<line class="zwinl" x1="%s" y1="%s" x2="%s" y2="%s"/>' % (f(cx), f(b[1]), f(cx), f(b[4])))

    # doors: the leaf open at 90 degrees and its swing, as on the architect's plans
    mids = {pc['n']: pc['b'] for pc in built['pieces']}
    for n, o, axis, hinge, swing, m in lay['doors']:
        if n not in mids: continue
        b = mids[n]
        a0, a1 = (o[0] + 3, o[2] - 3) if axis == 'x' else (o[1] + 3, o[3] - 3)
        mid = (b[1] + b[4]) / 2 if axis == 'x' else (b[0] + b[3]) / 2
        face = mid + swing * 6
        L = a1 - a0
        hp, far = (a0, a1) if hinge == 0 else (a1, a0)
        P = (lambda u, v: (u, v)) if axis == 'x' else (lambda u, v: (v, u))
        Hh, E, C = P(hp, face), P(hp, face + swing * L), P(far, face)
        cross = (E[0] - Hh[0]) * (C[1] - Hh[1]) - (E[1] - Hh[1]) * (C[0] - Hh[0])
        g.append('<line class="zleaf" x1="%s" y1="%s" x2="%s" y2="%s"/>' % (f(Hh[0]), f(Hh[1]), f(E[0]), f(E[1])))
        g.append('<path class="zswing" d="M%s %s A%s %s 0 0 %d %s %s"/>' % (f(E[0]), f(E[1]), f(L), f(L), 1 if cross > 0 else 0, f(C[0]), f(C[1])))

    # dimension lines inside the larger rooms: the width along the top, the depth down the left
    by_name = {r['n']: r for r in rows}
    seen = set()
    for n, r, zn in lay['rooms']:
        if n in seen: continue
        seen.add(n)
        w, d = r[2] - r[0], r[3] - r[1]
        if w < 200 or d < 200: continue
        y = r[1] + 22; x = r[0] + 22
        g.append('<g class="zdim">'
                 '<line x1="%s" y1="%s" x2="%s" y2="%s"/><line x1="%s" y1="%s" x2="%s" y2="%s"/><line x1="%s" y1="%s" x2="%s" y2="%s"/>'
                 '<text x="%s" y="%s">%.2f</text>'
                 '<line x1="%s" y1="%s" x2="%s" y2="%s"/><line x1="%s" y1="%s" x2="%s" y2="%s"/><line x1="%s" y1="%s" x2="%s" y2="%s"/>'
                 '<text x="%s" y="%s" transform="rotate(-90 %s %s)">%.2f</text></g>' % (
                     f(r[0] + 4), f(y), f(r[2] - 4), f(y), f(r[0] + 4), f(y - 7), f(r[0] + 4), f(y + 7), f(r[2] - 4), f(y - 7), f(r[2] - 4), f(y + 7),
                     f((r[0] + r[2]) / 2), f(y - 6), w / 100,
                     f(x), f(r[1] + 4), f(x), f(r[3] - 4), f(x - 7), f(r[1] + 4), f(x + 7), f(r[1] + 4), f(x - 7), f(r[3] - 4), f(x + 7), f(r[3] - 4),
                     f(x - 6), f((r[1] + r[3]) / 2), f(x - 6), f((r[1] + r[3]) / 2), d / 100))

    # the room names, sizes and areas
    measured = set()
    for lab, rn, x, y in lay['labels']:
        g.append('<text class="zname" x="%s" y="%s">%s</text>' % (f(x), f(y), html.escape(lab)))
        rm = by_name.get(rn)
        if rm and rn not in measured:
            measured.add(rn)
            g.append('<text class="zsize" x="%s" y="%s">%.2f × %.2f</text>' % (f(x), f(y + 16), rm['w'], rm['d']))
            g.append('<text class="zarea" x="%s" y="%s">%.1f m²</text>' % (f(x), f(y + 30), rm['a']))

    # north and the scale
    fac = SITE_FACING
    cx, cy = 1530, 1190
    g.append('<g class="znorth" transform="translate(%s %s)"><circle r="%s"/><path d="M0 %s L%s %s L0 %s L%s %s Z" transform="rotate(%g)"/>'
             '<text x="%s" y="%s">N</text></g>' % (f(cx), f(cy), f(28), f(-22), f(10), f(13), f(6), f(-10), f(13), (360 - fac) % 360, f(42 * math.sin(math.radians((360 - fac) % 360))), f(-42 * math.cos(math.radians((360 - fac) % 360)) + (9 if math.cos(math.radians((360 - fac) % 360)) < 0 else 0))))
    x0, y0 = 60, 1222
    ticks = [(0, '0'), (100, '1'), (200, '2'), (500, '5 m')]
    sb = ['<g class="zscale">', '<rect x="%s" y="%s" width="%s" height="%s" class="zsb1"/>' % (f(x0), f(y0), f(100), f(7)),
          '<rect x="%s" y="%s" width="%s" height="%s" class="zsb0"/>' % (f(x0 + 100), f(y0), f(100), f(7)),
          '<rect x="%s" y="%s" width="%s" height="%s" class="zsb1"/>' % (f(x0 + 200), f(y0), f(300), f(7))]
    sb += ['<text x="%s" y="%s">%s</text>' % (f(x0 + t), f(y0 - 8), lbl) for t, lbl in ticks]
    g.append(''.join(sb) + '</g>')
    g.append('</g>')
    return ''.join(g)


def compass_name(b):
    return '%d° %s' % (b, ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'][round(b / 22.5) % 16])


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
        g = [zones_svg(key, W, H)]
        models.append(''.join(g))
        trs = ''.join('<tr data-i="%d"><td>%s</td><td class="hide-s">%s</td><td class="n">%.2f × %.2f%s</td><td class="n">%.1f</td></tr>' % (
            i, html.escape(r['n']), r['zone'], r['w'], r['d'], ' +' if r['extra'] else '', r['a']) for i, r in enumerate(rows))
        tables.append(SCHED % dict(key=key, hidden=hidden, trs=trs, total=total, total2=total + outdoor))
        data[key] = dict(rooms=[dict(n=r['n'], d='%.2f × %.2f m' % (r['w'], r['d']), a='%.1f m²' % r['a']) for r in rows],
                         img=imgs[key], name=lay['name'], area='%.0f' % total)

    plans = ''.join('<button type="button" data-p="%s" aria-pressed="%s">%s <small>%s</small></button>' % (
        key, 'true' if key == 'existing' else 'false', *model.LAYOUTS[key]['button']) for key in model.ORDER)
    body = PLAN_BODY % dict(facing=compass_name(SITE_FACING), name=NAME, vw=W * k, vh=H * k, furn=imgs['existing']['furnished'], models='\n      '.join(models),
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
  <div class="hero-bg" aria-hidden="true"></div><div class="hero-light" aria-hidden="true"></div>
  <div class="bar"><div class="wrap"><span>5th floor · about %(tot)d m² · over a big garden</span><nav aria-label="Site"><a href="plan.html">Plan</a><a href="3d.html">3D</a></nav></div></div>
  <div class="copy wrap">
    <div class="eyebrow">Creek Town · New Cairo · interior architecture</div>
    <h1 class="wm" aria-label="Creektown Apartment, New Cairo"><span class="w1">Creektown <b>Apartment</b></span><span class="w2">New Cairo</span></h1>
    <p>Monica's &amp; Amira's new apartment: three bedrooms, a maid's room and an open reception, living and dining onto a terrace, and the architect's two options for reworking it. Measured from the drawings and built as a 3D model you can walk through with the real sun.</p>
    <div class="cta"><a class="btn solid" href="plan.html">See the plans</a><a class="btn ghost" href="3d.html">Walk through them</a></div>
  </div>
</header>
<div class="factsband"><div class="wrap"><div class="facts" aria-label="Key facts">
  <div><span>Size</span><b>About %(tot).0f m² net + %(ter).1f m² terrace</b><small>5th floor, looking over a big garden; floor area between walls, from the drawings at 1:50</small></div>
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
    <li><b>Which way it faces</b><span>Unit E07-53 is the brochure's 165 m² three-bedroom unit, on the pool side of building E07. On the brochure's maps, drawn with the Suez Road at the top, that side faces south, so the 3D sun takes the reception and master bedroom windows as facing south; a compass reading on site would pin it within the last 15°.</span></li>
    <li><b>Mirror image?</b><span>The compound model marks the unit at the left end of the building's pool side; the brochure's layout puts the drawn unit at the right end. If the terrace is on your left as you look out over the pool, the real flat is the mirror image of the drawings.</span></li>
    <li><b>Ceiling height</b><span>Taken as 2.80 m to the slab. Any beams and dropped ceilings still need measuring.</span></li>
    <li><b>The view and the building round it</b><span>The 3D model puts the apartment on the 5th floor, 15.5 m above the pool garden (3.10 m a storey), with the penthouse level above. Standing, the Neighbours switch shows the compound round E07 from the brochure's masterplan: the other buildings, the pools, roads, trees and the shops along the road, to scale and casting shade. They are simple shapes, not a photograph; Pool view and Terrace show the outlook.</span></li>
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
                       desc='Monica\'s and Amira\'s Creektown apartment in New Cairo: the plans to scale, as built and two layout options, and a 3D walkthrough with the real sun.') + body
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
    hero_image()
    imgs, W, H = render_plans()
    totals = plan_page(imgs, W, H)
    index_page(totals)
    print('index.html, plan.html and %d images; net inside: %s' % (
        sum(len(v) for v in imgs.values()) + 1, ', '.join('%s %.1f m²' % (k, v) for k, v in totals.items())))


if __name__ == '__main__':
    main()
