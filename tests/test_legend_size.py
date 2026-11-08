"""One text size for EVERY legend, hint, readout, value and title-line sprite in both languages (user 2026-11-07, again
candidate 12). Root cause of the repeat: text_sprite() cropped each line to its own ink, so lines without a bracket or
descender were 5 SD px tall and the rest 6, and the 90% legend scale rounded those heights per row (5 or 6 px drawn);
the old check only compared (font px, stroke) arguments and the '[' glyph of the lines that start with '['. This test
builds the atlas, takes every sprite whose key says it belongs to the legend (so a new one cannot slip through), and
requires: the exact expected key set, one sprite height, one baseline, glyph cap height equal within 1 SD px (4 HD px),
the [~] hint on the title line the same, and the title the only larger line."""
import contextlib, io, json, sys, re, zlib
from PIL import Image
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_assets as B

with contextlib.redirect_stdout(io.StringIO()):
    B.main()
sprites, index = B.LAST_BUILD
names = json.loads((ROOT / 'data/names.json').read_text())['legend']
kinds = ('legend', 'hint', 'readout', 'value')
found = {k for k in index if k[0] in kinds}
rows = ['all', 'rooms', 'locks', 'key', 'docs', 'puzzles', 'events', 'common', 'monsters']
expected = ({('legend', r, lang, on) for r in rows for lang in (0, 1) for on in (0, 1)}
            | {('legend', f'scope{n}', lang, 1) for n in (1, 2, 3) for lang in (0, 1)}
            | {('legend', 'lang', lang, 1) for lang in (0, 1)} | {('legend', 'title', lang, 1) for lang in (0, 1)}
            | {('hint', 'hide', lang) for lang in (0, 1)} | {('hint', 'fold', lang) for lang in (0, 1)}
            | {('hint', 'names', lang, st) for lang in (0, 1) for st in range(3)}
            | {('readout', r, lang, mod) for r in range(4) for lang in (0, 1) for mod in range(len(B.MODIFIERS))}
            | {('value', v) for v in range(10, 201, 10)})
assert found == expected, ('legend sprites not covered by this check (add them to `expected` and make them legend_sprite()):',
                           sorted(map(str, found ^ expected)))
asc22 = B.font(22).getmetrics()[0]
def cap(sprite, baseline):
    ink = np.nonzero((np.asarray(sprite.hd)[..., 3] > 127).any(1))[0]
    return baseline - int(ink.min())   # HD px from the baseline to the tallest glyph's top (outline included)
body, caps = [], {}
for key in sorted(found, key=str):
    sp = sprites[index[key]]
    if key[:2] == ('legend', 'title'):
        caps[key] = cap(sp, 3 + asc22)
    elif key[:2] == ('hint', 'hide'):
        caps[key] = cap(sp, 3 + asc22)   # framed on the title's baseline (16 px text)
    else:
        assert sp.hd.height == B.LEGEND_FRAME_SD * B.S, (key, sp.hd.height)   # one sprite height: 7 SD px
        caps[key] = cap(sp, B.legend_baseline()); body.append(key)
small = [caps[k] for k in body] + [caps[k] for k in caps if k[:2] == ('hint', 'hide')]
assert max(small) - min(small) <= B.S, ('glyph cap height differs by more than 1 SD px', {k: caps[k] for k in caps if caps[k] in (max(small), min(small))})
titles = [caps[k] for k in caps if k[:2] == ('legend', 'title')]
assert min(titles) >= max(small) + B.S, (titles, small)   # the heading is the only larger line
print('legend text size OK:', len(body), 'legend-size sprites + 2 [~] hints, cap height', min(small), '..', max(small), 'HD px; title', set(titles))

# COMMON item colour (user 2026-11-08): cool grey #B8BCC4 for the legend row [7] and the common-item names/badges, one value
# per category; disabled rows a darker grey #6A6A6A; the event row/marker purple. All distinct from the neighbours.
assert B.PALETTE[B.COMMON_GREY] == (184, 188, 196), B.PALETTE[B.COMMON_GREY]
assert B.PALETTE[B.GREY] == (106, 106, 106) and B.PALETTE[B.EVENT] == (176, 112, 255)
assert B.CATEGORY_COLOR['common'] == B.MARK_COLOR['common'] == B.COMMON_GREY and B.CATEGORY_COLOR['events'] == B.EVENT
assert B.rgba_of(B.COMMON_GREY)[:3] == (189, 189, 198)   # RGB555 value the game's palette can hold
def lab(c):
    c = np.array(c) / 255.; c = np.where(c > .04045, ((c + .055) / 1.055) ** 2.4, c / 12.92)
    x = c @ np.array([[.4124, .3576, .1805], [.2126, .7152, .0722], [.0193, .1192, .9505]]).T / np.array([.9505, 1, 1.089])
    f = np.where(x > .008856, np.cbrt(x), 7.787 * x + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])
de = lambda a, b: float(np.linalg.norm(lab(a) - lab(b)))
grey = B.PALETTE[B.COMMON_GREY]
assert de(grey, B.PALETTE[B.GREY]) > 30, 'enabled common row vs a disabled row'
assert de(grey, B.PALETTE[B.WHITE]) > 20 and de(grey, B.PALETTE[B.CREAM]) > 20, 'white / room names'
assert de(grey, B.PALETTE[B.AMBER]) > 60 and de(B.PALETTE[B.EVENT], B.PALETTE[B.AMBER]) > 60 and de(B.PALETTE[B.EVENT], B.PALETTE[B.PINK]) > 30
assert all(de(grey, B.PALETTE[c]) > 30 for c in (B.CYAN, B.PINK, B.GOLD, B.RED, B.EVENT))
print('legend colours OK; common grey vs white dE', round(de(grey, B.PALETTE[B.WHITE]), 1), 'vs disabled', round(de(grey, B.PALETTE[B.GREY]), 1))

# HD-off notice sprite: made on the SD grid (every SxS HD block is one flat colour, so the 4bpp atlas keeps it exactly),
# glyphs at least 14 SD px tall, white with a dark outline.
n = B.notice_sprite()
hd = np.asarray(n.hd)
blocks = hd.reshape(n.h, B.S, n.w, B.S, 4)
assert (blocks == blocks[:, :1, :, :1]).all(), 'notice must be exact pixel art'
sd_rgb = blocks[:, 0, :, 0]
white = (sd_rgb[..., :3] == B.PALETTE[B.WHITE]).all(-1) & (sd_rgb[..., 3] == 255)
rows = np.nonzero(white.any(1))[0]
assert rows.max() - rows.min() + 1 >= 3 * 14 and (n.sd[white] == B.WHITE).all(), (rows.min(), rows.max())
print('HD-off notice sprite OK', n.w, 'x', n.h, 'SD px')

# Check the shipped bytes, not just the in-memory rasters: the runtime reads rectangles and 4bpp pixels
# from assets.h, and REbirth selects the lossless HD WebP by the decoded SD page CRC.
header = (ROOT / 'src/assets.h').read_text()
rects = [tuple(map(int, m)) for m in re.findall(r'\{(\d+),(\d+),(\d+),(\d+),(\d+)\}', header.split('sprites[SPRITE_COUNT] = {', 1)[1].split('};', 1)[0])]
packed = np.array(list(map(int, re.findall(r'\d+', header.split('atlas_pixels[ATLAS_PAGES][256 * 128] = {', 1)[1].split('};', 1)[0]))), dtype=np.uint8).reshape(-1, 256, 128)
sd = np.empty((len(packed), 256, 256), np.uint8)
sd[:, :, 0::2], sd[:, :, 1::2] = packed & 15, packed >> 4
lut = np.array([B.rgba_of(i) for i in range(16)], np.uint8)
atlases = {}
for key in found:
    sp = sprites[index[key]]
    pg, x, y, w, h = rects[index[key]]
    assert (w, h) == (sp.w, sp.h), key
    assert np.array_equal(sd[pg, y:y+h, x:x+w], sp.sd), ('SD atlas crop', key)
    if pg not in atlases:
        crc = zlib.crc32(np.ascontiguousarray(lut[sd[pg]][..., [2, 1, 0, 3]]).tobytes())
        atlases[pg] = Image.open(ROOT / f'build/hires/misc/{crc:08X}.webp').convert('RGBA')
    crop = atlases[pg].crop((x*B.S, y*B.S, (x+w)*B.S, (y+h)*B.S))
    assert np.array_equal(np.asarray(crop), np.asarray(sp.hd)), ('HD atlas crop', key)
print('shipped SD/HD atlas crops OK:', len(found), 'sprites, both languages and every state')
