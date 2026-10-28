"""Run the original x86 room geometry renderer, including ownership/floor/visit gates."""
import json, runpy, struct, sys
from pathlib import Path
from collections import Counter
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from decode_map import SIZES
native=runpy.run_path(str(ROOT/'tests/test_native.py'))
u,call,setup=native['u'],native['call'],native['setup']
# Restore the original geometry function: ordinary overlay tests deliberately stub this function.
u.mem_write(0x4EAC60,bytes(native['gi'][0xEAC60:0xEAC60+16]))
vp=native['imports']['VirtualProtect']
u.mem_write(vp,b'\xb8\x01\x00\x00\x00\xc2\x10\x00')
assert call('AnnotatedMapTestInstallOutlineScope')==1
# Preserve the exact patched call bytes for a fail-closed signature test after the renders.
patched={p:bytes(u.mem_read(p,5)) for p in (0x4EAD35,0x4EBB9C,0x4EAD7A)}
assert call('AnnotatedMapTestInstallOutlineScope')==0
for p,expected in patched.items():assert bytes(u.mem_read(p,5))==expected

u.mem_map(0x22000000,0x40000)
u.mem_map(0x23000000,0x100000)
# The PC scratch-memory adapter and OT targets are renderer infrastructure, not eligibility.
u.mem_write(0x50A430,b'\xb8\x00\x00\x00\x23\xc3')
u.ctl_remove_cache(0x4EAC60,0x4ED650)
parts=[]
current=[None]
def capture(uc,addr,size,data):
    esp=uc.reg_read(UC_X86_REG_ESP)
    _,idx,part=struct.unpack('<III',uc.mem_read(esp,12))
    current[0]=(idx,part)
u.hook_add(UC_HOOK_CODE,capture,begin=0x4EADC7,end=0x4EADC7)
u.hook_add(UC_HOOK_CODE,lambda uc,a,z,_: parts.append(current[0]),begin=0x4EAE2B,end=0x4EAE2B)
blob=(ROOT/'local/extracted/DATA_J/ETC2/MAP_J.MAP').read_bytes()
pages=json.loads((ROOT/'data/map-pages.json').read_text())
for pg in range(7):
    for idx in range(64):native['visit'](pg,idx,False)
u.mem_write(0xA67574,bytes(4))

def draw(pg,scope,enabled=True,floor=None):
    seg=blob[sum(SIZES[:pg]):sum(SIZES[:pg+1])]
    h=struct.unpack_from('<9I',seg)
    u.mem_write(0x22000000,seg)
    setup(pg,100,-320,-240)
    s=native['S']
    u.mem_write(s+0xCC,struct.pack('<I',0x22000000))
    u.mem_write(s+0xB4,struct.pack('<I',0x22000000+h[3]))
    u.mem_write(s+0xAA,bytes((255,pg)))  # skip native player arrow, preserve displayed page
    if floor is not None:u.mem_write(s+0xAD,bytes((1,floor)))
    call('AnnotatedMapTestSet',int(enabled),scope,0)
    flags_before=bytes(u.mem_read(0xA673F0,0x620))
    owned_before=bytes(u.mem_read(0xA61CA0,32))
    parts.clear()
    u.mem_write(0x20008000,struct.pack('<II',0x20000100,s))
    u.reg_write(UC_X86_REG_ESP,0x20008000)
    u.emu_start(0x4EAC60,0x20000100,count=20_000_000)
    assert bytes(u.mem_read(0xA673F0,0x620))==flags_before
    assert bytes(u.mem_read(0xA61CA0,32))==owned_before
    return set(parts)

def revealed_reference(pg,floor=None):
    owned=bytes(u.mem_read(0xA67574,4))
    visits=bytes(u.mem_read(0xA6752C,56))
    u.mem_write(0xA67574,struct.pack('<I',0x80000000>>pg))
    if pg==4:
        for idx in range(11,16):native['visit'](4,idx)
    expected=draw(pg,2,floor=floor)
    u.mem_write(0xA67574,owned);u.mem_write(0xA6752C,visits)
    return expected

checks=0
for pg in range(7):
    baseline=draw(pg,1)
    assert not baseline,(pg,baseline)
    assert draw(pg,2)==baseline
    assert draw(pg,3,False)==baseline
    all_parts=draw(pg,3)
    assert all_parts,(pg,all_parts)
    # Match the game's revealed-room shapes, preserving its story-dependent part variants.
    assert all_parts==revealed_reference(pg),(pg,all_parts, revealed_reference(pg))
    checks+=1
factory=draw(4,3)
assert {11,12,13,14,15}<={idx for idx,part in factory}
for pg,floors in ((2,range(3)),(4,range(2)),(6,range(3))):
    for floor in floors:
        shown=draw(pg,3,floor=floor)
        assert shown==revealed_reference(pg,floor),(pg,floor,shown)
        assert all(native['native_room'](pg,idx) for idx,part in shown)
        checks+=1
print(f'Native room outlines: {checks} page/floor cases, actual geometry primitives, All/unowned/unvisited, other scopes/master off and unchanged flags OK')
