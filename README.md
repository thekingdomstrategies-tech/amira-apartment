# Creektown Apartment

Amira's new apartment in Creek Town, New Cairo: the architect's plans to scale (as built, and two layout options), and
a 3D walkthrough of each with the real sun. The site reuses the
[AZAD apartment site](https://github.com/kamelshenouda/azad) and its 3D viewer, pointed at this apartment.

- `index.html`: overview, key facts, the three plans compared room by room, what is still to confirm
- `plan.html`: for each plan, a colour-zoned drawing of the model (rooms coloured by what they are, walls, windows,
  door swings, furniture, room sizes, areas, dimensions, north and a scale, with a zoom), the architect's two sheets
  (furnished and empty), every room clickable, and a room schedule; `plan.html?plan=o1` opens option 1
- `3d.html`: the AZAD walkthrough with this apartment's walls, windows, doors, furniture, lighting and viewpoints, with
  a plan button each for as built, option 1 and option 2; `3d.html?plan=o2` opens option 2

| Plan | Key | Sheets | In short |
| --- | --- | --- | --- |
| As built | `existing` | `original_*.pdf` | 3 bedrooms, 3 bathrooms, closed kitchen, maid's room |
| Option 1 | `o1` | `option_1_*.pdf` | 2 bedrooms: a master suite with a dressing area, a galley kitchen in the old master bedroom, one shared bathroom, storage |
| Option 2 | `o2` | `option_2_*.pdf` | 3 bedrooms, one shared bathroom, a kitchen with an island that takes in the maid's room |

The site is published with GitHub Pages from `main` at **https://amira.kamelnabil.com/** (the `CNAME` file), and is
plain HTML with relative links, so any static server works too (for example `python3 -m http.server`). The domain
needs one DNS record at kamelnabil.com's DNS provider: a `CNAME` for `amira` pointing to
`thekingdomstrategies-tech.github.io`. `.nojekyll` tells Pages to serve the files as they are.

## Design

The pages follow the Creek Town brand, taken from the compound's brochure (`source/creek_town_brochure.pdf`):
Poppins throughout, heavy uppercase headings, a widely spaced light wordmark, large faded section numerals, square
edges, and the brochure's colours, measured from its vector fills:

| Role | Colour |
| --- | --- |
| Forest green: the cover, footer, selected buttons | `#1C3B28` |
| Leaf green: rules, numerals, plan highlights | `#5A8C5B` |
| Leaf panel: green panels carrying white text (a touch deeper than the brochure's leaf, for 4.5:1 contrast) | `#4C7D4D` |
| Lime: accents on the forest green | `#8DBA6A` |
| Text and fine print | `#404040`, `#6B6E6F` |

The overview and plan pages take it from the stylesheet in `tools/build_pages.py`. The 3D page keeps AZAD's viewer and
overrides its colour and font tokens (`BRAND_CSS` in `tools/build_3d.py`). Both have a dark theme. The compound's logo
and crest are not used; the wordmark is set in type.

The overview's header is the compound's apartment-building render (brochure page 53, `img/hero-building*.jpg`, made
by `tools/build_pages.py`) under a forest-green gradient, drifting slowly under a moving soft light; it holds still for
visitors who ask their system for reduced motion.

On a phone the 3D page is cut down to its main job, looking round the flat: the model fills the screen, from nearly
overhead on the overview. The controls sit in a sheet with three heights: a bar with the plan switch, the tabs and the
Go tab's row of rooms; open, at most 45 % of the screen (tap the handle, or a tab); and just its handle (swipe down, or
the full-screen button). The sheet closes back to the bar after a choice, or when you touch the model. Over the model
only the room you are in, the small plan, 1:1, full screen and, standing, the thumb pad to walk with
(`PHONE_CSS` and the phone section of `tools/build_3d.py`).

The 3D page opens from above (Overview) with no furniture, no doors and no sun path; the Furniture, Sun path, Shutters and
Neighbours switches turn them on. Every room view opens at 34 % zoom; 1:1 is true size.

## Where the numbers come from

`source/` holds the architect's files: `Creektown_apartment.dwg` and, for each plan, an empty and a furnished sheet
(`original_*`, `option_1_*`, `option_2_*`). The PDFs are 1:50 plots on A3 with every line still a vector, so the walls
are traced from each empty sheet (1 pt on the sheet = 1.764 cm). The DWG is kept but not read: the PDFs carry the same
linework.

The sheets are turned 90° anticlockwise so the room names read upright: x to the right, y down, in centimetres. Each
sheet sits at a slightly different place on its page, so it is first moved onto the original's frame by the concrete
facade band, which no option changes; all three plans then share one set of coordinates.

| Step | Script | Output |
| --- | --- | --- |
| Trace the walls from each empty sheet | `tools/extract_walls.py` | `data/walls_<sheet>.json` |
| The compound round building E07, from the brochure's masterplan | `tools/surroundings.py` | `data/surroundings.json` |
| Each plan's doors, rooms, furniture, lights, viewpoints | `tools/model.py` | (imported by the two below) |
| The 3D page from AZAD's viewer | `tools/build_3d.py --azad PATH` | `3d.html` |
| Plan images, plan page and overview | `tools/build_pages.py` | `plan.html`, `index.html`, `img/plan-<sheet>-*.jpg` |

`build_3d.py` needs a checkout of `kamelshenouda/azad` (by default next to this repository, at
`../kamelshenouda/azad`); it takes AZAD's `3d.html` as the template and replaces its model data, plans, viewpoints, site
and names. `lib/` is AZAD's vendored three.js r169 and three-mesh-bvh 0.8.3 (MIT). The scripts need Python 3 with numpy
and Pillow, and poppler's `pdftocairo` and `pdftoppm`. `img/3d-thumb.jpg` is a screenshot of the 3D overview.

## Still to confirm

These are stand-ins in the model until they are checked on site or with the architect:

- **The unit and its outlook.** Unit E07-53 is the brochure's 165 m² three-bedroom unit (page 93), on the 5th floor
  of building E07, on its pool side, the building at the head of the middle apartment cluster's pool. Its floor is
  taken as 15.5 m above the garden (3.10 m a storey), with the penthouse level above. On the brochure's maps (the Suez
  Road at the top, Rehab at the bottom) the pool side faces south (`SITE.facing`, within about 15°). The compound
  model marks the unit at the left end of the pool side, which with the brochure's layout would make it the mirror
  image of the drawings: to check on site.
- **The surroundings.** `tools/surroundings.py` reads the brochure's masterplan (page 7) into
  `data/surroundings.json`: the other apartment buildings (as E07-sized blocks with a penthouse level), the shops
  along the road, the pools, roads and trees, scaled from E07's roof and turned so E07's pool side matches the plan.
  The 3D page shows them standing, with the Neighbours switch, and lets the buildings cast shade.
- **Heights.** 2.80 m floor to slab; main windows 0.90 to 2.25 m, bathroom windows 1.50 to 2.10 m, kitchen windows 1.05
  to 2.10 m; doors 2.10 m (front door 2.20 m). All in `tools/model.py`.
- **The concrete band outside the facade** is drawn as a 95 cm planter or parapet.
- **Furniture** follows each furnished sheet as simple blocks; kitchens are simplified. Where an option draws a dining
  table alone, chairs are added.
- **Option 1, dressing area and kitchen.** The empty sheet draws no wall between them and no door to the master
  bathroom. The model adds a partition where the furnished sheet draws a line, and leaves the bathroom doorway open.
- **Doors and partitions the sheets leave out.** Option 1's bathroom door has no swing drawn, so it is hinged on the
  vanity side. Option 2's bathroom wall to the corridor is drawn without hatching, so it is added by hand
  (`extra_walls` in `tools/model.py`).
