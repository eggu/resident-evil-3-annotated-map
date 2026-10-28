"""Upcoming-event routes, scopes, branch exclusions and current-room-only lifecycle checks."""
import json, runpy, struct
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
t = runpy.run_path(str(ROOT / 'tests/test_native.py'))
u, call, setup, run, set_bit, visit, native_room = [t[k] for k in ('u', 'call', 'setup', 'run', 'set_bit', 'visit', 'native_room')]
markers = json.loads((ROOT / 'data/overlay.json').read_text())['markers']
events = [m for m in markers if m['kind'] == 'live']
assert len(events) == 10 and {m['event'] for m in events} == set(range(10))
assert all(m['sets'] == 3 for m in events)
assert all(b not in (1, 2, 4) for m in events for clause in m['guard'] for b, n, v in clause)
assert all(m['anchor'] in ('room', 'trigger') for m in events)
assert len([m for m in events if m['event'] == 7]) == 1  # R416/R510 are the same event.
# Room-level markers must sit on that room's opaque TIM shape, not its enclosing rectangle/hole.
from PIL import Image
pages = json.loads((ROOT / 'data/map-pages.json').read_text())
for marker in events:
    if marker['anchor'] != 'room': continue
    page, idx, x, y = [marker[k] for k in ('page', 'idx', 'x', 'y')]
    alpha = Image.open(ROOT / f'local/map-preview/page{page}-tim.png').getchannel('A')
    parts = pages[page]['rooms'][idx]['parts']
    assert any(px <= x <= px + u1 - u0 and py <= y <= py + v1 - v0 and
               alpha.getpixel((u0 + x - px, v0 + y - py)) > 0
               for u0, v0, u1, v1, px, py, *_ in parts), marker

watched = [(3, n) for n in (139, 49, 2, 13, 97, 141, 138, 219, 88, 199)] + [(7, 35), (4, 4), (4, 5), (2, 7)]
scenarios = [
    (0, [], {0, 1, 2, 3, 5, 6, 7, 9}),
    (1, [(7, 35)], {1, 2, 3, 4, 5, 6, 7, 9}),
    (1, [(7, 35), (3, 49), (3, 13)], {3, 4, 5, 6, 7, 9}),
    (1, [(7, 35), (3, 2)], {3, 4, 5, 6, 7, 9}),
    (1, [(3, 97), (3, 141)], {1, 2, 5, 6, 7, 9}),
    (2, [], {6, 7, 9}),
    (2, [(3, 138)], {7, 9}),
    (3, [], {7, 9}),
    (4, [(3, 219), (3, 88)], {8, 9}),
    (4, [(3, 219)], {9}),
    (4, [(3, 219), (3, 88), (3, 199)], {9}),
    (5, [], set()),
]
checks = 0
for aj in (False, True):
    for stage, enabled, wanted in scenarios:
        for bank, bit in watched: set_bit(bank, bit, (bank, bit) in enabled)
        u.mem_write(0xA673C6, struct.pack('<HH', stage, 0))
        actual = set()
        for m in events:
            state = {(b, n): t['get_bit'](b, n) for clause in m['guard'] for b, n, v in clause if b < 50}
            visible = all(any((state[b, n] == bool(v)) if b < 50 else stage <= v for b, n, v in clause) for clause in m['guard'])
            if visible: actual.add(m['event'])
        assert actual == wanted, (stage, enabled, actual, wanted)
        for page in range(7):
            setup(page)
            want = sum(m['event'] in wanted and m['page'] == page and native_room(page, m['idx']) for m in events)
            assert run(page, scope=3, aj=aj)[10] == want
            checks += 1

# Visited-only hides a first-entry warning. Revealed scope needs that page's map; all scope needs neither.
for bank, bit in watched: set_bit(bank, bit, False)
u.mem_write(0xA673C6, struct.pack('<HH', 0, 0))
for page in range(7):
    for idx in range(80): visit(page, idx, False)
u.mem_write(0xA67574, bytes(4))
page = next(m['page'] for m in events if m['event'] == 0)
setup(page)
assert run(page, scope=1)[10] == run(page, scope=2)[10] == 0
u.mem_write(0xA67574, struct.pack('<I', 0x80000000 >> page))
assert run(page, scope=2)[10] == run(page, scope=3)[10] == 1
assert run(page, scope=3, toggles=(1, 1, 1, 1, 1, 0, 1, 1))[10] == 0

# Temporary bits in another room must never hide a remote event.
rail = next(m for m in events if m['event'] == 9)
for bank, bit in watched: set_bit(bank, bit, False)
u.mem_write(0xA673C6, struct.pack('<HH', 4, 0))
setup(rail['page']); before = run(rail['page'], scope=3)[10]
set_bit(4, 5); assert run(rail['page'], scope=3)[10] == before
u.mem_write(0xA673C8, struct.pack('<H', 13))
assert run(rail['page'], scope=3)[10] == before - 1
set_bit(4, 5, False); set_bit(4, 4); set_bit(2, 7)
assert run(rail['page'], scope=3)[10] == before - 1
set_bit(2, 7, False); assert run(rail['page'], scope=3)[10] == before
print(f'Live Selection OK: ten event families, both datasets, {checks} native route/page cases; scopes/toggle/local lifetime checked')

# Confirm real native quads select the approved ! and ? sprites, both controlled by key5.
import re
icons = {name: t['sprites'][int(re.search(r'#define ICON_' + name + r' (\d+)', t['H'])[1])]
         for name in ('PUZZLE_MARKER', 'SELECTION_MARKER')}
icons['ROCKET_REWARD'] = t['sprites'][t['item_ids'][10]]
for bank, bit in watched: set_bit(bank, bit, False)
u.mem_write(0xA673C6, struct.pack('<HH', 0, 0))
seen = {key: 0 for key in icons}
for page in range(7):
    bounds = json.loads((ROOT / 'data/map-pages.json').read_text())[page]['bounds']
    cx, cy = (bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2
    setup(page, zoom=50, ox=-cx // 2, oy=-cy // 2)
    counts = run(page, scope=3, toggles=(1, 0, 0, 0, 0, 1, 0, 0))
    base, count = t['prims']()
    matches = {key: 0 for key in icons}
    for i in range(count - 14):
        q = bytes(u.mem_read(base + 40 * i, 40))
        for key, (pg, x, y, w, h) in icons.items():
            if (struct.unpack_from('<H', q, 22)[0] - 1, q[12], q[13]) == (pg, x, y): matches[key] += 1
    assert matches['PUZZLE_MARKER'] + matches['ROCKET_REWARD'] <= counts[6] and matches['SELECTION_MARKER'] <= counts[10]
    assert sum(matches.values()) == count - 14  # all non-legend quads; viewport clipping can omit markers
    for key in seen: seen[key] += matches[key]
assert all(seen.values()), seen
print('Native punctuation UVs OK:', seen)

cable = next(m for m in events if m['event'] == 5)
for bank, bit in watched: set_bit(bank, bit, False)
u.mem_write(0xA673C6, struct.pack('<HH', 1, 0))
setup(cable['page']); before = run(cable['page'], scope=3)[10]
set_bit(2, 7); assert run(cable['page'], scope=3)[10] == before
u.mem_write(0xA673C8, struct.pack('<H', 0x15))
assert run(cable['page'], scope=3)[10] == before - 1
print('Cable-car current-room cutscene lifetime OK')
