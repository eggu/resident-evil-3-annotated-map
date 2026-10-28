"""Read-only PE image + capstone helpers for the RE3 SourceNext executable."""
import struct, capstone, os, re
GAME = os.environ.get('RE3_GAME', 'game')
EXE = os.path.join(GAME, 'BIOHAZARD(R) 3 PC.exe')

class Image:
    def __init__(self, path=EXE):
        self.raw = open(path, 'rb').read()
        pe = struct.unpack_from('<I', self.raw, 0x3c)[0]
        nsec, = struct.unpack_from('<H', self.raw, pe + 6)
        optsz, = struct.unpack_from('<H', self.raw, pe + 20)
        self.base, = struct.unpack_from('<I', self.raw, pe + 24 + 28)
        self.sections = []
        for i in range(nsec):
            o = pe + 24 + optsz + i * 40
            name = self.raw[o:o + 8].rstrip(b'\0').decode()
            vsz, va, rsz, rptr = struct.unpack_from('<IIII', self.raw, o + 8)
            self.sections.append((name, self.base + va, vsz, rptr, rsz))
        self.md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        self.md.detail = False

    def off(self, va):
        for _, s, vsz, rptr, rsz in self.sections:
            if s <= va < s + max(vsz, rsz):
                return rptr + va - s if va - s < rsz else None
        return None

    def read(self, va, n):
        o = self.off(va)
        return self.raw[o:o + n]

    def u32(self, va): return struct.unpack('<I', self.read(va, 4))[0]

    def dis(self, va, n=40, stop_ret=True):
        out = []
        for ins in self.md.disasm(self.read(va, 0x2000), va):
            out.append(f'{ins.address:08x}: {ins.mnemonic} {ins.op_str}')
            if len(out) >= n or (stop_ret and ins.mnemonic == 'ret'):
                break
        return '\n'.join(out)

    def text(self):
        return [s for s in self.sections if s[0] == '.text'][0]

    def calls_to(self, target):
        """All E8 rel32 calls targeting `target` in .text."""
        _, s, vsz, rptr, rsz = self.text()
        data = self.raw[rptr:rptr + rsz]
        hits = []
        for m in re.finditer(b'\xe8', data):
            i = m.start()
            if i + 5 > len(data): break
            rel, = struct.unpack_from('<i', data, i + 1)
            if s + i + 5 + rel == target:
                hits.append(s + i)
        return hits

    def refs_imm(self, value):
        """Byte offsets in .text containing little-endian dword `value`."""
        _, s, vsz, rptr, rsz = self.text()
        data = self.raw[rptr:rptr + rsz]
        pat = struct.pack('<I', value)
        return [s + m.start() for m in re.finditer(re.escape(pat), data)]

def func_start(img, va):
    """Walk back to the byte after a run of >=1 nop/int3 padding preceded by ret/jmp."""
    o = img.off(va)
    raw = img.raw
    while o > 0:
        if raw[o - 1] in (0x90, 0xcc) and raw[o] not in (0x90, 0xcc):
            j = o - 1
            while raw[j] in (0x90, 0xcc): j -= 1
            if raw[j] in (0xc3,) or raw[j - 2] == 0xc2 or raw[j - 4] == 0xe9:
                return va - (img.off(va) - o)
        o -= 1
    return None

def func_dump(img, va, limit=3000):
    start = func_start(img, va)
    lines = []
    for ins in img.md.disasm(img.read(start, 0x8000), start):
        if ins.mnemonic == 'nop' or ins.mnemonic == 'int3':
            if lines and lines[-1].split(': ')[1].startswith(('ret', 'jmp')): break
        lines.append(f'{ins.address:08x}: {ins.mnemonic} {ins.op_str}')
        if len(lines) > limit: break
    return start, '\n'.join(lines)
