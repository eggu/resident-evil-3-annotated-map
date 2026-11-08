"""Legend title and its [~] hint share a baseline in both languages (user, candidate 4: '[~] 숨김' sat off the
'지도 메모' line). Renders the actual sprites from tools/build_assets.py and compares the ink bottoms of words without
descenders; a hint cropped to its own ink box, as before candidate 5, fails."""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_assets as B

names = json.loads((ROOT / 'data/names.json').read_text())
HIDE = ('[~] Hide', '[~] 숨김')   # as in build_assets.main


def word_bottom(sprite, text, word, px, stroke):
    """Lowest inked HD row under `word` (the last word of `text`), via the font's advance to that word."""
    f = B.font(px)
    l = f.getbbox(text, stroke_width=stroke)[0]
    x0 = int(f.getlength(text[:text.rindex(word)])) + 1 - l
    a = np.asarray(sprite.hd)[:, x0 + stroke:, 3] > 127
    return int(np.nonzero(a.any(1))[0].max())


for lang, (title_word, hide_word) in enumerate((('Notes', 'Hide'), ('메모', '숨김'))):
    title_text = names['legend']['title'][lang]
    title = B.framed_sprite(title_text, B.WHITE, 22, 3, 22)
    hide = B.framed_sprite(HIDE[lang], B.WHITE, 16, 2, 22)
    assert (title.w, title.h)[1] == hide.h, (title.h, hide.h)   # drawn at the same top by src/re3_map.c legend()
    tb, hb = word_bottom(title, title_text, title_word, 22, 3), word_bottom(hide, HIDE[lang], hide_word, 16, 2)
    assert abs(tb - hb) <= 2, (lang, tb, hb)   # strokes 3 vs 2 HD px
    # control: candidate 4's ink-cropped sprites, hint centred on the title in SD px (4 HD px each)
    old_t, old_h = B.text_sprite(title_text, B.WHITE, 22), B.text_sprite(HIDE[lang], B.WHITE, 16, stroke=2)
    off = (old_t.h - old_h.h) // 2 * B.S
    old_gap = abs(word_bottom(old_t, title_text, title_word, 22, 3) - (off + word_bottom(old_h, HIDE[lang], hide_word, 16, 2)))
    print(['en', 'ko'][lang], 'baseline offset HD px: candidate 4', old_gap, '-> now', abs(tb - hb))
    assert old_gap > 2 or not lang, old_gap   # the check sees the reported Korean offset
print('legend title/hint baseline OK (en, ko)')
