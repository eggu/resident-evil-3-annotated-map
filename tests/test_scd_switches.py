"""Case labels cannot keep a surrounding if open after its closing brace."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from extract_scd import parse_room

# Independent strict parser case tracking must agree on source lexical conditions everywhere.
def lexical(conds):
    return sorted(c for c in conds if not c.startswith(('switch', 'case', 'default', 'unknown_switch'))
                  and 'cmp(0, var_' not in c)

checked = 0
for dataset in ('DATA_J', 'DATA_AJ'):
    for path in sorted((ROOT / 'local/scd' / dataset).glob('R*.bio')):
        _, loose, loose_calls = parse_room(path)
        _, strict, strict_calls = parse_room(path, strict=True)
        assert len(loose) == len(strict)
        for a, b in zip(loose, strict):
            assert (a['proc'], a['op'], a['args']) == (b['proc'], b['op'], b['args'])
            assert lexical(a['cond']) == lexical(b['cond']), (path, a, b)
            checked += 1
        for proc in loose_calls:
            assert len(loose_calls[proc]) == len(strict_calls[proc])
            for (a, ac), (b, bc) in zip(loose_calls[proc], strict_calls[proc]):
                assert a == b
                assert lexical(ac) == lexical([c for c in bc if c != 'event_trigger']), (path, proc, ac, bc)

markers = json.loads((ROOT / 'data/overlay.json').read_text())['markers']
clock = [m for m in markers if m['kind'] == 'puzzle' and m['rdt'] == '309' and m.get('aot') != 28]
assert len(clock) == 9 and {m['sets'] for m in clock} == {3}
assert all(m['guard'] == [[[3, 120, 0]]] for m in clock), clock
assert len({(m['x'], m['y']) for m in clock}) == 3
# The real main_17 call is outside the random-layout initialization block.
for dataset in ('DATA_J', 'DATA_AJ'):
    calls = parse_room(ROOT / 'local/scd' / dataset / 'R309.bio')[2]['main']
    assert ('main_17', ['else[if (ck(3, 120, 1))]']) in calls, calls
print(f'switch lexical conditions OK: {checked} records and every call site, both datasets; Clock Room guards OK')

import itertools, runpy
native = runpy.run_path(str(ROOT / 'tests/test_native.py'))
for idx in range(64): native['visit'](2, idx, False)
native['visit'](2, 9)
for aj, initialized, solved, layout in itertools.product((False, True), (False, True), (False, True), range(4)):
    native['set_bit'](47, 22, initialized)
    native['set_bit'](48, 23, layout & 1)
    native['set_bit'](48, 24, layout & 2)
    native['set_bit'](3, 120, solved)
    native['set_bit'](3, 55, False)
    native['setup'](2, zoom=100, ox=-395, oy=-170)
    counts = native['run'](2, scope=1, aj=aj)
    assert counts[6] == (0 if solved else 9), (aj, initialized, solved, layout, counts)
native['visit'](2, 9, False)
native['set_bit'](3, 120, False)
assert native['run'](2, scope=1)[6] == 0
print('Clock Room actual ASI: 32 initialization/layout/completion/dataset cases, visited scope OK')

bell = next(m for m in markers if m.get('aot') == 28 and m['rdt'] == '309' and m['kind'] == 'puzzle')
assert bell['sets'] == 3 and bell['guard'] == [[[3, 55, 1]], [[3, 126, 0]]], bell
native['visit'](2, 9)
native['set_bit'](3, 120, True)
for aj, carlos_started, moved in itertools.product((False, True), repeat=3):
    native['set_bit'](3, 55, carlos_started)
    native['set_bit'](3, 126, moved)
    native['setup'](2, zoom=100, ox=-395, oy=-170)
    assert native['run'](2, scope=1, aj=aj)[6] == int(carlos_started and not moved)
print('Clock Room bell: story phase/completion/dataset cases OK')
