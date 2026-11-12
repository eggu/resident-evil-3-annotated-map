"""SD atlas for HDTextures=0 (user decisions 2026-11-12) -> src/sd_assets.h.

1x pixel markers (9x9, enemies 5x5), RE3 lock markers (body colour + pattern of the key), Galmuri9 room names and legend
with a 1 px shadow, five leader colours. CLUT rows (VRAM x 192, y 256..): 0-4 one per leader colour (shadow + ink), 5 icons, 6 legend and panel.
Pages go where the HD atlas would (no HD replacement ever matches them). Room names and leaders are fixed at build
time (user 2026-11-12) from data/sd-layout.json (tools/sd_layout.py); one colour for all (cream), placement tells them apart."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[1]
FONT = ImageFont.truetype(str(ROOT / 'fonts/Galmuri9.ttf'), 10)
PAGE, MAX_PAGES = 256, 6
# VRAM (x, y, usable height) per SD page: the HD atlas pages, then below them (game CLUT strips sit near y 480-490)
VRAM_PAGES = [(64, 0, 256), (128, 0, 256), (192, 0, 256), (256, 0, 256), (128, 256, 224), (192, 256, 224)]
TEXT = [(0, 0, 0), (8, 8, 8), (255, 240, 200), (120, 220, 255), (255, 150, 200), (170, 240, 110), (255, 180, 80),
        (250, 250, 250), (255, 205, 70), (90, 220, 255), (255, 140, 210), (255, 150, 40), (176, 112, 255), (184, 188, 196),
        (235, 60, 60), (106, 106, 106)]
SHADOW, INK, LEADER0, WHITE, GOLD, CYAN, PINK, AMBER, EVENT, COMMON_GREY, RED, DISABLED = 1, 2, 2, 7, 8, 9, 10, 11, 12, 13, 14, 15
CATEGORY = dict(all=WHITE, rooms=LEADER0, locks=GOLD, key=CYAN, docs=PINK, puzzles=AMBER, events=EVENT, common=COMMON_GREY, monsters=RED)
ICON = [(0, 0, 0), (8, 8, 8), (238, 184, 48), (176, 112, 255), (136, 232, 255), (90, 205, 90), (220, 50, 50), (80, 120, 255),
        (130, 140, 60), (195, 195, 205), (230, 190, 70), (248, 248, 248), (150, 150, 150), (140, 90, 40), (215, 190, 130), (62, 62, 70)]
LETTER = {k: i for i, k in enumerate('.kapcgrbosYwmnTX')}


def bgr555(c):
    r, g, b = (v >> 3 for v in c)
    return r | g << 5 | b << 10


def clut(p): return [0] + [bgr555(c) or 0x0421 for c in p[1:]] + [0] * (16 - len(p))
LEADERS = [(255, 240, 200), (120, 220, 255), (255, 150, 200), (170, 240, 110), (255, 180, 80)]   # tools/sd_place.py PAL


def diamond(f, glyph):
    rows = []
    for r in range(9):
        h = 4 - abs(4 - r)
        rows.append(''.join('w' if (r, c) in glyph and abs(c - 4) < h else 'k' if abs(c - 4) == h else f if abs(c - 4) < h else '.' for c in range(9)))
    return '|'.join(rows)


def herb(f): return '|'.join(['.........', '.kkkkkkk.', '.k' + f * 5 + 'k.', '..k' + f * 3 + 'k..', '..k' + f * 3 + 'k..', '...k' + f + 'k...', '...k' + f + 'k...', '....k....', '.........'])
def ammo(f): return '|'.join(['.........', '.........', '.Y.Y.Y.Y.', 'kkkkkkkkk', 'k' + f * 7 + 'k', 'k' + f * 7 + 'k', 'kkkkkkkkk', '.........', '.........'])
def grenade(f): return '...kkk...|..k' + f * 3 + 'k..|.k' + f * 5 + 'k.|.k' + f * 5 + 'k.|.knnnnnk.|.knnnnnk.|.knnnnnk.|..kkkkk..|.........'
def powder(glyph, f):
    """Gunpowder (user 2026-11-12): a tall aluminium can with its letter (A red, B yellow)."""
    g = glyph.split('|')
    return '|'.join(['..kkkkk..', '..ksssk..'] + ['..k' + ''.join(f if c == 'x' else 's' for c in r) + 'k..' for r in g] + ['..ksssk..', '..kkkkk..'])


def lock(body, sym, fg):
    """Lock: 2-row shackle, 9x7 body; sym is a 3x3 pattern ('x' = fg) or a full 7x5 interior (letters = colours)."""
    s = sym.split('|')
    if len(s) == 5:
        inner = [''.join(fg if c == 'x' else body if c == '.' else c for c in r) for r in s]
    else:
        inner = [body * 7] + [body * 2 + ''.join(fg if c == 'x' else body for c in r) + body * 2 for r in s] + [body * 7]
    return '|'.join(['..kkkkk..', '.kk...kk.', 'kkkkkkkkk'] + ['k' + r + 'k' for r in inner] + ['kkkkkkkkk'])


ICONS = {
    'puzzle': diamond('a', {(2, 4), (3, 4), (4, 4), (6, 4)}),
    'event': diamond('p', {(2, 3), (2, 4), (2, 5), (3, 5), (4, 4), (6, 4)}),
    'key': '.........|...kkk...|..kccck..|.kccccck.|.kccccck.|.kccccck.|..kccck..|...kkk...|.........',
    'herb_g': herb('g'), 'herb_r': herb('r'), 'herb_b': herb('b'),
    'ammo_handgun': ammo('r'), 'ammo_shotgun': ammo('o'), 'ammo_magnum': ammo('s'),
    'ammo_mt': '...kkk...|..krrrk..|..krrrk..|..krrrk..|..kXXXk..|..kXXXk..|..kXXXk..|..kkkkk..|.........',   # mine thrower: narrow round, red, black case
    'grenade': grenade('m'), 'grenade_acid': grenade('Y'), 'grenade_flame': grenade('r'),
    'grenade_freeze': grenade('c'),             # freeze rounds: ice-coloured grenade
    'powder_a': powder('.x.|x.x|xxx|x.x|x.x', 'r'), 'powder_b': powder('xx.|x.x|xx.|x.x|xx.', 'Y'),
    'spray': '...kkk...|...kmk...|..kkkkk..|..kwwwk..|..kwrwk..|..krrrk..|..kwrwk..|..kwwwk..|..kkkkk..',
    'ribbon': '..kkkkk..|.kmmmmmk.|kmwwwwwmk|kmwkkkwmk|kmwkmkwmk|kmwkkkwmk|kmwwwwwmk|.kmmmmmk.|..kkkkk..',
    'file': '.kkkkkk..|.kwwwwkk.|.kwkkwwk.|.kwwwwwk.|.kwkkkwk.|.kwwwwwk.|.kwkkkwk.|.kwwwwwk.|.kkkkkkk.',
    'map': '.........|kkkkkkkkk|kTrnTYnTk|kTTnTTnTk|kTTnTgnTk|kTTnTTnTk|kkkkkkkkk|.........|.........',
    'typewriter': '.........|..kkkkk..|..kwwwk..|kkkkkkkkk|kmmmmmmmk|kmXXXXXmk|kmmmmmmmk|kkkkkkkkk|.........',
    'itembox': '.........|kkkkkkkkk|knnnnnnnk|kkkkkkkkk|knnnYnnnk|knnnnnnnk|knnnnnnnk|kkkkkkkkk|.........',
    'enemy': 'kk.kk|krkrk|.krk.|krkrk|kk.kk',
}
# Lock markers by the key item that opens them (locks_final_RE3 assignment, user 2026-11-12).
LOCKS = {
    0x72: lock('s', '.x.|.x.|.x.', 'n'),                                   # Lockpick: as RE2 small key / lockpick
    0x73: lock('s', '...|xxx|...', 'w'),                                   # Warehouse Key
    0x74: lock('o', 'xxx|xxx|xxx', 'w'),                                   # Sickroom Key
    0x75: lock('Y', '.x.|xxx|.x.', 'r'),                                   # Emblem Key
    0x76: lock('b', '.YYYYY.|.Y.r.Y.|.YrYrY.|.Y.r.Y.|.YYYYY.', 'Y'),       # STARS key (BOTU)
    0x78: lock('X', '.Y...Y.|.Y...Y.|.Y...Y.|.Y...Y.|..YYY..', 'k'),       # Clock Tower (winder) key: empty brass head
    0x79: lock('X', '.Y...Y.|.YcccY.|.YcccY.|.YcccY.|..YYY..', 'k'),       # Chronos key: the same head with its glass
    0x7b: lock('Y', '...|xxx|...', 'n'), 0x7c: lock('Y', '...|xxx|...', 'n'),   # Park Key (both ids)
    0x7e: lock('s', '.......|xxxxxxx|.......|xxxxxxx|.......', 'k'),       # Facility Key
}
COMMON = {0x15: 'ammo_handgun', 0x16: 'ammo_magnum', 0x17: 'ammo_shotgun', 0x18: 'grenade', 0x19: 'grenade_flame',
          0x1a: 'grenade_acid', 0x1b: 'grenade_freeze', 0x1c: 'ammo_mt', 0x20: 'spray', 0x21: 'herb_g', 0x22: 'herb_b',
          0x23: 'herb_r', 0x61: 'powder_a', 0x62: 'powder_b', 0x81: 'ribbon'}


def icon_image(p):
    rows = p.split('|')
    a = np.zeros((len(rows), len(rows[0])), np.uint8)
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            a[y, x] = LETTER[c]
    return a


def text_image(text, colour):
    """Galmuri9, no anti-aliasing, 1 px shadow down-right; lines 11 px apart (tools/sd_layout.py LINE_H)."""
    lines = text.split('\n')
    w = max(int(FONT.getlength(l)) for l in lines) + 2
    m = Image.new('1', (w, 11 * len(lines) + 1))
    d = ImageDraw.Draw(m)
    for i, l in enumerate(lines):
        d.text((0, 11 * i), l, font=FONT, fill=1)
    g = np.array(m, np.uint8)
    a = np.zeros(g.shape, np.uint8)
    a[1:, 1:][g[:-1, :-1] > 0] = SHADOW
    a[g > 0] = colour
    ys, xs = np.nonzero(a)
    return a[:ys.max() + 1, :xs.max() + 1]


class Packer:
    def __init__(self): self.pages, self.x, self.y, self.h = [np.zeros((PAGE, PAGE), np.uint8)], 0, 0, 0
    def place(self, a):
        h, w = a.shape
        # u + w and v + h must stay below 256: the quad's far texture edge is an 8-bit coordinate (it wrapped to 0)
        if self.x + w > PAGE - 1: self.x, self.y, self.h = 0, self.y + self.h + 1, 0
        if self.y + h > VRAM_PAGES[len(self.pages) - 1][2] - 1:
            self.pages.append(np.zeros((PAGE, PAGE), np.uint8)); self.x = self.y = self.h = 0
        pg = len(self.pages) - 1
        self.pages[pg][self.y:self.y + h, self.x:self.x + w] = a
        r = (pg, self.x, self.y, w, h); self.x += w + 1; self.h = max(self.h, h)
        return r


def main():
    names = json.loads((ROOT / 'data/names.json').read_text())
    layout = json.loads((ROOT / 'data/sd-layout.json').read_text())
    sprites, index = [], {}
    def add(key, a, row):
        if key not in index:
            index[key] = len(sprites); sprites.append((a, row))
        return index[key]
    for k, p in ICONS.items(): add(('icon', k), icon_image(p), 1)
    for it, p in LOCKS.items(): add(('lock', it), icon_image(p), 1)
    add(('leader',), np.full((4, 4), INK, np.uint8), 0)   # drawn with the colour's CLUT row, sampled in the middle
    add(('panel',), np.full((4, 4), SHADOW, np.uint8), 2)
    rooms = []   # (page, idx, [(sprite, layout) English, Korean])
    for page, rs in sorted(layout.items(), key=lambda t: int(t[0])):
        for idx, by_lang in sorted(rs.items(), key=lambda t: int(t[0])):
            rooms.append((int(page), int(idx), [(add(('room', by_lang[l]['text']), text_image(by_lang[l]['text'], INK), 0), by_lang[l]) for l in ('en', 'ko')]))
    rows = ['all', 'rooms', 'locks', 'key', 'docs', 'puzzles', 'events', 'common', 'monsters']
    for r, key in zip(rows, '012345678'):
        for lang in (0, 1):
            for on in (0, 1):
                add(('legend', r, lang, on), text_image(f'[{key}] {names["legend"][r][lang]}', CATEGORY[r] if on else DISABLED), 2)
    for s in (1, 2, 3):
        for lang in (0, 1): add(('scope', s, lang), text_image(f'[9] {names["legend"][f"scope{s}"][lang]}', WHITE), 2)
    for lang in (0, 1):
        add(('lang', lang), text_image(f'[\\] {names["legend"]["language"][lang]}: {names["legend"]["lang"][lang]}', WHITE), 2)
        add(('title', lang), text_image(names['legend']['title'][lang], WHITE), 2)
        add(('hide', lang), text_image(('[~] Hide', '[~] 숨김')[lang], WHITE), 2)
        add(('fold', lang), text_image(('[~] Legend', '[~] 범례')[lang], WHITE), 2)
    packer = Packer()
    rects = [None] * len(sprites)   # tallest first: shelves fill far better than in definition order
    for i in sorted(range(len(sprites)), key=lambda i: (-sprites[i][0].shape[0], -sprites[i][0].shape[1])):
        rects[i] = packer.place(sprites[i][0])
    assert len(packer.pages) <= MAX_PAGES, f'{len(packer.pages)} SD pages; VRAM holds {MAX_PAGES}'
    sid = lambda key: index[key]
    L = ['/* generated by tools/build_sd.py from data/sd-layout.json: the SD atlas (HDTextures=0). Do not edit. */',
         f'#define SD_PAGES {len(packer.pages)}',
         'static const int16_t sd_vram[SD_PAGES][3] = {' + ','.join('{%d,%d,%d}' % v for v in VRAM_PAGES[:len(packer.pages)]) + '};   /* x, y, rows uploaded */',
         'typedef struct { uint8_t page, u, v, w, h, row; } SdSprite;   /* row: 0 ink (any leader colour row), 1 icons, 2 legend */',
         'static const uint16_t sd_cluts[7][16] = {' + ','.join('{' + ','.join(map(str, c)) + '}' for c in
             [clut([(0, 0, 0), TEXT[SHADOW], ink]) for ink in LEADERS] + [clut(ICON), clut(TEXT)]) + '};',
         'static const uint8_t sd_pixels[SD_PAGES][256 * 128] = {']
    for pg in packer.pages:
        L.append('{' + ','.join(map(str, (pg[:, 0::2] | (pg[:, 1::2] << 4)).astype(np.uint8).tobytes())) + '},')
    L.append('};')
    L.append('static const SdSprite sd_sprites[] = {' + ','.join(f'{{{p},{u},{v},{w},{h},{row}}}' for (p, u, v, w, h), (_, row) in zip(rects, sprites)) + '};')
    for k in ICONS: L.append(f'#define SD_{k.upper()} {sid(("icon", k))}')
    L.append(f'#define SD_LEADER {sid(("leader",))}')
    L.append(f'#define SD_PANEL {sid(("panel",))}')
    item = ['0xFFFF'] * 134
    for it, k in COMMON.items(): item[it] = str(sid(('icon', k)))
    for it in LOCKS: item[it] = str(sid(('lock', it)))
    L.append('static const uint16_t sd_item_icon[134] = {' + ','.join(item) + '};   /* common items and lock keys; 0xFFFF none */')
    L.append('typedef struct { uint8_t page, idx; uint16_t sprite[2]; int16_t x[2], y[2]; uint8_t colour[2], points[2]; int16_t pt[2][6]; } SdRoom;   /* x, y: name top-left */')
    out = []
    for page, idx, by in rooms:
        f = lambda k: '{' + ','.join(str(v) for v in k) + '}'
        pts = [[v for q in o['leader'][:3] for v in q] + [0] * (6 - 2 * len(o['leader'][:3])) for _, o in by]
        out.append('{%d,%d,%s,%s,%s,%s,%s,{%s,%s}}' % (page, idx, f(sp for sp, _ in by), f(o['x'] for _, o in by), f(o['y'] for _, o in by),
                   f(0 for _ in by), f(len(o['leader'][:3]) for _, o in by), f(pts[0]), f(pts[1])))
    L.append(f'#define SD_ROOM_COUNT {len(out)}')
    L.append('static const SdRoom sd_rooms[SD_ROOM_COUNT] = {' + ',\n'.join(out) + '};')
    L.append('static const uint16_t sd_legend[9][2][2] = {' + ','.join('{' + ','.join('{%d,%d}' % (sid(('legend', r, l, 0)), sid(('legend', r, l, 1))) for l in (0, 1)) + '}' for r in rows) + '};')
    L.append('static const uint16_t sd_scope[3][2] = {' + ','.join('{%d,%d}' % (sid(('scope', s, 0)), sid(('scope', s, 1))) for s in (1, 2, 3)) + '};')
    for k in ('lang', 'title', 'hide', 'fold'):
        L.append(f'static const uint16_t sd_{k}[2] = {{{sid((k, 0))},{sid((k, 1))}}};')
    (ROOT / 'src/sd_assets.h').write_text('\n'.join(L) + '\n')
    for i, pg in enumerate(packer.pages):
        lut = np.array([(0, 0, 0, 0)] + [c + (255,) for c in TEXT[1:]], np.uint8)
        Image.fromarray(lut[pg], 'RGBA').resize((PAGE * 2, PAGE * 2), Image.NEAREST).save(ROOT / f'build/sd-page{i}-text.png')
    print(f'{len(packer.pages)} SD pages, {len(sprites)} sprites, {len(out)} rooms')


if __name__ == '__main__':
    main()
