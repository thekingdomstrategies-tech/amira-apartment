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

# Creek Town, on the Suez Road opposite Rehab, New Cairo (approximate). Unit E07-53 looks over its building's pool
# garden from the plan's top edge; the brochure's maps are drawn with the Suez Road at the top and Rehab at the
# bottom, i.e. north up, and on them that side faces down the page: south, within about 15 degrees.
SITE = dict(lat=30.0740, lon=31.4870, facing=180)

# Phones: one job, looking round the flat. The model gets the screen; the sheet below holds only the plan switch and a
# row of rooms to swipe through, with every other control a pull-up away. Nothing sits over the model but the room
# you are in, Whole apartment and 1:1.
PHONE_CSS = (
    '@media (max-width:760px){'
    '.lbl,.status,#zhome,#zmeas,#zin,#zout,.hud>svg,.hud>span:not(#hudroom){display:none!important}'
    '.joy{left:12px!important;bottom:12px!important;width:112px!important;height:112px!important}'
    '.hud{left:10px!important;right:auto!important;top:10px!important;padding:6px 10px!important;font-size:12.5px!important;max-width:calc(100% - 130px)}'
    '.hud #hudroom{border-right:0!important;padding-right:0!important}.hud:has(#hudroom:empty){display:none!important}'
    '.minimap{width:96px!important;height:88px!important;top:10px!important}'
    '.zoomui{gap:8px!important}.zoomui button{width:44px!important;height:44px!important}'
    '.panel>.sitenav{padding-top:0!important}.panel>.sitenav a{min-height:34px!important}'
    '.panel .plans{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:4px!important;margin:2px 16px 0!important}'
    '.panel .plans button{min-height:40px;padding:6px 4px!important;border-radius:10px!important}.panel .plans button small{display:none!important}'
    '#tab-go{padding-top:10px!important;grid-auto-rows:max-content}#tab-go #views{min-height:48px!important}'
    '#tab-go #views{flex:none!important;display:flex!important;flex-wrap:nowrap!important;overflow-x:auto;gap:8px!important;padding:0 16px 2px!important;margin:0 -16px!important;'
    'scroll-snap-type:x proximity;-webkit-overflow-scrolling:touch;scrollbar-width:none;grid-template-columns:none!important}'
    '#tab-go #views::-webkit-scrollbar{display:none}'
    '#tab-go #views button{flex:none!important;width:auto!important;min-height:42px;padding:0 16px!important;border-radius:999px!important;white-space:nowrap;scroll-snap-align:start;grid-column:auto!important}'
    '#tab-go #views button[hidden]{display:none!important}#tab-go #views kbd{display:none}'
    '#tab-go .hint{display:none}'
    '.sheetgrip{height:34px!important}.sheetgrip i{width:52px!important;height:6px!important}'
    '.panel>.sitenav{touch-action:none}.panel{overscroll-behavior:contain}'
    '}'
)

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
    + PHONE_CSS
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


PHONE_OVERVIEW = ([1520, 600, 2750], [800, 590, 0])


def views_js():
    out = []
    for k, _, v, _ in model.VIEWS:
        parts = ['pos:%s' % json.dumps(v['pos']).replace(' ', ''), 'look:%s' % json.dumps(v['look']).replace(' ', '')]
        if 'mode' in v: parts.append("mode:'%s'" % v['mode'])
        if 'z' in v: parts.append('z:%s' % v['z'])
        parts.append('msg:%s' % json.dumps(v['msg']))
        out.append('  %s:{%s}' % (k, ','.join(parts)))
    # the walkthrough's spots are AZAD-only (hidden here) but the code still looks some of them up
    return ('var VIEWS={\n' + ',\n'.join(out) + '\n};\n'
            "if(window.matchMedia('(max-width:760px)').matches&&innerHeight>innerWidth){ VIEWS.overview.pos=%s; VIEWS.overview.look=%s; }"
            "   // a phone held upright: from nearly overhead, the flat's length up the screen" % (json.dumps(PHONE_OVERVIEW[0]), json.dumps(PHONE_OVERVIEW[1])))


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
    # ---------------- how the page opens: from above (Overview), no furniture (the doors stay), no sun path, no garden
    # shade (there is no garden at this level). Furniture starts at None in the state itself: switching to None hides
    # the doors as well, which is AZAD's choice for its bare rooms but not wanted here.
    s = rep("if(!userSet.fu)setKey('fu',k==='existing'?'none':'all',false);", "", s)
    s = rep("setKey('fu',LAYOUT==='existing'?'none':'all',false);", "", s)
    s = rep("var state={chg:'on',sp:'on',", "var state={chg:'on',sp:'off',", s)
    s = rep(",sh:'open',gs:'pergola',aw:'out',fu:'all',", ",sh:'open',gs:'none',aw:'out',fu:'none',", s)
    s = rep("var userSet={}, prevD='open', prevGs='pergola';", "var userSet={}, prevD='none', prevGs='none';", s)
    s = rep("isl:'design',k:'open',p:'open',d:'open',", "isl:'design',k:'open',p:'open',d:'none',", s)   # no door leaves until you ask for them
    s = rep("press('wm',state.wm); press('look',state.look);", "press('wm',state.wm); press('look',state.look); press('sp',state.sp); press('fu',state.fu); press('d',state.d);", s)
    s = rep("goto(VIEWS[h0]?h0:ALL.preview?'overview':'entrance');", "goto(VIEWS[h0]?h0:'overview');", s)
    s = rep("'Bare rooms: no furniture, doors or garden shade. Pick All or Built-in to furnish.'", "'No furniture. Pick All or Built-in to furnish the rooms.'", s)
    # the Garden shade control goes; its summary in the Light tab too
    s = sub1(r'<div class="ctl"><div class="cl"><span>Garden shade</span></div><div class="bt" data-state="gs">.*?</div></div>\s*', '', s, re.S)
    s = rep("var gsl={pergola:'pergola',awning:'shades '+state.aw,none:'no garden shade'}[state.gs];", "", s)
    s = rep("textContent, gsl, 'shutters '+state.sh]", "textContent, 'shutters '+state.sh]", s)

    # ---------------- the apartment on the 5th floor, over the garden. Standing, the ground and a lawn are 15.5 m below
    # the floor and the Neighbours switch shows the building round it; from above it stays a model on its plinth.
    E = model.ELEV / 100
    s = rep("// the five floors above: they cast shade but are not drawn, so the rooms stay visible",
            "// the floor above (the penthouse level): it casts shade but is not drawn, so the rooms stay visible", s)
    s = rep("var g=new T.ExtrudeGeometry(sh,{depth:16,bevelEnabled:false}); g.rotateX(Math.PI/2);   // from 19 m down to the slab at 3 m",
            "var g=new T.ExtrudeGeometry(sh,{depth:%g,bevelEnabled:false}); g.rotateX(Math.PI/2);   // one storey, from the slab up" % (model.STOREY / 100), s)
    s = rep("m.position.y=19; m.castShadow=true;", "m.position.y=%g; m.castShadow=true;" % (2 * model.STOREY / 100), s)
    lawn = ("var LAWN=(function(){var o=%s; var sh=new T.Shape(); o.forEach(function(q,i){if(i===0)sh.moveTo(q[0]*S,q[1]*S);else sh.lineTo(q[0]*S,q[1]*S);});"
            "var g=new T.ShapeGeometry(sh); g.rotateX(Math.PI/2); g.translate(0,-%g+.01,0); worldUV(g,TEXM.grass);"
            "var m=new T.Mesh(g,M.grass); m.receiveShadow=true; m.visible=false; m.userData={mk:'grass',site:1,fixed:1}; scene.add(m); return m;})();   // the big garden, %g m below\n"
            % (json.dumps(model.GARDEN).replace(' ', ''), E, E))
    s = rep("staticFloors.push(grass);\n", "staticFloors.push(grass);\n" + lawn, s)
    s = rep("cshadow.visible=ov; land.material=ov?studioMat:landMat; land.position.y=ov?-.006-PLINTH-.001:-.02;",
            "cshadow.visible=ov; land.material=ov?studioMat:landMat; land.position.y=ov?-.006-PLINTH-.001:-%g-.02; pave.visible=ov; LAWN.visible=!ov; if(SURR)SURR.visible=!ov&&state.up==='on';" % E, s)
    # the compound at ground level round E07, from the masterplan: pools, roads and trees (the buildings are ALL.context)
    surr = ("var SURR=(function(){var d=ALL.surround; if(!d)return null; var grp=new T.Group(), G=d.ground*S;"
            "function slab(list,z0,z1,mat){ if(!list.length)return; var gs=list.map(function(b){var g=new T.BoxGeometry((b[2]-b[0])*S,(z1-z0)*S,(b[3]-b[1])*S);"
            "g.translate((b[0]+b[2])/2*S,G+(z0+z1)/2*S,(b[1]+b[3])/2*S); return g;});"
            "var m=new T.Mesh(mergeGeometries(gs,false),mat); m.receiveShadow=true; m.userData={fixed:1}; grp.add(m); }"
            "slab(d.roads,1.5,3,std({color:0x4A4D4F,roughness:.95}));"
            "slab(d.water,2,5,std({color:0x3C9DCB,roughness:.06,metalness:.05}));"
            "var trunks=[], crowns=[];"
            "d.trees.forEach(function(t){ var x=t[0]*S, z=t[1]*S, k=t[3], palm=t[2]==='palm';"
            "var th=(palm?7.5:2.6)*k, tr=new T.CylinderGeometry(palm?.13:.17,palm?.2:.24,th,7); tr.translate(x,G+th/2,z); trunks.push(tr);"
            "if(palm){ var fl=2.6*k, rot=(t[0]*7+t[1]*3)%60*Math.PI/180; for(var f=0;f<8;f++){ var fr=new T.BoxGeometry(fl,.04,.55*k); fr.translate(fl/2,0,0);"
            "fr.rotateZ(-.42-.12*(f%2)); fr.rotateY(rot+f*Math.PI/4); fr.translate(x,G+th,z); crowns.push(fr); }"
            "var hd=new T.SphereGeometry(.45*k,8,6); hd.translate(x,G+th,z); crowns.push(hd); }"
            "else { var r=2.6*k, c=new T.SphereGeometry(r,14,10); c.scale(1,.82,1); c.translate(x,G+th+r*.62,z); crowns.push(c);"
            "var c2=new T.SphereGeometry(r*.7,12,8); c2.translate(x+r*.45,G+th+r*.95,z-r*.2); crowns.push(c2); } });"
            "if(trunks.length){ var tm=new T.Mesh(mergeGeometries(trunks,false),M.trunk), cm=new T.Mesh(mergeGeometries(crowns,false),M.leaf);"
            "tm.castShadow=cm.castShadow=true; tm.receiveShadow=cm.receiveShadow=true; tm.userData=cm.userData={fixed:1}; grp.add(tm); grp.add(cm); }"
            "grp.visible=false; scene.add(grp); return grp;})();   // the compound below the windows\n")
    s = rep("var LAWN=(function(){", surr + "var LAWN=(function(){", s)

    # ---------------- phones (see PHONE_CSS)
    s = rep("function peekH(){ var t=panelEl.querySelector('.tabs'); return t?Math.round(t.offsetTop+t.offsetHeight+16):190; }",
            "function peekH(){ var go=document.getElementById('tab-go'), t=(mq.matches&&go&&!go.hidden&&document.getElementById('views'))||panelEl.querySelector('.tabs'); if(!t)return 190;"
            " return Math.round(t.getBoundingClientRect().bottom-panelEl.getBoundingClientRect().top+(mq.matches?12:16)); }", s)
    # a drag settles one step in the direction it went (or further if it went that far), not back where it started
    s = rep("    var h=panelEl.offsetHeight, best='peek'; ['peek','half','full'].forEach(function(k){ if(Math.abs(hOf(k)-h)<Math.abs(hOf(best)-h))best=k; }); snap(best); });",
            "    settle(); });", s)
    s = rep("  g.addEventListener('pointerdown',function(e){ drag={y:e.clientY,h:panelEl.offsetHeight,moved:false};",
            "  var ORD=mq.matches?['min','peek','half']:['peek','half','full'];\n"
            "  function settle(){ var h=panelEl.offsetHeight, i=ORD.indexOf(cur), best=cur;\n"
            "    if(i<0)i=0; if(h>hOf(cur)+24){ best=ORD[Math.min(2,i+1)]; ORD.forEach(function(k,j){ if(j>ORD.indexOf(best)&&hOf(k)<=h+40)best=k; }); }\n"
            "    else if(h<hOf(cur)-24){ best=ORD[Math.max(0,i-1)]; ORD.forEach(function(k,j){ if(j<ORD.indexOf(best)&&hOf(k)>=h-40)best=k; }); }\n"
            "    snap(best); }\n"
            "  g.addEventListener('pointerdown',function(e){ drag={y:e.clientY,h:panelEl.offsetHeight,moved:false};", s)
    # the sheet's header row (the Plan / 3D links) drags it too, once the finger has moved; a tap still follows the link
    s = rep("  init(); if(mq.addEventListener)mq.addEventListener('change',init);\n",
            "  init(); if(mq.addEventListener)mq.addEventListener('change',init);\n"
            "  var nav=panelEl.querySelector('.sitenav'), nd=null, swallow=false;\n"
            "  if(nav){ nav.addEventListener('pointerdown',function(e){ if(mq.matches)nd={y:e.clientY,h:panelEl.offsetHeight,on:false,id:e.pointerId}; });\n"
            "    nav.addEventListener('pointermove',function(e){ if(!nd)return; var dy=nd.y-e.clientY; if(!nd.on&&Math.abs(dy)>8){ nd.on=true; try{nav.setPointerCapture(nd.id);}catch(x){} } if(nd.on){ setH(nd.h+dy); e.preventDefault(); } });\n"
            "    nav.addEventListener('pointerup',function(){ if(!nd)return; var d=nd; nd=null; if(d.on){ swallow=true; setTimeout(function(){swallow=false;},400); settle(); } });\n"
            "    nav.addEventListener('pointercancel',function(){ nd=null; });\n"
            "    nav.addEventListener('click',function(e){ if(swallow){ swallow=false; e.preventDefault(); e.stopPropagation(); } },true); }\n"
            # the peek is measured again once the Go tab is on screen (it is chosen after the sheet is set up)
            "  var goTab=document.getElementById('tab-go'); function refit(){ if(mq.matches&&cur==='peek')snap('peek'); }\n"
            "  if(goTab&&window.MutationObserver)new MutationObserver(refit).observe(goTab,{attributes:true,attributeFilter:['hidden']});\n"
            "  if(document.fonts&&document.fonts.ready)document.fonts.ready.then(refit); setTimeout(refit,300);\n"
            # full screen on a phone: the sheet goes down to its handle (and the browser goes full screen where it can)
            "  window.sheetMini=function(){ var z=document.getElementById('zall');\n"
            "    if(cur!=='min'){ snap('min'); z.setAttribute('aria-pressed','true');\n"
            "      var de=document.documentElement; if(de.requestFullscreen&&!document.fullscreenElement)de.requestFullscreen().catch(function(){}); }\n"
            "    else { snap('peek'); z.setAttribute('aria-pressed','false'); if(document.fullscreenElement&&document.exitFullscreen)document.exitFullscreen().catch(function(){}); } };\n"
            "  function zallLabel(){ var z=document.getElementById('zall'); if(!z)return; z.setAttribute('aria-label',mq.matches?'Full screen':'Show the whole apartment'); z.title=mq.matches?'Full screen: hide the controls':'Whole apartment'; }\n"
            "  zallLabel(); if(mq.addEventListener)mq.addEventListener('change',zallLabel);\n"
            "  function closeSoon(){ if(mq.matches&&cur==='half')setTimeout(function(){ if(cur==='half')snap('peek'); },350); }\n"
            "  panelEl.addEventListener('click',function(e){ if(e.target.closest('.tabp .bt button, .tabp .plans button, #views button'))closeSoon(); });\n"
            "  panelEl.addEventListener('change',function(e){ if(e.target.tagName==='SELECT')closeSoon(); });\n"
            "  document.getElementById('layout').addEventListener('click',closeSoon);\n"
            "  stage.addEventListener('pointerdown',function(){ if(mq.matches&&cur==='half')snap('peek'); });\n", s)
    s = rep("document.getElementById('zall').addEventListener('click',function(){goto('overview');});",
            "document.getElementById('zall').addEventListener('click',function(){ if(window.matchMedia('(max-width:760px)').matches&&window.sheetMini){ window.sheetMini(); return; } goto('overview'); });", s)
    # opening another tab from the peek opens the sheet; back on Go, the peek fits the rooms again
    s = rep("[].forEach.call(document.querySelectorAll('.tabs button'),function(b){ b.addEventListener('click',function(){ window.sheetOpen(); }); });",
            "[].forEach.call(document.querySelectorAll('.tabs button'),function(b){ b.addEventListener('click',function(){ if(b.getAttribute('data-tab')!=='go')window.sheetOpen(); else if(cur==='peek')setTimeout(function(){snap('peek');},0); }); });", s)
    s = rep("var k='peek'; try{ k=localStorage.getItem('azad-3d-sheet')||'peek'; }catch(e){} snap(k);", "snap('peek');", s)
    # on a phone the sheet has three heights: just its handle (full screen), the bar (plans, tabs, rooms) and open,
    # at most 45 % of the screen. Tapping the handle opens and closes it; it closes by itself after a choice, or when
    # you touch the model.
    s = rep("function hOf(k){ var H=appEl.clientHeight; return k==='full'?Math.round(H*.86):k==='half'?Math.round(H*.5):peekH(); }",
            "function hOf(k){ var H=appEl.clientHeight; if(k==='min')return g.offsetHeight; if(mq.matches)return k==='peek'?peekH():Math.max(peekH(),Math.round(H*.45)-14);"
            " return k==='full'?Math.round(H*.86):k==='half'?Math.round(H*.5):peekH(); }", s)
    s = rep("function setH(px){ appEl.style.setProperty('--sh',Math.round(Math.max(peekH(),Math.min(appEl.clientHeight*.9,px)))+'px'); resize(); dirty=true; }",
            "function setH(px){ var lo=mq.matches?g.offsetHeight:peekH(), hi=mq.matches?Math.max(peekH(),appEl.clientHeight*.45-14):appEl.clientHeight*.9;"
            " appEl.style.setProperty('--sh',Math.round(Math.max(lo,Math.min(hi,px)))+'px'); resize(); dirty=true; }", s)
    s = rep("if(!d.moved){ snap(cur==='peek'?'half':cur==='half'?'full':'peek'); return; }",
            "if(!d.moved){ snap(mq.matches?(cur==='half'?'peek':'half'):(cur==='peek'?'half':cur==='half'?'full':'peek')); return; }", s)
    s = rep("if(e.key==='Enter'||e.key===' '){ snap(cur==='peek'?'half':cur==='half'?'full':'peek'); e.preventDefault(); }",
            "if(e.key==='Enter'||e.key===' '){ snap(mq.matches?(cur==='half'?'peek':'half'):(cur==='peek'?'half':cur==='half'?'full':'peek')); e.preventDefault(); }", s)
    # a tap on the handle moves the sheet under the finger: the click that follows must not land on what is now there
    s = rep("  g.addEventListener('pointerup',function(){ if(!drag)return; var d=drag; drag=null;",
            "  var gripT=0; document.addEventListener('click',function(e){ if(performance.now()-gripT<500&&!g.contains(e.target)){ e.preventDefault(); e.stopPropagation(); } },true);\n"
            "  g.addEventListener('pointerup',function(){ if(!drag)return; var d=drag; drag=null; gripT=performance.now();", s)
    s = rep("window.sheetOpen=function(){ if(mq.matches&&cur==='peek')snap('half'); };",
            "window.sheetOpen=function(){ if(mq.matches&&cur!=='half')snap('half'); };", s)
    # a tall screen held upright: wide views widen sideways, but the up-down angle stops at 90 degrees (no fisheye)
    s = rep("function eyeFov(){ return 2*Math.atan(trueHalfTan()/EYEZ/Math.max(camera.aspect,0.2))*180/Math.PI; }",
            "function eyeFov(){ return Math.min(90,2*Math.atan(trueHalfTan()/EYEZ/Math.max(camera.aspect,0.2))*180/Math.PI); }", s)
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
            "(LAYOUT==='existing'?'As built, with the architect\\'s furniture.':LAYOUT==='o1'?'Option 1, two bedrooms, with the architect\\'s furniture.':LAYOUT==='o2'?'Option 2, three bedrooms, with the architect\\'s furniture.':LAYOUT==='o3'?'Option 3, Amira\\'s layout: her furniture and measures.'", s)
    # Option 3 offers two hobs; AZAD's island switch (state.isl, design / trial) chooses between them
    s = rep('<div class="ctl" data-only="p1"><div class="cl"><span>Kitchen island</span></div><div class="bt" data-state="isl">'
            '<button type="button" data-v="design" aria-pressed="true" title="Your design: the island with the oak L bar, and the oak table for 8 in the reception">Design</button>'
            '<button type="button" data-v="trial" aria-pressed="false" title="From your photo of 13 Oct: a square stone island, with a stone table for 8 carrying on from its end">Trial: stone table</button>',
            '<div class="ctl" data-only="o3"><div class="cl"><span>Hob</span></div><div class="bt" data-state="isl">'
            '<button type="button" data-v="design" aria-pressed="true" title="A 95 cm hob, five burners">95 cm</button>'
            '<button type="button" data-v="trial" aria-pressed="false" title="A 60 cm hob, four burners, with worktop either side">60 cm</button>', s)

    # ---------------- the page: names, the plans offered, the viewpoints, the mini-plan
    s = sub1(r'<title>[^<]*</title>', '<title>%s 3D</title>' % NAME, s)
    s = sub1(r'<meta name="description" content="[^"]*">',
             '<meta name="description" content="Walk-through 3D model of the Creektown apartment: as built and the architect\'s two layout options and Amira\'s, furnished, in true measurements from the plans.">', s)
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
