"""Run the built ASI against the real executable image under Unicorn and compare its primitives with an
independent Python model of the visibility rules. Usage:
  RE3_GAME_EXE='/path/BIOHAZARD(R) 3 PC.exe' python tests/test_native.py
"""
import os, re, struct, sys
from collections import Counter
from pathlib import Path
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_ECX

ROOT = Path(__file__).resolve().parents[1]
EXE = Path(os.environ.get('RE3_GAME_EXE', 'game/BIOHAZARD(R) 3 PC.exe'))
DLL = ROOT / 'build/RE3.AnnotatedMap.asi'
ARGS = dict(GetAsyncKeyState=1, GetTickCount=0, WritePrivateProfileStringA=4, GetPrivateProfileIntA=4,
            GetPrivateProfileStringA=6, CreateFileA=7, WriteFile=5, CloseHandle=1, lstrlenA=1, wsprintfA=-1,
            VirtualProtect=4, FlushInstructionCache=3, GetCurrentProcess=0, GetModuleHandleA=1,
            GetModuleFileNameA=3, DisableThreadLibraryCalls=1, lstrcpyA=2, DeleteFileA=1)


def load(blob, base):
    pe = struct.unpack_from('<I', blob, 60)[0]; o = pe + 24
    pref, size, hdr = struct.unpack_from('<I', blob, o + 28)[0], struct.unpack_from('<I', blob, o + 56)[0], struct.unpack_from('<I', blob, o + 60)[0]
    im = bytearray(size); im[:hdr] = blob[:hdr]
    for i in range(struct.unpack_from('<H', blob, pe + 6)[0]):
        h = o + struct.unpack_from('<H', blob, pe + 20)[0] + i * 40
        vs, rv, rs, raw = struct.unpack_from('<IIII', blob, h + 8); im[rv:rv + rs] = blob[raw:raw + rs]
    rv, z = struct.unpack_from('<II', blob, o + 96 + 5 * 8); p = rv
    while z and p < rv + z:
        page, ln = struct.unpack_from('<II', im, p)
        for j in range(p + 8, p + ln, 2):
            e = struct.unpack_from('<H', im, j)[0]
            if e >> 12 == 3:
                t = page + (e & 4095); struct.pack_into('<I', im, t, (struct.unpack_from('<I', im, t)[0] + base - pref) & 0xFFFFFFFF)
        p += ln
    return im, o


u = Uc(UC_ARCH_X86, UC_MODE_32)
gi, _ = load(EXE.read_bytes(), 0x400000)
u.mem_map(0x400000, (len(gi) + 4095) // 4096 * 4096); u.mem_write(0x400000, bytes(gi))
u.mem_write(0x4EAC60, b'\xC3')          # native map draw is not under test
di, o = load(DLL.read_bytes(), 0x10000000)
u.mem_map(0x25000000, 0x2000)
stub = 0x25000000
imports = {}
p = struct.unpack_from('<I', di, o + 96 + 8)[0]
while struct.unpack_from('<I', di, p + 12)[0]:
    lookup, _, _, _, iat = struct.unpack_from('<5I', di, p); lookup = lookup or iat; i = 0
    while (e := struct.unpack_from('<I', di, lookup + i * 4)[0]):
        name = di[e + 2:di.index(0, e + 2)].decode()
        imports[name] = stub
        n = ARGS[name]
        code = b'\x31\xC0' + (b'\xC3' if n <= 0 else b'\xC2' + struct.pack('<H', 4 * n))
        u.mem_write(stub, code); struct.pack_into('<I', di, iat + i * 4, stub); stub += 8; i += 1
    p += 20
u.mem_map(0x10000000, (len(di) + 4095) // 4096 * 4096); u.mem_write(0x10000000, bytes(di))
rv = struct.unpack_from('<I', di, o + 96)[0]
n, (func, names, ords) = struct.unpack_from('<I', di, rv + 24)[0], struct.unpack_from('<3I', di, rv + 28)
exports = {}
for i in range(n):
    q = struct.unpack_from('<I', di, names + 4 * i)[0]
    exports[di[q:di.index(0, q)].decode()] = 0x10000000 + struct.unpack_from('<I', di, func + struct.unpack_from('<H', di, ords + 2 * i)[0] * 4)[0]
u.mem_map(0x20000000, 0x10000); u.mem_map(0x21000000, 0x40000)

# Fake GPU interface: [0x539C14] -> object -> vtable; slot +0x4C (LoadImage, thiscall 2 args) records uploads.
OBJ, VT, LOAD = 0x21030000, 0x21030100, 0x21030200
u.mem_write(LOAD, b'\xC2\x08\x00'); u.mem_write(OBJ, struct.pack('<I', VT)); u.mem_write(VT + 0x4C, struct.pack('<I', LOAD))
u.mem_write(0x539C14, struct.pack('<I', OBJ))
uploads = []
u.hook_add(UC_HOOK_CODE, lambda uc, addr, size, _: uploads.append(struct.unpack('<4h', uc.mem_read(struct.unpack('<I', uc.mem_read(uc.reg_read(UC_X86_REG_ESP) + 4, 4))[0], 8))), begin=LOAD, end=LOAD)


def call(name, *args):
    u.mem_write(0x20008000, struct.pack('<' + 'I' * (len(args) + 1), 0x20000100, *args))
    u.reg_write(UC_X86_REG_ESP, 0x20008000)
    u.emu_start(exports[name], 0x20000100, count=20_000_000)
    return u.reg_read(UC_X86_REG_EAX)


# ---------- independent model from the generated header
H = (ROOT / 'src/assets.h').read_text()
# Every placed item must have its own artwork instead of a generic ammo/diamond sprite.
import json
item_ids = [int(v) for v in re.search(r'item_icons\[134\] = \{([0-9,]+)\}', H)[1].split(',')]
fallback = {int(re.search(r'#define ICON_' + name + r' (\d+)', H)[1]) for name in ('AMMO', 'DIAMOND')}
placements = json.loads((ROOT / 'data/overlay.json').read_text())['markers']
for marker in placements:
    if marker['kind'] in ('key', 'common', 'lock') and marker['item'] < 134:
        assert item_ids[marker['item']] not in fallback, hex(marker['item'])

def rows(name):
    body = H.split(name, 1)[1].split('= {', 1)[1].split('};', 1)[0]
    return [tuple(int(x) for x in re.findall(r'-?\d+', m)) for m in re.findall(r'\{([-0-9,{} ]+?)\}(?=,|$)', body.replace('{{', '{').replace('}}', '}'))]
markers = [tuple(int(x) for x in m) for m in re.findall(r'\{(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+)\}', H.split('markers[MARKER_COUNT]', 1)[1].split('};', 1)[0])]
literals = [tuple(int(x) for x in m) for m in re.findall(r'\{(\d+),(\d+),(-?\d+)\}', H.split('literals[]', 1)[1].split('};', 1)[0])]
clauses = [tuple(int(x) for x in m) for m in re.findall(r'\{(\d+),(\d+)\}', H.split('clauses[]', 1)[1].split('};', 1)[0])]
rooms = [tuple(int(x) for x in m) for m in re.findall(r'\{(\d+),(\d+),\{(-?\d+),(-?\d+)\},\{(-?\d+),(-?\d+)\},\{(\d+),(\d+)\}\}', H.split('room_labels[ROOM_COUNT]', 1)[1].split('};', 1)[0])]
sprites = [tuple(int(x) for x in m) for m in re.findall(r'\{(\d+),(\d+),(\d+),(\d+),(\d+)\}', H.split('sprites[SPRITE_COUNT]', 1)[1].split('};', 1)[0])]
assert int(re.search(r'MARKER_COUNT (\d+)', H)[1]) == len(markers) > 300
assert int(re.search(r'ROOM_COUNT (\d+)', H)[1]) == len(rooms) > 100
TABLE = 0x52EAAC
bank_addr = [struct.unpack('<I', u.mem_read(TABLE + 4 * b, 4))[0] for b in range(50)]
assert bank_addr[0] == 0xA61CA0 and bank_addr[7] == 0xA67458 and bank_addr[9] == 0xA6751C


def set_bit(bank, bit, on=True):
    a = bank_addr[bank] + 4 * ((bit >> 5) & 7)
    v = struct.unpack('<I', u.mem_read(a, 4))[0]; m = 0x80000000 >> (bit & 31)
    u.mem_write(a, struct.pack('<I', (v | m) if on else (v & ~m)))
def get_bit(bank, bit):
    return bool(struct.unpack('<I', u.mem_read(bank_addr[bank] + 4 * ((bit >> 5) & 7), 4))[0] & (0x80000000 >> (bit & 31)))
def visit(page, idx, on=True):
    a = 0xA6752C + 4 * (page * 2 + (idx >> 5)); v = struct.unpack('<I', u.mem_read(a, 4))[0]; m = 0x80000000 >> (idx & 31)
    u.mem_write(a, struct.pack('<I', (v | m) if on else (v & ~m)))
def visited(page, idx): return bool(struct.unpack('<I', u.mem_read(0xA6752C + 4 * (page * 2 + (idx >> 5)), 4))[0] & (0x80000000 >> (idx & 31)))


S = 0xA3B200            # global status/map work struct (natives read it directly)
OT = 0x21010000
ANCHOR = 0x21011000     # stands in for the native player-arrow insertion point
def setup(page, zoom=100, ox=0, oy=0):
    u.mem_write(S, bytes(0x100))
    u.mem_write(S + 0xAB, bytes([page])); u.mem_write(S + 0xA4, struct.pack('<i', zoom))
    u.mem_write(S + 0x7C, struct.pack('<iiii', ox, oy, 0, 0))
    u.mem_write(OT, struct.pack('<8I', 0, OT, OT + 4, OT + 8, OT + 12, OT + 16, OT + 20, OT + 24))
    u.mem_write(OT + 4, struct.pack('<I', ANCHOR)); u.mem_write(ANCHOR, struct.pack('<I', 0xDEAD0000))
    u.mem_write(0xA5FBC0, struct.pack('<I', OT))


def model(page, scope, korean, toggles=(1,) * 8, aj=False):
    kinds = Counter()
    second = lambda st: st >= 2 and not get_bit(0, 24)
    def shown(pg, idx): return native_room(pg, idx) and (scope >= 3 or visited(pg, idx) or (scope == 2 and bool(struct.unpack('<I', u.mem_read(0xA67574, 4))[0] & (0x80000000 >> pg))))
    def literal(l):
        b, bit, n = l
        if b < 50: return get_bit(b, bit) == n
        v = struct.unpack('<h', u.mem_read(0xA67396 + bit * 2, 2))[0]
        return (v == n, v > n, v >= n, v < n, v <= n, v != n, bool(v & n), not (v & n))[b - 50]
    def guard(m):
        for c0 in range(m[8], m[8] + m[9]):
            first, count = clauses[c0]
            if not any(literal(literals[l]) for l in range(first, first + count)):
                return False
        return True
    if toggles[0] and toggles[1]:
        kinds['room'] = sum(1 for r in rooms if r[0] == page and shown(r[0], r[1]))
    drawn_group = False
    for n, m in enumerate(markers):
        kind, pg, idx, sets, x, y, extra, flag = m[:8]
        if not (n and markers[n - 1][:8] == m[:8]):
            drawn_group = False
        if drawn_group:
            continue
        if pg != page or not (sets & (2 if aj else 1)) or not shown(pg, idx) or not guard(m) or not toggles[0]:
            continue
        st = sets >> 4
        picked = get_bit(8 if second(st) else 7, flag)
        ok = {0: toggles[1], 1: toggles[1], 2: toggles[2] and not get_bit(9, flag), 3: toggles[3] and not picked,
              4: toggles[4] and not picked, 5: toggles[4] and not picked, 6: toggles[5] and not (pg == 4 and idx == 9 and extra == 96 and (struct.unpack('<HH', u.mem_read(0xA673C6, 4)) != (4, 9) or get_bit(4, 26))), 7: toggles[6] and not picked,
              8: toggles[7] and (flag == 255 or not get_bit(6 if second(st) else 5, flag)),
              10: toggles[5] and not (extra == 9 and struct.unpack('<HH', u.mem_read(0xA673C6, 4)) == (4, 13) and (get_bit(4, 5) or (get_bit(4, 4) and get_bit(2, 7)))) and not (extra == 5 and struct.unpack('<HH', u.mem_read(0xA673C6, 4)) == (1, 21) and get_bit(2, 7))}[kind]
        if ok:
            kinds[kind] += 1
            drawn_group = True
    return kinds


def native_room(page, idx):
    u.mem_write(0x20008000, struct.pack('<III', 0x20000100, page, idx)); u.reg_write(UC_X86_REG_ESP, 0x20008000)
    u.emu_start(0x4EB9F0, 0x20000100, count=100000)
    return u.reg_read(UC_X86_REG_EAX) & 0xFF != 0


def run(page, scope=1, korean=1, toggles=(1,) * 8, aj=False):
    call('AnnotatedMapTestSet', 1, scope, korean)
    u.mem_write(0x20000000, struct.pack('<I', 0))
    # apply individual toggles through the exported key handler (edge-triggered)
    for i, t in enumerate(toggles):
        if not t:
            call('AnnotatedMapTestKeys', 1 << i); call('AnnotatedMapTestKeys', 0)
    u.mem_write(0xA67A44, struct.pack('<I', 1 if aj else 0))
    call('AnnotatedMapTestDraw', S)
    got = Counter({k: call('AnnotatedMapTestCount', k) for k in range(9)})
    got['room'] = call('AnnotatedMapTestCount', 9)
    got[10] = call('AnnotatedMapTestCount', 10)
    want = model(page, scope, korean, toggles, aj)
    for k in set(got) | set(want):
        assert got[k] == want[k], (page, scope, toggles, aj, k, got[k], want[k])
    return got


def prims():
    call('AnnotatedMapTestPrims', 0x20000200)
    base = struct.unpack('<I', u.mem_read(0x20000200, 4))[0]
    n = call('AnnotatedMapTestPrims', 0x20000200)
    return base, n


checks = Counter()
# 1. Nothing visited: only the legend, uploaded once (2 atlas pages + CLUT).
setup(0)
run(0)
base, n = prims()
assert n == 14, n            # panel + title + opacity + 8 rows + scope + language + size
pages_n = int(re.search(r'ATLAS_PAGES (\d+)', H)[1])
assert uploads == [(64 + 64 * k, 0, 64, 256) for k in range(pages_n)] + [(0, 0, 16, 1), (0, 1, 16, 1)], uploads
run(0); assert len(uploads) == pages_n + 2   # same session: no re-upload
o0 = call('AnnotatedMapTestOpacity')
call('AnnotatedMapTestKeys', (1 << 12) | (1 << 11)); call('AnnotatedMapTestKeys', 0)   # Shift + '-'
assert call('AnnotatedMapTestOpacity') == o0 - 10 or o0 == 10
run(0); assert uploads[-1] == (0, 1, 16, 1) and len(uploads) == 2 * (pages_n + 2)   # whole atlas re-uploaded
checks['legend+upload'] += 1

# 2. Every page fully visited, both data sets, both languages.
for page in range(7):
    for idx in range(80):
        visit(page, idx)
for page in range(7):
    setup(page)
    for aj in (False, True):
        g = run(page, 1, page & 1, aj=aj)
        checks['page'] += 1
    assert g['room'] > 0

# 3. Chain order: anchor -> our prims in painter order -> previous successor; geometry and texture fields.
import json
bounds = json.loads((ROOT / 'data/map-pages.json').read_text())[0]['bounds']
cx, cy = (bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2
setup(0, zoom=40, ox=-cx * 40 // 100, oy=-cy * 40 // 100); g3 = run(0)
base, n = prims()
labelled = sum(1 for k in (2, 3) for _ in range(g3[k]))   # locks and key items add a name quad
assert n == 14 + sum(g3.values()) + labelled, (n, g3)
assert n > 80, (n, g3)
p = struct.unpack('<I', u.mem_read(ANCHOR, 4))[0] & ~3 & 0xFFFFFFFF
order = []
while p != 0xDEAD0000 and len(order) <= n:
    order.append(p); p = struct.unpack('<I', u.mem_read(p, 4))[0] & ~3 & 0xFFFFFFFF
assert order == [base + 40 * i for i in range(n)], 'OT chain must follow painter order'
for i in range(n):
    b = bytes(u.mem_read(base + 40 * i, 40))
    code, clut, tpage = b[7], struct.unpack_from('<H', b, 14)[0], struct.unpack_from('<H', b, 22)[0]
    x0, y0, x3, y3 = *struct.unpack_from('<hh', b, 8), *struct.unpack_from('<hh', b, 32)
    NAME_FIRST = int(re.search(r'NAME_PAGE_FIRST (\d+)', H)[1])
    assert code in (0x2C, 0x2E) and clut == (64 if tpage - 1 >= NAME_FIRST else 0) and 1 <= tpage <= pages_n and x3 > x0 and y3 > y0
    assert any(s[0] == tpage - 1 and s[1] <= b[12] and b[36] <= s[1] + s[3] and s[2] <= b[13] and b[37] <= s[2] + s[4] for s in sprites), i
def wh(i):
    q = bytes(u.mem_read(base + 40 * i, 40))
    return struct.unpack_from('<h', q, 32)[0] - struct.unpack_from('<h', q, 8)[0], struct.unpack_from('<h', q, 34)[0] - struct.unpack_from('<h', q, 10)[0]
sizes = Counter(w for w, h in map(wh, range(n)) if w == h)   # square prims = icons
assert sizes[4] > 0 and sizes[7] == 0, sizes   # zoom 40 -> clamped 50%: 7px item icons draw at 4px
room_ids = {r[6] for r in rooms} | {r[7] for r in rooms}
for i in range(n):   # names draw at 70% of their sprite size when zoomed out
    q = bytes(u.mem_read(base + 40 * i, 40)); w = struct.unpack_from('<h', q, 32)[0] - struct.unpack_from('<h', q, 8)[0]
    sp = next((sp for k, sp in enumerate(sprites) if k in room_ids and sp[0] == struct.unpack_from('<H', q, 22)[0] - 1 and (sp[1], sp[2]) == (q[12], q[13])), None)
    if sp: assert w == (sp[3] * 70 + 50) // 100, (w, sp)
checks['prims'] += n

# Live enemy tests use these atlas IDs.
head_ids = [int(x) for x in re.search(r'monster_icons\[MONSTER_COUNT\] = \{([0-9,]+)\}', H)[1].split(',')]
assert len(head_ids) == len(set(head_ids)) == 12
# 4. Flags: pickups, difficulty guards, unlocks, kills, data set, toggles, scope.
setup(0)
key = next(m for m in markers if m[1] == 0 and m[0] == 3 and m[9] == 0)
before = run(0)[3]; set_bit(7, key[7]); assert run(0)[3] == before - 1; set_bit(7, key[7], False)
ribbons = [m for m in markers if m[0] == 7 and m[6] == 0x81 and m[1] == 0]
assert ribbons and all(literals[clauses[m[8]][0]][:3] == (0, 23, 0) for m in ribbons)
hard = run(0)[7]; set_bit(0, 23); easy = run(0)[7]; set_bit(0, 23, False)
assert easy < hard
lock = next(m for m in markers if m[0] == 2 and m[1] == 0)
before = run(0)[2]; set_bit(9, lock[7]); assert run(0)[2] < before; set_bit(9, lock[7], False)
setup(2)
off = run(2, toggles=(1, 1, 0, 1, 0, 1, 0, 1)); assert off[2] == off[4] == off[5] == off[7] == 0
none = run(2, toggles=(0, 1, 1, 1, 1, 1, 1, 1)); assert sum(none.values()) == 0
for page in range(7):
    for idx in range(80):
        visit(page, idx, False)
setup(1)
assert run(1, scope=1)['room'] == 0 and run(1, scope=3)['room'] >= 20
# Ordinary enemies do not require a loaded actor: the native slots remain empty.
assert struct.unpack('<I', u.mem_read(0xA6228C, 4))[0] <= 0xA621EC
ordinary = 0
for pg in range(7):
    setup(pg); ordinary += run(pg, scope=3)[8]
assert ordinary > 0
for pg in range(7):
    setup(pg)
    assert run(pg, scope=1)[8] == 0
    u.mem_write(0xA67574, struct.pack('<I', 0x80000000 >> pg))
    assert run(pg, scope=2)[8] == run(pg, scope=3)[8]
u.mem_write(0xA67574, bytes(4))
# Exercise signed comparison boundaries against the independently evaluated CNF model.
variables = sorted({n for b, n, v in literals if b >= 50})
for value in (-32768, -1, 1, 32767):
    for var in variables: u.mem_write(0xA67396 + var * 2, struct.pack('<h', value))
    for pg in range(7):
        setup(pg); run(pg, scope=3)
for var in variables: u.mem_write(0xA67396 + var * 2, bytes(2))
# Killing a scoped spawn suppresses its marker even without a native actor.
for bank in (5, 6):
    u.mem_write(bank_addr[bank], b'\xff' * 32)
killed_total = 0
for pg in range(7):
    setup(pg); killed_total += run(pg, scope=3)[8]
assert killed_total < ordinary  # kill ID 255 placements remain visible
for bank in (5, 6): u.mem_write(bank_addr[bank], bytes(32))
# Exercise cabinet -> safe, inserted-but-unsolved, solved, and post-console valve states in the ASI.
puzzle_bits = [(9, 1), (3, 117), (3, 178), (3, 179), (3, 181), (3, 180), (3, 243), (3, 215), (3, 213)]
for aj in (False, True):
    for phase in ((), ((3, 117), (3, 179), (3, 181), (3, 243), (3, 213)), tuple(puzzle_bits)):
        for bank, bit in puzzle_bits: set_bit(bank, bit, (bank, bit) in phase)
        for pg in (0, 3, 4):
            setup(pg); run(pg, scope=3, aj=aj)
for bank, bit in puzzle_bits: set_bit(bank, bit, False)
checks['puzzle_phases'] += 18
checks['flags'] += 1
# Name size follows RE2: edge-triggered +/-50..150, Shift opacity, key8 scope cycle.
def tap(mask):
    call('AnnotatedMapTestKeys', mask); call('AnnotatedMapTestKeys', 0)
call('AnnotatedMapTestSet', 1, 1, 1)
assert call('AnnotatedMapTestSize') == 100
for expected in (2, 3, 1):
    call('AnnotatedMapTestKeys', 1 << 8)
    assert call('AnnotatedMapTestScope') == expected
    call('AnnotatedMapTestKeys', 1 << 8)
    assert call('AnnotatedMapTestScope') == expected
    call('AnnotatedMapTestKeys', 0)
call('AnnotatedMapTestKeys', 1 << 10); call('AnnotatedMapTestKeys', 1 << 10)
assert call('AnnotatedMapTestSize') == 110 and call('AnnotatedMapTestScope') == 1
call('AnnotatedMapTestKeys', 0)
for _ in range(20): tap(1 << 10)
assert call('AnnotatedMapTestSize') == 150
op = call('AnnotatedMapTestOpacity'); tap((1 << 12) | (1 << 11))
assert call('AnnotatedMapTestSize') == 150 and call('AnnotatedMapTestOpacity') == max(10, op - 10)
for _ in range(20): tap(1 << 11)
assert call('AnnotatedMapTestSize') == 50 and call('AnnotatedMapTestScope') == 1

# Compare original ASI primitives: names resize before placement; icons keep their dimensions.
def geometry(size, lang):
    while call('AnnotatedMapTestSize') < size: tap(1 << 10)
    while call('AnnotatedMapTestSize') > size: tap(1 << 11)
    setup(0, zoom=40, ox=-cx * 40 // 100, oy=-cy * 40 // 100); run(0, scope=3, korean=lang)
    base, count = prims(); names, icons = [], []
    for i in range(count - 14):  # legend is last and changes only its displayed percentage
        q = bytes(u.mem_read(base + 40 * i, 40))
        wh = (struct.unpack_from('<h', q, 32)[0] - struct.unpack_from('<h', q, 8)[0],
              struct.unpack_from('<h', q, 34)[0] - struct.unpack_from('<h', q, 10)[0])
        (names if struct.unpack_from('<H', q, 22)[0] - 1 >= NAME_FIRST else icons).append(wh)
    return names, icons
for lang in (0, 1):
    small, icons = geometry(50, lang)
    large, icons_large = geometry(150, lang)
    assert small and len(small) == len(large) and icons == icons_large, (lang, len(small), len(large), Counter(icons), Counter(icons_large))
    assert all(lw >= sw and lh >= sh for (sw, sh), (lw, lh) in zip(small, large))
    assert any(lw > sw for (sw, sh), (lw, lh) in zip(small, large))
geometry(100, 1)

# Execute actual load/save functions with in-memory Win32 INI APIs.
profile, saved = {}, {}
def cstring(ptr):
    out = bytearray()
    while (b := u.mem_read(ptr + len(out), 1)) != b'\0': out.extend(b)
    return out.decode()
def ini_api(uc, addr, length, name):
    argc = 3 if name == 'wsprintfA' else ARGS[name]
    args = struct.unpack('<' + 'I' * argc, uc.mem_read(uc.reg_read(UC_X86_REG_ESP) + 4, 4 * argc))
    value = 1
    if name == 'GetPrivateProfileIntA': value = int(profile.get(cstring(args[1]), args[2])) & 0xffffffff
    elif name == 'GetPrivateProfileStringA':
        text = profile.get(cstring(args[1]), cstring(args[2])).encode()[:args[4] - 1]
        uc.mem_write(args[3], text + b'\0'); value = len(text)
    elif name == 'WritePrivateProfileStringA': saved[cstring(args[1])] = cstring(args[2])
    else:
        fmt = cstring(args[1]); count = len(re.findall(r'%(?:[0-9]+)?[dux]', fmt))
        values = struct.unpack('<' + 'I' * count, uc.mem_read(uc.reg_read(UC_X86_REG_ESP) + 12, 4 * count))
        text = (fmt % values).encode(); uc.mem_write(args[0], text + b'\0'); value = len(text)
    uc.reg_write(UC_X86_REG_EAX, value)
for api in ('GetPrivateProfileIntA', 'GetPrivateProfileStringA', 'WritePrivateProfileStringA', 'wsprintfA'):
    u.mem_write(imports[api], b'\x90\x90')  # preserve mock return value instead of xor eax,eax
    u.hook_add(UC_HOOK_CODE, ini_api, user_data=api, begin=imports[api], end=imports[api])
for value, expected in [(-1, 50), (54, 50), (55, 60), (100, 100), (146, 150), (999, 150)]:
    profile['NameSize'] = value; call('AnnotatedMapTestLoadSettings')
    assert call('AnnotatedMapTestSize') == expected
profile.clear(); call('AnnotatedMapTestLoadSettings')
assert call('AnnotatedMapTestSize') == 100
for _ in range(5): tap(1 << 10)
tap(1 << 8)
assert saved['NameSize'] == '150' and saved['Scope'] == '2' and saved['NameOpacity'] == '70', saved
profile.update(saved); call('AnnotatedMapTestLoadSettings')
assert call('AnnotatedMapTestSize') == 150 and call('AnnotatedMapTestScope') == 2
profile.clear(); call('AnnotatedMapTestLoadSettings')
checks['name_controls'] += 1
print(dict(checks), 'OK')

# Optional visual check: PREVIEW=dir renders the emulator's own primitives over the decoded map shapes,
# using each page's default view (zoom 100, pan origin from the projection header) and every floor.
if os.environ.get('PREVIEW'):
    from PIL import Image
    out = Path(os.environ['PREVIEW']); out.mkdir(parents=True, exist_ok=True)
    pages = json.loads((ROOT / 'data/map-pages.json').read_text())
    mapdata = (ROOT / 'local/extracted/DATA_J/ETC2/MAP_J.MAP').read_bytes()
    atlas = [Image.open(ROOT / f'build/atlas-preview/page{k}-hd.png') for k in range(int(re.search(r'ATLAS_PAGES (\d+)', H)[1]))]
    K = 4
    for page in range(7):
        seg = mapdata[pages[page]['offset']:]; b = pages[page]['header'][3]
        ox, oy, has_floors, floors = struct.unpack_from('<hhBB', seg, b + struct.unpack_from('<I', seg, b + 4)[0])
        for idx in range(80):
            visit(page, idx)
        for floor in range(max(1, floors)):
            for lang in (0, 1):
                setup(page, 100, ox, oy)
                u.mem_write(S + 0x94, struct.pack('<ii', ox, oy)); u.mem_write(S + 0xAD, bytes([has_floors, floor]))
                run(page, 1, lang, toggles=(1, 1, 1, 1, 1, 1, 1, 1))
                base, n = prims()
                canvas = Image.new('RGBA', (320 * K, 240 * K), (8, 10, 12, 255))
                tim = Image.open(ROOT / f'local/map-preview/page{page}-tim.png')
                for r in pages[page]['rooms']:
                    if not native_room(page, r['index']): continue
                    for u0, v0, u1, v1, x, y, *_ in r['parts']:
                        if u1 < u0 or v1 < v0: continue
                        canvas.alpha_composite(tim.crop((u0, v0, u1 + 1, v1 + 1)).resize(((u1 - u0 + 1) * K, (v1 - v0 + 1) * K), Image.NEAREST),
                                               ((x + ox + 160) * K, (y + oy + 120) * K)) if x + ox + 160 >= 0 and y + oy + 120 >= 0 else None
                for i in range(n):
                    q = bytes(u.mem_read(base + 40 * i, 40))
                    x0, y0 = struct.unpack_from('<hh', q, 8); x3, y3 = struct.unpack_from('<hh', q, 32)
                    u0, v0, u3, v3, tp = q[12], q[13], q[36], q[37], struct.unpack_from('<H', q, 22)[0] - 1
                    src = atlas[tp].crop((u0 * 4, v0 * 4, u3 * 4, v3 * 4)).resize(((x3 - x0) * K, (y3 - y0) * K), Image.LANCZOS)
                    if x0 >= 0 and y0 >= 0: canvas.alpha_composite(src, (x0 * K, y0 * K))
                canvas.save(out / f'page{page}-f{floor}-{"ko" if lang else "en"}.png')
    print('preview written to', out)
