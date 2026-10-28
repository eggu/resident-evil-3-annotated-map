"""Every reachable item without its own position (corpse, object, cutscene) gets a map marker."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_overlay import revealed_by, held_spot
from extract_scd import parse_room

missing = []
for name in ('DATA_J', 'DATA_AJ'):
    for rid, r in json.loads((ROOT / f'data/rooms-{name}.json').read_text()).items():
        if int(rid[0]) > 5:
            continue
        bio = ROOT / 'local/scd' / name / f'R{rid}.bio'
        procs, shown = parse_room(bio, strict=True)[0], revealed_by(bio)
        for i in r['items']:
            if i['path'] and i['w'] <= 1 and i['d'] <= 1 and not held_spot(i['aot'], r['aots'], shown, procs) \
                    and not any(e['proc'] == i['proc'] and e['cond'] == i['cond'] for e in r['enemies']):
                missing.append((name, rid, i['name']))
assert not missing, missing
markers = {(m['rdt'], m['item']) for m in json.loads((ROOT / 'data/overlay.json').read_text())['markers'] if 'item' in m}
assert {('21A', 0x15), ('21A', 0x87), ('113', 0x75), ('20C', 0x19), ('502', 0x0A)} <= markers   # Zigzag Alley merc ammo etc.
print('held items OK')
guards = {(m['rdt'], m['item']): m['guard'] for m in json.loads((ROOT / 'data/overlay.json').read_text())['markers'] if 'item' in m}
assert guards[('202', 0x18)] == [[[3, 240, 1]]], guards[('202', 0x18)]   # Construction St. grenades: car opened (aot_on guard)
assert guards[('103', 0x62)] == [[[3, 7, 1]]], guards[('103', 0x62)]     # Business Main St. powder: switched off until zombie bursts out
assert guards[('21A', 0x87)] == [] and guards[('307', 0x1B)] == []      # own pickup flag / room-local bank 4 not used
print('item switch conditions OK')
ms = json.loads((ROOT / 'data/overlay.json').read_text())['markers']
compass = [m for m in ms if m['rdt'] == '205' and m.get('item') == 0x50 and m['kind'] == 'key']
assert compass and all(m['x'] > 560 for m in compass), compass   # on the water feature statue, not world origin (inside Restaurant)
hook = [m for m in ms if m['rdt'] == '211' and m.get('item') == 0x32 and m['kind'] == 'key']
assert [(m['x'], m['y']) for m in hook] == [(499, 99)], hook          # locker by the back door, not mirrored placeholder coords
zombies = [m for m in ms if m['rdt'] == '206' and m['kind'] == 'enemy']
# real cmp(0, 39, CMP_EQ, n) form compiles; only entry-dependent groups (previous room / camera cut) stay unknown
assert sum([] not in m['guard'] for m in zombies) >= 12 and any([55, 39, 6] in c for m in zombies for c in m['guard'])
print('placeholder positions and shopping district encounters OK')

computer = [m for m in ms if m["rdt"] == "11B" and m["kind"] == "puzzle" and "aot" not in m]
assert len(computer) == 1 and computer[0]["sets"] == 3, computer
assert computer[0]["guard"] == [[[9, 27, 0]]], computer
print("Sales Office computer puzzle: both datasets, hidden after unlock OK")

substation = [m for m in ms if m["rdt"] == "214" and m["kind"] == "puzzle"]
assert len(substation) == 2 and all(m["sets"] == 3 for m in substation), substation
assert {str(m["guard"]) for m in substation} == {str([[[3, 92, 0]]]), str([[[3, 94, 0], [3, 95, 0]]])}, substation
from build_overlay import project
from pe import Image
from build_overlay import remap_table
page, idx = remap_table(Image()).get((1, 0x14), (1, 0x14))
proj = json.loads((ROOT / 'data/map-pages.json').read_text())[page]['rooms'][idx]['proj']
assert {(m['x'], m['y']) for m in substation} == {project(proj, -7888, -22635), project(proj, -12833, -25810)}, substation
voltage = next(m for m in substation if len(m['guard'][0]) == 2)
for low in (0, 1):
    for high in (0, 1):
        visible = any({94: low, 95: high}[bit] == value for bank, bit, value in voltage['guard'][0])
        assert visible == (not (low and high))
print('Sub Station: real switch/transformer positions, both datasets, all voltage completion states OK')

from build_overlay import center
pages = json.loads((ROOT / 'data/map-pages.json').read_text())
table = remap_table(Image())
for rid, aid, bit in [('20D', 2, 47), ('30C', 9, 136), ('40D', 2, 224)]:
    markers = [m for m in ms if m['rdt'] == rid and m['kind'] == 'puzzle' and 'item' not in m]
    assert len(markers) == 1 and markers[0]['sets'] == 3, markers
    marker = markers[0]
    assert marker['guard'] == [[[3, bit, 0]]], marker
    for dataset in ('DATA_J', 'DATA_AJ'):
        room = json.loads((ROOT / f'data/rooms-{dataset}.json').read_text())[rid]
        spot = next(a for a in room['aots'] if a['aot'] == aid and a['sce'] == 'SCE_EVENT')
        stage, roomid = int(rid[0]) - 1, int(rid[1:], 16)
        page, idx = table.get((stage, roomid), (stage, roomid))
        assert (marker['page'], marker['idx']) == (page, idx)
        assert (marker['x'], marker['y']) == project(pages[page]['rooms'][idx]['proj'], *center(spot)), marker
assert len([m for m in ms if m['rdt'] == '30C' and m['kind'] == 'puzzle' and 'item' in m]) == 3
print('Gas Station, music box and fountain: both datasets, actual interaction positions, completion guards OK')
