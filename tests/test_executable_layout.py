"""Exercise ASI initialization with changed PE metadata and incompatible map code."""
import os
import struct
from pathlib import Path

from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP

native = Path(__file__).with_name('test_native.py')
harness = native.read_text().split('# Fake GPU interface:', 1)[0]
sites = (0x461780, 0x4617C5, 0x4EAD35, 0x4EBB9C, 0x4EAD7A)


def check(change=None, expect_hooks=True, exe=None, call_sites=sites):
    scope = {'__file__': str(native)}
    code = harness
    if exe and str(exe).endswith('.bin'):   # unpacked memory image dumped from a running process
        code = code.replace('gi, _ = load(EXE.read_bytes(), 0x400000)', 'gi = bytearray(ALT_EXE.read_bytes())', 1)
        scope['ALT_EXE'] = Path(exe)
    elif exe:
        code = code.replace('gi, _ = load(EXE.read_bytes()', 'gi, _ = load(ALT_EXE.read_bytes()', 1)
        scope['ALT_EXE'] = Path(exe)
    exec(code, scope)
    u, imports, image, dll, optional = (scope[k] for k in ('u', 'imports', 'gi', 'di', 'o'))
    u.mem_write(0x4EAC60, bytes(image[0xEAC60:0xEAC61]))
    for name, result, stack_bytes in (
        ('GetModuleHandleA', 0x400000, 4),
        ('VirtualProtect', 1, 16),
    ):
        u.mem_write(imports[name], struct.pack('<BIBH', 0xB8, result, 0xC2, stack_bytes))
    if change:
        change(u, image)
    before = [bytes(u.mem_read(site, 5)) for site in call_sites]
    u.mem_write(0x20008000, struct.pack('<4I', 0x20000100, 0x10000000, 1, 0))
    u.reg_write(UC_X86_REG_ESP, 0x20008000)
    entry, = struct.unpack_from('<I', dll, optional + 16)
    u.emu_start(0x10000000 + entry, 0x20000100)
    after = [bytes(u.mem_read(site, 5)) for site in call_sites]
    if expect_hooks:
        for site, old, new in zip(call_sites, before, after):
            assert old != new and new[0] == 0xE8
            target = site + 5 + struct.unpack_from('<i', new, 1)[0]
            assert 0x10000000 <= target < 0x10000000 + len(dll)
    else:
        assert before == after
    return u, scope['exports']


def change_metadata(u, image):
    pe, = struct.unpack_from('<I', image, 60)
    u.mem_write(0x400000 + pe + 8, struct.pack('<I', 0x12345678))
    u.mem_write(0x400000 + pe + 80, struct.pack('<I', len(image) + 0x1000))


check()
check(change_metadata)
check(lambda u, _: u.mem_write(0x4EAC60, b'\x90'), expect_hooks=False)
check(lambda u, _: u.mem_write(0x461780, b'\x90'), expect_hooks=False)

check(lambda u, _: u.mem_write(0x401000, bytes(0x109000)), expect_hooks=False)   # still packed: no hooks yet
print('Map initialization accepts changed PE metadata and rejects incompatible or packed code before hooking.')


def overlay(exe, draw, room_exists, map_calls, load_image, shift, label):
    sites = (*map_calls, draw + 0xD5, room_exists + 0x1AC, draw + 0x11A)
    u, exports = check(exe=exe, call_sites=sites)

    def call(address, *args):
        u.mem_write(0x20008000, struct.pack('<' + 'I' * (len(args) + 1), 0x20000100, *args))
        u.reg_write(UC_X86_REG_ESP, 0x20008000)
        u.emu_start(address, 0x20000100, count=2_000_000)
        assert u.reg_read(UC_X86_REG_ESP) == 0x20008004
        return u.reg_read(UC_X86_REG_EAX)

    # Keep the real room gate and primitive routines. Stub native map rendering and VRAM transfer.
    state, ot, anchor = 0x21020000, 0x21010000, 0x21011000
    u.mem_write(draw, b'\xC3')
    u.mem_write(load_image, b'\xC3')
    u.mem_write(state, bytes(0x100))
    u.mem_write(state + 0xA4, struct.pack('<I', 100))
    u.mem_write(0xA5FBC0 - shift, struct.pack('<I', ot))
    u.mem_write(ot + 4, struct.pack('<I', anchor))
    u.mem_write(anchor, struct.pack('<I', 0xDEAD0000))
    call(exports['AnnotatedMapTestSet'], 1, 3, 0)
    call(exports['AnnotatedMapTestSdMode'], 1)
    hook = map_calls[0] + 5 + struct.unpack('<i', u.mem_read(map_calls[0] + 1, 4))[0]
    call(hook, state)
    assert call(exports['AnnotatedMapTestCount'], 9) > 0
    assert bytes(u.mem_read(anchor, 4)) != struct.pack('<I', 0xDEAD0000)
    print(f'{label} layout installs all five hooks and submits SD room primitives.')


if japanese_exe := os.environ.get('RE3_CLASSIC_JP_EXE'):
    overlay(japanese_exe, 0x4E7D80, 0x4E8B10, (0x45E820, 0x45E865), 0x422EB0, 0x6280, 'Classic Japanese')
if steam_dump := os.environ.get('RE3_STEAM_DUMP'):
    overlay(steam_dump, 0x4E79E0, 0x4E8770, (0x45E580, 0x45E5C5), 0x423200, 0x5420, 'Steam English (unpacked)')
