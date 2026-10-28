"""Redrawn RE3 pixel icons: coverage, transparency, palette and SD visibility."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_assets import item_icon, pixel_sprite
from build_overlay import MONSTERS, MONSTER
overlay = json.loads((ROOT / 'data/overlay.json').read_text())
items = sorted({m['item'] for m in overlay['markers'] if m['kind'] in ('key', 'common', 'lock') and m['item'] < 134})
facilities = ('typewriter', 'itembox', 'map', 'document', 'key', 'diamond')
names = [f'item-{item:02x}' for item in items] + list(facilities) + ['monster-' + name for name in MONSTERS] + ['puzzle-marker', 'selection-marker']
# Keep the existing internal Dummy Key artwork, but never require it as a usable lock.
assert {p.stem for p in (ROOT / 'assets/icons').glob('*.png')} == set(names) | {'item-71'}
preview = Image.new('RGBA', (400, ((len(names) + 9) // 10) * 40), (28, 32, 35, 255))
artwork = []
for j, name in enumerate(names):
    source = Image.open(ROOT / 'assets/icons' / (name + '.png')).convert('RGBA')
    assert source.size == (32, 32) and len(source.getcolors(1024)) <= 17, name
    sp = pixel_sprite(name)
    assert sp.hd.getpixel((0, 0))[3] == 0, name
    assert sp.hd.size == (40, 40) and sp.sd.any(), name
    assert set(np.asarray(sp.hd)[..., 3].ravel()) == {0, 255}, name
    artwork.append(source.tobytes())
    preview.alpha_composite(sp.hd, ((j % 10) * 40, (j // 10) * 40))
assert len(set(artwork)) == len(artwork), 'Every icon must have its own artwork'
# Distinguishing green, blue and red herb colors survive packing.
for item, channel in ((33, 1), (34, 2), (35, 0)):
    a = np.asarray(item_icon(item).hd)
    assert (a[..., channel] > np.max(np.delete(a[..., :3], channel, axis=2), axis=2)).any(), item
preview.save(ROOT / 'assets/icons-preview.png')
heads = Image.new('RGBA', (640, 384), (28, 32, 35, 255))
draw = ImageDraw.Draw(heads)
font = ImageFont.truetype(str(ROOT / 'fonts/Pretendard-Medium.otf'), 14)
sources = json.loads((ROOT / 'assets/monster-sources.json').read_text())
assert len(sources) == len(MONSTERS)
for j, monster in enumerate(MONSTERS):
    im = Image.open(ROOT / 'assets/icons' / ('monster-' + monster + '.png')).convert('RGBA')
    x, y = (j % 4) * 160, (j // 4) * 128
    heads.alpha_composite(im.resize((96, 96), Image.Resampling.NEAREST), (x + 32, y))
    draw.text((x + 80, y + 102), sources[j]['slug'], anchor='mt', font=font, fill='white')
heads.save(ROOT / 'assets/monster-heads-preview.png')
assert {m['monster'] for m in overlay['markers'] if m['kind'] == 'enemy'} == set(MONSTERS)
for raw, expected in [('HUNTER', 'hunter'), ('HUNTER_GAMMA', 'hunter_gamma'), ('BS23', 'brain'),
                      ('BS28', 'drain'), ('MINI_BRAINSUCKER', 'brain'), ('SPIDER', 'spider'),
                      ('MINI_SPIDER', 'small_spider'), ('SLIDING_WORM', 'worm'), ('GRAVE_DIGGER', 'grave')]:
    assert next(kind for prefix, kind in MONSTER if raw.startswith(prefix)) == expected, raw
print(len(names), 'redrawn pixel icons: coverage, palette, transparency, SD visibility OK')

# Each formerly substituted key must retain its own reference-based source during repacking.
manifest = json.loads((ROOT / 'assets/manifest.json').read_text())
keys = ('75', '79', '7c', '71', '76')
assert not manifest.get('derived'), 'Recoloured key substitutes must not return'
for key in keys:
    name = 'item-' + key
    assert int(key, 16) in manifest['items']
    assert manifest['corrections'][name]['approved_variant'] == 'C'
    assert Image.open(ROOT / 'assets/icons' / (name + '.png')).convert('RGBA').tobytes() == Image.open(ROOT / 'assets/previews/key-resolution-v1/C' / (name + '-32.png')).convert('RGBA').tobytes()
assert {r['item_id'] for r in json.loads((ROOT / 'assets/key-sources.json').read_text())['items']} == set(keys)

extra = {0x0A, 0x0C, 0x19, 0x1B, 0x31, 0x33, 0x3F, 0x45, 0x46, 0x52, 0x7F}
assert extra <= set(items)
assert extra <= set(manifest['items'])

# Ammo and gems retain their original distinguishing colour after tiny-icon packing.
for item, channel in ((0x19, 0), (0x1B, 2), (0x45, 2), (0x46, 0)):
    a = np.asarray(item_icon(item).hd)
    assert (a[..., channel] > np.max(np.delete(a[..., :3], channel, axis=2), axis=2)).any(), hex(item)
