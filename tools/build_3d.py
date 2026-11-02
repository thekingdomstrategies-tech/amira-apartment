#!/usr/bin/env python3
"""Build 3d.html: the AZAD walkthrough (github.com/kamelshenouda/azad) re-pointed at the Creektown apartment.

The AZAD viewer is one page: the controls, a three.js renderer and the apartment as data (`var ALL={...}`). This script
takes that page as a template, swaps in the model from tools/model.py, and rewrites the parts that describe AZAD:
names, the plans it offers, the viewpoints, the site's latitude and orientation, the mini-plan, and the outline of the
floors above that shade the rooms.

Usage: python3 tools/build_3d.py [--azad PATH_TO_AZAD_CHECKOUT]   ->  3d.html
"""
import argparse, html, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = 'Creektown Apartment'

# Creek Town, New Cairo. The latitude/longitude are the compound's; the bearing the plan's top edge faces is NOT known
# yet (the drawings carry no north arrow), so 180 (top edge facing due south) is a placeholder: set it once confirmed.
SITE = dict(lat=30.0280, lon=31.4590, facing=180)

# The Creek Town palette, measured from the vector fills of the compound's brochure; text panels use a slightly deeper
# leaf so white text keeps a 4.5:1 contrast.
BRAND = dict(forest='#1C3B28', leaf='#5A8C5B', panel='#4C7D4D', lime='#8DBA6A')
BRAND_CSS = (
    ':root{--paper:#F4F5F3;--sheet:#FFFFFF;--ink:#1F2421;--ink2:#404040;--muted:#5F6461;--line:#DADBDC;'
    '--accent:#1C3B28;--accent-ink:#FFFFFF;--oak:#A87A4B;'
    '--display:"Poppins","Helvetica Neue",Arial,sans-serif;--mono:"Poppins","Helvetica Neue",Arial,sans-serif;'
    '--glass:rgba(255,255,255,.66);--btn-line:rgba(28,59,40,.14)}'
    '@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--paper:#0E1711;--sheet:#15231A;--ink:#E3E8E3;'
    '--ink2:#BAC3BB;--muted:#94A095;--line:#26382C;--accent:#9CCB80;--accent-ink:#0E1711;--glass:rgba(14,23,17,.62)}}'
    ':root[data-theme="dark"]{--paper:#0E1711;--sheet:#15231A;--ink:#E3E8E3;--ink2:#BAC3BB;--muted:#94A095;'
    '--line:#26382C;--accent:#9CCB80;--accent-ink:#0E1711;--glass:rgba(14,23,17,.62)}'
    '.phead .ptitle{font-weight:700;text-transform:uppercase;letter-spacing:-.005em}'
    '.phead .eyebrow{color:#3E6E40;letter-spacing:.16em}'
    '@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) .phead .eyebrow{color:#9CCB80}}'
    ':root[data-theme="dark"] .phead .eyebrow{color:#9CCB80}'
)


def sub1(pattern, repl, s, flags=0):
    """re.sub that must hit exactly once, so a template change is noticed instead of silently skipped."""
    out, n = re.subn(pattern, lambda m: repl, s, count=1, flags=flags)
    if n != 1:
        raise SystemExit('template changed: no match for %r' % pattern[:80])
    return out


def rep(old, new, s, count=1):
    if s.count(old) < 1:
        raise SystemExit('template changed: %r not found' % old[:80])
    return s.replace(old, new) if count == 0 else s.replace(old, new, count)


def views_js():
    out = []
    for k, _, v, _ in model.VIEWS:
        parts = ['pos:%s' % json.dumps(v['pos']).replace(' ', ''), 'look:%s' % json.dumps(v['look']).replace(' ', '')]
        if 'mode' in v: parts.append("mode:'%s'" % v['mode'])
        if 'z' in v: parts.append('z:%s' % v['z'])
        parts.append('msg:%s' % json.dumps(v['msg']))
        out.append('  %s:{%s}' % (k, ','.join(parts)))
    # the walkthrough's spots are AZAD-only (hidden here) but the code still looks some of them up
    return 'var VIEWS={\n' + ',\n'.join(out) + '\n};'


def bprint_svg(ALL, outline):
    """The plan drawn while the model loads: one group of walls per plan, the chosen one shown."""
    groups = []
    for key in model.ORDER:
        L = ALL['layouts'][key]
        walls = [it['b'] for it in L['items'] if it.get('g') == 'wall' and it['b'][2] == 0 and it['b'][5] >= 90]
        rects = ''.join('<rect x="%g" y="%g" width="%g" height="%g" style="--i:%d"/>' % (b[0], b[1], b[3] - b[0], b[4] - b[1], i)
                        for i, b in enumerate(sorted(walls, key=lambda b: (b[1], b[0]))))
        groups.append('<g data-l="%s">%s</g>' % (key, rects))
    s = ALL['layouts']['existing']['site']
    d = 'M' + ' L'.join('%g %g' % (x, y) for x, y in outline) + ' Z'
    return ('<svg class="bprint" id="bprint" viewBox="%g %g %g %g" aria-hidden="true"><path class="bgarden" d="%s" style="opacity:.25"/>'
            '%s</svg>' % (s[0] + 100, s[1] + 100, s[2] - s[0] - 200, s[3] - s[1] - 200, d, ''.join(groups)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--azad', default=os.path.join(os.path.dirname(ROOT), 'kamelshenouda', 'azad'))
    a = ap.parse_args()
    src = open(os.path.join(a.azad, '3d.html'), encoding='utf-8').read()

    m = re.search(r'\nvar ALL=(\{.*?\});\n', src, re.S)
    azad_all = json.loads(m.group(1))
    ALL, outline = model.all_data(azad_all)
    s = src[:m.start()] + '\nvar ALL=' + json.dumps(ALL, separators=(',', ':'), ensure_ascii=False) + ';\n' + src[m.end():]

    # ---------------- the code: site, viewpoints, front door, floors above, north arrow
    s = sub1(r'var SITE=\{lat:[^}]*\};', 'var SITE={lat:%(lat)s,lon:%(lon)s,facing:%(facing)s};' % SITE, s)
    s = sub1(r'var VIEWS=\{\n.*?\n\};', views_js(), s, re.S)
    door = [1311, 1078]
    s = rep('door=P(1455,1420,0)', 'door=P(%d,%d,0)' % tuple(door), s)
    s = sub1(r'var UPPER=\(function\(\)\{var o=\[\[.*?\]\];', 'var UPPER=(function(){var o=%s;' % json.dumps(outline).replace(' ', ''), s)
    s = rep('var p=P(950,1720,1)', 'var p=P(1700,1240,1)', s)
    # AZAD's as-built plan opens with bare rooms; this one opens furnished, as the architect drew it
    s = rep("if(!userSet.fu)setKey('fu',k==='existing'?'none':'all',false);", "if(!userSet.fu)setKey('fu','all',false);", s)
    s = rep("setKey('fu',LAYOUT==='existing'?'none':'all',false);", "setKey('fu','all',false);", s)
    s = rep("p.n!=='Window'&&p.n!=='Garden doors'", "p.n!=='Window'&&p.n!=='Terrace doors'", s, 0)
    s = rep("It reaches the garden glass.':'The garden glass is in shade.'", "It reaches the main windows.':'The main windows are in shade.'", s)
    s = rep("['top','garden side'],['bottom','entrance side']", "['top','window side'],['bottom','entrance side']", s)
    s = rep("'AZAD furniture · '", "'Creektown furniture · '", s)
    s = rep("'AZAD finishes on trial · '", "'Creektown finishes on trial · '", s)
    s = rep("'Pick a spot inside the apartment or the garden.'", "'Pick a spot inside the apartment.'", s)
    # the overview's first view, and the default when nothing is stored
    s = s.replace("localStorage.getItem('azad-3d-plan')", "localStorage.getItem('creektown-3d-plan')")
    s = s.replace("localStorage.setItem('azad-3d-plan',k)", "localStorage.setItem('creektown-3d-plan',k)")
    s = s.replace("||'p1'; }catch(e){}", "||'existing'; }catch(e){}")
    s = s.replace("'azad-3d-tab'", "'creektown-3d-tab'")
    # AZAD's four plans (existing, p1, c, d) become this site's three
    keys = '|'.join(model.ORDER)
    s = rep("""document.querySelector('#bprint g[data-l="p1"]')""", """document.querySelector('#bprint g[data-l="existing"]')""", s)
    s = rep("/v1~(existing|p1|c|d)~/", "/v1~(%s)~/" % keys, s)
    s = rep("/[?&]plan=(existing|p1|c|d)/", "/[?&]plan=(%s)/" % keys, s)
    s = rep("var LAYOUT_ORDER=['existing','p1','c','d']", "var LAYOUT_ORDER=%s" % json.dumps(model.ORDER).replace('"', "'").replace(' ', ''), s)
    s = rep("LAYOUT_ORDER[(LAYOUT_ORDER.indexOf(LAYOUT)+1)%4]", "LAYOUT_ORDER[(LAYOUT_ORDER.indexOf(LAYOUT)+1)%LAYOUT_ORDER.length]", s)
    s = rep("['existing','p1','c','d'].forEach(function(L){ db.doc('furnish/'+L)", "LAYOUT_ORDER.forEach(function(L){ db.doc('furnish/'+L)", s)
    s = rep("(LAYOUT==='existing'?'The original walls, furnished with a typical layout for comparison.'",
            "(LAYOUT==='existing'?'As built, with the architect\\'s furniture.':LAYOUT==='o1'?'Option 1, two bedrooms, with the architect\\'s furniture.':LAYOUT==='o2'?'Option 2, three bedrooms, with the architect\\'s furniture.'", s)

    # ---------------- the page: names, the plans offered, the viewpoints, the mini-plan
    s = sub1(r'<title>[^<]*</title>', '<title>%s 3D</title>' % NAME, s)
    s = sub1(r'<meta name="description" content="[^"]*">',
             '<meta name="description" content="Walk-through 3D model of the Creektown apartment: as built and the architect\'s two layout options, furnished, in true measurements from the plans.">', s)
    s = rep('aria-label="AZAD Apartment: home">← <span class="hn">AZAD Apartment</span>',
            'aria-label="%s: home">← <span class="hn">%s</span>' % (NAME, NAME), s)
    s = sub1(r'<a href="renders.html">Renders</a>\s*<a href="package.html">Package</a>', '', s)
    s = rep('<div class="eyebrow">AZAD Apartment · 3D</div>', '<div class="eyebrow">%s · 3D</div>' % NAME, s)
    plans = ''.join('<button type="button" data-v="%s" aria-pressed="%s" title="%s">%s<small>%s</small></button>' % (
        k, 'true' if k == 'existing' else 'false', html.escape(model.LAYOUTS[k]['title']), *model.LAYOUTS[k]['button']) for k in model.ORDER)
    s = sub1(r'<div class="plans" id="layout" role="group" aria-label="Plan">.*?</div>',
             '<div class="plans" id="layout" role="group" aria-label="Plan">%s</div>' % plans, s, re.S)
    btns = []
    for k, label, _, only in model.VIEWS:
        if k == 'overview':
            btns.append('<button type="button" class="wide" data-view="overview" aria-pressed="true"><span>Overview</span><kbd class="sk" data-k="0"></kbd></button>')
        else:
            btns.append('<button type="button" data-view="%s"%s>%s</button>' % (k, ' data-only="%s"' % ' '.join(only) if only else '', html.escape(label)))
    s = sub1(r'<div class="rooms" id="views">.*?</div>', '<div class="rooms" id="views">\n        ' + '\n        '.join(btns) + '\n      </div>', s, re.S)
    s = sub1(r'<svg class="bprint" id="bprint".*?</svg>', bprint_svg(ALL, outline), s, re.S)
    s = sub1(r'<img class="lprev" alt="" src="data:image/[^"]*">', '', s)
    s = s.replace('AZAD Apartment', NAME)
    # share links: AZAD points them at its own claude.ai artifact unless it runs on GitHub Pages or azad.*; this site
    # has no artifact, so a link always points back to wherever the page is served (amira.kamelnabil.com, github.io)
    s = sub1(r"var ON_SITE=/[^;]*;[^\n]*", "var ON_SITE=true;   // always the public site: this one has no claude.ai artifact", s)
    s = sub1(r"var SITE_BASE=ON_SITE\?location\.origin\+location\.pathname:'[^']*';", "var SITE_BASE=location.origin+location.pathname;", s)
    # AZAD's side-by-side comparison page is not part of this site (the code still looks the link up)
    s = rep('<div class="app">', '<style>#cmplink{display:none!important}</style>\n<div class="app">', s)

    # ---------------- the Creek Town brand (the compound brochure) over AZAD's theme: Poppins, forest and leaf green.
    # AZAD's stylesheet runs on a few colour and font tokens; a later block of the same specificity overrides them.
    s = sub1(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com/css2\?family=Montserrat[^"]*">',
             '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap">', s)
    s = rep('#2E5A74', BRAND['forest'], s, 0)        # AZAD's blue, also written out in a few badges and focus rings
    s = rep('0x2E5A74', '0x' + BRAND['leaf'][1:], s, 0)   # and in the 3D markers (walk-to dots, tape measure)
    s = rep('<div class="app">', '<style>%s</style>\n<div class="app">' % BRAND_CSS, s)

    out = os.path.join(ROOT, '3d.html')
    open(out, 'w', encoding='utf-8').write(s)
    print('%s: %s, %d KB' % (os.path.relpath(out, ROOT), ', '.join('%s %d items' % (k, len(ALL['layouts'][k]['items'])) for k in model.ORDER), len(s) // 1024))


if __name__ == '__main__':
    main()
