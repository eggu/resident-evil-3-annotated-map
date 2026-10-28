"""Build overlay atlas pages and runtime tables.

Outputs
  src/assets.h          4bpp SD pages (256x256), CLUT, label/icon rectangles, markers, guards, room anchors
  build/hires/misc/*.webp  4x HD replacements keyed like REbirth pages: CRC32 of the page decoded to BGRA
                           through the CLUT (0 = transparent).
  build/atlas-preview/*.png
"""
import json, zlib, struct
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from build_overlay import MONSTERS

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / 'fonts/Pretendard-Medium.otf'
S = 4                       # HD scale
PAGE = 256
PALETTE = [(0, 0, 0), (16, 16, 16), (240, 226, 190), (255, 205, 70), (90, 220, 255), (255, 150, 40),
           (140, 140, 140), (255, 255, 255), (48, 48, 48), (255, 120, 60), (235, 60, 60), (90, 205, 90),
           (90, 140, 255), (170, 120, 70), (200, 230, 200), (255, 140, 210)]
OUTLINE, CREAM, GOLD, CYAN, AMBER, GREY, WHITE, PANEL, ORANGE, RED, GREEN, BLUE, BROWN, PALE, PINK = range(1, 16)
CATEGORY_COLOR = dict(all=WHITE, rooms=CREAM, locks=GOLD, key=CYAN, docs=PINK, puzzles=AMBER, common=ORANGE,
                      monsters=RED)


def bgr555(rgb):
    r, g, b = (c >> 3 for c in rgb)
    return r | g << 5 | b << 10


CLUT = [0] + [bgr555(c) or 0x0421 for c in PALETTE[1:]]


# per opacity level 10..100%: outline colour (index 1) nudged within near-black so every level has its own key
NAME_CLUTS = [[CLUT[0], (1 + (k & 3)) | (1 + (k >> 2)) << 5 | 1 << 10] + CLUT[2:] for k in range(10)]


def rgba_of(index, clut=None):
    v = (clut or CLUT)[index]
    if index == 0:
        return (0, 0, 0, 0)
    return tuple(((v >> s & 31) << 3) | (v >> s & 31) >> 2 for s in (0, 5, 10)) + (255,)


class Sprite:
    def __init__(self, hd):           # hd: RGBA image at S x
        w, h = (hd.width + S - 1) // S, (hd.height + S - 1) // S
        self.hd = Image.new('RGBA', (w * S, h * S))
        self.hd.alpha_composite(hd)
        self.w, self.h = w, h
        self.sd = sd_indices(self.hd)


def sd_indices(hd):
    """Downsample an HD RGBA sprite to palette indices: per SxS block, the dominant opaque colour."""
    a = np.asarray(hd)
    h, w = a.shape[0] // S, a.shape[1] // S
    pal = np.array(PALETTE, np.int32)
    out = np.zeros((h, w), np.uint8)
    for y in range(h):
        for x in range(w):
            blk = a[y * S:(y + 1) * S, x * S:(x + 1) * S].reshape(-1, 4)
            opaque = blk[blk[:, 3] >= 128]
            if len(opaque) * 3 < S * S:
                continue
            c = opaque[:, :3].mean(0)
            out[y, x] = 1 + int(np.argmin(((pal[1:] - c) ** 2).sum(1)))
    return out


_fonts = {}


def font(px):
    if px not in _fonts:
        _fonts[px] = ImageFont.truetype(str(FONT), px)
    return _fonts[px]


def text_sprite(text, color, px=20, stroke=3):
    f = font(px)
    l, t, r, b = f.getbbox(text, stroke_width=stroke)
    im = Image.new('RGBA', (r - l + 2, b - t + 2))
    ImageDraw.Draw(im).text((1 - l, 1 - t), text, font=f, fill=PALETTE[color] + (255,),
                            stroke_width=stroke, stroke_fill=PALETTE[OUTLINE] + (255,))
    return Sprite(im)


def pixel_sprite(name, size=10):
    """Pack redrawn 2D artwork without smoothing; originals are identity references only."""
    im = Image.open(ROOT / 'assets/icons' / (name + '.png')).convert('RGBA')
    assert im.size == (32, 32) and im.getbbox(), name
    assert set(im.getchannel('A').get_flattened_data()) <= {0, 255}, name
    out = Image.new('RGBA', (size * S, size * S))
    im = im.resize((size * S - 2 * S,) * 2, Image.Resampling.NEAREST)
    out.alpha_composite(im, (S, S))
    return Sprite(out)


COMMON_AMMO = range(0x14, 0x20)   # handgun..freeze rounds


def item_icon(item):
    return pixel_sprite(f'item-{item:02x}')


def icon(kind, size=10):
    """Pixel icons drawn on an SD grid of `size` cells, each S px."""
    if kind in ('typewriter', 'itembox', 'map', 'document', 'key', 'diamond', 'puzzle-marker', 'selection-marker'):
        return pixel_sprite(kind, size)
    n = size * S
    im = Image.new('RGBA', (n, n))
    d = ImageDraw.Draw(im)
    o = PALETTE[OUTLINE] + (255,)
    def c(i): return PALETTE[i] + (255,)
    q = n / 10
    if kind == 'star':
        import math
        pts = [(n / 2 + (0.48 if k % 2 == 0 else 0.2) * n * math.sin(k * math.pi / 5),
                n / 2 - (0.48 if k % 2 == 0 else 0.2) * n * math.cos(k * math.pi / 5)) for k in range(10)]
        d.polygon(pts, fill=c(CYAN), outline=o, width=S)
    elif kind == 'ammo':
        for x in (2, 4.5, 7):
            d.rectangle([q * (x - 0.9), q * 3, q * (x + 0.9), q * 9], fill=c(GOLD), outline=o, width=S)
            d.ellipse([q * (x - 0.9), q * 1.5, q * (x + 0.9), q * 4.5], fill=c(ORANGE), outline=o, width=S)
    elif kind in ('herb_g', 'herb_r', 'herb_b'):
        col = {'herb_g': GREEN, 'herb_r': RED, 'herb_b': BLUE}[kind]
        d.ellipse([q, q * 3, q * 5.5, q * 7.5], fill=c(col), outline=o, width=S)
        d.ellipse([q * 4.5, q * 3, q * 9, q * 7.5], fill=c(col), outline=o, width=S)
        d.ellipse([q * 2.7, q * 0.8, q * 7.3, q * 5], fill=c(col), outline=o, width=S)
        d.rectangle([q * 4.4, q * 6, q * 5.6, q * 9.5], fill=c(GREEN), outline=o, width=S)
    elif kind == 'spray':
        d.rectangle([q * 3, q * 3, q * 7, q * 9.5], fill=c(WHITE), outline=o, width=S)
        d.rectangle([q * 4, q * 0.5, q * 6, q * 3], fill=c(GREY), outline=o, width=S)
        d.rectangle([q * 4.5, q * 5, q * 5.5, q * 8], fill=c(RED)); d.rectangle([q * 3.5, q * 6, q * 6.5, q * 7], fill=c(RED))
    elif kind == 'ribbon':
        d.ellipse([q, q, q * 9, q * 9], fill=c(GREY), outline=o, width=S)
        d.ellipse([q * 3.5, q * 3.5, q * 6.5, q * 6.5], fill=o)
    elif kind == 'powder':
        d.polygon([(q * 2, q * 9), (q * 3, q * 3), (q * 7, q * 3), (q * 8, q * 9)], fill=c(GREY), outline=o, width=S)
        d.rectangle([q * 3.5, q, q * 6.5, q * 3], fill=c(PANEL), outline=o, width=S)
    elif kind == 'dot':
        d.ellipse([q * 2, q * 2, q * 8, q * 8], fill=c(CYAN), outline=o, width=S)
    elif kind == 'line':
        d.rectangle([0, 0, n, n], fill=c(CREAM))
    elif kind == 'panel':
        d.rectangle([0, 0, n, n], fill=c(PANEL))
    return Sprite(im)


ICON_KINDS = ['star', 'diamond', 'key', 'document', 'map', 'typewriter', 'itembox', 'ammo', 'herb_g', 'herb_r',
              'herb_b', 'spray', 'ribbon', 'powder', 'dot', 'line', 'panel', 'puzzle-marker', 'selection-marker']


class Packer:
    def __init__(self):
        self.pages = []

    def place(self, sp):
        for idx, pg in enumerate(self.pages):
            pos = pg.fit(sp.w + 1, sp.h + 1)
            if pos:
                return idx, pos
        self.pages.append(Shelf())
        return len(self.pages) - 1, self.pages[-1].fit(sp.w + 1, sp.h + 1)


class Shelf:
    def __init__(self):
        self.x = self.y = self.row = 0

    def fit(self, w, h):
        if self.x + w > PAGE:
            self.x, self.y, self.row = 0, self.y + self.row, 0
        if self.y + h > PAGE:
            return None
        pos = (self.x, self.y)
        self.x += w
        self.row = max(self.row, h)
        return pos


def main():
    names = json.loads((ROOT / 'data/names.json').read_text())
    overlay = json.loads((ROOT / 'data/overlay.json').read_text())
    pages_map = json.loads((ROOT / 'data/map-pages.json').read_text())
    sprites, index = [], {}
    def add(key, sp):
        if key not in index:
            index[key] = len(sprites)
            sprites.append(sp)
        return index[key]
    for k in ICON_KINDS:
        add(('icon', k), icon(k))
    for monster in MONSTERS:
        add(('monster', monster), pixel_sprite('monster-' + monster))
    for it in sorted({m['item'] for m in overlay['markers'] if m['kind'] in ('key', 'common', 'lock') and m['item'] < 134}):
        add(('item_icon', it), item_icon(it))
    room_names = sorted({r['name'] for r in overlay['rooms'] if r['name']})
    for n in room_names:
        add(('room', n, 0), text_sprite(n, CREAM, 20))
        add(('room', n, 1), text_sprite(names['rooms'][n], CREAM, 20))
    label_items = sorted({m['item'] for m in overlay['markers'] if m['kind'] in ('key', 'lock')})
    for it in label_items:
        en, ko = names['items'][str(it)]
        add(('item', it, 0), text_sprite(en, CYAN, 18))
        add(('item', it, 1), text_sprite(ko, CYAN, 18))
        add(('lockname', it, 0), text_sprite(en, GOLD, 18))
        add(('lockname', it, 1), text_sprite(ko, GOLD, 18))
    legend_rows = ['all', 'rooms', 'locks', 'key', 'docs', 'puzzles', 'common', 'monsters']
    keys = '01234567'
    for row, key in zip(legend_rows, keys):
        for lang in (0, 1):
            for on in (0, 1):
                add(('legend', row, lang, on), text_sprite(f'[{key}] {names["legend"][row][lang]}',
                                                           CATEGORY_COLOR[row] if on else GREY, 20))
    for s in (1, 2, 3):
        for lang in (0, 1):
            add(('legend', f'scope{s}', lang, 1), text_sprite(f'[8] {names["legend"][f"scope{s}"][lang]}', WHITE, 20))
    for lang in (0, 1):
        add(('legend', 'lang', lang, 1), text_sprite(f'[9] {names["legend"]["lang"][lang]}', WHITE, 20))
        add(('legend', 'title', lang, 1), text_sprite(names['legend']['title'][lang], WHITE, 22))
        for level in range(10, 101, 10):   # name opacity shown beside the title (Shift + -/+)
            add(('legend', 'opacity', lang, level), text_sprite(f'{("Name opacity", "이름 불투명도")[lang]} {level}%', GREY, 16, stroke=2))
        for level in range(50, 151, 10):
            add(('legend', 'size', lang, level), text_sprite(f'{("Name size", "이름 크기")[lang]} {level}%', GREY, 16, stroke=2))
    # Names live on their own pages: their HD replacement bakes in the name opacity (REbirth blends HD alpha),
    # one HD file per 10% level, told apart by a CLUT whose outline colour differs invisibly per level.
    # The runtime picks the level from RE3.AnnotatedMap.ini NameOpacity (~1.5 MB of HD files for all levels).
    is_name = [False] * len(sprites)
    for key, i in index.items():
        if key[0] in ('room', 'item', 'lockname'):
            is_name[i] = True
    packers = (Packer(), Packer())
    rects = [packers[n].place(sp) for sp, n in zip(sprites, is_name)]
    first_name_page = len(packers[0].pages)
    rects = [((pg + first_name_page) if n else pg, uv) for (pg, uv), n in zip(rects, is_name)]
    npages = first_name_page + len(packers[1].pages)
    sd = np.zeros((npages, PAGE, PAGE), np.uint8)
    hd = [Image.new('RGBA', (PAGE * S, PAGE * S)) for _ in range(npages)]
    for sp, (pg, (u, v)) in zip(sprites, rects):
        sd[pg, v:v + sp.h, u:u + sp.w] = sp.sd
        hd[pg].alpha_composite(sp.hd, (u * S, v * S))
    out = ROOT / 'build'
    (out / 'hires/misc').mkdir(parents=True, exist_ok=True)
    for old in (out / 'hires/misc').glob('*.webp'):
        old.unlink()   # keys change whenever the atlas does
    (out / 'atlas-preview').mkdir(parents=True, exist_ok=True)
    keys_out = []
    def save(pg, clut, image, tag):
        lut = np.array([rgba_of(i, clut) for i in range(16)], np.uint8)
        key = f'{zlib.crc32(np.ascontiguousarray(lut[sd[pg]][..., [2, 1, 0, 3]]).tobytes()):08X}'
        image.save(out / f'hires/misc/{key}.webp', lossless=True)
        keys_out.append(f'{pg}{tag}:{key}')
        return lut
    for pg in range(npages):
        if pg < first_name_page:
            lut = save(pg, CLUT, hd[pg], '')
        else:
            for level in range(1, 11):
                faded = np.asarray(hd[pg]).copy()
                faded[..., 3] = (faded[..., 3].astype(np.uint16) * level // 10).astype(np.uint8)
                lut = save(pg, NAME_CLUTS[level - 1], Image.fromarray(faded, 'RGBA'), f'@{level * 10}')
        Image.fromarray(lut[sd[pg]], 'RGBA').resize((PAGE * 2, PAGE * 2), Image.NEAREST).save(out / f'atlas-preview/page{pg}-sd.png')
        hd[pg].save(out / f'atlas-preview/page{pg}-hd.png')
    write_header(sd, rects, sprites, index, overlay, pages_map, names, room_names, label_items, legend_rows, keys_out, first_name_page)
    from build_map_header import build as build_map_header
    build_map_header(out / "hires/misc")
    print(npages, 'pages', len(sprites), 'sprites', keys_out)


_tims = {}


def tim_alpha(page):
    """Opaque mask of the decoded map TIM (local/map-preview/page<n>-tim.png, palette index 0 = transparent)."""
    if page not in _tims:
        _tims[page] = np.asarray(Image.open(ROOT / f'local/map-preview/page{page}-tim.png'))[..., 3] > 0
    return _tims[page]


def anchor(room, shared, page, w, h):
    """Label anchor: the room pixel farthest from the room's edge (map space). Rooms are drawn as textured
    rectangles whose transparent texels carve the real shape (a corridor rectangle can enclose another room),
    so the mask uses the texture's opaque texels; parts several rooms share (building outlines) are ignored."""
    ps = [p for p in room['parts'] if p[2] >= p[0] and p[3] >= p[1] and tuple(p[:6]) not in shared] or \
         [p for p in room['parts'] if p[2] >= p[0] and p[3] >= p[1]]
    x0 = min(p[4] for p in ps); y0 = min(p[5] for p in ps)
    x1 = max(p[4] + p[2] - p[0] + 1 for p in ps); y1 = max(p[5] + p[3] - p[1] + 1 for p in ps)
    mask = np.zeros((y1 - y0 + 2, x1 - x0 + 2), bool)
    alpha = tim_alpha(page)
    for u0, v0, u1, v1, x, y in (p[:6] for p in ps):
        mask[y - y0 + 1:y - y0 + 2 + v1 - v0, x - x0 + 1:x - x0 + 2 + u1 - u0] |= alpha[v0:v1 + 1, u0:u1 + 1]
    if not mask.any():
        for u0, v0, u1, v1, x, y in (p[:6] for p in ps):
            mask[y - y0 + 1:y - y0 + 2 + v1 - v0, x - x0 + 1:x - x0 + 2 + u1 - u0] = True
    dist = np.zeros(mask.shape, np.int32); cur = mask.copy(); k = 0
    while cur.any():                                   # 4-neighbour erosion distance
        k += 1; dist[cur] = k
        cur = cur & np.roll(cur, 1, 0) & np.roll(cur, -1, 0) & np.roll(cur, 1, 1) & np.roll(cur, -1, 1)
    # Centre the w x h label where it covers the most of this room's own pixels (narrow corridors that wrap
    # another room keep their name on the corridor); ties go to deeper, then more central pixels.
    pad = max(w, h)
    big = np.zeros((mask.shape[0] + 2 * pad, mask.shape[1] + 2 * pad), np.int32)
    big[pad:pad + mask.shape[0], pad:pad + mask.shape[1]] = mask
    ii = np.pad(big.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    ys, xs = np.nonzero(mask)
    ty, tx = ys + pad - h // 2, xs + pad - w // 2
    cover = ii[ty + h, tx + w] - ii[ty, tx + w] - ii[ty + h, tx] + ii[ty, tx]
    cy, cx = ys.mean(), xs.mean()
    score = cover * 10000 + dist[ys, xs] * 100 - np.hypot(ys - cy, xs - cx)
    j = int(np.argmax(score))
    return int(xs[j]) + x0 - 1, int(ys[j]) + y0 - 1


def write_header(sd, rects, sprites, index, overlay, pages_map, names, room_names, label_items, legend_rows, keys, first_name_page):
    L = ['/* Generated by tools/build_assets.py; do not edit. */', '#pragma once', '#include <stdint.h>',
         f'#define ATLAS_PAGES {len(sd)}', f'/* HD keys: {" ".join(keys)} */',
         'static const uint16_t atlas_clut[16] = {' + ','.join(f'0x{c:04x}' for c in CLUT) + '};',
         f'#define NAME_PAGE_FIRST {first_name_page}',
         'static const uint16_t name_cluts[10][16] = {' + ','.join('{' + ','.join(f'0x{c:04x}' for c in cl) + '}' for cl in NAME_CLUTS) + '};',
         'static const uint8_t atlas_pixels[ATLAS_PAGES][256 * 128] = {']
    for pg in sd:
        packed = (pg[:, 0::2] | (pg[:, 1::2] << 4)).astype(np.uint8).tobytes()
        L.append('{' + ','.join(str(b) for b in packed) + '},')
    L.append('};')
    L.append('typedef struct { uint8_t page, u, v, w, h; } Sprite;')
    L.append(f'#define SPRITE_COUNT {len(sprites)}')
    L.append('static const Sprite sprites[SPRITE_COUNT] = {' + ','.join(f'{{{pg},{u},{v},{sp.w},{sp.h}}}' for sp, (pg, (u, v)) in zip(sprites, rects)) + '};')
    for k in ICON_KINDS:
        L.append(f"#define ICON_{k.upper().replace('-', '_')} {index[('icon', k)]}")
    L.append(f'#define MONSTER_COUNT {len(MONSTERS)}')
    L.append('static const uint16_t monster_icons[MONSTER_COUNT] = {' + ','.join(str(index[('monster', monster)]) for monster in MONSTERS) + '};')
    L.append('static const uint16_t item_icons[134] = {' + ','.join(str(index.get(('item_icon', it), index[('icon', 'ammo' if it in COMMON_AMMO else 'diamond')])) for it in range(134)) + '};')
    # rooms: anchors and label sprites per (page, idx)
    rooms = [r for r in overlay['rooms'] if r['name']]
    L.append('typedef struct { uint8_t page, idx; int16_t x[2], y[2]; uint16_t label[2]; } RoomLabel;')
    L.append(f'#define ROOM_COUNT {len(rooms)}')
    rows = []
    for r in rooms:
        allparts = [tuple(p[:6]) for q in pages_map[r['page']]['rooms'] for p in q['parts']]
        shared = {p for p in allparts if allparts.count(p) > 1}
        pts = [anchor(pages_map[r['page']]['rooms'][r['idx']], shared, r['page'], sprites[index[('room', r['name'], lang)]].w,
                      sprites[index[('room', r['name'], lang)]].h) for lang in (0, 1)]
        rows.append(f'{{{r["page"]},{r["idx"]},{{{pts[0][0]},{pts[1][0]}}},{{{pts[0][1]},{pts[1][1]}}},{{{index[("room", r["name"], 0)]},{index[("room", r["name"], 1)]}}}}}')
    L.append('static const RoomLabel room_labels[ROOM_COUNT] = {' + ','.join(rows) + '};')
    L.append('typedef struct { uint16_t item; uint16_t label[2], lock_label[2]; } ItemLabel;')
    L.append(f'#define ITEM_LABEL_COUNT {len(label_items)}')
    L.append('static const ItemLabel item_labels[ITEM_LABEL_COUNT] = {' + ','.join(
        f'{{{it},{{{index[("item", it, 0)]},{index[("item", it, 1)]}}},{{{index[("lockname", it, 0)]},{index[("lockname", it, 1)]}}}}}' for it in label_items) + '};')
    leg = []
    for row in legend_rows:
        leg.append('{' + ','.join(f'{{{index[("legend", row, lang, 0)]},{index[("legend", row, lang, 1)]}}}' for lang in (0, 1)) + '}')
    L.append('static const uint16_t legend_sprites[8][2][2] = {' + ','.join(leg) + '};')
    L.append('static const uint16_t legend_scope[3][2] = {' + ','.join(
        f'{{{index[("legend", f"scope{s}", 0, 1)]},{index[("legend", f"scope{s}", 1, 1)]}}}' for s in (1, 2, 3)) + '};')
    L.append(f'static const uint16_t legend_lang[2] = {{{index[("legend", "lang", 0, 1)]},{index[("legend", "lang", 1, 1)]}}};')
    L.append(f'static const uint16_t legend_title[2] = {{{index[("legend", "title", 0, 1)]},{index[("legend", "title", 1, 1)]}}};')
    L.append('static const uint16_t legend_opacity[10][2] = {' + ','.join(
        f'{{{index[("legend", "opacity", 0, lv)]},{index[("legend", "opacity", 1, lv)]}}}' for lv in range(10, 101, 10)) + '};')
    L.append('static const uint16_t legend_size[11][2] = {' + ','.join(
        f'{{{index[("legend", "size", 0, lv)]},{index[("legend", "size", 1, lv)]}}}' for lv in range(50, 151, 10)) + '};')
    # markers + guards
    kinds = ['typewriter', 'itembox', 'lock', 'key', 'file', 'map', 'puzzle', 'common', 'enemy', 'room', 'live']
    lits, clauses, rows = [], [], []
    for m in overlay['markers']:
        if m['kind'] == 'enemy' and [] in m['guard']:
            continue
        x, y = snap(m, pages_map)
        c0 = len(clauses)
        for cl in m['guard']:
            l0 = len(lits)
            lits.extend(cl)
            clauses.append((l0, len(cl)))
        extra = MONSTERS.index(m['monster']) if m['kind'] == 'enemy' else m.get('event', m.get('item', 0))
        flag = m.get('flag', m.get('lock', m.get('kill', 255)))
        sets = m['sets'] | ((int(m['rdt'][0]) - 1) << 4)
        if m['kind'] == 'enemy' and m.get('anchor') == 'room': sets |= 4
        rows.append(f'{{{kinds.index(m["kind"])},{m["page"]},{m["idx"]},{sets},{x},{y},{extra},{flag},{c0},{len(clauses) - c0}}}')
    L.append('enum { K_TYPEWRITER, K_ITEMBOX, K_LOCK, K_KEY, K_FILE, K_MAP, K_PUZZLE, K_COMMON, K_ENEMY, K_ROOM, K_LIVE };')
    L.append('enum { ' + ', '.join('M_' + monster.upper() for monster in MONSTERS) + ' };')
    L.append('typedef struct { uint8_t kind, page, idx, sets /* bit0 DATA_J, bit1 DATA_AJ, bit2 room badge, bits4-6 RDT stage */; int16_t x, y; uint8_t extra, flag; uint16_t clause, nclause; } Marker;')
    L.append(f'#define MARKER_COUNT {len(rows)}')
    L.append('static const Marker markers[MARKER_COUNT] = {' + ','.join(rows) + '};')
    L.append('typedef struct { uint8_t bank, bit; int16_t value; } Literal;')
    L.append('static const Literal literals[] = {' + (','.join(f'{{{b},{n},{v}}}' for b, n, v in lits) or '{0,0,0}') + '};')
    L.append('typedef struct { uint16_t first, count; } Clause;')
    L.append('static const Clause clauses[] = {' + (','.join(f'{{{a},{b}}}' for a, b in clauses) or '{0,0}') + '};')
    (ROOT / 'src/assets.h').write_text('\n'.join(L) + '\n')


_snap_pixels = {}


def snap(m, pages_map):
    """Nearest opaque pixel of this room, excluding outlines/parts shared with other rooms."""
    key = (id(pages_map), m['page'], m['idx'])
    if key not in _snap_pixels:
        rooms = pages_map[m['page']]['rooms']
        parts = [p for p in rooms[m['idx']]['parts'] if p[2] >= p[0] and p[3] >= p[1]]
        counts = Counter(tuple(p[:6]) for room in rooms for p in room['parts'])
        own = [p for p in parts if counts[tuple(p[:6])] == 1] or parts
        alpha, points = tim_alpha(m['page']), []
        for u0, v0, u1, v1, x, y, *_ in own:
            ys, xs = np.nonzero(alpha[v0:v1 + 1, u0:u1 + 1])
            if len(xs): points.append(np.column_stack((xs + x, ys + y)))
        _snap_pixels[key] = np.concatenate(points) if points else np.empty((0, 2), dtype=int)
    points = _snap_pixels[key]
    if len(points):
        distance = ((points - (m['x'], m['y'])) ** 2).sum(axis=1)
        x, y = points[int(np.argmin(distance))]
        return int(x), int(y)
    # Some native parts have no decoded alpha evidence: retain their previous rectangle clamp.
    candidates = []
    for u0, v0, u1, v1, x, y, *_ in pages_map[m['page']]['rooms'][m['idx']]['parts']:
        if u1 < u0 or v1 < v0: continue
        cx, cy = min(max(m['x'], x), x + u1 - u0), min(max(m['y'], y), y + v1 - v0)
        candidates.append(((cx - m['x']) ** 2 + (cy - m['y']) ** 2, cx, cy))
    return min(candidates)[1:] if candidates else (m['x'], m['y'])


if __name__ == '__main__':
    main()
