"""Cut reviewed generated artwork into 32px, 16-color, binary-alpha pixel icons."""
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def pack():
    assets = ROOT / 'assets'
    manifest = json.loads((assets / 'manifest.json').read_text())
    sheet = Image.open(assets / manifest['source_sheet']).convert('RGBA')
    xs, ys = manifest['cell_bounds_x'], manifest['cell_bounds_y']
    assert sheet.size == (xs[-1], ys[-1])
    rows = [(f'item-{item:02x}', j // 10, j % 10) for j, item in enumerate(manifest['items'])]
    rows += [(name, 5, j) for j, name in enumerate(manifest['facilities'])]
    rows += [('monster-' + name, None, None) for name in manifest.get('monsters', [])]
    rows += [(name, None, None) for name in manifest.get('markers', [])]
    hashes = {}
    for name, row, col in rows:
        correction = {}
        if row is None or name in manifest.get('corrections', {}):
            correction = manifest['corrections'][name]
            im = Image.open(assets / correction['source']).convert('RGBA').crop(correction['bounds'])
        else:
            box = (xs[col], ys[row], xs[col + 1], ys[row + 1])
            im = sheet.crop(box)
        if correction.get('prepared'):
            # Preserve the approved 32px drawing exactly when regenerating the atlas.
            assert im.size == (32, 32) and len(im.getcolors(1024)) <= 17, name
            assert set(im.getchannel('A').get_flattened_data()) <= {0, 255}, name
            out = im
        else:
            alpha = im.getchannel('A').point(lambda v: 255 if v >= 128 else 0)
            im.putalpha(alpha)
            bbox = alpha.getbbox()
            assert bbox, name
            im = im.crop(bbox)
            im.thumbnail((28, 28), Image.Resampling.NEAREST)
            alpha = im.getchannel('A')
            im = im.convert('RGB').quantize(colors=16, dither=Image.Dither.NONE).convert('RGBA')
            im.putalpha(alpha)
            out = Image.new('RGBA', (32, 32))
            out.alpha_composite(im, ((32 - im.width) // 2, (32 - im.height) // 2))
        dest = assets / 'icons' / (name + '.png')
        out.save(dest)
        hashes[name] = hashlib.sha256(dest.read_bytes()).hexdigest()
    (assets / 'icon-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(len(rows), 'pixel icons packed')


if __name__ == '__main__':
    pack()
