"""Real SCD interaction positions and independent puzzle phase expectations, both datasets."""
import itertools, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_overlay import cells, center, project, remap_table
from pe import Image

markers = json.loads((ROOT / 'data/overlay.json').read_text())['markers']
pages = json.loads((ROOT / 'data/map-pages.json').read_text())
table = remap_table(Image())


def visible(marker, state):
    return all(any(state.get((bank, bit), 0) == value for bank, bit, value in clause)
               for clause in marker['guard'])


# Expected conditions are from SCD completion/reset operations, not the builder's rule table.
sites = [('11B', 18, [(9, 27, 0)]), ('304', 14, [(3, 136, 0)]), ('304', 15, [(3, 136, 0)]),
         ('113', 8, [(9, 1, 0)]), ('406', 1, [(3, 117, 1), (3, 178, 0)]),
         *[('406', aot, [(3, 117, 0)]) for aot in range(10, 14)],
         ('40B', 1, [(3, 179, 0)]), ('40B', 2, [(3, 180, 0)]),
         *[('502', aot, []) for aot in range(10, 15)],
         ('502', 15, [(3, 213, 0)]), ('506', 18, [(3, 215, 0)])]
checks = 0
for dataset, mask in [('DATA_J', 1), ('DATA_AJ', 2)]:
    rooms = json.loads((ROOT / f'data/rooms-{dataset}.json').read_text())
    for rid, aid, required in sites:
        spot = next(a for a in rooms[rid]['aots'] if a['aot'] == aid and a['sce'] == 'SCE_EVENT')
        x, z = center(spot)
        locs = {(pg, idx, *project(pages[pg]['rooms'][idx]['proj'], x, z))
                for pg, idx, extra in cells(int(rid[0]) - 1, int(rid[1:], 16), x, z, table, spot['floor'])}
        group = [m for m in markers if m['rdt'] == rid and m['kind'] == 'puzzle' and 'item' not in m
                 and m['sets'] & mask and (m['page'], m['idx'], m['x'], m['y']) in locs]
        assert {(m['page'], m['idx'], m['x'], m['y']) for m in group} == locs, (dataset, rid, aid, group)
        bits = {(b, n) for m in group for clause in m['guard'] for b, n, v in clause}
        bits.update((b, n) for b, n, v in required)
        # Insertion/initialization states must not end the still-unsolved puzzle marker.
        bits.update({'11B': [(3, 163), (3, 168), (3, 169), (3, 170)], '113': [(3, 8)], '40B': [(3, 181)], '506': [(3, 243)]}.get(rid, []))
        bits = sorted(bits)
        for values in itertools.product((0, 1), repeat=len(bits)):
            state = dict(zip(bits, values))
            expected = all(state[(b, n)] == v for b, n, v in required)
            assert any(visible(m, state) for m in group) == expected, (dataset, rid, aid, state, group)
            checks += 1
    assert not any(m['kind'] == 'puzzle' and m['rdt'] == '40B' and m.get('item') == 0x58 for m in markers)
    assert not any(m['kind'] == 'puzzle' and m['rdt'] == '506' and m.get('item') == 0x6F for m in markers)
print(f'puzzle positions/phases OK: {len(sites)} interactions, both datasets, {checks} states')

# Actual ASI: only Main Hall visited, two references before solving, neither after.
import runpy
native = runpy.run_path(str(ROOT / 'tests/test_native.py'))
for idx in range(64): native['visit'](2, idx, False)
native['visit'](2, 4)
for aj in (False, True):
    for solved in (False, True):
        native['set_bit'](3, 136, solved)
        native['setup'](2, zoom=100, ox=-380, oy=-200)
        counts = native['run'](2, scope=1, aj=aj)
        assert counts[6] == (0 if solved else 2), (aj, solved, counts)
print('Main Hall melody references: visited-only native draw and completion hiding, both datasets OK')

for idx in range(64): native['visit'](0, idx, False)
native['visit'](0, 27)
for aj in (False, True):
    for unlocked in (False, True):
        native['set_bit'](9, 27, unlocked)
        native['setup'](0, zoom=100, ox=-140, oy=-200)
        assert native['run'](0, scope=1, aj=aj)[6] == (0 if unlocked else 2)
print('Sales Office: advertisement clue and computer both hide on unlock, both datasets OK')
