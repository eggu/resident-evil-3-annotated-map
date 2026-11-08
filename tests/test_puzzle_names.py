"""Puzzle markers are named after the puzzle (data/puzzle-names.json), never after the item they need."""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_assets import PUZZLE_NAME_BASE, puzzle_key, puzzle_names
from labels import ko_item

table = json.loads((ROOT / 'data/puzzle-names.json').read_text())
names = json.loads((ROOT / 'data/names.json').read_text())
markers = json.loads((ROOT / 'data/overlay.json').read_text())['markers']
puzzles = [m for m in markers if m['kind'] == 'puzzle']

keys = {puzzle_key(m) for m in puzzles}
assert keys == set(table['names']) | set(table['unresolved']), (keys ^ (set(table['names']) | set(table['unresolved'])))
assert not set(table['names']) & set(table['unresolved'])
for k, v in table['names'].items():
    assert v['en'].strip() and v['ko'].strip() and v['evidence'].strip(), k
for k, why in table['unresolved'].items():
    assert why.strip(), k

# No puzzle name may equal an item name (key items included) unless the reviewed exception list says so.
item_names = {n for pair in names['items'].values() for n in pair} | {ko_item(ko) for _, ko in names['items'].values()}
clash = {n for v in table['names'].values() for n in (v['en'], v['ko'], ko_item(v['ko'])) if n in item_names}
assert clash <= set(table['exceptions']), clash

# Generated header: every named marker gets its table id, the id has a MarkName entry, nothing else changes.
ids, text = puzzle_names()
header = (ROOT / 'src/assets.h').read_text()
rows = re.search(r'Marker markers\[MARKER_COUNT\] = \{(.*?)\};', header, re.S).group(1)
kinds = [int(r.split(',')[0]) for r in re.findall(r'\{(\d+,\d+,\d+,\d+,-?\d+,-?\d+,\d+,\d+,\d+,\d+)\}', rows)]
pids = [int(x) for x in re.search(r'puzzle_names\[MARKER_COUNT\] = \{(.*?)\};', header).group(1).split(',')]
assert len(kinds) == len(pids)
K_PUZZLE = 6
drawn = [m for m in markers if not (m['kind'] == 'enemy' and [] in m['guard'])]
assert len(drawn) == len(kinds)
for m, kind, pid in zip(drawn, kinds, pids):
    if m['kind'] == 'puzzle':
        assert kind == K_PUZZLE and pid == ids.get(puzzle_key(m), 0), (m, pid)
    else:
        assert pid == 0
entries = set(re.findall(r'\{%d,(\d+),\{\{' % K_PUZZLE, header.split('mark_names[MARK_NAME_COUNT]')[1].split('legend_sprites')[0]))
assert {str(i) for i in text} <= entries, set(map(str, text)) - entries
assert min(text) >= PUZZLE_NAME_BASE and len(text) == len({(v['en'], v['ko']) for v in table['names'].values()})
print(f'puzzle names OK: {len(table["names"])} entries / {len(text)} distinct names, {len(table["unresolved"])} unresolved, {len(puzzles)} markers')

# Actual ASI: with item names on, a puzzle marker draws its puzzle name in both languages, not the item's name.
import runpy, struct
t = runpy.run_path(str(ROOT / 'tests/test_native.py'))
u, call, setup, run, visit, prims, sprites = (t[k] for k in ('u', 'call', 'setup', 'run', 'visit', 'prims', 'sprites'))
pages = json.loads((ROOT / 'data/map-pages.json').read_text())
lines = {(int(k), int(i)): [[int(a), int(b)], [int(c), int(d)]] for k, i, a, b, c, d in
         re.findall(r'\{(\d+),(\d+),\{\{(\d+),(\d+)\},\{(\d+),(\d+)\}\}\}', header.split('mark_names[MARK_NAME_COUNT] = {', 1)[1].split('};', 1)[0])}
assert not [i for k, i in lines if k == K_PUZZLE and i < PUZZLE_NAME_BASE and not any(
    m.get('item') == i and puzzle_key(m) in table['unresolved'] for m in puzzles)], 'item-named puzzle without a table exception'


def drawn_names(page, lang, guard):
    for bank, bit, value in guard[0]: t['set_bit'](bank, bit, bool(value))
    for p in range(7):
        for i in range(80): visit(p, i)
    b = pages[page]['bounds']; cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
    setup(page, zoom=50, ox=-cx // 2, oy=-cy // 2); call('AnnotatedMapTestOptions', 1, 1, 0)
    run(page, scope=3, korean=lang)
    base, n = prims(); seen = set()
    for i in range(n):
        q = bytes(u.mem_read(base + 40 * i, 40)); pg = struct.unpack_from('<H', q, 22)[0] - 1
        seen.update(k for k, s in enumerate(sprites) if s[0] == pg and (s[1], s[2]) == (q[12], q[13]))
    return seen


checks = 0
for expect_key, page in (('205/-/79', 1), ('109/-/53', 0), ('309/28/-', 2), ('30C/9/-', 2), ('502/10/-', 4)):
    m = next(m for m in puzzles if puzzle_key(m) == expect_key)
    assert m['page'] == page, (expect_key, m['page'])
    for lang in (0, 1):
        want = {s for s in lines[K_PUZZLE, ids[expect_key]][lang] if s != 65535}
        assert want <= drawn_names(page, lang, m['guard']), (expect_key, lang)
        checks += 1
print(f'puzzle names drawn by the ASI with item names on: {checks} page/language checks OK')
