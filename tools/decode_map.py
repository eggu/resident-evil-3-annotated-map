"""Decode DATA_J/ETC2/MAP_J.MAP into data/map-pages.json and preview PNGs (local/map-preview/).

Segment layout (loader 0x4EB870, draw 0x4EAC60, executable sizes table 0x535128):
  +0x04 room table: u32 count, then count x {u32 parts_off (from table start), u16 parts, u16 marks}
        part / mark records are 12 bytes: u0 v0 u1 v1 (texture rect), s16 x, s16 y (map space), u8 type, u8 attr, u16 ?
  +0x0C projection table (status +0xB4): u32 table_off, then 8-byte {s16 mx, s16 my, s16 wx, s16 wz} per room
  +0x14 map TIM (Upload_tim 0x428980)
Player projection (0x4EAF50): map = (mx + (x - wx)/450, my - (z - wz)/450).
"""
import json, struct
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SIZES = (0x12000, 0x12800, 0xA000, 0x12000, 0x12000, 0x12000, 0x12000, 0x12000, 0x12800)  # exe 0x535128
NAMES = ('Uptown', 'Downtown', 'Clock Tower', 'Park', 'Dead Factory', 'Police Station', 'Hospital', 'Uptown 2', 'Downtown 2')


def tim(data):
    magic, flags = struct.unpack_from('<II', data, 0)
    assert magic == 0x10, hex(magic)
    bpp = flags & 3
    pos = 8
    clut = None
    if flags & 8:
        blen, cx, cy, cw, ch = struct.unpack_from('<IHHHH', data, pos)
        clut = [struct.unpack_from(f'<{cw}H', data, pos + 12 + r * cw * 2) for r in range(ch)]
        clut_pos = (cx, cy)
        pos += blen
    blen, ix, iy, iw, ih = struct.unpack_from('<IHHHH', data, pos)
    px = data[pos + 12:pos + blen]
    w = iw * (4 if bpp == 0 else 2 if bpp == 1 else 1)
    return dict(bpp=bpp, clut=clut, clut_pos=clut_pos if clut else None, vram=(ix, iy, iw, ih), w=w, h=ih, px=px)


def rgb(c):
    return ((c & 31) * 255 // 31, (c >> 5 & 31) * 255 // 31, (c >> 10 & 31) * 255 // 31, 0 if c == 0 else 255)


def image(t, row=0):
    im = Image.new('RGBA', (t['w'], t['h']))
    pal = [rgb(c) for c in t['clut'][row]] if t['clut'] else None
    out = []
    for y in range(t['h']):
        for x in range(t['w']):
            if t['bpp'] == 0:
                b = t['px'][(y * t['w'] + x) // 2]
                out.append(pal[(b >> (4 * (x & 1))) & 15])
            elif t['bpp'] == 1:
                out.append(pal[t['px'][y * t['w'] + x]])
            else:
                out.append(rgb(struct.unpack_from('<H', t['px'], 2 * (y * t['w'] + x))[0]))
    im.putdata(out)
    return im


def decode():
    data = (ROOT / 'local/extracted/DATA_J/ETC2/MAP_J.MAP').read_bytes()
    pages, off = [], 0
    for page, size in enumerate(SIZES):
        seg = data[off:off + size]
        h = struct.unpack_from('<9I', seg, 0)
        tbl = h[1]
        n = struct.unpack_from('<I', seg, tbl)[0]
        proj_base = h[3]
        proj_tbl = proj_base + struct.unpack_from('<I', seg, proj_base)[0]
        rooms = []
        for k in range(n):
            po, nparts, nmarks = struct.unpack_from('<IHH', seg, tbl + 4 + 8 * k)
            recs = [struct.unpack_from('<4B2h2BH', seg, tbl + po + 12 * j) for j in range(nparts + nmarks)]
            mx, my, wx, wz = struct.unpack_from('<4h', seg, proj_tbl + 8 * k)
            rooms.append(dict(index=k, parts=[list(r) for r in recs[:nparts]], marks=[list(r) for r in recs[nparts:]],
                              proj=dict(mx=mx, my=my, wx=wx, wz=wz)))
        t = tim(seg[h[5]:])
        pages.append(dict(page=page, name=NAMES[page], offset=off, header=list(h), rooms=rooms,
                          tim=dict(bpp=t['bpp'], vram=t['vram'], clut_pos=t['clut_pos'], w=t['w'], h=t['h'],
                                   clut_rows=len(t['clut']) if t['clut'] else 0)))
        yield pages[-1], t
        off += size


def main():
    out_dir = ROOT / 'local/map-preview'
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = []
    for page, t in decode():
        pages.append(page)
        src = image(t)
        src.save(out_dir / f'page{page["page"]}-tim.png')
        parts = [(r['index'], p) for r in page['rooms'] for p in r['parts'] if p[2] >= p[0] and p[3] >= p[1]]
        if not parts:
            continue
        x0 = min(p[4] for _, p in parts) - 8; y0 = min(p[5] for _, p in parts) - 8
        x1 = max(p[4] + p[2] - p[0] + 1 for _, p in parts) + 8; y1 = max(p[5] + p[3] - p[1] + 1 for _, p in parts) + 8
        page['bounds'] = [x0, y0, x1, y1]
        canvas = Image.new('RGBA', (x1 - x0, y1 - y0), (0, 0, 0, 255))
        for _, (u0, v0, u1, v1, x, y, typ, attr, _x) in parts:
            canvas.alpha_composite(src.crop((u0, v0, u1 + 1, v1 + 1)), (x - x0, y - y0))
        big = canvas.resize((canvas.width * 3, canvas.height * 3), Image.NEAREST)
        draw = ImageDraw.Draw(big)
        for r in page['rooms']:
            ps = [p for p in r['parts'] if p[2] >= p[0] and p[3] >= p[1]]
            if ps:
                cx = sum(p[4] + (p[2] - p[0]) / 2 for p in ps) / len(ps); cy = sum(p[5] + (p[3] - p[1]) / 2 for p in ps) / len(ps)
                draw.text(((cx - x0) * 3, (cy - y0) * 3), f'{r["index"]:X}', fill=(255, 40, 40, 255))
        big.save(out_dir / f'page{page["page"]}.png')
    (ROOT / 'data/map-pages.json').write_text(json.dumps(pages, indent=1) + '\n')
    for p in pages:
        print(p['page'], p['name'], len(p['rooms']), p['tim'])


if __name__ == '__main__':
    main()
