"""Fill the missing native Disused Plant header replacement using the installed HD style."""
import struct, zlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from decode_map import SIZES, tim, image
ROOT = Path(__file__).resolve().parents[1]


def build(out):
    blob = (ROOT / 'local/extracted/DATA_J/ETC2/MAP_J.MAP').read_bytes()
    seg = blob[sum(SIZES[:4]):sum(SIZES[:5])]
    header = struct.unpack_from('<9I', seg)
    rgba = np.asarray(image(tim(seg[header[7]:]))).copy()
    v = np.rint(rgba[:, :, :3].astype(float) * 31 / 255).astype('uint8')
    rgba[:, :, :3] = (v << 3) | (v >> 2)
    key = f'{zlib.crc32(rgba[:, :, [2, 1, 0, 3]].tobytes()):08X}'
    assert key == '4D420B84' and rgba.shape == (40, 256, 4)
    hd = Image.open(ROOT / 'assets/map/clock-header-reference.webp').convert('RGBA')
    assert hd.size == (1024, 160)
    hd.paste((0, 0, 0, 0), (128, 0, 704, 64))
    hd.paste((0, 0, 0, 0), (704, 64, 832, 128))  # Plant has no Clock Tower 3F glyph.
    title = Image.new('RGBA', (576, 64))
    draw = ImageDraw.Draw(title)
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf', 68)
    bounds = draw.textbbox((0, 0), 'DISUSED PLANT', font=font, stroke_width=2)
    draw.text((-bounds[0], -bounds[1]), 'DISUSED PLANT', font=font, fill='#c8c8c8', stroke_width=2, stroke_fill='#484848')
    title = title.crop((0, 0, bounds[2]-bounds[0], bounds[3]-bounds[1])).resize((576, 60), Image.Resampling.LANCZOS)
    hd.alpha_composite(title, (128, 0))
    out.mkdir(parents=True, exist_ok=True)
    hd.save(out / f'{key}.webp', lossless=True)
    return key
