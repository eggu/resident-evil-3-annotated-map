"""Clock Tower story phases must select ordinary encounters independently of item/puzzle toggles."""
import itertools, runpy, struct
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
t = runpy.run_path(str(ROOT / 'tests/test_native.py'))
u, run, setup, bit, visit = [t[k] for k in ('u','run','setup','set_bit','visit')]
for b in (5,6): u.mem_write(t['bank_addr'][b],bytes(32))
for idx in range(64): visit(2,idx,False)
u.mem_write(0xA673E4, struct.pack('<h',0))  # no active Nemesis room event
bit(3,112,True)
bit(3,200,False)
for aj, second, item_puzzles in itertools.product((False,True),repeat=3):
    bit(0,24,not second)
    toggles=(1,1,1,int(item_puzzles),1,int(item_puzzles),1,1)
    bit(3,55,False)
    visit(2,1)
    setup(2,100,-330,-240)
    assert run(2,scope=1,aj=aj,toggles=toggles)[8]==5
    bit(6 if second else 5,32,True)
    assert run(2,scope=1,aj=aj,toggles=toggles)[8]==4
    bit(6 if second else 5,32,False)
    bit(3,55,True)
    assert run(2,scope=1,aj=aj,toggles=toggles)[8]==4
    visit(2,1,False)
    bit(3,41,True);bit(48,1,False)
    bit(3,55,False)
    visit(2,2)
    setup(2,100,-330,-205)
    assert run(2,scope=1,aj=aj,toggles=toggles)[8]==3
    bit(3,55,True)
    assert run(2,scope=1,aj=aj,toggles=toggles)[8]==5
    visit(2,2,False)
    visit(2,5)
    bit(3,76,True);bit(48,9,False)
    for late,want in ((False,4),(True,2)):
        bit(3,55,late)
        setup(2,100,-430,-300)
        counts=run(2,scope=1,aj=aj,toggles=toggles)
        assert counts[8]==want, (aj,second,item_puzzles,late,counts)
    visit(2,5,False)
print('Clock Tower: both datasets/kill banks/item+puzzle toggles, Piano/Dining eligibility and first-Jill Bedroom dog exclusion OK; fresh-game visual acceptance pending')
