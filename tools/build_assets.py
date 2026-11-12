"""Build overlay atlas pages and runtime tables.

Outputs
  src/assets.h          4bpp SD pages (256x256), CLUT, label/icon rectangles, markers, guards, room anchors
  build/hires/misc/*.webp  4x HD replacements keyed like REbirth pages: CRC32 of the page decoded to BGRA
                           through the CLUT (0 = transparent).
  build/atlas-preview/*.png
"""
import json, math, zlib, struct
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from build_overlay import MONSTERS
import room_layout
from labels import ko_item, name_lines

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / 'fonts/Pretendard-Medium.otf'
S = 4                       # HD scale
LEGEND_PX, LEGEND_STROKE = 16, 2   # every legend, hint and readout row is this one text size (the title is a heading)
PAGE = 256
PALETTE = [(0, 0, 0), (16, 16, 16), (240, 226, 190), (255, 205, 70), (90, 220, 255), (255, 150, 40),
           (106, 106, 106), (255, 255, 255), (48, 48, 48), (184, 188, 196), (235, 60, 60), (176, 112, 255),
           (90, 140, 255), (170, 120, 70), (200, 230, 200), (255, 140, 210)]
OUTLINE, CREAM, GOLD, CYAN, AMBER, GREY, WHITE, PANEL, COMMON_GREY, RED, EVENT, BLUE, BROWN, PALE, PINK = range(1, 16)   # GREY = disabled rows
HERB_GREEN = (90, 205, 90)
CATEGORY_COLOR = dict(all=WHITE, rooms=CREAM, locks=GOLD, key=CYAN, docs=PINK, puzzles=AMBER, events=EVENT, common=COMMON_GREY,
                      monsters=RED)


def bgr555(rgb):
    r, g, b = (c >> 3 for c in rgb)
    return r | g << 5 | b << 10


CLUT = [0] + [bgr555(c) or 0x0421 for c in PALETTE[1:]]


# per opacity level 10..100%: outline colour (index 1) nudged within near-black so every level has its own key
NAME_CLUTS = [[CLUT[0], (1 + (k & 3)) | (1 + (k >> 2)) << 5 | 4 << 10] + CLUT[2:] for k in range(10)]
# per icon opacity level: the same nudge with blue 3 (names use 4, the base outline 2), so no two keys collide
ICON_CLUTS = [[CLUT[0], (1 + (k & 3)) | (1 + (k >> 2)) << 5 | 3 << 10] + CLUT[2:] for k in range(10)]
MAX_PAGES = 4   # VRAM x 64..319 at y 0..255 (status-screen probe, local/internal-docs/docs/NATIVE.md)


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


_text_cache = {}


def text_sprite(text, color, px=20, stroke=3):
    """One raster per text; a two-line text ('\\n') is centred line by line."""
    key = (text, color, px, stroke)
    if key in _text_cache:
        return _text_cache[key]
    f = font(px)
    if '\n' in text:
        probe = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        l, t, r, b = (math.floor(v) if i < 2 else math.ceil(v) for i, v in
                      enumerate(probe.multiline_textbbox((0, 0), text, font=f, stroke_width=stroke, align='center')))
        im = Image.new('RGBA', (r - l + 2, b - t + 2))
        ImageDraw.Draw(im).multiline_text((1 - l, 1 - t), text, font=f, fill=PALETTE[color] + (255,), align='center',
                                          stroke_width=stroke, stroke_fill=PALETTE[OUTLINE] + (255,))
    else:
        l, t, r, b = f.getbbox(text, stroke_width=stroke)
        im = Image.new('RGBA', (r - l + 2, b - t + 2))
        ImageDraw.Draw(im).text((1 - l, 1 - t), text, font=f, fill=PALETTE[color] + (255,),
                                stroke_width=stroke, stroke_fill=PALETTE[OUTLINE] + (255,))
    _text_cache[key] = Sprite(im)
    return _text_cache[key]


LEGEND_FRAME_SD = 7   # every legend/hint/readout/value sprite is this many SD px tall (candidate 13)


def legend_baseline():
    """Baseline row (HD px, from the sprite top) shared by every legend-size sprite: the tallest bracket sits 1 px below the top."""
    t = font(LEGEND_PX).getbbox('[]gy한Q|', stroke_width=LEGEND_STROKE, anchor='ls')[1]
    return 1 - t


def legend_sprite(text, color):
    """One text size AND one sprite height for all legend, hint, readout and value lines. text_sprite() crops each line to
    its own ink, so a line without a bracket or descender came out 5 SD px tall and the others 6; the 90% legend scale then
    rounded those heights per row (5 or 6 px, glyphs visibly different sizes, user candidate 12). Here the frame and
    baseline are fixed, only the width follows the text."""
    key = ('legend_sprite', text, color)
    if key not in _text_cache:
        f = font(LEGEND_PX)
        l, _, r, _ = f.getbbox(text, stroke_width=LEGEND_STROKE, anchor='ls')
        im = Image.new('RGBA', (r - l + 2, LEGEND_FRAME_SD * S))
        ImageDraw.Draw(im).text((1 - l, legend_baseline()), text, font=f, anchor='ls', fill=PALETTE[color] + (255,),
                                stroke_width=LEGEND_STROKE, stroke_fill=PALETTE[OUTLINE] + (255,))
        _text_cache[key] = Sprite(im)
    return _text_cache[key]


def framed_sprite(text, color, px, stroke, frame_px):
    """Text on a fixed vertical frame: the height and baseline of the frame_px font, whatever the glyphs. Two texts
    framed alike share a baseline when drawn at the same top (the legend title and its [~] hint, user candidate 4)."""
    f, frame = font(px), font(frame_px)
    asc, desc = frame.getmetrics()
    pad = 3
    l, _, r, _ = f.getbbox(text, stroke_width=stroke)
    im = Image.new('RGBA', (r - l + 2, asc + desc + 2 * pad))
    ImageDraw.Draw(im).text((1 - l, pad + asc), text, font=f, anchor='ls', fill=PALETTE[color] + (255,),
                            stroke_width=stroke, stroke_fill=PALETTE[OUTLINE] + (255,))
    return Sprite(im)


# HD textures off (REbirth HDTextures=0): the atlas is drawn from its 4bpp SD pixels, where the 16 px font is
# unreadable. The notice is a hand-made 5x7 pixel font drawn 2x on the SD grid, so it is legible without HD.
NOTICE_LINES = ('HD textures off:', 'set HDTextures=1', 'in config.ini')
NOTICE_SCALE = 2
_G = {  # 5 wide; rows from the top of a 9-row cell (7 above the baseline, 2 below)
    'T': ['XXXXX'] + ['..X..'] * 6,
    'H': ['X...X'] * 3 + ['XXXXX'] + ['X...X'] * 3, 'D': ['XXXX.'] + ['X...X'] * 5 + ['XXXX.'],
    't': ['.X...', '.X...', 'XXXX.', '.X...', '.X...', '.X..X', '..XX.'],
    'e': ['', '', '.XXX.', 'X...X', 'XXXXX', 'X....', '.XXX.'], 'x': ['', '', 'X...X', '.X.X.', '..X..', '.X.X.', 'X...X'],
    'u': ['', '', 'X...X', 'X...X', 'X...X', 'X..XX', '.XXXX'], 'r': ['', '', 'X.XX.', 'XX..X', 'X....', 'X....', 'X....'],
    's': ['', '', '.XXXX', 'X....', '.XXX.', '....X', 'XXXX.'], 'o': ['', '', '.XXX.', 'X...X', 'X...X', 'X...X', '.XXX.'],
    'f': ['..XX.', '.X..X', '.X...', 'XXX..', '.X...', '.X...', '.X...'], 'c': ['', '', '.XXX.', 'X...X', 'X....', 'X...X', '.XXX.'],
    'n': ['', '', 'X.XX.', 'XX..X', 'X...X', 'X...X', 'X...X'], 'i': ['..X..', '', '.XX..', '..X..', '..X..', '..X..', '.XXX.'],
    'g': ['', '', '.XXXX', 'X...X', 'X...X', 'X...X', '.XXXX', '....X', '.XXX.'], ':': ['', '', '..X..', '', '', '..X..'],
    '=': ['', '', '', 'XXXXX', '', 'XXXXX'], '1': ['..X..', '.XX..', '..X..', '..X..', '..X..', '..X..', '.XXX.'], '.': ['', '', '', '', '', '', '..X..']}


def notice_sprite():
    k = NOTICE_SCALE
    adv, cell = (5 + 1) * k, 9 * k
    w = max(sum(adv if ch != ' ' else 3 * k for ch in line) for line in NOTICE_LINES) + 2
    h = len(NOTICE_LINES) * (cell + 2 * k) + 2
    ink = np.zeros((h, w), bool)
    for n, line in enumerate(NOTICE_LINES):
        x, y0 = 1, 1 + n * (cell + 2 * k)
        for ch in line:
            if ch == ' ':
                x += 3 * k; continue
            for r, row in enumerate(_G[ch]):
                for c, v in enumerate(row):
                    if v == 'X': ink[y0 + r * k:y0 + (r + 1) * k, x + c * k:x + (c + 1) * k] = True
            x += adv
    pad = np.pad(ink, 1)
    edge = np.zeros_like(ink)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            edge |= pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
    sd = np.zeros((h, w, 4), np.uint8)
    sd[edge & ~ink] = PALETTE[OUTLINE] + (255,)
    sd[ink] = PALETTE[WHITE] + (255,)
    return Sprite(Image.fromarray(sd, 'RGBA').resize((w * S, h * S), Image.NEAREST))


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
    def c(i): return (PALETTE[i] if isinstance(i, int) else i) + (255,)
    q = n / 10
    if kind == 'star':
        import math
        pts = [(n / 2 + (0.48 if k % 2 == 0 else 0.2) * n * math.sin(k * math.pi / 5),
                n / 2 - (0.48 if k % 2 == 0 else 0.2) * n * math.cos(k * math.pi / 5)) for k in range(10)]
        d.polygon(pts, fill=c(CYAN), outline=o, width=S)
    elif kind == 'ammo':
        for x in (2, 4.5, 7):
            d.rectangle([q * (x - 0.9), q * 3, q * (x + 0.9), q * 9], fill=c(GOLD), outline=o, width=S)
            d.ellipse([q * (x - 0.9), q * 1.5, q * (x + 0.9), q * 4.5], fill=c(COMMON_GREY), outline=o, width=S)
    elif kind in ('herb_g', 'herb_r', 'herb_b'):
        col = {'herb_g': HERB_GREEN, 'herb_r': RED, 'herb_b': BLUE}[kind]
        d.ellipse([q, q * 3, q * 5.5, q * 7.5], fill=c(col), outline=o, width=S)
        d.ellipse([q * 4.5, q * 3, q * 9, q * 7.5], fill=c(col), outline=o, width=S)
        d.ellipse([q * 2.7, q * 0.8, q * 7.3, q * 5], fill=c(col), outline=o, width=S)
        d.rectangle([q * 4.4, q * 6, q * 5.6, q * 9.5], fill=c(HERB_GREEN), outline=o, width=S)
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


MARK_COLOR = dict(key=CYAN, lock=GOLD, file=PINK, map=PINK, common=COMMON_GREY, puzzle=AMBER)
MARK_CATS = ['key', 'lock', 'file', 'map', 'common', 'puzzle']
MODIFIERS = ('Shift', 'Ctrl')


def item_text(names, item, lang):
    en, ko = names['items'][str(item)]
    return ko_item(ko) if lang else en


# Puzzle markers are named after the puzzle (data/puzzle-names.json), not the item they need (user 2026-11-07).
# Name ids start above every item id so (kind, id) stays one lookup key in the ASI; unresolved puzzles keep the item id.
PUZZLE_NAME_BASE = 150


def puzzle_names(root=ROOT):
    table = json.loads((root / 'data/puzzle-names.json').read_text())
    pairs = sorted({(v['en'], v['ko']) for v in table['names'].values()})
    ids = {pair: PUZZLE_NAME_BASE + i for i, pair in enumerate(pairs)}
    assert PUZZLE_NAME_BASE + len(pairs) <= 255
    return {k: ids[v['en'], v['ko']] for k, v in table['names'].items()}, {i: p for p, i in ids.items()}


def puzzle_key(m):
    return f"{m['rdt']}/{m.get('aot', '-')}/{m.get('item', '-')}"


def mark_text(names, pz_text, cat, ident, lang):
    if cat == 'puzzle' and ident >= PUZZLE_NAME_BASE:
        en, ko = pz_text[ident]
        return ko_item(ko) if lang else en
    return item_text(names, ident, lang)


def with_area_names(overlay, names):
    """Areas named only for orientation (data/sd-extra-names.json, user 2026-11-13: Uptown's police station block, HD
    and SD) go after the real rooms so the room count skips them (ROOM_NAMED_COUNT)."""
    extra = [(int(pg), int(i), n) for pg, rs in json.loads((ROOT / 'data/sd-extra-names.json').read_text()).items()
             if not pg.startswith('_') for i, n in rs.items()]
    rooms = [r for r in overlay['rooms'] if r['name']]
    return ({**overlay, 'rooms': rooms + [dict(page=pg, idx=i, name=n['en']) for pg, i, n in extra], 'named_rooms': len(rooms)},
            {**names, 'rooms': {**names['rooms'], **{n['en']: n['ko'] for _, _, n in extra}}})


def main():
    names = json.loads((ROOT / 'data/names.json').read_text())
    overlay = json.loads((ROOT / 'data/overlay.json').read_text())
    pages_map = json.loads((ROOT / 'data/map-pages.json').read_text())
    overlay, names = with_area_names(overlay, names)
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
    layout = room_layouts(overlay, pages_map, names)
    for (page, idx, lang), o in sorted(layout.items()):
        add(('room', o['text'], lang), text_sprite(o['text'], CREAM, 20))
    add(('notice',), notice_sprite())
    add(('leader',), Sprite(Image.new('RGBA', (S, S), PALETTE[CREAM] + (255,))))
    # Every named marker: its item's name in the category colour, one sprite per line (RE0 wrapping).
    pz_ids, pz_text = puzzle_names()
    mark_names = sorted({(m['kind'], pz_ids.get(puzzle_key(m)) if m['kind'] == 'puzzle' and puzzle_key(m) in pz_ids else m['item'])
                         for m in overlay['markers'] if m['kind'] in MARK_CATS
                         and (puzzle_key(m) in pz_ids or (0 < m.get('item', 0) and str(m['item']) in names['items']))})
    for cat, it in mark_names:
        for lang in (0, 1):
            for n, line in enumerate(name_lines(mark_text(names, pz_text, cat, it, lang))):
                add(('mark', cat, it, lang, n), text_sprite(line, MARK_COLOR[cat], 18))
    legend_rows = ['all', 'rooms', 'locks', 'key', 'docs', 'puzzles', 'events', 'common', 'monsters']
    keys = '012345678'
    for row, key in zip(legend_rows, keys):
        for lang in (0, 1):
            for on in (0, 1):
                add(('legend', row, lang, on), legend_sprite(f'[{key}] {names["legend"][row][lang]}', CATEGORY_COLOR[row] if on else GREY))
    for s in (1, 2, 3):
        for lang in (0, 1):
            add(('legend', f'scope{s}', lang, 1), legend_sprite(f'[9] {names["legend"][f"scope{s}"][lang]}', WHITE))
    # Hints, RE0 candidate 49 format: a lone key in brackets, '·' between alternatives, '+' for combinations.
    hints = dict(hide=('[~] Hide', '[~] 숨김'), fold=('[~] Legend', '[~] 범례'),
                 names=(('[H] Item names: Off', '[H] Item names: All', '[H] Item names: No common'),
                        ('[H] 아이템 이름: 끔', '[H] 아이템 이름: 모두', '[H] 아이템 이름: 일반 제외')))
    readout = (('[ · ] Name opacity', '[ · ] 이름 불투명도'), ('- · + Name size', '- · + 이름 크기'),
               ('{} + [ · ] Icon opacity', '{} + [ · ] 아이콘 불투명도'), ('{} + - · + Icon size', '{} + - · + 아이콘 크기'))
    for lang in (0, 1):
        # [\\] language, same size and colour as the [H] item-names label: '[\\] Language: English' / '[\\] 언어: 한국어'
        add(('legend', 'lang', lang, 1), legend_sprite(f'[\\] {names["legend"]["language"][lang]}: {names["legend"]["lang"][lang]}', WHITE))
        add(('legend', 'title', lang, 1), framed_sprite(names['legend']['title'][lang], WHITE, 22, 3, 22))
        add(('hint', 'hide', lang), framed_sprite(hints['hide'][lang], WHITE, LEGEND_PX, LEGEND_STROKE, 22))   # on the title's baseline
        add(('hint', 'fold', lang), legend_sprite(hints['fold'][lang], WHITE))
        for state in range(3):   # 0 off, 1 all, 2 no common items
            add(('hint', 'names', lang, state), legend_sprite(hints['names'][lang][state], WHITE if state else GREY))
        for mod in range(len(MODIFIERS)):
            for row, text in enumerate(readout):
                add(('readout', row, lang, mod), legend_sprite(text[lang].format(MODIFIERS[mod]), WHITE))
    for value in range(10, 201, 10):
        add(('value', value), legend_sprite(f'{value}%', GOLD))
    # Names live on their own pages: their HD replacement bakes in the name opacity (REbirth blends HD alpha),
    # one HD file per 10% level, told apart by a CLUT whose outline colour differs invisibly per level.
    # Icons share the other pages with the legend: the icon CLUT row gives those pages one more HD file per
    # icon opacity level, while the legend keeps the base CLUT and its opaque file.
    is_name = [False] * len(sprites)
    for key, i in index.items():
        if key[0] in ('room', 'mark', 'leader'):
            is_name[i] = True
    packers = (Packer(), Packer())
    rects = [packers[n].place(sp) for sp, n in zip(sprites, is_name)]
    first_name_page = len(packers[0].pages)
    rects = [((pg + first_name_page) if n else pg, uv) for (pg, uv), n in zip(rects, is_name)]
    npages = first_name_page + len(packers[1].pages)
    assert npages <= MAX_PAGES, f'{npages} atlas pages; VRAM x 64..319 holds {MAX_PAGES}'
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
        assert not (out / f'hires/misc/{key}.webp').exists(), f'HD key collision {key}'
        image.save(out / f'hires/misc/{key}.webp', lossless=True)
        keys_out.append(f'{pg}{tag}:{key}')
        return lut
    def faded(pg, level):
        a = np.asarray(hd[pg]).copy()
        a[..., 3] = (a[..., 3].astype(np.uint16) * level // 10).astype(np.uint8)
        return Image.fromarray(a, 'RGBA')
    for pg in range(npages):
        if pg < first_name_page:
            lut = save(pg, CLUT, hd[pg], '')
            for level in range(1, 11):
                save(pg, ICON_CLUTS[level - 1], faded(pg, level), f'i{level * 10}')
        else:
            for level in range(1, 11):
                lut = save(pg, NAME_CLUTS[level - 1], faded(pg, level), f'@{level * 10}')
        Image.fromarray(lut[sd[pg]], 'RGBA').resize((PAGE * 2, PAGE * 2), Image.NEAREST).save(out / f'atlas-preview/page{pg}-sd.png')
        hd[pg].save(out / f'atlas-preview/page{pg}-hd.png')
    global LAST_BUILD
    LAST_BUILD = (sprites, index)   # tests/test_legend_size.py measures every legend-size sprite
    write_header(sd, rects, sprites, index, overlay, pages_map, layout, mark_names, legend_rows, keys_out, first_name_page)
    from build_map_header import build as build_map_header
    build_map_header(out / "hires/misc")
    print(npages, 'pages', len(sprites), 'sprites', len(keys_out), 'HD files')


def room_cells(room, shared, page):
    """Pixels of a room's own shape: opaque texels of its parts, building outlines several rooms share excluded."""
    ps = [p for p in room['parts'] if p[2] >= p[0] and p[3] >= p[1] and p[6] != 7 and tuple(p[:6]) not in shared] or \
         [p for p in room['parts'] if p[2] >= p[0] and p[3] >= p[1] and p[6] != 7]
    alpha, cells = tim_alpha(page), set()
    for u0, v0, u1, v1, x, y, _t, attr in (p[:8] for p in ps):
        o = tex_offset(attr)
        ys, xs = np.nonzero(part_layer(alpha, u0 + o, v0, u1 + o, v1, attr))
        cells |= {(int(a + x), int(b + y)) for a, b in zip(xs, ys)}
    if not cells:
        for u0, v0, u1, v1, x, y in (p[:6] for p in ps):
            cells |= {(x + i, y + j) for j in range(v1 - v0 + 1) for i in range(u1 - u0 + 1)}
    return cells


def room_layouts(overlay, pages_map, names):
    """{(page, idx, lang): dict(text, x, y, line)} from tools/room_layout.py; defects stop the build."""
    out, defects = {}, []
    for page in sorted({r['page'] for r in overlay['rooms'] if r['name']}):
        rooms = [r for r in overlay['rooms'] if r['name'] and r['page'] == page]
        allparts = [tuple(p[:6]) for q in pages_map[page]['rooms'] for p in q['parts']]
        shared = {p for p in allparts if allparts.count(p) > 1}
        cells = {r['idx']: room_cells(pages_map[page]['rooms'][r['idx']], shared, page) for r in rooms}
        for lang in (0, 1):
            rows = [dict(key=r['idx'], name=names['rooms'][r['name']] if lang else r['name'], cells=cells[r['idx']]) for r in rooms]
            size_of = lambda text: (text_sprite(text, CREAM, 20).w, text_sprite(text, CREAM, 20).h)
            placed = room_layout.place_page(rows, size_of)   # RE0 rule 11: markers are not an input
            defects += [f'page {page} {"ko" if lang else "en"}: {d}' for d in room_layout.check_page(rows, placed, size_of)]
            for idx, o in placed.items():
                out[page, idx, lang] = o
    (ROOT / 'build').mkdir(exist_ok=True)
    (ROOT / 'build/room-layout-report.txt').write_text('\n'.join(defects) + '\n')
    assert not [d for d in defects if 'forced' not in d and 'long leader' not in d], defects
    leaders = sum(1 for o in out.values() if o['line'])
    print(f'room names: {len(out)} placed, {leaders} with leaders, {sum(1 for o in out.values() if chr(10) in o["text"])} wrapped; {defects}')
    return out


_tims = {}


def tex_offset(attr):
    """Part attribute bit 1 selects the right half of the 512-texel map TIM (u + 256), as the game draws the Park map."""
    return 256 * ((attr >> 1) & 1)


def tim_alpha(page):
    """Texel indices of the map TIM (local/map-preview/page<n>-tim-index.png from tools/decode_map.py)."""
    if page not in _tims:
        _tims[page] = np.asarray(Image.open(ROOT / f'local/map-preview/page{page}-tim-index.png'))
    return _tims[page]


def part_layer(idx, u0, v0, u1, v1, attr):
    """Drawn texels of a map part: each 4bpp texel holds two 2-bit layers and attr bit 0 picks the high one (the game's
    CLUT rows 8-15); value 0 is transparent. Park's big frame polygons are outlines only in that layer."""
    t = idx[v0:v1 + 1, u0:u1 + 1]
    return ((t >> 2) if attr & 1 else (t & 3)) > 0


def anchor(room, shared, page, w, h):
    """Label anchor: the room pixel farthest from the room's edge (map space). Rooms are drawn as textured
    rectangles whose transparent texels carve the real shape (a corridor rectangle can enclose another room),
    so the mask uses the texture's opaque texels; parts several rooms share (building outlines) are ignored."""
    ps = [p for p in room['parts'] if p[2] >= p[0] and p[3] >= p[1] and p[6] != 7 and tuple(p[:6]) not in shared] or \
         [p for p in room['parts'] if p[2] >= p[0] and p[3] >= p[1] and p[6] != 7]
    x0 = min(p[4] for p in ps); y0 = min(p[5] for p in ps)
    x1 = max(p[4] + p[2] - p[0] + 1 for p in ps); y1 = max(p[5] + p[3] - p[1] + 1 for p in ps)
    mask = np.zeros((y1 - y0 + 2, x1 - x0 + 2), bool)
    alpha = tim_alpha(page)
    for u0, v0, u1, v1, x, y, _t, attr in (p[:8] for p in ps):
        o = tex_offset(attr)
        mask[y - y0 + 1:y - y0 + 2 + v1 - v0, x - x0 + 1:x - x0 + 2 + u1 - u0] |= part_layer(alpha, u0 + o, v0, u1 + o, v1, attr)
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


def write_header(sd, rects, sprites, index, overlay, pages_map, layout, mark_names, legend_rows, keys, first_name_page):
    L = ['/* Generated by tools/build_assets.py; do not edit. */', '#pragma once', '#include <stdint.h>',
         f'#define ATLAS_PAGES {len(sd)}', f'/* HD keys: {" ".join(keys)} */',
         'static const uint16_t atlas_clut[16] = {' + ','.join(f'0x{c:04x}' for c in CLUT) + '};',
         f'#define NAME_PAGE_FIRST {first_name_page}',
         'static const uint16_t name_cluts[10][16] = {' + ','.join('{' + ','.join(f'0x{c:04x}' for c in cl) + '}' for cl in NAME_CLUTS) + '};',
         'static const uint16_t icon_cluts[10][16] = {' + ','.join('{' + ','.join(f'0x{c:04x}' for c in cl) + '}' for cl in ICON_CLUTS) + '};',
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
    L.append(f"#define LEADER_SPRITE {index[('leader',)]}")
    L.append(f"#define NOTICE_SPRITE {index[('notice',)]}")
    L.append(f'#define MONSTER_COUNT {len(MONSTERS)}')
    L.append('static const uint16_t monster_icons[MONSTER_COUNT] = {' + ','.join(str(index[('monster', monster)]) for monster in MONSTERS) + '};')
    L.append('static const uint16_t item_icons[134] = {' + ','.join(str(index.get(('item_icon', it), index[('icon', 'ammo' if it in COMMON_AMMO else 'diamond')])) for it in range(134)) + '};')
    # Rooms: fixed name centre (x2/y2 = 2x map px at name size 100, native zoom 100) and an optional leader.
    rooms = [r for r in overlay['rooms'] if r['name']]
    L.append('typedef struct { uint8_t page, idx, lead[2]; int16_t x2[2], y2[2]; uint16_t label[2]; int16_t line[2][4]; } RoomLabel;')
    L.append(f'#define ROOM_COUNT {len(rooms)}')
    L.append(f'#define ROOM_NAMED_COUNT {overlay["named_rooms"]}   /* rooms after this are area names (data/sd-extra-names.json) */')
    rows = []
    for r in rooms:
        o = [layout[r['page'], r['idx'], lang] for lang in (0, 1)]
        line = [list(q['line'] or (0, 0, 0, 0)) for q in o]
        rows.append(f'{{{r["page"]},{r["idx"]},{{{int(bool(o[0]["line"]))},{int(bool(o[1]["line"]))}}},'
                    f'{{{round(o[0]["x"] * 2)},{round(o[1]["x"] * 2)}}},{{{round(o[0]["y"] * 2)},{round(o[1]["y"] * 2)}}},'
                    f'{{{index[("room", o[0]["text"], 0)]},{index[("room", o[1]["text"], 1)]}}},'
                    f'{{{{{",".join(map(str, line[0]))}}},{{{",".join(map(str, line[1]))}}}}}}}')
    L.append('static const RoomLabel room_labels[ROOM_COUNT] = {' + ','.join(rows) + '};')
    kinds = ['typewriter', 'itembox', 'lock', 'key', 'file', 'map', 'puzzle', 'common', 'enemy', 'room', 'live']
    L.append('#define NO_LINE 0xFFFF')
    L.append('typedef struct { uint8_t kind, item; uint16_t line[2][2]; } MarkName;   /* [lang][line] */')
    L.append(f'#define MARK_NAME_COUNT {len(mark_names)}')
    L.append('static const MarkName mark_names[MARK_NAME_COUNT] = {' + ','.join(
        f'{{{kinds.index(cat)},{it},{{' + ','.join('{' + ','.join(str(index.get(('mark', cat, it, lang, n), 0xFFFF)) for n in (0, 1)) + '}' for lang in (0, 1)) + '}}'
        for cat, it in mark_names) + '};')
    leg = []
    for row in legend_rows:
        leg.append('{' + ','.join(f'{{{index[("legend", row, lang, 0)]},{index[("legend", row, lang, 1)]}}}' for lang in (0, 1)) + '}')
    L.append('static const uint16_t legend_sprites[9][2][2] = {' + ','.join(leg) + '};')
    L.append('static const uint16_t legend_scope[3][2] = {' + ','.join(
        f'{{{index[("legend", f"scope{s}", 0, 1)]},{index[("legend", f"scope{s}", 1, 1)]}}}' for s in (1, 2, 3)) + '};')
    L.append(f'static const uint16_t legend_lang[2] = {{{index[("legend", "lang", 0, 1)]},{index[("legend", "lang", 1, 1)]}}};')
    L.append(f'static const uint16_t legend_title[2] = {{{index[("legend", "title", 0, 1)]},{index[("legend", "title", 1, 1)]}}};')
    L.append(f'static const uint16_t hint_hide[2] = {{{index[("hint", "hide", 0)]},{index[("hint", "hide", 1)]}}};')
    L.append(f'static const uint16_t hint_fold[2] = {{{index[("hint", "fold", 0)]},{index[("hint", "fold", 1)]}}};')
    L.append('static const uint16_t hint_names[2][3] = {' + ','.join('{' + ','.join(str(index[("hint", "names", lang, st)]) for st in range(3)) + '}' for lang in (0, 1)) + '};   /* [lang][off, all, no common] */')
    L.append('static const uint16_t readout_hints[4][2][2] = {' + ','.join(
        '{' + ','.join('{' + ','.join(str(index[('readout', row, lang, mod)]) for mod in (0, 1)) + '}' for lang in (0, 1)) + '}' for row in range(4)) + '};   /* [row][lang][modifier] */')
    L.append('static const uint16_t value_sprites[20] = {' + ','.join(str(index[('value', v)]) for v in range(10, 201, 10)) + '};   /* 10%..200% */')
    # markers + guards
    lits, clauses, rows, far, pids = [], [], [], [], []
    pz_ids, _ = puzzle_names()
    for m in overlay['markers']:
        if m['kind'] == 'enemy' and [] in m['guard']:
            continue
        x, y = snap(m, pages_map)
        if m['kind'] == 'lock' and m.get('far') and m['far'][0] == m['page']:
            fx, fy = far_point(m, (x, y), pages_map)
            far.append(f'{{{len(rows)},{m["far"][1]},{fx},{fy}}}')
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
        pids.append(pz_ids.get(puzzle_key(m), 0) if m['kind'] == 'puzzle' else 0)
    L.append('enum { K_TYPEWRITER, K_ITEMBOX, K_LOCK, K_KEY, K_FILE, K_MAP, K_PUZZLE, K_COMMON, K_ENEMY, K_ROOM, K_LIVE };')
    L.append('enum { ' + ', '.join('M_' + monster.upper() for monster in MONSTERS) + ' };')
    L.append('typedef struct { uint8_t kind, page, idx, sets /* bit0 DATA_J, bit1 DATA_AJ, bit2 room badge, bits4-6 RDT stage */; int16_t x, y; uint8_t extra, flag; uint16_t clause, nclause; } Marker;')
    L.append(f'#define MARKER_COUNT {len(rows)}')
    L.append('static const Marker markers[MARKER_COUNT] = {' + ','.join(rows) + '};')
    L.append('/* puzzle marker name id (a MarkName item of kind K_PUZZLE); 0 keeps the item name */')
    L.append('static const uint8_t puzzle_names[MARKER_COUNT] = {' + ','.join(map(str, pids)) + '};')
    L.append('/* RE1 HD lock style (INI LockMarker=Unvisited): the door trigger on the destination side, same page. */')
    L.append('typedef struct { uint16_t marker; uint8_t idx; int16_t x, y; } LockFar;')
    L.append(f'#define LOCK_FAR_COUNT {len(far)}')
    L.append('static const LockFar lock_far[] = {' + (','.join(far) or '{0xFFFF,0,0,0}') + '};')
    L.append('typedef struct { uint8_t bank, bit; int16_t value; } Literal;')
    L.append('static const Literal literals[] = {' + (','.join(f'{{{b},{n},{v}}}' for b, n, v in lits) or '{0,0,0}') + '};')
    L.append('typedef struct { uint16_t first, count; } Clause;')
    L.append('static const Clause clauses[] = {' + (','.join(f'{{{a},{b}}}' for a, b in clauses) or '{0,0}') + '};')
    (ROOT / 'src/assets.h').write_text('\n'.join(L) + '\n')


FAR_MIN = 6   # map px: the destination-side point is a marker's width away from the door point


def far_point(m, door, pages_map):
    """Nearest pixel of the destination room's own shape to its door trigger, at least FAR_MIN from the door."""
    page, idx, fx, fy = m['far']
    probe = dict(page=page, idx=idx, x=fx, y=fy)
    snap(probe, pages_map)
    points = _snap_pixels[(id(pages_map), page, idx)]
    if not len(points):
        return fx, fy
    far = points[((points - door) ** 2).sum(axis=1) >= FAR_MIN ** 2]
    if not len(far):
        return snap(probe, pages_map)
    x, y = far[int(np.argmin(((far - (fx, fy)) ** 2).sum(axis=1)))]
    return int(x), int(y)


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
        for u0, v0, u1, v1, x, y, _t, attr, *_ in own:
            o = tex_offset(attr)
            ys, xs = np.nonzero(part_layer(alpha, u0 + o, v0, u1 + o, v1, attr))
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
