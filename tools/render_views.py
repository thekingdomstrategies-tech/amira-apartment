"""The photoreal renders: which views, from where, by day and by night. Read by tools/render_cycles.py (which renders
them in Blender) and tools/build_pages.py (which lays them out on renders.html)."""

DAY_LABEL = '15 November, 1:30 pm'
NIGHT_LABEL = 'Evening, lights on'

# key, title, caption, camera (cm), target (cm), lens (mm), times ('day', 'night'), plan
RENDERS = [
    ('living', 'The living room', 'Across the living room to the new 2.80 sofa, the coffee table on its rug, and the window over the pool garden.',
     [1445, 330, 135], [1000, 270, 88], 17, ('day', 'night')),
    ('tv', 'The TV wall', 'From the 2.80 sofa: the TV wall unit round the column, the two poufs, and the 2.00 sofa at right angles.',
     [1040, 330, 112], [1560, 380, 118], 20, ('day',)),
    ('arrival', 'From the front door', 'Just inside the front door: the dining table for eight under the rattan pendants, the living room and the terrace doors beyond.',
     [1345, 1040, 150], [1290, 560, 105], 17, ('day', 'night')),
    ('dining', 'Dining', 'The 2.00 table for eight on its rug, the 2.20 sideboard on the bathroom wall, and the living room beyond.',
     [1345, 875, 145], [1050, 650, 85], 17, ('day', 'night')),
    ('piano', 'The piano corner', 'The grey 1.40 sofa with its throw, the nest of round tables, and the black upright piano.',
     [1255, 640, 140], [1500, 790, 80], 20, ('day',)),
    ('kitchen', 'The kitchen', 'Her own units, re-used: grey painted doors, arched and glazed wall cupboards, the granite worktop, the new fridge and built-in oven.',
     [803, 575, 150], [803, 140, 100], 16, ('day', 'night')),
    ('corridor', 'The corridor', 'Down the corridor to the new door at its end: the kitchen open on the left, the bathroom\'s sliding door on the right.',
     [445, 556, 150], [1030, 553, 110], 18, ('day',)),
    ('bathroom', 'The bathroom', 'From beside the WC: the walk-in shower at the far end behind its glass, with a rain head and a hand shower, and on the left the one counter with the basin, the washing machine and the cupboard.',
     [950, 700, 150], [600, 698, 105], 16, ('day',)),
    ('master', 'The master bedroom', 'Her mahogany bed, headboard on the wall to bedroom 2, with the new 80 cm bedside tables.',
     [415, 370, 150], [190, 650, 70], 16, ('day', 'night')),
    ('wardrobe', 'The dressing area', 'Her mahogany wall unit as the wardrobe: 70 and 60 along the window, the corner, then five units down the kitchen wall.',
     [462, 468, 150], [600, 150, 145], 16, ('day',)),
    ('dressing', 'The dressing table', 'The wall unit\'s dressing table, 1.28, with the hanging TV on its left and the framed mirror on its right.',
     [332, 590, 140], [326, 318, 112], 20, ('day',)),
    ('bedroom2', 'Bedroom 2', 'The 1.20 bed with the pull-out bed under it, the 2.20 wardrobe, and the hanging desk under the window.',
     [400, 760, 150], [150, 1000, 80], 17, ('day',)),
    ('terrace', 'From the terrace', 'Out over the pool garden from the terrace, five floors up.',
     [1455, 125, 150], [1300, -2600, -900], 18, ('day',)),
]

# exposure, in stops, on top of the day's or the night's: the dark mahogany dressing area gets more, bright rooms less
EXPOSURE = {'corridor-day': .45, 'wardrobe-day': .8, 'dressing-day': .35, 'master-day': .25, 'kitchen-day': .2, 'living-day': -.2,
            'tv-day': -.2, 'terrace-day': -1.2, 'piano-day': -.1}

