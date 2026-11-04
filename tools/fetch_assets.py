"""Download the free (CC0) Poly Haven textures, sky and models the high-quality renders use, into .assets/.

    python3 tools/fetch_assets.py

Poly Haven (polyhaven.com) publishes everything under CC0, so nothing needs crediting, but it is credited on the
renders page anyway. The files are cached and skipped when present; .assets/ is not committed.
"""
import json, os, sys, urllib.request

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.assets')
API = 'https://api.polyhaven.com/files/'

TEXTURES = ['white_plaster_02', 'oak_veneer_01', 'rough_linen', 'wool_boucle', 'curly_teddy_natural', 'marble_01',
            'fabric_pattern_07', 'velour_velvet']
MAPS = {'Diffuse': 'diff', 'nor_gl': 'nor', 'Rough': 'rough'}
HDRIS = ['kloofendal_48d_partly_cloudy_puresky']
MODELS = ['potted_plant_02', 'potted_plant_04', 'book_encyclopedia_set_01', 'ceramic_vase_01', 'ceramic_vase_03',
          'hanging_picture_frame_02', 'throw_pillows_01', 'wooden_bowl_01']


def get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'amira-apartment-renders'})
    with urllib.request.urlopen(req, timeout=120) as r, open(path + '.part', 'wb') as f:
        f.write(r.read())
    os.replace(path + '.part', path)
    print('  ', os.path.relpath(path, ROOT))


def files(name):
    req = urllib.request.Request(API + name, headers={'User-Agent': 'amira-apartment-renders'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main(res='2k'):
    for t in TEXTURES:
        d = files(t)
        for k, short in MAPS.items():
            if k in d:
                get(d[k][res]['jpg']['url'], os.path.join(ROOT, 'tex', t, '%s.jpg' % short))
    for h in HDRIS:
        get(files(h)['hdri']['4k']['hdr']['url'], os.path.join(ROOT, 'hdri', h + '.hdr'))
    for m in MODELS:
        d = files(m)
        if 'gltf' not in d:
            print('  no glTF for', m); continue
        g = d['gltf'][res]['gltf']
        base = os.path.join(ROOT, 'models', m)
        get(g['url'], os.path.join(base, m + '.gltf'))
        for rel, inc in g['include'].items():
            get(inc['url'], os.path.join(base, rel))
    print('assets in', ROOT)


if __name__ == '__main__':
    main(*sys.argv[1:])
