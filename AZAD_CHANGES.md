# Changes made on the Creektown site, for porting back to AZAD

This repository (`thekingdomstrategies-tech/amira-apartment`) started from the AZAD site and its 3D viewer
(`kamelshenouda/azad` at commit `890e70b`). Its `3d.html` is **AZAD's `3d.html` patched by `tools/build_3d.py`**:
every `rep(old, new, s)` and `sub1(pattern, new, s)` call in that file is a literal old → new edit against AZAD's
exported `3d.html`. To port a change, find the `old` string in AZAD's page (or in the AZAD source that produces it)
and apply the `new` one. Strings are quoted below by the function or element they touch.

Sections, most useful first:

1. [Bugs in AZAD's viewer, fixed here](#1-bugs-in-azads-viewer-fixed-here): apply as they are.
2. [The phone layout of the 3D page](#2-the-phone-layout-of-the-3d-page): a full redesign; recommended.
3. [3D defaults and controls](#3-3d-defaults-and-controls): choices; take the ones AZAD wants.
4. [3D model features](#4-3d-model-features): new geometry and surroundings.
5. [The zoned plan](#5-the-zoned-plan-plan-page): a new coloured plan drawing with its own toolbar.
6. [Overview page and design](#6-overview-page-and-design).
7. [Pipeline tools](#7-pipeline-tools-building-a-model-from-the-architects-pdfs): only if AZAD gets new PDF drawings.
8. [Not for AZAD](#8-not-for-azad): Creektown-only changes, listed so they are not ported by mistake.

---

## 1. Bugs in AZAD's viewer, fixed here

These are wrong in AZAD today, whatever its design choices.

| # | Bug | Where | Fix |
|---|-----|-------|-----|
| 1.1 | **On a phone, tapping the sheet's handle also presses whatever button slides under the finger.** The sheet opens, moves up under the finger, and the click that follows the tap lands on a plan, room or tab button. In practice the sheet opens and closes again at once, or switches plan. | the phone sheet IIFE (`// phone: pull the controls up or down; tap the handle to step`), `g.addEventListener('pointerup', …)` | After a grip tap, swallow clicks for 500 ms: `var gripT=0; document.addEventListener('click',function(e){ if(performance.now()-gripT<500&&!g.contains(e.target)){ e.preventDefault(); e.stopPropagation(); } },true);` and set `gripT=performance.now();` at the top of the grip's `pointerup`. |
| 1.2 | **A short drag of the sheet snaps straight back.** `pointerup` snaps to the *nearest* height, so a 40–80 px drag returns to where it started; it feels as if the sheet won't move. | same IIFE, the `pointerup` line `var h=panelEl.offsetHeight, best='peek'; ['peek','half','full'].forEach(…nearest…); snap(best);` | Settle by direction: more than 24 px up goes one step up (further if dragged past the next height), more than 24 px down goes one step down. See `settle()` in `tools/build_3d.py`. |
| 1.3 | **Wide room views stretch into a fisheye on a phone held upright.** `eyeFov()` widens the vertical angle without limit as the aspect ratio narrows. | `function eyeFov(){ return 2*Math.atan(trueHalfTan()/EYEZ/Math.max(camera.aspect,0.2))*180/Math.PI; }` | Cap it: `return Math.min(90, 2*Math.atan(…)*180/Math.PI);` |
| 1.4 | **The ⤢ button does nothing in the overview** (it is "Show the whole apartment", and you are already looking at it). On a phone, people read ⤢ as full screen. | `document.getElementById('zall').addEventListener('click',function(){goto('overview');});` | On phones make it full screen: see 2.7. |
| 1.5 | **The sheet height on a phone is measured before the selected tab is shown,** so a peek that should include the tab's first row comes out short. | `peekH()` and `init()` in the sheet IIFE | Measure with `getBoundingClientRect()` and re-fit once the tab appears: a `MutationObserver` on the tab's `hidden` attribute, plus `document.fonts.ready` and a `setTimeout(…,300)`. See `refit()`. |
| 1.6 | **On a phone the sheet reopens at whatever height was stored last** (`localStorage 'azad-3d-sheet'`), often half the screen, hiding the model. | `function init(){ … var k='peek'; try{ k=localStorage.getItem('azad-3d-sheet')||'peek'; }catch(e){} snap(k); }` | Always open at the small bar: `snap('peek');`. |
| 1.7 | **Furniture None also hides the doors** (`setKey('fu','none')` presses `d:none` and `gs:none`), so "no furniture" and "no doors" cannot be chosen separately at load. | `setKey()`, the `if(key==='fu'&&val!==was){…}` coupling | If AZAD keeps the coupling for its bare-rooms button, set the initial state directly in `var state={…}` instead of through `setKey` (see 3.1). |

---

## 2. The phone layout of the 3D page

The goal: on a phone the page does one job, looking round the flat. All of it lives in a `@media (max-width:760px)`
block (`PHONE_CSS` in `tools/build_3d.py`) plus the sheet logic in the "phones" section of the same file.

**2.1 Nothing over the model but the essentials.** Hide on phones: `.lbl` (room labels), `.status` (caption line),
`#zhome`, `#zmeas`, `#zin`, `#zout`, `.hud>svg` (compass), `.hud>span:not(#hudroom)` (zoom, bearing, distance). Keep
`#hudroom` (the room you are in, compact at top left; hide the HUD when it is empty with `.hud:has(#hudroom:empty)`), the
minimap (smaller: 96 × 88 px), `#z11` (1:1), `#zall` (now full screen) and the thumb pad.

**2.2 The thumb pad stays, bigger.** `.joy` at 112 × 112 px, left 12 px, bottom 12 px. It still only shows when
standing on a touch screen (`joyShow()`).

**2.3 Rooms as one swipeable row under the Go tab.** `#tab-go #views` becomes a flex row: no wrap, horizontal scroll,
`scroll-snap-type:x proximity`, hidden scrollbar, pill buttons (min-height 42 px, `border-radius:999px`,
`white-space:nowrap`). Hide `#tab-go .hint`. **Important:** inside the tab's grid that row is squeezed to about 2 px
unless you also set `#tab-go{grid-auto-rows:max-content}` and `#tab-go #views{min-height:48px}`.

**2.4 Plan buttons in one row of three:** `.panel .plans{display:grid;grid-template-columns:repeat(3,minmax(0,1fr))}`.
Hide their `<small>` subtitles on phones.

**2.5 A sheet with three heights** (replaces peek / half / full on phones):

- `min`: just the handle (full screen);
- `peek`: the bar, which is the site links, the plan buttons, the tabs and, when Go is open, the room row
  (`peekH()` measures the bottom of `#views` when `#tab-go` is visible, otherwise the bottom of `.tabs`);
- `half`: open, capped at **45 % of the screen**. The sheet has `margin-top:-14px`, so the cap is `H*.45-14`.

`hOf()` and `setH()` take the phone limits (`lo` = handle height, `hi` = 45 %). Tapping the handle toggles
peek ↔ half; swipes settle by direction (1.2); `ORD=['min','peek','half']` on phones.

**2.6 The sheet opens and closes by itself:**

- a tab other than Go opens it (`sheetOpen()` → half); tapping Go at the peek re-fits the peek to the room row;
- after a choice, back to the peek in 350 ms (`closeSoon()`): a click on `.tabp .bt button`, `.tabp .plans button`
  or `#views button`, a `change` on a `select`, or a click in `#layout` (the plan switch);
- touching the model closes it: `stage.addEventListener('pointerdown', …snap('peek')…)`.

**2.7 Full screen on phones.** `window.sheetMini()` toggles `min` ↔ `peek`, calls
`document.documentElement.requestFullscreen()` where the browser allows it (Android; iPhone Safari does not allow it
for pages), and sets `aria-pressed`. `#zall` calls it on phones (`matchMedia('(max-width:760px)')`) and still goes to
the overview on a computer; its `aria-label` and `title` change with the media query.

**2.8 A bigger handle, and the header row drags too.** `.sheetgrip{height:34px}` with a 52 × 6 px bar. The
`.sitenav` row (Plan / 3D links) also drags the sheet: start after 8 px of vertical movement, `setPointerCapture`,
and swallow the click that follows a drag (capture-phase listener) so the links still work on a plain tap.
`.panel>.sitenav{touch-action:none}` and `.panel{overscroll-behavior:contain}`.

**2.9 A portrait overview on phones.** After `var VIEWS={…}`:
`if(matchMedia('(max-width:760px)').matches&&innerHeight>innerWidth){ VIEWS.overview.pos=[…]; VIEWS.overview.look=[…]; }`.
That is a camera from nearly overhead, with the flat's long side up the screen, so the whole plan fills a tall screen.
AZAD needs its own numbers; Creektown's are `pos=[1520,600,2750]`, `look=[800,590,0]` in plan centimetres.

---

## 3. 3D defaults and controls

Take the ones AZAD wants; all are one-line changes.

| # | Change | How |
|---|--------|-----|
| 3.1 | Open on the **Overview** | `goto(VIEWS[h0]?h0:ALL.preview?'overview':'entrance');` → `goto(VIEWS[h0]?h0:'overview');` |
| 3.2 | **Furniture None** at load, without hiding the doors | `var state={… fu:'all' …}` → `fu:'none'`; remove the two `setKey('fu',LAYOUT==='existing'?'none':'all',false)` calls (one in `setLayout()`, one at start-up); add `press('fu',state.fu)` next to `press('wm',state.wm); press('look',state.look);` |
| 3.3 | **Doors None** at load, and furnishing does not bring them back | `d:'open'` → `d:'none'`; `prevD='open'` → `prevD='none'`; `press('d',state.d)` |
| 3.4 | **Sun path hidden** at load | `sp:'on'` → `sp:'off'`; `press('sp',state.sp)` |
| 3.5 | **Garden shade removed** | delete the `<div class="ctl">…Garden shade…data-state="gs"…</div>`; `gs:'none'`, `prevGs='none'`; drop `gsl` and its use in the Light tab summary |
| 3.6 | **Every room view opens at one zoom** (34 % here, very wide) | `z:` on every view in `VIEWS` (`ZOOM` in `tools/model.py`) |
| 3.7 | **Share links always point to the page you are on** | `var ON_SITE=/github\.io$|^azad\.|…/.test(location.hostname);` → `var ON_SITE=true;`, and `var SITE_BASE=ON_SITE?location.origin+location.pathname:'https://claude.ai/artifact/…';` → `var SITE_BASE=location.origin+location.pathname;`. Only needed if AZAD is served from another host; on its claude.ai artifact the old fallback is what it wants. |
| 3.8 | **The rooms light up from the real front door** | `startLxRamp()`: `door=P(1455,1420,0)` is AZAD's door; keep it in step if AZAD's plan changes |

---

## 4. 3D model features

**4.1 Multiple plans with their own views.** Each view in `VIEWS` can belong to some plans only: the view buttons get
`data-only="existing o1"`, and `syncLayoutUI()` already hides them per plan. When AZAD's four plans are replaced or
renamed, also update `/v1~(existing|p1|c|d)~/`, `/[?&]plan=(…)/`, `LAYOUT_ORDER`, its `%4`
(→ `%LAYOUT_ORDER.length`), the `['existing','p1','c','d'].forEach` in the db sync, and the `#bprint g[data-l="p1"]`
fallback in the loading plan.

**4.2 Shutters on every window and garden door.** AZAD has `sh-half` / `sh-closed` boxes on some openings only. Here
they are generated for every window and slider, on the face with no room behind it: a 2 cm board from the sill (or
halfway) to the head + 4 cm, 3 cm wider than the opening each side (`shutter()` in `tools/model.py`).

**4.3 The flat on an upper floor.** For an apartment that is not on the ground (Creektown is on the 5th floor):

- `UPPER` (AZAD's "five floors above") becomes one storey, from the slab up: `depth:16` → the storey height,
  `m.position.y=19` → 2 storeys;
- a lawn at ground level, `ELEV` below the floor (`var LAWN=…`), and the paving hidden standing:
  `stageFor(ov)` sets `land.position.y=ov?…:-ELEV-.02; pave.visible=ov; LAWN.visible=!ov;`;
- `ALL.context` holds the massing round it (the floors below, the rest of the block, the neighbouring buildings, each
  with a penthouse level), shown and casting shade with the Neighbours switch.

**4.4 The neighbourhood below the windows** (`var SURR=…`): roads and pools as thin slabs, and procedural trees, either
palms (a trunk with 8 tilted fronds) or round trees (two overlapping crowns). It is one merged mesh per material,
visible only standing with Neighbours on (`SURR.visible=!ov&&state.up==='on'` in `stageFor`). The data is
`ALL.surround = {ground, water:[rects], roads:[rects], trees:[[x,y,'palm'|'round',scale]]}`, read from a masterplan
image by `tools/surroundings.py` (see 7.3).

**4.5 A ceiling over a covered terrace,** so it does not look open to the sky when the floor above covers it.

---

## 5. The zoned plan (plan page)

A new default drawing on the plan page, like an architect's coloured plan, drawn from the same model as the 3D page.
It is `zones_svg()` in `tools/build_pages.py` and `tools/clean_walls.py`. For AZAD, port the idea onto its own plan
page and model data (`ALL.layouts[k].items`, `rooms`, `pieces`).

- **Rooms coloured by type:** living warm `#F5EADD`, bedrooms green `#E4EEE2` (master `#DDEBDC`), kitchen lavender
  `#ECE8F3`, bathrooms blue `#DDEAF2`, circulation grey `#EDEBE7`, service sand `#F1EADB`, garden or terrace green
  `#E2EED9` with a dashed edge.
- **Walls from the 3D model,** so openings are already cut: items with `g:'wall'`, `z0=0`, `z1≥200` are walls, and
  `z1=PARAPET` is the facade band. They are cleaned, then drawn thinner:
  - `clean()` closes gaps up to 9 cm, drops slivers under 4 cm and chips under 400 cm², and snaps wall faces to the
    most common face within 7 cm (a thin wall keeps its two faces). It keeps every door and window footprint clear.
  - `thin()` draws the dark core 40 % thinner (at most 5 cm a side, never under 4 cm), across the thickness only, over
    the true footprint in pale `#E4E7E2`.
  - Each layer is **one SVG `<path>`**, so no anti-aliasing seams show between pieces.
- **Windows:** a white pane with a blue-grey line along it, from the pieces named `Window` and `Terrace doors`.
- **Door swings:** the leaf at 90° plus a dashed quarter arc, from the door's hinge end and swing side. The SVG
  `sweep` flag comes from the cross product of hinge → leaf end and hinge → closed end.
- **Furniture from above:** the model's `f:'loose'`/`'built'` boxes and cylinders, drawn lowest first, with legs and
  slivers under 8 cm left out and rugs dashed.
- **Labels:** the room name (bold, uppercase), size `w × d`, and area in m² (off by default).
- **Dimension lines** inside rooms of at least 2 × 2 m: the width along the top, the depth down the left, with tick ends.
- **North arrow,** rotated by the site's facing (`rotate((360-facing)%360)`), with the N placed at the arrow's tip.
  **Scale bar** marked 0, 1, 2 and 5 m.
- **Under the title:** "Rooms 119 m² · Top of the plan faces 180° S", using a 16-point compass name.
- **Toolbar:** Furniture Shown/Hidden, Room sizes On/Off, Areas Off/On, Dimensions On/Off, Zoom 1×/2×/3×. Each option
  is a class on `#sheet` (`nofurn`, `nosizes`, `areas`, `nodims`). Zoom sets the inner wrapper's width to 100/200/300 %
  inside `overflow:auto`. The choices are stored in `localStorage`.
- **Fixes on the same page:**
  - SVG elements ignore `.hidden`: toggle the `hidden` attribute with `setAttribute` / `removeAttribute`.
  - The hover tooltip must add `sheet.scrollLeft` / `scrollTop` once the sheet scrolls.

---

## 6. Overview page and design

These are Creektown's choices; port the techniques, not the brand.

- **Animated hero:** a photo (here the compound's building render) under a brand-colour gradient. It is deep colour on
  the text side, and the photo is masked in from 22 % so no hard edge shows. The photo drifts and slowly zooms
  (`hero-drift`, 46 s, alternate), a soft-light radial glow moves over it (`hero-light`, 26 s), and the title lines fade
  up on load. All of it stops under `prefers-reduced-motion`. On phones the gradient runs top to bottom so the text
  stays readable.
- **Brand restyle of the 3D viewer** without touching its stylesheet: AZAD's CSS runs on tokens (`--paper`, `--sheet`,
  `--ink`, `--muted`, `--line`, `--accent`, `--display`, `--mono`, `--glass`), so one later `<style>` block overrides
  them for light and dark. Replace the hard-coded accent `#2E5A74` (badges, focus rings) and `0x2E5A74` (3D walk-to
  dots and tape-measure markers) too.
- **Contrast:** white text on a mid green needed a slightly deeper panel colour to reach 4.5:1. Check AZAD's olive
  `#7B7258` and gold `#B79565` text the same way.
- **Three-plans comparison** on the overview: one card per plan (bedrooms, bathrooms, net m², bullet changes, Plan and
  3D links) and a room-by-room area table across the plans.

---

## 7. Pipeline tools (building a model from the architect's PDFs)

These are only useful if AZAD gets new vector drawings.

- **7.1 `tools/extract_walls.py`:** walls from a vector PDF plan.
  - `pdftocairo -svg`, then sort the paths by pen (wall outline, column, hatch, facade fill).
  - Cut the plan into a grid at every outline x and y; a cell is a wall if it holds hatching.
  - Close hairline gaps, then merge cells greedily into rectangles.
  - Several sheets of the same flat are aligned on a feature none of them changes (here the facade band).
  - 1:50 on A3 gives 1 pt = 1.764 cm.
- **7.2 `tools/build_pages.py` `render_plans()`:** each sheet rendered, turned, shifted onto the same frame and cropped
  at 2 px/cm, so drawings, clickable rooms and 3D share coordinates.
- **7.3 `tools/surroundings.py`:** a masterplan image turned into model data.
  - Buildings are white roofs, pools blue, roads wide grey (kept only for large connected parts), and trees a jittered
    grid on the lawn clear of the rest.
  - The scale comes from a known building's roof against its floor plate.
- **7.4 `tools/model.py`:** several plans in one `LAYOUTS` table: doors, openings, extra partitions, L-shaped rooms
  (a name repeated), labels, furniture functions and views per plan.

---

## 8. Not for AZAD

These are Creektown-only, listed so they are not ported by mistake:

- the brand (Poppins, forest and leaf greens, the Creektown wordmark), and the AZAD-credit footer removal;
- `CNAME` `amira.kamelnabil.com`, `.nojekyll`, and the Vercel DNS record;
- the site latitude, longitude and facing, the 5th-floor height, and E07's surroundings;
- the three Creektown plans, their furniture, rooms and views, and the hero photo;
- "Monica's & Amira's" copy and the to-confirm notes.
