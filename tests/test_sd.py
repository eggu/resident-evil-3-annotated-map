"""SD mode (Classic REbirth HDTextures=0, user decisions 2026-11-12): the built tables are checked without the game.
Layout (data/sd-layout.json): every named room has a name in both languages, none forced; on small maps every name stays
on the 320x240 screen clear of the map furniture boxes; names of one floor never touch (2 px); every leader starts inside
its own room and ends 1 px from its name. Atlas (src/sd_assets.h): every sprite's far texture edge stays below 256 and
inside its VRAM page; every common item and lock key on the maps has an SD marker; markers are 9x9 (enemy 5x5)."""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
src = (ROOT / 'tools/sd_layout.py').read_text().split('def _job(')[0]
exec(src.replace("ROOT = Path(__file__).resolve().parents[1]", f"ROOT = Path({str(ROOT)!r})"))
import build_sd

overlay = json.loads((ROOT / 'data/overlay.json').read_text())
pages_map = json.loads((ROOT / 'data/map-pages.json').read_text())
layout = json.loads((ROOT / 'data/sd-layout.json').read_text())
checked = 0
for page in sorted({r['page'] for r in overlay['rooms'] if r['name']}):
    named = {r['idx'] for r in overlay['rooms'] if r['page'] == page and r['name']}
    got = layout[str(page)]
    bx0, by0, bx1, by1 = pages_map[page]['bounds']
    small = bx1 - bx0 <= SCREEN_W and by1 - by0 <= SCREEN_H
    sx, sy = ((SCREEN_W - (bx1 - bx0)) // 2 - bx0, (SCREEN_H - (by1 - by0)) // 2 - by0) if small else (0, 0)
    allparts = [tuple(p[:6]) for q in pages_map[page]['rooms'] for p in q['parts']]
    shared = {p for p in allparts if allparts.count(p) > 1}
    alpha = tim_alpha(page)
    for lang in ('en', 'ko'):
        boxes = []
        for idx in named:
            o = got[str(idx)][lang]
            assert not o['forced'], (page, lang, o['text'])
            w, h = size_of(o['text'])
            box = (o['x'] + sx, o['y'] + sy, w, h)
            if small:
                assert 6 <= box[0] and box[0] + w <= 314 and 6 <= box[1] and box[1] + h <= 228, (page, lang, o['text'], box)
            cells = room_cells(next(q for q in pages_map[page]['rooms'] if q['index'] == idx), shared, alpha)
            if o['leader']:
                assert tuple(o['leader'][0]) in cells, (page, lang, o['text'], 'leader starts outside its room')
                ex, ey = o['leader'][-1]; ex += sx; ey += sy
                gap = max(box[0] - ex, ex - (box[0] + w - 1), box[1] - ey, ey - (box[1] + h - 1))
                assert gap == 1, (page, lang, o['text'], 'leader end not 1 px from its name', gap)
            boxes.append((o['floor'], box, o['text']))
            checked += 1
        for i, (fa, a, ta) in enumerate(boxes):
            for fb, b, tb in boxes[i + 1:]:
                if fa != fb and -1 not in (fa, fb):
                    continue   # different floors are never on screen together
                assert (a[0] + a[2] + 2 <= b[0] or b[0] + b[2] + 2 <= a[0] or a[1] + a[3] + 2 <= b[1] or b[1] + b[3] + 2 <= a[1]), (page, lang, ta, tb)

h = (ROOT / 'src/sd_assets.h').read_text()
pages = int(re.search(r'#define SD_PAGES (\d+)', h).group(1))
vram = [tuple(map(int, v)) for v in re.findall(r'\{(\d+),(\d+),(\d+)\}', h.split('sd_vram[SD_PAGES][3] = {')[1].split('};')[0])]
spr = [tuple(map(int, m)) for m in re.findall(r'\{(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)\}', h.split('sd_sprites[] = {')[1].split('};')[0])]
assert pages <= len(build_sd.VRAM_PAGES) and len(vram) == pages
for pg, u, v, w, hh, row in spr:
    assert u + w <= 255 and v + hh <= vram[pg][2] - 1, ('sprite crosses its page edge', pg, u, v, w, hh)
icons = [int(v, 0) for v in h.split('sd_item_icon[134] = {')[1].split('}')[0].split(',')]
needed = {m['item'] for m in overlay['markers'] if m['kind'] in ('common', 'lock')}
assert all(icons[i] != 0xFFFF for i in needed), sorted(i for i in needed if icons[i] == 0xFFFF)
for k, p in list(build_sd.ICONS.items()) + [(f'lock {k:#x}', p) for k, p in build_sd.LOCKS.items()]:
    rows = p.split('|')
    assert {len(r) for r in rows} == {len(rows)} and len(rows) == (5 if k == 'enemy' else 9), (k, [len(r) for r in rows])
print(f'SD layout and atlas OK: {checked} names, {len(spr)} sprites on {pages} pages')
