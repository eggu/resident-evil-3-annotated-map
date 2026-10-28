"""Encounter branch compilation and brace-safe switch extraction."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from enemy_conditions import guard
from extract_scd import parse_room
assert guard(['if (ck(3, 41, 1) && cmp(0, var_27, 3, -1))']) == [[[3,41,1]],[[53,39,-1]]]
assert guard(['else[if (ck(3, 41, 1) && cmp(0, var_27, 3, -1))]']) == [[[3,41,0],[52,39,-1]]]
assert guard(['else[if (cmp(0, 39, CMP_EQ, 6))]']) == [[[55,39,6]]]          # real decompiler form
assert guard(['if (cmp(0, 42, CMP_GE, 3))']) == [[[52,42,3]]]
assert guard(['else[if (ck(3, 32, 1) && cmp(0, 26, CMP_EQ, 8))]']) == [[[3,32,0]]]   # cut: room-local, unknown
assert guard(['if (cmp(0, var_1A, 0, 2))']) == [[]]
assert guard(['if (cmp(0, var_04, 0, 2))']) == [[]]
assert guard(['else[if (memb_cmp(0, 15, 4, 2, 0))]']) == [[]]
assert guard(['if (ck(3, 41, 1) || ck(3, 42, 0))']) == [[[3,41,1],[3,42,0]]]
source = '''proc main
{
    switch (var_2A)
    {
        case 1:
            if (ck(3, 41, 1))
            {
                em_set(1);
            }
            break;
        default:
            em_set(2);
            break;
    }
    em_set(3);
}
'''
with tempfile.TemporaryDirectory() as d:
    p = Path(d) / 'R100.bio'; p.write_text(source)
    _, records, _ = parse_room(p, strict=True)
assert guard(records[0]['cond']) == [[[3,41,1]],[[50,42,1]]]
assert guard(records[1]['cond']) == [[[55,42,1]]]
assert records[2]['cond'] == [], records[2]
print('Encounter boolean, signed comparison, unknown and switch/default checks OK')
