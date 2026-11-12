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
            GetModuleFileNameA=3, DisableThreadLibraryCalls=1, lstrcpyA=2, lstrcmpiA=2, DeleteFileA=1, MoveFileExA=3, CopyFileA=3)


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


# GetTickCount returns tick[0]; every key event is TICK_STEP ms after the previous one (past the debounce).
tick, TICK_STEP = [1000], [400]
u.mem_write(imports['GetTickCount'], b'\x90\x90')
u.hook_add(UC_HOOK_CODE, lambda uc, a, n, _: uc.reg_write(UC_X86_REG_EAX, tick[0]), begin=imports['GetTickCount'], end=imports['GetTickCount'])


def call(name, *args):
    if name == 'AnnotatedMapTestKeys': tick[0] += TICK_STEP[0]
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
# RoomLabel: page, idx, lead[2], x2[2], y2[2], label[2], line[2][4]
rooms = [(int(m[0]), int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]), int(m[6]), int(m[7]), int(m[8]), int(m[9]),
          tuple(int(v) for v in m[10].split(',')), tuple(int(v) for v in m[11].split(',')))
         for m in re.findall(r'\{(\d+),(\d+),\{(\d),(\d)\},\{(-?\d+),(-?\d+)\},\{(-?\d+),(-?\d+)\},\{(\d+),(\d+)\},\{\{([-\d,]+)\},\{([-\d,]+)\}\}\}', H.split('room_labels[ROOM_COUNT]', 1)[1].split('};', 1)[0])]
sprites = [tuple(int(x) for x in m) for m in re.findall(r'\{(\d+),(\d+),(\d+),(\d+),(\d+)\}', H.split('sprites[SPRITE_COUNT]', 1)[1].split('};', 1)[0])]
assert int(re.search(r'MARKER_COUNT (\d+)', H)[1]) == len(markers) > 300
assert int(re.search(r'ROOM_COUNT (\d+)', H)[1]) == len(rooms) > 100
ROOM_NAMED = int(re.search(r'ROOM_NAMED_COUNT (\d+)', H)[1])   # area names (data/sd-extra-names.json) come after the rooms
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


def model(page, scope, korean, toggles=(1,) * 9, aj=False):
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
        kinds['room'] = sum(1 for r in rooms[:ROOM_NAMED] if r[0] == page and shown(r[0], r[1]))
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
              4: toggles[4] and not picked, 5: toggles[4] and not picked, 6: toggles[5] and not (pg == 4 and idx == 9 and extra == 96 and (struct.unpack('<HH', u.mem_read(0xA673C6, 4)) != (4, 9) or get_bit(4, 26))), 7: toggles[7] and not picked,
              8: toggles[8] and (flag == 255 or not get_bit(6 if second(st) else 5, flag)),
              10: toggles[6] and not (extra == 9 and struct.unpack('<HH', u.mem_read(0xA673C6, 4)) == (4, 13) and (get_bit(4, 5) or (get_bit(4, 4) and get_bit(2, 7)))) and not (extra == 5 and struct.unpack('<HH', u.mem_read(0xA673C6, 4)) == (1, 21) and get_bit(2, 7))}[kind]
        if ok:
            kinds[kind] += 1
            drawn_group = True
    return kinds


def native_room(page, idx):
    u.mem_write(0x20008000, struct.pack('<III', 0x20000100, page, idx)); u.reg_write(UC_X86_REG_ESP, 0x20008000)
    u.emu_start(0x4EB9F0, 0x20000100, count=100000)
    return u.reg_read(UC_X86_REG_EAX) & 0xFF != 0


def run(page, scope=1, korean=1, toggles=(1,) * 9, aj=False):
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
    elif name == 'WritePrivateProfileStringA':
        if args[1]: saved[cstring(args[1])] = cstring(args[2]); written_to.add(args[3])
        else: flushes.append(args[3])
    elif name == 'MoveFileExA': moves.append((args[0], args[1], args[2])); value = move_result[0]
    elif name == 'DeleteFileA': deletes.append(args[0])
    elif name == 'CopyFileA': copies.append(args)
    else:
        fmt = cstring(args[1]); count = len(re.findall(r'%(?:[0-9]+)?[dux]', fmt))
        values = struct.unpack('<' + 'I' * count, uc.mem_read(uc.reg_read(UC_X86_REG_ESP) + 12, 4 * count))
        text = (fmt % values).encode(); uc.mem_write(args[0], text + b'\0'); value = len(text)
    uc.reg_write(UC_X86_REG_EAX, value)
written_to, flushes, moves, deletes, move_result, copies = set(), [], [], [], [1], []
for api in ('GetPrivateProfileIntA', 'GetPrivateProfileStringA', 'WritePrivateProfileStringA', 'wsprintfA', 'MoveFileExA', 'DeleteFileA', 'CopyFileA'):
    u.mem_write(imports[api], b'\x90\x90')  # preserve mock return value instead of xor eax,eax
    u.hook_add(UC_HOOK_CODE, ini_api, user_data=api, begin=imports[api], end=imports[api])
checks = Counter()
call('AnnotatedMapTestSdMode', 0)   # HD checks first (no config.ini here would otherwise mean SD)
# 1. Nothing visited: only the legend, uploaded once (2 atlas pages + CLUT).
setup(0)
run(0)
base, n = prims()
LEGEND_N, READOUT_N = 15, 9   # legend panel, title, [~] hint, rows [0]..[8], then [H], [9], [\\]; then the readout panel and 4 x (hint, value)
assert n == LEGEND_N + READOUT_N, n
# Legend (user 2026-11-08, RE0 two columns): [0]..[4] then [H] item names | [5]..[8] then [9] scope and [\\] language; the panel never
# resizes with scope, and all columns stay inside it. Whole block drawn at 90% from its bottom-left corner (user, candidate
# 4); readouts on its right, bottom-aligned with the legend's last four lines; the [~] hint on the title's line.
box = lambda b: (*struct.unpack_from('<hh', b, 8), *struct.unpack_from('<hh', b, 32))
SPR = [tuple(int(x) for x in m) for m in re.findall(r'\{(\d+),(\d+),(\d+),(\d+),(\d+)\}', H.split('sprites[SPRITE_COUNT]', 1)[1].split('};', 1)[0])]
def sprite_of(b):
    pg, u0, v0 = struct.unpack_from('<H', b, 22)[0] - 1, b[12], b[13]
    return next(sp for sp in SPR if sp[:3] == (pg, u0, v0))
def panels():
    base, n = prims()
    q = [bytes(u.mem_read(base + 40 * i, 40)) for i in range(n)]
    return q, n
for ko in (0, 1):
    widths = []
    for sc in (1, 2, 3):
        run(0, scope=sc, korean=ko); q, n = panels()
        leg, ro_panel, ro = q[n - LEGEND_N - READOUT_N:n - READOUT_N], q[n - READOUT_N], q[n - READOUT_N + 1:]
        panel, rows = box(leg[0]), [box(b) for b in leg[3:12]]
        names_row, scope_row, lang_row = box(leg[12]), box(leg[13]), box(leg[14])
        left, right = rows[:5], rows[5:]
        assert {r[0] for r in left} == {6 * 90 // 100 + 1} and len({r[0] for r in right}) == 1, rows
        assert right[0][0] > max(r[2] for r in left + [names_row]), (rows, names_row)
        assert names_row[0] == left[0][0] and scope_row[0] == lang_row[0] == right[0][0], (names_row, scope_row, lang_row)
        assert [r[1] for r in left[:4]] == [r[1] for r in right] and scope_row[1] == left[4][1], (rows, scope_row)   # [9] under [8], level with [4]
        assert all(6 <= left[k + 1][1] - left[k][1] <= 7 for k in range(4)), rows
        assert names_row[1] == lang_row[1] and 6 <= names_row[1] - left[4][1] <= 7 and 6 <= lang_row[1] - scope_row[1] <= 7, (names_row, lang_row)   # [H] under [4], [\\] under [9]
        assert names_row[3] - names_row[1] == lang_row[3] - lang_row[1] or abs((names_row[3] - names_row[1]) - (lang_row[3] - lang_row[1])) <= 1, (names_row, lang_row)   # same size
        # 90%: every text quad is its sprite scaled by 0.9 (+-1 px rounding); the panel's top is 0.9 of its full height
        for b in leg[1:] + ro:
            sp, bx = sprite_of(b), box(b)
            assert abs((bx[2] - bx[0]) - sp[3] * .9) <= 1 and abs((bx[3] - bx[1]) - sp[4] * .9) <= 1, (sp, bx)
        # Equal body frames must stay equal after the actual x86 lquad rounding, at EVERY row.
        body_quads = leg[3:] + ro
        assert {box(b)[3] - box(b)[1] for b in body_quads} == {6}, [box(b) for b in body_quads]
        title_h = SPR[int(re.findall(r'\d+', H.split('legend_title[2] = {', 1)[1])[ko])][4]
        full_top = (240 - 4 - 6 * 7) - title_h - 4
        assert panel[0] == 3 and panel[3] == 239 and abs((239 - panel[1]) - (239 - full_top) * .9) <= 1, (panel, full_top)
        assert all(panel[0] <= b[0] and b[2] <= panel[2] and panel[1] <= b[1] and b[3] <= panel[3] for b in map(box, leg[1:])), (panel, rows)
        hint_h = names_row
        widths.append(panel[2] - panel[0])
        hints, vals = [box(b) for b in ro[0::2]], [box(b) for b in ro[1::2]]
        rp = box(ro_panel)   # the readouts' own panel: beside the legend, starting at its first row (no empty band above 'Name opacity')
        assert rp[0] == panel[2] and rp[3] == panel[3] and 0 <= hints[0][1] - rp[1] <= 4 and rp[1] > panel[1], (rp, panel, hints[0])
        title, hide = box(leg[1]), box(leg[2])
        assert left[0][1] - title[3] <= 2, (title, left[0])   # title line close above the rows (user, candidate 2)
        assert hide[1] == title[1] and hide[3] == title[3], (title, hide)   # [~] hint on the title's line, ko and en
        assert min(h[0] for h in hints) > max(r[2] for r in right + [scope_row, lang_row]) and len({v[2] for v in vals}) == 1, (hints, vals)
        assert [h[1] for h in hints] == [left[2][1], left[3][1], left[4][1], hint_h[1]], (hints, left, hint_h)   # bottom-aligned with the last legend row
        assert all(rp[0] <= b[0] and b[2] <= rp[2] - 2 and rp[1] <= b[1] and b[3] <= rp[3] for b in hints + vals), (rp, hints, vals)
    assert len(set(widths)) == 1, widths
call('AnnotatedMapTestSet', 1, 1, 1)
pages_n = int(re.search(r'ATLAS_PAGES (\d+)', H)[1])
CLUTS = [(0, 0, 16, 1), (0, 1, 16, 1), (0, 2, 16, 1)]
assert uploads == [(64 + 64 * k, 0, 64, 256) for k in range(pages_n)] + CLUTS, uploads
run(0); assert len(uploads) == pages_n + 3   # same session: no re-upload
o0 = call('AnnotatedMapTestOpacity')
call('AnnotatedMapTestKeys', 1 << 13); call('AnnotatedMapTestKeys', 0)   # '['
assert call('AnnotatedMapTestOpacity') == o0 - 10 or o0 == 10
run(0); assert uploads[-3:] == CLUTS and len(uploads) == 2 * (pages_n + 3)   # whole atlas re-uploaded
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
# Item names are off by default: room names (and their leaders) and the marks that are on screen, not covered.
assert n <= LEGEND_N + READOUT_N + sum(g3.values()) + g3['room'], (n, g3)
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
    assert code in (0x2C, 0x2E) and clut in ((64,) if tpage - 1 >= NAME_FIRST else (0, 128)) and 1 <= tpage <= pages_n and x3 > x0 and y3 > y0
    assert any(s[0] == tpage - 1 and s[1] <= b[12] and b[36] <= s[1] + s[3] and s[2] <= b[13] and b[37] <= s[2] + s[4] for s in sprites), i
def wh(i):
    q = bytes(u.mem_read(base + 40 * i, 40))
    return struct.unpack_from('<h', q, 32)[0] - struct.unpack_from('<h', q, 8)[0], struct.unpack_from('<h', q, 34)[0] - struct.unpack_from('<h', q, 10)[0]
sizes = Counter(w for w, h in map(wh, range(n)) if w == h)   # square prims = icons
assert sizes[4] > 0 and sizes[7] == 0, sizes   # zoom 40 -> clamped 50%: 7px item icons draw at 4px
room_ids = {r[8] for r in rooms} | {r[9] for r in rooms}
for i in range(n):   # names draw at 70% of their sprite size when zoomed out
    q = bytes(u.mem_read(base + 40 * i, 40)); w = struct.unpack_from('<h', q, 32)[0] - struct.unpack_from('<h', q, 8)[0]
    sp = next((sp for k, sp in enumerate(sprites) if k in room_ids and sp[0] == struct.unpack_from('<H', q, 22)[0] - 1 and (sp[1], sp[2]) == (q[12], q[13])), None)
    if sp: assert w == (((sp[3] * 80 + 50) // 100) * 70 + 50) // 100, (w, sp)   # name size 100 = the old 80%
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
off = run(2, toggles=(1, 1, 0, 1, 0, 1, 1, 0, 1)); assert off[2] == off[4] == off[5] == off[7] == 0
none = run(2, toggles=(0, 1, 1, 1, 1, 1, 1, 1, 1)); assert sum(none.values()) == 0
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
# Name size: edge-triggered 50..200 (100 = the old 80%), Shift opacity, key 9 scope cycle, key \\ language.
def tap(mask):
    call('AnnotatedMapTestKeys', mask); call('AnnotatedMapTestKeys', 0)
call('AnnotatedMapTestSet', 1, 1, 1)
assert call('AnnotatedMapTestSize') == 100
for expected in (2, 3, 1):
    call('AnnotatedMapTestKeys', 1 << 9)
    assert call('AnnotatedMapTestScope') == expected
    call('AnnotatedMapTestKeys', 1 << 9)
    assert call('AnnotatedMapTestScope') == expected
    call('AnnotatedMapTestKeys', 0)
call('AnnotatedMapTestKeys', 1 << 10); call('AnnotatedMapTestKeys', 1 << 10)
assert call('AnnotatedMapTestSize') == 110 and call('AnnotatedMapTestScope') == 1
call('AnnotatedMapTestKeys', 0)
for _ in range(20): tap(1 << 10)
assert call('AnnotatedMapTestSize') == 200
op = call('AnnotatedMapTestOpacity'); tap(1 << 13)
assert call('AnnotatedMapTestSize') == 200 and call('AnnotatedMapTestOpacity') == max(10, op - 10)
for _ in range(25): tap(1 << 11)
assert call('AnnotatedMapTestSize') == 50 and call('AnnotatedMapTestScope') == 1

# Compare original ASI primitives: names resize before placement; icons keep their dimensions.
def geometry(size, lang):
    while call('AnnotatedMapTestSize') < size: tap(1 << 10)
    while call('AnnotatedMapTestSize') > size: tap(1 << 11)
    # Legend folded (panel + one line): an unfolded legend hides the room names that grow into it.
    setup(0, zoom=40, ox=-cx * 40 // 100, oy=-cy * 40 // 100); call('AnnotatedMapTestOptions', 0, 0, 0); run(0, scope=3, korean=lang)
    call('AnnotatedMapTestOptions', 0, 1, 0)
    base, count = prims(); names, icons = [], []
    for i in range(count - 2):  # the folded legend is last
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

for value, expected in [(-1, 50), (54, 50), (55, 60), (100, 100), (196, 200), (999, 200)]:
    profile['Version'] = 4; profile['NameSize'] = value; call('AnnotatedMapTestLoadSettings')
    assert call('AnnotatedMapTestSize') == expected
profile.clear(); call('AnnotatedMapTestLoadSettings')
assert call('AnnotatedMapTestSize') == 100
for _ in range(5): tap(1 << 10)
tap(1 << 9)
assert saved['NameSize'] == '150' and saved['Scope'] == '2' and saved['NameOpacity'] == '70', saved
profile.update(saved); call('AnnotatedMapTestLoadSettings')
assert call('AnnotatedMapTestSize') == 150 and call('AnnotatedMapTestScope') == 2
profile.clear(); call('AnnotatedMapTestLoadSettings')
# Version: an older file is written once with Version=4 and its values kept (sizes re-based, see below); a version-4 file is not.
saved.clear(); moves.clear()
profile.update(NameSize=120, NameOpacity=40, Scope=3, Language='ko'); call('AnnotatedMapTestLoadSettings')
assert saved['Version'] == '4' and saved['NameSize'] == '150' and saved['NameOpacity'] == '40' and saved['Scope'] == '3', saved
assert saved['ItemNames'] == '0' and saved['IconSize'] == '100' and saved['IconOpacity'] == '100' and saved['Legend'] == '1', saved
assert saved['Modifier'] == 'Shift' and saved['LockMarker'] == 'Door' and len(moves) == 1, (saved, moves)
profile.update(saved); saved.clear(); moves.clear(); call('AnnotatedMapTestLoadSettings')
assert not saved and not moves and call('AnnotatedMapTestSize') == 150
# Atomic save: every key goes to one temporary file, flushed, then moved over the INI (replace + write through).
written_to.clear(); flushes.clear(); tap(1 << 15)
tmp = written_to.pop(); assert not written_to and flushes == [tmp] and moves[-1][0] == tmp and moves[-1][2] == 9, (tmp, flushes, moves)
assert cstring(tmp).endswith('.ini.tmp') or cstring(tmp) == '', cstring(tmp)
deletes.clear(); move_result[0] = 0; tap(1 << 15); move_result[0] = 1
assert deletes[-1] == tmp, deletes   # a failed replace removes the temporary file and keeps the old INI
assert copies and copies[-1][1] == tmp and copies[-1][2] == 0, copies   # the save starts from a copy of the current INI (comments survive)
# The shipped packaging/RE3.AnnotatedMap.ini: read as the mod reads it, it equals the built-in defaults, is already
# Version 4 (no migration write), and lists exactly the keys the mod saves.
import configparser
cp = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=None); cp.optionxform = str
cp.read(ROOT / 'packaging/RE3.AnnotatedMap.ini', encoding='utf-8')
shipped, before = dict(cp['AnnotatedMap']), dict(profile)
profile.clear(); profile.update(shipped); saved.clear(); moves.clear(); call('AnnotatedMapTestLoadSettings')
assert not saved and not moves, (saved, moves)   # Version=4: loaded as is
assert [call('AnnotatedMapTestSetting', k) for k in range(8)] == [100, 70, 100, 100, 0, 1, 0, 0]
assert [call('AnnotatedMapTestScope')] == [1]
profile.clear(); call('AnnotatedMapTestLoadSettings'); tap(1 << 15); tap(1 << 15); tap(1 << 15)   # full cycle back to the default
assert set(shipped) == set(saved) and all(shipped[k] == saved[k] for k in saved), (set(shipped) ^ set(saved), shipped, saved)   # same keys and values as the defaults the mod writes
profile.clear(); profile.update(before); call('AnnotatedMapTestLoadSettings')
# REbirth's HDTextures switch is read from config.ini [DLL] for the log hint (blurry map text when it is 0 or missing).
profile.clear(); assert call('AnnotatedMapTestHdTextures') == 0xFFFFFFFF   # not found: -1
profile['HDTextures'] = 1; assert call('AnnotatedMapTestHdTextures') == 1
profile['HDTextures'] = 0; assert call('AnnotatedMapTestHdTextures') == 0
# Auto picks HD only with REbirth loaded, HDTextures=1 and no retro/low-res mode (user 2026-11-13); no REbirth is SD.
assert call('AnnotatedMapTestSdAuto', 1, 1, 0, 0) == 0
for args in ((0, 1, 0, 0), (1, 0, 0, 0), (1, 0xFFFFFFFF, 0, 0), (1, 1, 1, 0), (1, 1, 0, 1), (0, 0xFFFFFFFF, 0, 0)):
    assert call('AnnotatedMapTestSdAuto', *args) == 1, args
profile.clear(); profile.update(before)
# Modifier and lock side come from the INI; out-of-range values are clamped.
profile.update(Modifier='Ctrl', LockMarker='Unvisited', IconSize=999, IconOpacity=0, ItemNames=1, Legend=0); call('AnnotatedMapTestLoadSettings')
assert [call('AnnotatedMapTestSetting', k) for k in range(8)] == [150, 40, 200, 10, 1, 0, 1, 1], [call('AnnotatedMapTestSetting', k) for k in range(8)]
profile.clear(); call('AnnotatedMapTestLoadSettings')
assert [call('AnnotatedMapTestSetting', k) for k in range(8)] == [100, 70, 100, 100, 0, 1, 0, 0]
checks['name_controls'] += 1
# Keys (RE0 layout, modifier = bit 12): - + name size, [ ] name opacity, modifier + those for icons, H, ~.
def setting(k): return call('AnnotatedMapTestSetting', k)
tap(1 << 10); assert setting(0) == 110 and setting(2) == 100
tap(1 << 14); assert setting(1) == 80 and setting(3) == 100
call('AnnotatedMapTestKeys', 1 << 12); tap((1 << 12) | (1 << 10)); assert setting(2) == 110 and setting(0) == 110
tap((1 << 12) | (1 << 13)); assert setting(3) == 90 and setting(1) == 80
for _ in range(15): tap((1 << 12) | (1 << 10))
assert setting(2) == 200
for _ in range(15): tap((1 << 12) | (1 << 13))
assert setting(3) == 10
tap(1 << 12)   # modifier alone changes nothing
assert [setting(k) for k in range(4)] == [110, 80, 200, 10]
# H cycles hidden -> all (1) -> all except common (2) -> hidden (0), saved as ItemNames=0/1/2.
assert setting(4) == 0
for want in (1, 2, 0, 1):
    saved.clear(); tap(1 << 15); assert setting(4) == want and saved['ItemNames'] == str(want), (want, saved)
tap(1 << 15); tap(1 << 15); assert setting(4) == 0
# Migration from the old on/off item names: old on (1) -> all, old off (0 or missing) -> hidden, a stray larger value
# in an old file counts as on; version 2 files are rewritten once as version 3; version 3 keeps 2 (no common).
for old_version, value, want in ((2, 1, 1), (2, 0, 0), (0, 1, 1), (2, 7, 1), (3, 2, 2), (3, 1, 1), (4, 2, 2), (4, 1, 1), (4, 0, 0), (4, 9, 0)):
    profile.clear(); saved.clear(); moves.clear()
    profile.update(Version=old_version, ItemNames=value); call('AnnotatedMapTestLoadSettings')
    assert setting(4) == want, (old_version, value, setting(4), want)
    assert (saved.get('Version') == '4') == (old_version < 4) and (not moves) == (old_version >= 4), (old_version, saved, moves)
    if old_version < 4: assert saved['ItemNames'] == str(want), saved
# Version 4 migration (user 2026-11-08): NameSize s -> s / 0.8 and IconSize s -> s / 1.3 (rounded to 10) so names and item icons
# keep their size; Events starts as the old Puzzles value (live selections were puzzles); a missing key and a version-4 file
# are left alone.
for old_name in range(50, 161, 10):
    profile.clear(); saved.clear(); profile.update(Version=3, NameSize=old_name, IconSize=old_name); call('AnnotatedMapTestLoadSettings')
    want_n = min(200, max(50, (old_name * 100 + 400) // 800 * 10)); want_i = min(200, max(50, (old_name * 100 + 650) // 1300 * 10))
    assert saved['NameSize'] == str(want_n) and saved['IconSize'] == str(want_i), (old_name, saved)
    assert abs(want_n * .8 - old_name) <= 4 or want_n in (50, 200), (old_name, want_n)   # same visible name size, within one step
    assert abs(want_i * 1.3 - old_name) <= 6.5 or want_i in (50, 200), (old_name, want_i)
for old, new_name, new_icon in ((100, 130, 80), (80, 100, 60), (130, 160, 100)):
    profile.clear(); saved.clear(); profile.update(Version=3, NameSize=old, IconSize=old); call('AnnotatedMapTestLoadSettings')
    assert (saved['NameSize'], saved['IconSize']) == (str(new_name), str(new_icon)), (old, saved)
profile.clear(); saved.clear(); profile.update(Version=4, NameSize=100, IconSize=100); call('AnnotatedMapTestLoadSettings')
assert not saved and call('AnnotatedMapTestSize') == 100   # already version 4: not converted again
profile.clear(); saved.clear(); call('AnnotatedMapTestLoadSettings')
assert saved['NameSize'] == '100' and saved['IconSize'] == '100' and saved['Version'] == '4', saved   # a new install keeps the defaults
profile.clear(); saved.clear(); profile.update(Version=3, Puzzles=1); call('AnnotatedMapTestLoadSettings')
assert saved['Events'] == '1' and saved['Puzzles'] == '1', saved
profile.clear(); saved.clear(); profile.update(Version=4, Puzzles=1, Events=0); call('AnnotatedMapTestLoadSettings')
assert not saved and call('AnnotatedMapTestSetting', 0) == 100
profile.clear(); call('AnnotatedMapTestLoadSettings')
# Keys: 0..8 toggle the legend rows (6 = Events), 9 cycles the scope, \ (VK_OEM_5) switches the language and nothing else.
profile.clear(); call('AnnotatedMapTestLoadSettings'); saved.clear()
for bit, key in ((1, 'Rooms'), (2, 'Locks'), (3, 'KeyItems'), (4, 'Documents'), (5, 'Puzzles'), (6, 'Events'), (7, 'CommonItems'), (8, 'Monsters')):
    saved.clear(); tap(1 << bit); first = saved[key]; tap(1 << bit); assert saved[key] != first and saved['Language'] == 'en', (bit, key, saved)
saved.clear(); tap(1 << 17); assert saved['Language'] == 'ko' and saved['Scope'] == '1', saved
tap(1 << 17); assert saved['Language'] == 'en'
saved.clear(); tap(1 << 9); assert saved['Scope'] == '2' and saved['Language'] == 'en', saved
profile.clear(); call('AnnotatedMapTestLoadSettings')
tap(1 << 16); assert setting(5) == 0; tap(1 << 16); assert setting(5) == 1
# Debounce: a second press of the same key within 350 ms is ignored, a later one counts.
TICK_STEP[0] = 100; ko = setting(4); tap(1 << 15); tap(1 << 15); assert setting(4) == (ko + 1) % 3
TICK_STEP[0] = 400; tap(1 << 15); assert setting(4) == (ko + 2) % 3
profile.clear(); call('AnnotatedMapTestLoadSettings')
checks['keys+ini'] += 1
# SD mode (HDTextures=0, user 2026-11-12): SD atlas, SD legend (title, [~], 9 rows, [9], [\\] on one panel), no readouts;
# every mark is a 1x SD sprite (side 9, enemies 5) and room names come with their leaders.
call('AnnotatedMapTestSdMode', 1)
setup(0); run(0); base, n = prims()
assert n == 1 + 2 + 9 + 2, n
SDH = (ROOT / 'src/sd_assets.h').read_text()
assert 'SD_ROOM_COUNT' in SDH
for page in range(7):
    setup(page)
    got = run(page, scope=3, toggles=[1] * 9)
    base, n = prims()
    assert 0 < n < 1400, (page, n)
    for i in range(n):
        b = u.mem_read(base + 40 * i, 40)
        xs = [struct.unpack_from('<h', b, o)[0] for o in (8, 16, 24, 32)]; ys = [struct.unpack_from('<h', b, o)[0] for o in (10, 18, 26, 34)]
        assert max(xs) >= 0 and min(xs) < 320 and max(ys) >= 0 and min(ys) < 240, (page, i, xs, ys)   # nothing wholly off screen
checks['sd'] += 1
call('AnnotatedMapTestSdMode', 0)
print(dict(checks), 'OK')

# Render every submitted legend state from the shipped HD/SD atlases, using x86-produced geometry.
from PIL import Image, ImageDraw
seen = {}
setup(0)
for ko in (0, 1):
    for modifier in ('Shift', 'Ctrl'):
        for value in range(10, 201, 10):
            profile.clear()
            profile.update(Version=4, NameSize=value, IconSize=value, NameOpacity=value,
                           IconOpacity=value, Modifier=modifier)
            call('AnnotatedMapTestLoadSettings')
            for state in range(3):
                call('AnnotatedMapTestOptions', state, 1, 0)
                run(0, scope=state + 1, korean=ko, toggles=(value % 20 == 0,) * 9)
                qs, n = panels()
                text = qs[-LEGEND_N-READOUT_N+1:-READOUT_N] + qs[-READOUT_N+1:]
                assert {box(b)[3]-box(b)[1] for b in text[2:]} == {6}
                for b in text:
                    seen[sprite_of(b)] = box(b)
            call('AnnotatedMapTestOptions', 0, 0, 0)
            run(0, korean=ko)
            qs, n = panels(); seen[sprite_of(qs[-1])] = box(qs[-1])
expected_ids = set()
for table in ('legend_sprites', 'legend_scope', 'legend_lang', 'legend_title', 'hint_hide',
              'hint_fold', 'hint_names', 'readout_hints', 'value_sprites'):
    declaration = re.search(r'\b' + table + r'\[[^=]+?= \{(.*?)\};', H).group(1)
    expected_ids.update(map(int, re.findall(r'\d+', declaration)))
assert set(seen) == {SPR[i] for i in expected_ids}, 'a legend sprite never reached actual x86 submission'
out = ROOT / 'build/legend-render-regression'
out.mkdir(exist_ok=True)
for route in ('hd', 'sd'):
    atlases = [Image.open(ROOT / f'build/atlas-preview/page{k}-{route}.png').convert('RGBA') for k in range(pages_n)]
    sheet = Image.new('RGBA', (1000, len(seen)*40), (24, 24, 24, 255))
    draw = ImageDraw.Draw(sheet)
    factor = 4 if route == 'hd' else 2
    for row, (sp, bx) in enumerate(sorted(seen.items())):
        pg, x, y, w, h = sp
        crop = atlases[pg].crop((x*factor, y*factor, (x+w)*factor, (y+h)*factor))
        crop = crop.resize(((bx[2]-bx[0])*4, (bx[3]-bx[1])*4), Image.Resampling.LANCZOS if route == 'hd' else Image.Resampling.NEAREST)
        draw.text((2, row*40+6), str(SPR.index(sp)), fill='white')
        sheet.alpha_composite(crop, (50, row*40))
    sheet.save(out / f'all-legend-{route}.png')
profile.clear(); call('AnnotatedMapTestLoadSettings')
print('actual x86 legend submissions and SD/HD render sheets OK:', len(seen), 'sprites')

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
                call('AnnotatedMapTestOptions', int(os.environ.get('PREVIEW_NAMES', '0')), 1, 0)   # PREVIEW_NAMES=1: item names on
                run(page, 1, lang, toggles=(1, 1, 1, 1, 1, 1, 1, 1, 1))
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
