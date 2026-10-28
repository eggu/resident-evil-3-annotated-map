"""Shared-part/transparent-room placement and the reported visited-only Piano Room case."""
import json, sys, runpy, struct, re, itertools
from pathlib import Path
from collections import Counter
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_assets import snap, tim_alpha, _snap_pixels
pages = json.loads((ROOT / 'data/map-pages.json').read_text())
markers = json.loads((ROOT / 'data/overlay.json').read_text())['markers']
verified, fallback = 0, 0
for marker in markers:
    x, y = snap(marker, pages)
    room = pages[marker['page']]['rooms'][marker['idx']]
    points = _snap_pixels[id(pages), marker['page'], marker['idx']]
    if len(points):
        assert np.any(np.all(points == (x, y), axis=1)), marker
        verified += 1
    else:
        assert any(px <= x <= px + u1 - u0 and py <= y <= py + v1 - v0 for u0, v0, u1, v1, px, py, *_ in room['parts']), marker
        fallback += 1
piano = next(m for m in markers if m['kind'] == 'lock' and m['rdt'] == '301' and m['item'] == 120)
assert (piano['x'], piano['y']) == (334, 227)  # real AOT3 area invokes positionless door1
assert snap(piano, pages) == (334, 228)
assert 322 <= snap(piano, pages)[0] <= 348 and 227 <= snap(piano, pages)[1] <= 266

# Audit every reachable placeholder locked door in both datasets through its actual aot_on event.
from build_overlay import held_spot, revealed_by, project, center
from extract_scd import parse_room
resolved = []
for ds in ('DATA_J', 'DATA_AJ'):
    rooms = json.loads((ROOT / f'data/rooms-{ds}.json').read_text())
    for rid, room in rooms.items():
        if int(rid[0]) > 5: continue
        for door in room['doors']:
            if door['path'] is None or not 0 < door['key'] < 254 or door['w'] > 1 or door['d'] > 1: continue
            bio = ROOT / 'local/scd' / ds / f'R{rid}.bio'
            spot = held_spot(door['aot'], room['aots'], revealed_by(bio), parse_room(bio, strict=True)[0])
            assert spot is not None and spot['aot'] == 3, (ds, rid, door)
            assert rid == '301' and door['aot'] == 1
            assert project(pages[2]['rooms'][1]['proj'], *center(spot)) == (334, 227)
            # Nearest native door mark is the upper horizontal red mark, not the side exit.
            marks = pages[2]['rooms'][1]['marks']
            centers = [(p[4] + (p[2] - p[0]) / 2, p[5] + (p[3] - p[1]) / 2) for p in marks]
            closest = min(centers, key=lambda p: (p[0] - 334) ** 2 + (p[1] - 227) ** 2)
            assert closest == (333.5, 228.0), closest
            resolved.append((ds, rid, door['aot'], spot['aot']))
assert len(resolved) == 2, resolved

# Actual ASI: only Piano Room/Courtyard visited; no pickup key leaks from Chapel/Bedroom.
t = runpy.run_path(str(ROOT / 'tests/test_native.py'))
u, call, setup, run, visit, set_bit = [t[k] for k in ('u', 'call', 'setup', 'run', 'visit', 'set_bit')]
for idx in range(80): visit(2, idx, False)
for idx in (1, 3): visit(2, idx)
set_bit(9, 21, False)
setup(2, zoom=100, ox=-320, oy=-228)
counts = run(2, scope=1)
assert counts[3] == 0 and counts[2] == 1, counts
m = next(m for m in t['markers'] if m[0] == 2 and m[1:3] == (2, 1) and m[6] == 120)
assert m[4:6] == (334, 228), m
set_bit(9, 21); assert run(2, scope=1)[2] == 0

# Header settings: same x, separate rows, small dimensions, inside panel in both languages/extremes.
for lang in (0, 1):
    for size, opacity in itertools.product((50, 150), (10, 100)):
        while call('AnnotatedMapTestSize') < size: t['tap'](1 << 10)
        while call('AnnotatedMapTestSize') > size: t['tap'](1 << 11)
        while call('AnnotatedMapTestOpacity') < opacity: t['tap']((1 << 12) | (1 << 10))
        while call('AnnotatedMapTestOpacity') > opacity: t['tap']((1 << 12) | (1 << 11))
        setup(2, zoom=100, ox=-320, oy=-228); run(2, scope=1, korean=lang)
        base, n = t['prims']()
        quads = [bytes(u.mem_read(base + 40 * i, 40)) for i in range(n - 14, n)]
        xy = lambda q: struct.unpack_from('<hh', q, 8)
        end = lambda q: struct.unpack_from('<hh', q, 32)
        panel, title, opacity, size_quad = quads[:4]
        assert xy(opacity)[0] == xy(size_quad)[0] and xy(opacity)[1] < xy(size_quad)[1]
        assert end(opacity)[1] <= xy(size_quad)[1]
        assert max(end(opacity)[1], end(size_quad)[1]) <= xy(quads[4])[1]
        for q in (opacity, size_quad):
            assert xy(panel)[0] <= xy(q)[0] < end(q)[0] <= end(panel)[0]
            assert xy(panel)[1] <= xy(q)[1] < end(q)[1] <= end(panel)[1]
            assert end(q)[1] - xy(q)[1] < end(quads[4])[1] - xy(quads[4])[1]
print(f'marker placement OK: {verified} alpha-backed points, {fallback} preserved native-rectangle fallbacks; visited-only Winder lock and bilingual compact header checked')

# Optional CPU reconstruction of the user's visited-only Clock Tower view; not a GPU screenshot.
import os
if os.environ.get('PREVIEW'):
    from PIL import Image
    out = Path(os.environ['PREVIEW']); out.mkdir(parents=True, exist_ok=True)
    set_bit(9, 21, False)
    while call('AnnotatedMapTestSize') > 100: t['tap'](1 << 11)
    while call('AnnotatedMapTestSize') < 100: t['tap'](1 << 10)
    while call('AnnotatedMapTestOpacity') > 70: t['tap']((1 << 12) | (1 << 11))
    while call('AnnotatedMapTestOpacity') < 70: t['tap']((1 << 12) | (1 << 10))
    atlas = [Image.open(ROOT / f'build/atlas-preview/page{i}-hd.png') for i in range(int(re.search(r'ATLAS_PAGES (\d+)', t['H'])[1]))]
    tim = Image.open(ROOT / 'local/map-preview/page2-tim.png')
    for lang in (0, 1):
        setup(2, zoom=100, ox=-380, oy=-240); run(2, scope=1, korean=lang)
        base, n = t['prims'](); canvas = Image.new('RGBA', (1280, 960), (8, 10, 12, 255))
        allparts = Counter(tuple(p[:6]) for r in pages[2]['rooms'] for p in r['parts'])
        for idx in (1, 3):
            parts = pages[2]['rooms'][idx]['parts']
            parts = [p for p in parts if allparts[tuple(p[:6])] == 1] or parts
            for u0, v0, u1, v1, x, y, *_ in parts:
                sprite = tim.crop((u0, v0, u1 + 1, v1 + 1)).resize(((u1 - u0 + 1) * 4, (v1 - v0 + 1) * 4), Image.Resampling.NEAREST)
                canvas.alpha_composite(sprite, ((x - 380 + 160) * 4, (y - 240 + 120) * 4))
        for i in range(n):
            q = bytes(u.mem_read(base + 40 * i, 40))
            x0, y0 = struct.unpack_from('<hh', q, 8); x1, y1 = struct.unpack_from('<hh', q, 32)
            tp = struct.unpack_from('<H', q, 22)[0] - 1
            sprite = atlas[tp].crop((q[12] * 4, q[13] * 4, q[36] * 4, q[37] * 4)).resize(((x1 - x0) * 4, (y1 - y0) * 4), Image.Resampling.LANCZOS)
            canvas.alpha_composite(sprite, (x0 * 4, y0 * 4))
        canvas.save(out / f'clock-visited-{lang}.png')
    print('CPU reconstruction:', out)
