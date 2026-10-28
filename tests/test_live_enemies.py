"""Real x86 Nemesis eligibility and projection; ordinary actor exclusion."""
import json, runpy, struct
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EDI, UC_X86_REG_ESP

ROOT = Path(__file__).resolve().parents[1]
t = runpy.run_path(str(ROOT / 'tests/test_native.py'))
u, call, setup, prims = (t[k] for k in ('u', 'call', 'setup', 'prims'))
set_bit, visit, S = (t[k] for k in ('set_bit', 'visit', 'S'))
em, projection = 0x22000000, 0x22008000
u.mem_map(em, 0x9000)
first, endptr = 0xA621EC, 0xA6228C
original_table = bytes(u.mem_read(first, 128))
original_end = bytes(u.mem_read(endptr, 4))
assert any(m[0] == 8 for m in t['markers'])
assert any(m[6] == 7 for m in t['markers'] if m[0] == 8)

marker_blob = b''.join(struct.pack('<BBBBhhBBHH', *m) for m in t['markers'])
offset = bytes(t['di']).find(marker_blob)
assert offset >= 0
for i, m in enumerate(t['markers']):
    if m[0] == 8: u.mem_write(0x10000000 + offset + i * 14 + 3, b'\0')

# Check the exact game's update predicate, not only a matching Python model.
assert bytes(u.mem_read(0x42DCAE, 22)) == bytes.fromhex('8b0f81e1ffffffcf8ac1890fa8017442f6474780753c')
for flags, ai, expected in ((0, 0, False), (1, 128, False), (1, 192, False), (1, 0, True), (1, 64, True)):
    u.mem_write(em, struct.pack('<I', flags))
    u.mem_write(em + 0x47, bytes([ai]))
    stops = []
    def stop(uc, address, size, _):
        if address in (0x42DD00, 0x42DCC4):
            stops.append(address)
            uc.emu_stop()
    h = u.hook_add(UC_HOOK_CODE, stop, begin=0x42DCAE, end=0x42DD00)
    u.reg_write(UC_X86_REG_EDI, em)
    u.emu_start(0x42DCAE, 0x42DD01, count=20)
    u.hook_del(h)
    assert stops == [0x42DCC4 if expected else 0x42DD00], (flags, ai, stops)

pages = json.loads((ROOT / 'data/map-pages.json').read_text())
proj = pages[0]['rooms'][7]['proj']
checks = 0

def draw(flags=1, ai=0, life=100, kind=0x34, kill=255, page=0, stage=0, room=7, actors=1, monsters=True, all_on=True, dx=0, dz=0, end=None, cell=7, objects=None):
    global checks
    u.mem_write(em, bytes(0x1FC))
    u.mem_write(em, struct.pack('<I', flags))
    u.mem_write(em + 0x47, bytes([ai]))
    u.mem_write(em + 0x4A, bytes([kind]))
    u.mem_write(em + 0xCC, struct.pack('<H', life))
    u.mem_write(em + 0x147, bytes([kill]))
    u.mem_write(em + 0x34, struct.pack('<iii', proj['wx'] + dx, 0, proj['wz'] + dz))
    u.mem_write(first, bytes(128))
    if objects is None:
        pointers = [em] * actors
    else:
        pointers = []
        for j, obj in enumerate(objects):
            if obj is None:
                pointers.append(0)
                continue
            if 'alias' in obj:
                pointers.append(pointers[obj['alias']])
                continue
            actor = em + j * 0x200
            u.mem_write(actor, bytes(0x1FC))
            u.mem_write(actor, struct.pack('<I', obj.get('flags', 1)))
            u.mem_write(actor + 0x47, bytes([obj.get('ai', 0)]))
            u.mem_write(actor + 0x4A, bytes([obj['kind']]))
            u.mem_write(actor + 0xCC, struct.pack('<H', obj.get('life', 100)))
            u.mem_write(actor + 0x147, bytes([obj.get('kill', 255)]))
            u.mem_write(actor + 0x34, struct.pack('<iii', proj['wx'], 0, proj['wz']))
            pointers.append(actor)
        actors = len(pointers)
    assert actors <= 32
    for j, actor in enumerate(pointers):
        u.mem_write(first + j * 4, struct.pack('<I', actor))
    u.mem_write(endptr, struct.pack('<I', first + actors * 4 if end is None else end))
    u.mem_write(0xA673C6, struct.pack('<HH', stage, room))
    setup(page, ox=-proj['mx'], oy=-proj['my'])
    u.mem_write(S + 0xB4, struct.pack('<I', projection))
    u.mem_write(projection, struct.pack('<I', 4))
    u.mem_write(projection + 4 + cell * 8, struct.pack('<4h', *(proj[k] for k in ('mx', 'my', 'wx', 'wz'))))
    call('AnnotatedMapTestSet', 1, 3, 0)
    for key in [*range(1, 7), *([] if monsters else [7]), *([] if all_on else [0])]:
        call('AnnotatedMapTestKeys', 1 << key)
        call('AnnotatedMapTestKeys', 0)
    call('AnnotatedMapTestDraw', S)
    checks += 1
    return call('AnnotatedMapTestCount', 8), prims()

for kwargs in ({'actors': 0}, {'flags': 0}, {'ai': 128}, {'ai': 192}, {'life': 0}, {'kind': 0x50},
               {'page': 1}, {'monsters': False}, {'all_on': False}, {'end': first + 3}, {'end': first + 132}):
    assert draw(**kwargs)[0] == 0, kwargs
for kwargs in ({}, {'ai': 64}, {'kind': 0x36}, {'kind': 0x38}, {'actors': 2}):
    count, (base, n) = draw(**kwargs)
    assert count == 1 and n == 15, (kwargs, count, n)
    q = bytes(u.mem_read(base, 40))
    assert struct.unpack_from('<hh', q, 8) == (156, 116)
    pg, su, sv, sw, sh = t['sprites'][t['head_ids'][7]]
    assert (q[12], q[13], q[36], q[37], struct.unpack_from('<H', q, 22)[0]) == (su, sv, su + sw, sv + sh, pg + 1)
# Every known enemy ID maps to its own species head, including named zombies and baby insects.
known = {**{kind: 0 for kind in [*range(0x10, 0x20), 0x58, 0x59]},
         0x20: 1, 0x21: 2, 0x22: 3, 0x23: 9, 0x24: 8, 0x25: 5,
         0x26: 10, 0x27: 9, 0x28: 4, 0x30: 11, 0x32: 6, 0x34: 7, 0x36: 7, 0x38: 7}
for kind, head in known.items():
    count, (base, n) = draw(kind=kind)
    assert count == (head == 7), hex(kind)
    if head != 7: continue
    assert n == 15, hex(kind)
    q = bytes(u.mem_read(base, 40))
    pg, su, sv, sw, sh = t['sprites'][t['head_ids'][head]]
    assert (q[12], q[13], q[36], q[37], struct.unpack_from('<H', q, 22)[0]) == (su, sv, su + sw, sv + sh, pg + 1), hex(kind)
    for kwargs in ({'flags': 0}, {'ai': 128}, {'life': 0}):
        assert draw(kind=kind, **kwargs)[0] == 0, (kind, kwargs)
    set_bit(5, 68)
    assert draw(kind=kind, kill=68)[0] == 0, kind
    set_bit(5, 68, False)
for kind in [*range(16), 0x29, 0x2D, 0x2F, 0x35, *range(0x50, 0x58), *range(0x5A, 0x61), 0x67, 0xFF]:
    assert draw(kind=kind)[0] == 0, hex(kind)
# Ordinary live actors must not add duplicates to scoped static encounters.
assert draw(objects=[{'kind': 0x21}] * 32)[0] == 0
assert draw(objects=[{'kind': kind} for kind in known])[0] == 1
# Native projection arithmetic rounds both signs toward zero.
for dx, dz in ((449, -449), (450, -450), (-450, 450), (1800, -900)):
    count, (base, _) = draw(dx=dx, dz=dz)
    assert count == 1
    q = bytes(u.mem_read(base, 40))
    trunc = lambda x: int(x / 450)
    assert struct.unpack_from('<hh', q, 8) == (156 + trunc(dx), 116 - trunc(dz))
for stage, bank in ((0, 5), (2, 6)):
    set_bit(bank, 68)
    assert draw(stage=stage, kill=68)[0] == 0
    set_bit(bank, 68, False)
# Compare cell selection against the real native remapper at all position-dependent branches.
room_gate = bytes(u.mem_read(0x4EB9F0, 6))
u.mem_write(0x4EB9F0, bytes.fromhex('b801000000c3'))
u.ctl_remove_cache(0x4EB9F0, 0x4EB9F6)
proj = dict(mx=10, my=20, wx=0, wz=0)
for stage, room, x, z, flag, adjust in (
        (0, 0x10, 0, 0, None, 0), (1, 0x0F, -8823, 0, None, 0),
        (1, 0x0F, -8822, 0, None, 9501), (3, 0x15, 799, 0, None, 0),
        (3, 0x15, 800, 0, None, -9000), (4, 2, 0, 0, (4, 31, False), 0),
        (4, 2, 0, 0, (4, 31, True), 0), (2, 0x17, 0, -11301, (3, 200, False), 0),
        (2, 0x17, 0, -11300, (3, 200, False), 0), (2, 0x17, 0, -11300, (3, 200, True), 0),
        (5, 7, 0, 0, None, 0)):
    if flag:
        set_bit(*flag)
    u.mem_write(0xA62048, struct.pack('<iii', x, 0, z))
    u.mem_write(projection + 0xF00, bytes([stage, room]))
    u.mem_write(0x20008000, struct.pack('<III', 0x20000100, projection + 0xF00, projection + 0xF01))
    u.reg_write(UC_X86_REG_ESP, 0x20008000)
    u.emu_start(0x4ED650, 0x20000100, count=10000)
    page, idx = bytes(u.mem_read(projection + 0xF00, 2))
    count, (base, _) = draw(stage=stage, room=room, page=page, dx=x, dz=z, cell=idx)
    assert count == 1, (stage, room, page, idx)
    q = bytes(u.mem_read(base, 40))
    assert struct.unpack_from('<hh', q, 8) == (156 + int((x + adjust) / 450), 116 - int(z / 450))
    if flag:
        set_bit(flag[0], flag[1], False)
u.mem_write(0x4EB9F0, bytes.fromhex('b800000000c3'))
u.ctl_remove_cache(0x4EB9F0, 0x4EB9F6)
assert draw()[0] == 0  # native story/floor gate still hides a live actor
u.mem_write(0x4EB9F0, room_gate)
u.ctl_remove_cache(0x4EB9F0, 0x4EB9F6)
# A real, finite R110 encounter survives without a loaded actor; live position wins in that cell.
prospective = [m for m in json.loads((ROOT / 'data/overlay.json').read_text())['markers']
               if m.get('monster') == 'nemesis' and [] not in m['guard']]
assert prospective and all(lit[0] not in (4, 47, 48) for m in prospective for cl in m['guard'] for lit in cl)
static_indices = [i for i, m in enumerate(t['markers']) if m[0] == 8 and m[1:3] == (5, 0) and m[6] == 7]
assert static_indices
for i in static_indices:
    u.mem_write(0x10000000 + offset + i * 14, marker_blob[i * 14:(i + 1) * 14])
assert draw(page=5, stage=0, room=0x10, cell=0, actors=0)[0] == 1
assert draw(page=5, stage=0, room=0x10, cell=0)[0] == 1
set_bit(5, 68)
assert draw(page=5, stage=0, room=0x10, cell=0, actors=0)[0] == 0
set_bit(5, 68, False)
assert draw(page=5, stage=0, room=0x10, cell=0, actors=0, monsters=False)[0] == 0
assert draw(page=5, stage=0, room=0x10, cell=0, actors=0, all_on=False)[0] == 0
visit(5, 0, False)
call('AnnotatedMapTestSet', 1, 1, 0)
call('AnnotatedMapTestDraw', S)
assert call('AnnotatedMapTestCount', 8) == 0
visit(5, 0)
call('AnnotatedMapTestDraw', S)
assert call('AnnotatedMapTestCount', 8) == 1
# The player's death/room flags and the monster toggle are not modified by this reader.
u.mem_write(first, original_table)
u.mem_write(endptr, original_end)
print('live enemies:', checks, 'checks across', len(known), 'native IDs: species UV, visibility, kill, mixed actors and projection OK')
