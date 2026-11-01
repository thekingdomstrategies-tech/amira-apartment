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
    for k, _, v in model.VIEWS:
        parts = ['pos:%s' % json.dumps(v['pos']).replace(' ', ''), 'look:%s' % json.dumps(v['look']).replace(' ', '')]
        if 'mode' in v: parts.append("mode:'%s'" % v['mode'])
        if 'z' in v: parts.append('z:%s' % v['z'])
        parts.append('msg:%s' % json.dumps(v['msg']))
        out.append('  %s:{%s}' % (k, ','.join(parts)))
    # the walkthrough's spots are AZAD-only (hidden here) but the code still looks some of them up
    return 'var VIEWS={\n' + ',\n'.join(out) + '\n};'


def bprint_svg(L, outline):
    walls = [it['b'] for it in L['items'] if it.get('g') == 'wall' and it['b'][2] == 0 and it['b'][5] >= 90]
    rects = ''.join('<rect x="%g" y="%g" width="%g" height="%g" style="--i:%d"/>' % (b[0], b[1], b[3] - b[0], b[4] - b[1], i)
                    for i, b in enumerate(sorted(walls, key=lambda b: (b[1], b[0]))))
    s = L['site']
    d = 'M' + ' L'.join('%g %g' % (x, y) for x, y in outline) + ' Z'
    return ('<svg class="bprint" id="bprint" viewBox="%g %g %g %g" aria-hidden="true"><path class="bgarden" d="%s" style="opacity:.25"/>'
            '<g data-l="existing">%s</g></svg>' % (s[0] + 100, s[1] + 100, s[2] - s[0] - 200, s[3] - s[1] - 200, d, rects))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--azad', default=os.path.join(os.path.dirname(ROOT), 'kamelshenouda', 'azad'))
    a = ap.parse_args()
    src = open(os.path.join(a.azad, '3d.html'), encoding='utf-8').read()

    m = re.search(r'\nvar ALL=(\{.*?\});\n', src, re.S)
    azad_all = json.loads(m.group(1))
    ALL, outline = model.all_data(azad_all)
    L = ALL['layouts']['existing']
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

    # ---------------- the page: names, the plans offered, the viewpoints, the mini-plan
    s = sub1(r'<title>[^<]*</title>', '<title>%s 3D</title>' % NAME, s)
    s = sub1(r'<meta name="description" content="[^"]*">',
             '<meta name="description" content="Walk-through 3D model of the Creektown apartment, as built with the architect\'s furniture, in true measurements from the plans.">', s)
    s = rep('aria-label="AZAD Apartment: home">← <span class="hn">AZAD Apartment</span>',
            'aria-label="%s: home">← <span class="hn">%s</span>' % (NAME, NAME), s)
    s = sub1(r'<a href="renders.html">Renders</a>\s*<a href="package.html">Package</a>', '', s)
    s = rep('<div class="eyebrow">AZAD Apartment · 3D</div>', '<div class="eyebrow">%s · 3D</div>' % NAME, s)
    s = sub1(r'<div class="plans" id="layout" role="group" aria-label="Plan">.*?</div>',
             '<div class="plans" id="layout" role="group" aria-label="Plan"><button type="button" data-v="existing" aria-pressed="true" '
             'title="The apartment as drawn by the architect, with the furniture layout">As built<small>with furniture</small></button></div>', s, re.S)
    btns = []
    for k, label, _ in model.VIEWS:
        if k == 'overview':
            btns.append('<button type="button" class="wide" data-view="overview" aria-pressed="true"><span>Overview</span><kbd class="sk" data-k="0"></kbd></button>')
        else:
            btns.append('<button type="button" data-view="%s">%s</button>' % (k, html.escape(label)))
    s = sub1(r'<div class="rooms" id="views">.*?</div>', '<div class="rooms" id="views">\n        ' + '\n        '.join(btns) + '\n      </div>', s, re.S)
    s = sub1(r'<svg class="bprint" id="bprint".*?</svg>', bprint_svg(L, outline), s, re.S)
    s = sub1(r'<img class="lprev" alt="" src="data:image/[^"]*">', '', s)
    s = s.replace('AZAD Apartment', NAME)
    # one plan only: AZAD's side-by-side comparison page is not part of this site (the code still looks the link up)
    s = rep('<div class="app">', '<style>#cmplink{display:none!important}</style>\n<div class="app">', s)

    out = os.path.join(ROOT, '3d.html')
    open(out, 'w', encoding='utf-8').write(s)
    print('%s: %d items, %d KB' % (os.path.relpath(out, ROOT), len(L['items']), len(s) // 1024))


if __name__ == '__main__':
    main()
