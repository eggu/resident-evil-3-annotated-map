"""RE0 HD map rules in the actual ASI (user 2026-11-07): fixed room names and leaders, the item-name toggle, mark
tiers and removal, panels kept clear, legend fold, icon-opacity CLUT and the RE1 HD lock option. Usage as test_native."""
import json, re, runpy, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
t = runpy.run_path(str(ROOT / 'tests/test_native.py'))
u, call, setup, run, visit, prims, H, rooms, markers = (t[k] for k in ('u', 'call', 'setup', 'run', 'visit', 'prims', 'H', 'rooms', 'markers'))
PANELS = t['LEGEND_N'] + t['READOUT_N']
NAME_FIRST = int(re.search(r'NAME_PAGE_FIRST (\d+)', H)[1])
sprites = t['sprites']
pages = json.loads((ROOT / 'data/map-pages.json').read_text())
LEADER = int(re.search(r'#define LEADER_SPRITE (\d+)', H)[1])
mark_name_ids = {int(v) for m in re.findall(r'\{\d+,\d+,\{\{(\d+),(\d+)\},\{(\d+),(\d+)\}\}\}', H.split('mark_names[MARK_NAME_COUNT] = {', 1)[1].split('};', 1)[0]) for v in m} - {65535}
monster_ids = {int(v) for v in re.search(r'monster_icons\[MONSTER_COUNT\] = \{([0-9,]+)\}', H)[1].split(',')}
item_ids = [int(v) for v in re.search(r'item_icons\[134\] = \{([0-9,]+)\}', H)[1].split(',')]
puzzle_ids = {int(re.search(rf'#define ICON_{n} (\d+)', H)[1]) for n in ('PUZZLE_MARKER',)}
# key item icons that never stand for a lock (a lock shows its key's icon and is not top tier)
key_ids = ({item_ids[m[6]] for m in markers if m[0] == 3 and m[6] < 134} - {item_ids[m[6]] for m in markers if m[0] == 2 and m[6] < 134}) | puzzle_ids
common_ids = ({item_ids[m[6]] for m in markers if m[0] == 7 and m[6] < 134} | monster_ids) - key_ids
name_lines = {(int(k), int(i)): {int(a), int(b), int(c), int(d)} - {65535} for k, i, a, b, c, d in
              re.findall(r'\{(\d+),(\d+),\{\{(\d+),(\d+)\},\{(\d+),(\d+)\}\}\}', H.split('mark_names[MARK_NAME_COUNT] = {', 1)[1].split('};', 1)[0])}
far = [tuple(int(v) for v in m) for m in re.findall(r'\{(\d+),(\d+),(-?\d+),(-?\d+)\}', H.split('lock_far[] = {', 1)[1].split('};', 1)[0])]


def quads():
    base, n = prims()
    out = []
    for i in range(n):
        q = bytes(u.mem_read(base + 40 * i, 40))
        x0, y0 = struct.unpack_from('<hh', q, 8); x1, y1 = struct.unpack_from('<hh', q, 32)
        page, clut = struct.unpack_from('<H', q, 22)[0] - 1, struct.unpack_from('<H', q, 14)[0]
        sid = next((k for k, s in enumerate(sprites) if s[0] == page and (s[1], s[2]) == (q[12], q[13])), None)
        out.append(dict(box=(x0, y0, x1, y1), sid=sid, clut=clut, page=page))
    return out
def hit(a, b): return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
def view(page, zoom=100):
    b = pages[page]['bounds']; cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
    setup(page, zoom=zoom, ox=-cx * zoom // 100, oy=-cy * zoom // 100)
    return cx, cy
checks = {}
for page in range(7):
    for idx in range(80): visit(page, idx)

# 1. Item names: off by default, on with H; marks and names never under the panels; icons use the icon CLUT row.
for page in range(7):
    for names in (0, 1):
        view(page, 50); call('AnnotatedMapTestOptions', names, 1, 0)
        run(page, scope=3, korean=page & 1); q = quads()
        body, panels = q[:-PANELS], q[-PANELS:]
        named = [x for x in body if x['sid'] in mark_name_ids]
        assert names or not named, (page, len(named))
        checks['names drawn'] = checks.get('names drawn', 0) + len(named)
        assert all(not hit(x['box'], p['box']) for x in body for p in panels[:2]), page   # legend and readout panels
        for x in body:
            assert x['clut'] == (64 if x['page'] >= NAME_FIRST else 128), x
        assert all(x['clut'] == 0 for x in panels)
        # 2. Tiers: no common item or enemy icon whose middle lies on a key item or puzzle icon's middle.
        icons = [x for x in body if x['page'] < NAME_FIRST]
        core = lambda x: ((x['box'][0] + x['box'][2]) / 2, (x['box'][1] + x['box'][3]) / 2)
        side = max((x['box'][2] - x['box'][0] for x in icons), default=0)
        for a in icons:
            if a['sid'] not in common_ids: continue
            for b in icons:
                if b['sid'] in key_ids:
                    (ax, ay), (bx, by) = core(a), core(b)
                    assert abs(ax - bx) >= 2 * (side * 7 // 36 + 1) or abs(ay - by) >= 2 * (side * 7 // 36 + 1), (page, a, b)
        checks['names+tiers'] = checks.get('names+tiers', 0) + 1
call('AnnotatedMapTestOptions', 0, 1, 0)
assert checks['names drawn'] > 50, checks

# 3. Room names are fixed: centre (or leader end) stays where it was generated at any name size; leaders drawn.
leads = 0
for page in range(7):
    cx, cy = view(page, 100)
    for size in (50, 150, 100):
        while call('AnnotatedMapTestSize') < size: t['tap'](1 << 10)
        while call('AnnotatedMapTestSize') > size: t['tap'](1 << 11)
        run(page, scope=3, korean=0); q = quads()[:-PANELS]
        for r in rooms:
            if r[0] != page or not t['native_room'](page, r[1]): continue
            if r[2]: ex, ey = r[10][2] - cx + 160, r[10][3] - cy + 120
            else: ex, ey = r[4] / 2 - cx + 160, r[6] / 2 - cy + 120
            same = [x['box'] for x in q if x['sid'] == r[8]]   # rooms of one name share their sprite
            box = min(same, key=lambda b: abs((b[0] + b[2]) / 2 - ex) + abs((b[1] + b[3]) / 2 - ey), default=None)
            if box is None: continue   # off screen at this view, or hidden under a panel
            if r[2]:
                assert box[0] - 1 <= ex <= box[2] + 1 and box[1] - 1 <= ey <= box[3] + 1, (r, box, ex, ey)   # touches the end
                assert any(x['sid'] == LEADER for x in q); leads += 1
            else:
                mx, my = r[4] / 2 - cx + 160, r[6] / 2 - cy + 120
                assert abs((box[0] + box[2]) / 2 - mx) <= 1 and abs((box[1] + box[3]) / 2 - my) <= 1, (r, box, mx, my)
assert leads, 'no leader exercised'
checks['room names'] = leads

# 4. Legend fold: one '[~] Legend' line, no readouts; marks may then use the bottom-right corner.
view(0, 50); call('AnnotatedMapTestOptions', 0, 0, 0); run(0, scope=3); q = quads()
assert q[-1]['clut'] == 0 and q[-2]['clut'] == 0
fold_ids = {int(v) for v in re.search(r'hint_fold\[2\] = \{([0-9,]+)\}', H)[1].split(',')}
readout_ids = {int(v) for v in re.findall(r'\d+', H.split('readout_hints[4][2][2] = {', 1)[1].split('};', 1)[0])}
assert q[-1]['sid'] in fold_ids and q[-2]['sid'] is None and not any(x['sid'] in readout_ids for x in q)   # panel tile is inset
call('AnnotatedMapTestOptions', 0, 1, 0)
checks['fold'] = 1

# 5. RE1 HD lock option: destination side unless only the destination was visited.
marker_index = {i: m for i, m in enumerate(markers)}
moved = 0
for mi, idx2, fx, fy in far:
    m = marker_index[mi]
    if m[0] != 2 or m[2] == idx2: continue
    page = m[1]
    cx, cy = (m[4] + fx) // 2, (m[5] + fy) // 2   # centred on the door, clear of the panels
    setup(page, zoom=100, ox=-cx, oy=-cy)
    def lock_box(far_side, src_seen, dst_seen):
        for i in range(80): visit(page, i, False)
        visit(page, m[2], src_seen); visit(page, idx2, dst_seen)
        call('AnnotatedMapTestOptions', 0, 1, far_side)
        run(page, scope=3, korean=0, toggles=(1, 0, 1, 0, 0, 0, 0, 0, 0))
        icons = [x for x in quads()[:-PANELS] if x['sid'] == item_ids[m[6]]]
        return [((x['box'][0] + x['box'][2]) // 2, (x['box'][1] + x['box'][3]) // 2) for x in icons]
    door, dest = (m[4] - cx + 160, m[5] - cy + 120), (fx - cx + 160, fy - cy + 120)
    if not (0 < dest[0] < 320 and 0 < dest[1] < 240 and 0 < door[0] < 320 and 0 < door[1] < 240): continue
    near = lambda pts, p: any(abs(a - p[0]) <= 1 and abs(b - p[1]) <= 1 for a, b in pts)
    if not lock_box(0, 1, 0): continue   # its story guard is not met in this synthetic state
    assert near(lock_box(0, 1, 0), door), (m, door)
    assert near(lock_box(1, 1, 0), dest), (m, dest)
    assert near(lock_box(1, 0, 1), door), (m, door)
    moved += 1
assert moved, 'no lock exercised'
call('AnnotatedMapTestOptions', 0, 1, 0)
checks['lock side'] = moved
# 6. RE0 rule 14, full data: every page, both data sets, both languages, zoomed out and in over the whole page,
# item names on. No item is named twice at one spot, neither in the ASI's marks nor in the drawn names.
MARK = struct.Struct('<4h4h2hH7Bx')   # sizeof(Mark) == 30   # Rect m, Rect name, cx, cy, sprite, cat, event, state, slot, ringed, kind, item
DUP_PX = 4   # map px: RE3's side-by-side pickups of one item lie 1-4 px apart (tools/build_overlay.py data)
merged, named_total, touching = 0, 0, 0
for page in range(7):
    for aj in (False, True):
        for lang in (0, 1):
            for zoom in (50, 100):
                b = pages[page]['bounds']
                spots = [((b[0] + b[2]) // 2, (b[1] + b[3]) // 2)] if zoom == 50 else \
                        [(x, y) for x in range(b[0] + 80, b[2], 160) for y in range(b[1] + 60, b[3], 120)]
                for cx, cy in spots:
                    setup(page, zoom=zoom, ox=-cx * zoom // 100, oy=-cy * zoom // 100); call('AnnotatedMapTestOptions', 1, 1, 0)
                    run(page, scope=3, korean=lang, aj=aj)
                    u.mem_write(0x20000300, bytes(4)); packed = call('AnnotatedMapTestMarks', 0x20000300)
                    base = struct.unpack('<I', u.mem_read(0x20000300, 4))[0]
                    marks = [MARK.unpack(bytes(u.mem_read(base + MARK.size * i, MARK.size))) for i in range(packed & 0xFFFF)]
                    merged += packed >> 16
                    tol = (DUP_PX * zoom + 50) // 100   # enemies (kind 8): exact spot only, as RE0
                    named = [m for m in marks if m[13] == 2]   # state NAMED (fields: m 0-3, name 4-7, cx cy 8-9, sprite, cat, event, state 13, slot, ringed, kind 16, item 17)
                    named_total += len(named)
                    for i, a in enumerate(marks):
                        for c in marks[i + 1:]:
                            t_ = 0 if a[16] == 8 else tol
                            assert not (a[16:18] == c[16:18] and abs(a[8] - c[8]) <= t_ and abs(a[9] - c[9]) <= t_), (page, a, c)
                    # drawn names: one quad per name line, at the mark's name box
                    q = quads()[:-PANELS]
                    for m in named:   # every name touches its own mark (no second ring, no clamp drift)
                        assert m[4] <= m[2] and m[0] <= m[6] and m[5] <= m[3] and m[1] <= m[7], ('name away from its mark', page, zoom, lang, aj, m)
                        touching += 1
                        own = name_lines[m[16], m[17]]
                        inside = [x for x in q if x['sid'] in own and x['box'][0] >= m[4] and x['box'][2] <= m[6] and x['box'][1] >= m[5] and x['box'][3] <= m[7]]
                        assert len(inside) in (1, 2), (page, zoom, m, inside)
                    # each drawn name line belongs to one named mark: no line drawn without its mark, none twice
                    drawn = [x for x in q if x['sid'] in mark_name_ids]
                    assert len(drawn) == sum(len([1 for x in q if x['sid'] in name_lines[m[16], m[17]] and m[4] <= x['box'][0] and x['box'][2] <= m[6] and m[5] <= x['box'][1] and x['box'][3] <= m[7]]) for m in named), (page, zoom)
call('AnnotatedMapTestOptions', 0, 1, 0)
assert merged > 0 and named_total > 200, (merged, named_total)
checks['rule 14'] = dict(merged=merged, named=named_total)
checks['names touch marks'] = touching

# 7. RE0 rule 11: room names are drawn first and are not collision targets.
# (a) Generation never reads markers: without any marker, or with a marker on every room's pole, the layout is
#     the one in src/assets.h.
import sys
sys.path.insert(0, str(ROOT / 'tools'))
import build_assets
overlay = json.loads((ROOT / 'data/overlay.json').read_text())
names_json = json.loads((ROOT / 'data/names.json').read_text())
def table(layout):
    return {(p, i, l): (round(o['x'] * 2), round(o['y'] * 2), o['line'] and tuple(o['line'])) for (p, i, l), o in layout.items()}
want = {(r[0], r[1], l): (r[4 + l], r[6 + l], (r[10 + l] if r[2 + l] else None)) for r in rooms for l in (0, 1)}
crowded = dict(overlay, markers=[dict(kind='key', page=r['page'], idx=r['idx'], x=0, y=0, item=1) for r in overlay['rooms']] * 3)
for variant in (dict(overlay, markers=[]), crowded):
    got = table(build_assets.room_layouts(variant, pages, names_json))
    assert got == want, [k for k in want if got.get(k) != want[k]][:5]
# (b) At runtime nothing moves because of a room name: every mark and item name is identical with the room names
#     drawn and with them suppressed (test export), and every room-name quad precedes every mark and item-name quad.
room_sids = {r[8] for r in rooms} | {r[9] for r in rooms} | {LEADER}
compared = 0
for page in range(7):
    view(page, 100); call('AnnotatedMapTestOptions', 1, 1, 0)
    def snapshot(no_rooms):
        call('AnnotatedMapTestNoRoomNames', no_rooms)
        run(page, scope=3, korean=0)
        call('AnnotatedMapTestNoRoomNames', 0)
        u.mem_write(0x20000300, bytes(4)); n = call('AnnotatedMapTestMarks', 0x20000300) & 0xFFFF
        base = struct.unpack('<I', u.mem_read(0x20000300, 4))[0]
        ms = [MARK.unpack(bytes(u.mem_read(base + MARK.size * i, MARK.size))) for i in range(n)]
        return [m[:8] + m[13:14] for m in ms], quads()[:-PANELS]
    on, q = snapshot(0)
    off, q_off = snapshot(1)
    assert on == off, (page, [m for m in on if m not in off][:3], [m for m in off if m not in on][:3])
    assert [x for x in q if x['sid'] not in room_sids] == q_off, page   # same quads apart from the room names
    kinds = ['room' if x['sid'] in room_sids else 'mark' for x in q]
    if 'room' in kinds and 'mark' in kinds:
        assert max(i for i, k in enumerate(kinds) if k == 'room') < min(i for i, k in enumerate(kinds) if k == 'mark'), page
    compared += len(on)
call('AnnotatedMapTestOptions', 0, 1, 0)
assert compared > 100, compared
checks['room names ignore marks'] = compared
print('RE0 rules OK:', checks)

# 8. HD textures off (REbirth config.ini HDTextures=0): a plain-pixel notice top-left, nothing under it; absent when on
#    or when the key is missing; config.ini is re-read when the map is opened again (at most once a second).
NOTICE = int(re.search(r'#define NOTICE_SPRITE (\d+)', H)[1])
profile, tick = t['profile'], t['tick']
def notice_quads(page=0):
    view(page, 50); call('AnnotatedMapTestOptions', 1, 1, 0); run(page, scope=3, korean=0)
    q = quads(); return [x for x in q if x['sid'] == NOTICE], q[:-PANELS]
profile.pop('HDTextures', None); tick[0] += 1500
assert not notice_quads()[0]   # key missing: only the log warns
for page in range(7):
    profile['HDTextures'] = 1; tick[0] += 1500
    assert not notice_quads(page)[0], page
    profile['HDTextures'] = 0; tick[0] += 1500
    shown, body = notice_quads(page)
    assert len(shown) == 1, (page, shown)
    nb = shown[0]['box']
    assert nb[0] >= 3 and nb[1] >= 3 and nb[2] < 200 and nb[3] < 80 and shown[0]['clut'] == 0, nb   # top-left, opaque UI row
    leg = [x['box'] for x in quads()[-PANELS:-PANELS + 1]]
    assert not any(hit(nb, b) for b in leg), (nb, leg)   # the legend panel is bottom-left
    assert not any(hit(nb, x['box']) for x in body if x['sid'] != NOTICE and x['sid'] is not None if x['page'] < NAME_FIRST), page   # no mark under it
    assert nb[3] - nb[1] >= 3 * 14, nb   # 3 lines of large plain glyphs
# re-check at map open: the file changed to 1 within the same second keeps the old answer, a second later it is read
profile['HDTextures'] = 1; tick[0] += 100
assert notice_quads()[0], 'throttled: still the earlier answer'
tick[0] += 1500
assert not notice_quads()[0]
profile.pop('HDTextures', None); tick[0] += 1500; notice_quads()
call('AnnotatedMapTestOptions', 0, 1, 0)
checks['hd notice'] = 1
print('HD-off notice OK')

# 9. Item names in three states (H): 0 hidden, 1 all, 2 all except common items. Drawn names and the legend row per state.
hint_rows = [[int(v) for v in re.findall(r'\d+', row)] for row in re.search(r'hint_names\[2\]\[3\] = \{(.*?)\};', H)[1].replace('},{', '}|{').split('|')]
common_name_ids = {int(v) for k, i, a, b, c, d in re.findall(r'\{(\d+),(\d+),\{\{(\d+),(\d+)\},\{(\d+),(\d+)\}\}\}', H.split('mark_names[MARK_NAME_COUNT] = {', 1)[1].split('};', 1)[0])
                   if k == '7' for v in (a, b, c, d)} - {65535}
other_name_ids = mark_name_ids - common_name_ids
assert common_name_ids and other_name_ids and len(hint_rows) == 2 and all(len(r) == 3 for r in hint_rows), (common_name_ids, hint_rows)
seen = {0: 0, 1: 0, 2: 0}; widths = set()
for page in range(7):
    for lang in (0, 1):
        by_state = {}
        for state in (0, 1, 2):
            view(page, 50); call('AnnotatedMapTestOptions', state, 1, 0); run(page, scope=3, korean=lang)
            q = quads(); body = q[:-PANELS]
            ids = [x['sid'] for x in body if x['sid'] in mark_name_ids]
            by_state[state] = sorted((x['sid'], x['box']) for x in body if x['sid'] in other_name_ids)
            seen[state] += len(ids)
            assert any(x['sid'] == hint_rows[lang][state] for x in q[-PANELS:]), (page, lang, state)   # the legend row names the state
            assert not any(x['sid'] in hint_rows[lang] and x['sid'] != hint_rows[lang][state] for x in q[-PANELS:]), (page, lang, state)
            widths.add((lang, q[-PANELS]['box'][2] - q[-PANELS]['box'][0]))   # legend panel width
            if state == 0: assert not ids, (page, lang, len(ids))
            if state == 2: assert not any(i in common_name_ids for i in ids), (page, lang)
        assert by_state[1] == by_state[2], (page, lang)   # no common names changes no other name
assert seen[0] == 0 and seen[1] > seen[2] > 0, seen
assert any(x for x in [seen[1] - seen[2]]), seen   # common names exist in state 1 only
assert len(widths) == 2, widths   # per language one legend width in all three states: it never resizes
call('AnnotatedMapTestOptions', 0, 1, 0)
checks['item names 3 states'] = seen
print('item names 3 states OK', seen)

# 10. Size baselines (user 2026-11-08): name size 100 = the old 80%, item icon size 100 = the old 130%; other icons unscaled.
item_sids = {item_ids[m[6]] for m in markers if m[0] in (2, 3, 7) and m[6] < 134 and m[6] != 10} - puzzle_ids - monster_ids   # keys, lock keys, common items
side_item, side_other = {}, {}
for page in range(7):
    view(page, 100); call('AnnotatedMapTestOptions', 0, 1, 0); run(page, scope=3, korean=0); body = quads()[:-PANELS]
    for x in body:
        w = x['box'][2] - x['box'][0]
        if x['sid'] in room_sids and x['sid'] != LEADER and x['page'] >= NAME_FIRST:
            assert w == (sprites[x['sid']][3] * 80 + 50) // 100, (x['sid'], w, sprites[x['sid']])   # name size 100 = 80% of the sprite
        if x['sid'] in puzzle_ids - {item_ids[10]}: side_other[w] = side_other.get(w, 0) + 1
        elif x['sid'] in item_sids and x['page'] < NAME_FIRST: side_item[w] = side_item.get(w, 0) + 1
assert 8 in side_other and 9 in side_item, (side_other, side_item)   # puzzle marker 8 px, item icons 7 * 1.3 = 9 px at 100/100
assert not any(w in side_other for w in (9, 10)) and 8 not in side_item, (side_other, side_item)
# at the largest icon setting both grow, items by the same 1.3
view(2, 100); call('AnnotatedMapTestOptions', 0, 1, 0)
call('AnnotatedMapTestKeys', 1 << 12)
for _ in range(10): t['tap']((1 << 12) | (1 << 10))   # icon size 200
run(2, scope=3, korean=0); big = [x['box'][2] - x['box'][0] for x in quads()[:-PANELS] if x['sid'] in item_sids]
call('AnnotatedMapTestKeys', 0)
for _ in range(10): t['tap']((1 << 12) | (1 << 11))
assert big and set(big) <= {18}, big   # 7 px base * 200% * 1.3
call('AnnotatedMapTestOptions', 0, 1, 0)
checks['size baselines'] = (side_other, side_item)
print('size baselines OK', side_other, side_item)
