"""Post-use suppression, old-room variants, and reversible item-use mechanisms."""
import itertools, json, runpy, struct
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
markers = json.loads((ROOT / 'data/overlay.json').read_text())['markers']

def visible(m, state):
    return all(any(state.get((b, n), 0) == v for b, n, v in clause) for clause in m['guard'])

# Independent SCD-derived phase rules; all existing variants at the same use point must agree.
rules = [(['109', '123'], [53, 62, 63], [(3, 28, 0)]),
         (['218'], [60], [(3, 186, 0), (7, 65, 0)]),
         (['203'], [49], [(3, 107, 0)]),
         (['205'], [79], [(7, 68, 1)]), (['205'], [80], [(7, 67, 1)]),
         (['310'], [85], [(3, 66, 1), (3, 172, 0)]),
         (['404'], [64], [(3, 80, 0)]),
         (['502'], [96], [(9, 33, 0)]),
         (['506'], [126], [(8, 109, 0), (3, 244, 0)])]
checks = 0
for mask in (1, 2):
    for rdts, items, expected in rules:
        group = [m for m in markers if m['kind'] == 'puzzle' and m['rdt'] in rdts and m.get('item') in items and m['sets'] & mask]
        assert group, (rdts, items)
        keys = sorted({(b, n) for m in group for clause in m['guard'] for b, n, v in clause} | {(b, n) for b, n, v in expected})
        for values in itertools.product((0, 1), repeat=len(keys)):
            state = dict(zip(keys, values))
            assert any(visible(m, state) for m in group) == all(state[b, n] == v for b, n, v in expected), (rdts, items, state, group)
            checks += 1
# No unconditional item-use survivor except R509, which is gated by its real current-room VM state.
assert all(m['guard'] or m['rdt'] == '509' for m in markers if m['kind'] == 'puzzle' and 'item' in m)

# Emulate native pre/post flags with all source-room variants loaded in the table.
t = runpy.run_path(str(ROOT / 'tests/test_native.py'))
u, setup, run, set_bit = [t[k] for k in ('u', 'setup', 'run', 'set_bit')]
for aj in (False, True):
    for bank, bit, page in [(3, 28, 0), (3, 186, 0), (3, 107, 1), (3, 80, 6), (9, 33, 4), (3, 244, 4)]:
        set_bit(bank, bit, False); setup(page); before = run(page, scope=3, aj=aj)[6]
        set_bit(bank, bit); after = run(page, scope=3, aj=aj)[6]
        assert after < before, (aj, bank, bit, page, before, after)
        set_bit(bank, bit, False)
# Reversible devices must return when the script restores their state.
for bank, bit, page in [(3, 107, 1), (7, 68, 1), (7, 67, 1)]:
    set_bit(bank, bit, False); setup(page); original = run(page, scope=3)[6]
    set_bit(bank, bit); alternate = run(page, scope=3)[6]
    assert original != alternate
    set_bit(bank, bit, False); assert run(page, scope=3)[6] == original
# R509 completion bank4:26 has no proven persistent equivalent; show it only in loaded R509 before use.
u.mem_write(0xA673C6, struct.pack('<HH', 4, 0)); set_bit(4, 26, False)
setup(4); remote = run(4, scope=3)[6]
u.mem_write(0xA673C8, struct.pack('<H', 9)); assert run(4, scope=3)[6] == remote + 1
set_bit(4, 26); assert run(4, scope=3)[6] == remote
print(f'puzzle completion OK: {checks} independent phase states, both datasets; old variants/reversible/local-only reader checked')
