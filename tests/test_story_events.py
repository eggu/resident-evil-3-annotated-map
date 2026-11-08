"""Story-scene events (user 2026-11-08), full data: every event marker has a persistent done-flag, lies in its room, is
drawn while the scene is still to come and hidden once the flag is set, and only under the [6] Events toggle."""
import json, runpy, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_assets import snap, _snap_pixels
import numpy as np
t = runpy.run_path(str(ROOT / 'tests/test_native.py'))
call, setup, run, set_bit, get_bit, visit = [t[k] for k in ('call', 'setup', 'run', 'set_bit', 'get_bit', 'visit')]
pages = json.loads((ROOT / 'data/map-pages.json').read_text())
markers = json.loads((ROOT / 'data/overlay.json').read_text())['markers']
data = json.loads((ROOT / 'data/story-events.json').read_text())
story = [m for m in markers if m['kind'] == 'live' and m['event'] >= 20]
by_id = {e['id']: e for e in data['events']}
assert story and {m['event'] for m in story} == set(by_id), ({m['event'] for m in story} ^ set(by_id))
PERSISTENT = {0, 3, 5, 6, 7, 8, 9}

for m in story:
    ev = [e for e in data['events'] if e['id'] == m['event'] and e['rdt'] == m['rdt']]
    assert ev, m
    # 1. a persistent done-flag the scene itself sets: "bank/bit must be 0" is in the guard, which is what hides the marker
    dones = [e['done'] for e in ev]
    assert any([*d, 0] in [lit for clause in m['guard'] for lit in clause] for d in dones), (m, dones)
    assert all(d[0] in PERSISTENT for d in dones) and all(b in PERSISTENT or b >= 50 for clause in m['guard'] for b, n, v in clause), m
    # 2. inside its room: on the room's drawn shape (or its native rectangle when the room has no alpha shape)
    x, y = snap(m, pages)
    room = pages[m['page']]['rooms'][m['idx']]
    pts = _snap_pixels[id(pages), m['page'], m['idx']]
    if len(pts): assert np.any(np.all(pts == (x, y), axis=1)), m
    else: assert any(px <= x <= px + u1 - u0 and py <= y <= py + v1 - v0 for u0, v0, u1, v1, px, py, *_ in room['parts']), m

# 3. runtime: guard satisfied + flag clear -> drawn; flag set -> hidden; Events toggle off -> not drawn
checked = 0
groups = {}
for m in story: groups.setdefault((m['event'], m['page'], m['idx'], m['x'], m['y']), []).append(m)   # story variants of one spot draw once
for members in groups.values():
    m = members[0]
    dones = {tuple(e['done']) for mm in members for e in data['events'] if e['id'] == mm['event'] and e['rdt'] == mm['rdt']}
    for aj in (False, True):
        if not m['sets'] & (2 if aj else 1): continue
        lits = [lit for clause in m['guard'] for lit in clause if lit[0] < 50]
        saved = {k: get_bit(*k) for k in {(b, n) for b, n, v in lits} | dones}
        for b, n, v in lits: set_bit(b, n, bool(v))
        for idx in range(80): visit(m['page'], idx, False)
        setup(m['page'], zoom=50)
        if not t['native_room'](m['page'], m['idx']): continue
        only_events = (1, 0, 0, 0, 0, 0, 1, 0, 0)
        before = run(m['page'], scope=3, aj=aj, toggles=only_events)[10]
        for b, n in dones: set_bit(b, n, True)   # the scene(s) happened
        after = run(m['page'], scope=3, aj=aj, toggles=only_events)[10]
        for b, n in dones: set_bit(b, n, False)
        off = run(m['page'], scope=3, aj=aj, toggles=(1, 0, 0, 0, 0, 1, 0, 1, 1))[10]
        assert before > after and off == 0, (m, before, after, off)
        for k, v in saved.items(): set_bit(k[0], k[1], v)
        checked += 1
assert checked >= len(groups), checked
print('Story events OK:', len(story), 'markers,', len(by_id), 'scenes,', checked, 'visibility checks;', len(data['skipped']), 'scenes skipped (see data/story-events.json)')

# 4. Event marks have NO name (RE0 rule): no name-table entry of kind K_LIVE, and in every view, language and [H] state
#    (hidden / all / no common) an event mark is never NAMED and owns no name box.
import re, struct
H = t['H']
table = H.split('mark_names[MARK_NAME_COUNT] = {', 1)[1].split('};', 1)[0]
kinds = {int(k) for k in re.findall(r'\{(\d+),\d+,\{\{\d+,\d+\},\{\d+,\d+\}\}\}', table)}
K_LIVE = int(re.search(r'K_LIVE\b', H.split('enum { K_TYPEWRITER', 1)[1].split('};', 1)[0]) and len(H.split('enum { K_TYPEWRITER', 1)[1].split('};', 1)[0].split('K_LIVE')[0].split(',')) - 1)
assert K_LIVE == 10 and K_LIVE not in kinds, kinds
MARK = struct.Struct('<4h4h2hH7Bx')   # Rect m, Rect name, cx, cy, sprite, cat, event, state, slot, ringed, kind, item
u = t['u']
event_marks = 0
for page in range(7):
    for lang in (0, 1):
        for state in (0, 1, 2):
            setup(page, zoom=50); call('AnnotatedMapTestOptions', state, 1, 0)
            run(page, scope=3, korean=lang)
            u.mem_write(0x20000300, bytes(4)); packed = call('AnnotatedMapTestMarks', 0x20000300)
            base = struct.unpack('<I', u.mem_read(0x20000300, 4))[0]
            for i in range(packed & 0xFFFF):
                m = MARK.unpack(bytes(u.mem_read(base + MARK.size * i, MARK.size)))
                if m[16] == K_LIVE:
                    event_marks += 1
                    assert m[13] != 2 and m[4:8] == (0, 0, 0, 0), (page, lang, state, m)   # state 2 = NAMED
call('AnnotatedMapTestOptions', 0, 1, 0)
assert event_marks > 0, event_marks
print('Event marks carry no name OK:', event_marks, 'marks over 7 pages x 2 languages x 3 [H] states')
