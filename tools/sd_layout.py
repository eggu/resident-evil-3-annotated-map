"""SD room-name layout for every map page and language -> data/sd-layout.json (map coordinates).

Inputs: data/overlay.json, data/map-pages.json, data/names.json, local/map-preview/page<n>(-tim).png (tools/decode_map.py)
and fonts/Galmuri9.ttf. Slow (minutes): run when names, rooms, marks or the rules change, then tools/build_sd.py.
Small pages (the whole map fits 320x240 at zoom 100) are laid out on the centred screen; larger pages on the map itself."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFont
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import room_layout
exec((ROOT / 'tools/sd_place.py').read_text())   # place(), abbr(), colour(), PAL

FONT = ImageFont.truetype(str(ROOT / 'fonts/Galmuri9.ttf'), 10)
LINE_H = 11   # 10 px Galmuri9 + 1 px shadow
LEADER_INSET = 3   # leaders start this far inside their room
SCREEN_W, SCREEN_H = 320, 240
FLOORS = json.loads((ROOT / 'data/sd-floors.json').read_text())


def size_of(text):
    lines = text.split('\n')
    return max(int(FONT.getlength(l)) for l in lines) + 1, LINE_H * len(lines)


def tim_alpha(page):
    return np.asarray(Image.open(ROOT / f'local/map-preview/page{page}-tim-index.png'))


def part_layer(idx, u0, v0, u1, v1, attr, values=False):
    """Drawn texels of a map part (tools/build_assets.py part_layer): attr bit 0 picks the high 2-bit layer."""
    t = idx[v0:v1 + 1, u0:u1 + 1]
    t = (t >> 2) if attr & 1 else (t & 3)
    return t if values else t > 0


def tex_offset(attr):
    """Part attribute bit 1 selects the right half of the 512-texel map TIM (u + 256); seen against the game's Park map."""
    return 256 * ((attr >> 1) & 1)


def room_cells(room, shared, alpha):
    """Same rule as tools/build_assets.py room_cells: opaque texels of the room's own parts."""
    ps = [p for p in room['parts'] if p[2] >= p[0] and p[3] >= p[1] and p[6] != 7 and tuple(p[:6]) not in shared] or \
         [p for p in room['parts'] if p[2] >= p[0] and p[3] >= p[1] and p[6] != 7]
    cells = set()
    for u0, v0, u1, v1, x, y, _t, attr in (p[:8] for p in ps):
        o = tex_offset(attr)
        ys, xs = np.nonzero(part_layer(alpha, u0 + o, v0, u1 + o, v1, attr))
        cells |= {(int(a + x), int(b + y)) for a, b in zip(xs, ys)}
    if not cells:
        for u0, v0, u1, v1, x, y in (p[:6] for p in ps):
            cells |= {(x + i, y + j) for j in range(v1 - v0 + 1) for i in range(u1 - u0 + 1)}
    return cells


def edge_mids(own):
    """Middle pixel of every straight edge run (3 px or longer) of the room, with its outward direction. A side with no
    such run (a diamond-shaped room, a stair stub) still offers the middle of its longest run."""
    out = []
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        key = (lambda c: (c[1], c[0])) if dy else (lambda c: (c[0], c[1]))
        edge = sorted((c for c in own if (c[0] + dx, c[1] + dy) not in own), key=key)
        run, runs = [], []
        for c in edge + [None]:
            if c is not None and run and key(c)[0] == key(run[-1])[0] and key(c)[1] == key(run[-1])[1] + 1:
                run.append(c); continue
            if run: runs.append(run)
            run = [c] if c is not None else []
        long = [r for r in runs if len(r) >= 3] or ([max(runs, key=len)] if runs else [])
        for r in long:   # start a little inside the room (user 2026-11-12), as far as the room allows
            x, y = r[len(r) // 2]
            k = 0
            while k < LEADER_INSET and (x - dx * (k + 1), y - dy * (k + 1)) in own: k += 1
            out.append(((x - dx * k, y - dy * k), (dx, dy)))
    return out


# Small pages (no zoom): the screen furniture of the native map, as seen in SD (user 2026-11-12): title, compass, the four
# green arrows, the scale and the folded legend. Names keep out of these boxes (x, y, w, h on the 320x240 screen).
HUD = [(10, 8, 206, 34), (270, 8, 44, 54), (150, 20, 20, 22), (150, 196, 20, 22), (20, 110, 22, 22), (278, 110, 22, 22),
       (176, 202, 138, 26), (2, 218, 66, 22),
       (0, 0, 320, 6), (0, 228, 320, 12), (0, 0, 6, 240), (314, 0, 6, 240)]   # screen edges: the map may sit a few px off centre


def floors_of(cells):
    """Floors of one map page (the game shows each floor on its own screen, e.g. Dead Factory 1F / 2F): rooms whose
    pixels touch belong to the same floor, rooms overlapping (> 20% of the smaller) to different ones. Groups are
    2-coloured over their overlaps; a group overlapping nothing is on every floor (-1)."""
    keys = sorted(k for k in cells if cells[k])
    over = lambda a, b: len(cells[a] & cells[b]) > .2 * min(len(cells[a]), len(cells[b]))
    grown = {k: {(x + i, y + j) for x, y in cells[k] for i in (-1, 0, 1) for j in (-1, 0, 1)} for k in keys}
    parent = {k: k for k in keys}
    def find(k):
        while parent[k] != k: parent[k] = parent[parent[k]]; k = parent[k]
        return k
    conflicts = [(a, b) for a in keys for b in keys if a < b and over(a, b)]
    bad = {frozenset(p) for p in conflicts}
    for a in keys:
        for b in keys:
            if a < b and frozenset((a, b)) not in bad and grown[a] & cells[b] and find(a) != find(b):
                ga, gb = find(a), find(b)   # merge unless that would put an overlapping pair on one floor
                if not any({find(x), find(y)} == {ga, gb} or (find(x) == find(y) == ga) for x, y in conflicts):
                    parent[gb] = ga
    groups = {find(k) for k in keys}
    gconf = {g: {find(b) if find(a) == g else find(a) for a, b in conflicts if g in (find(a), find(b))} - {g} for g in groups}
    floor_of = {}
    for g in sorted(groups, key=lambda g: -len(gconf[g])):
        if not gconf[g]: floor_of[g] = -1; continue
        taken = {floor_of[o] for o in gconf[g] if o in floor_of}
        floor_of[g] = next(f for f in range(8) if f not in taken)
    return {k: floor_of[find(k)] for k in keys} | {k: -1 for k in cells if k not in parent}


def page_layout(page, overlay, pages_map, names, langs=('ko', 'en')):
    bx0, by0, bx1, by1 = pages_map[page]['bounds']
    small = bx1 - bx0 <= SCREEN_W and by1 - by0 <= SCREEN_H
    sx, sy = ((SCREEN_W - (bx1 - bx0)) // 2 - bx0, (SCREEN_H - (by1 - by0)) // 2 - by0) if small else (-bx0, -by0)
    W, H = (SCREEN_W, SCREEN_H) if small else (bx1 - bx0, by1 - by0)
    shift = lambda cs: {(x + sx, y + sy) for x, y in cs}
    allparts = [tuple(p[:6]) for q in pages_map[page]['rooms'] for p in q['parts']]
    shared = {p for p in allparts if allparts.count(p) > 1}
    alpha = tim_alpha(page)   # texel indices
    all_rooms = {q['index']: q for q in pages_map[page]['rooms'] if q['parts']}
    cells = {i: shift(room_cells(q, shared, alpha)) for i, q in all_rooms.items()}
    floor = floors_of(cells) if page in FLOORS['floor_pages'] else {i: -1 for i in cells}
    for f, room_names in enumerate(FLOORS.get(str(page), {}).values()):   # screenshot-confirmed floors win
        for r in overlay['rooms']:
            if r['page'] == page and r['name'] in room_names and r['idx'] in floor: floor[r['idx']] = f
    floors = sorted({f for f in floor.values() if f >= 0}) or [0]
    def picture(idxs):   # map pixels and grey outline pixels drawn for these rooms (all their parts)
        pix, grey = set(), set()
        for i in idxs:
            for u0, v0, u1, v1, x, y, _t, attr in (p[:8] for p in all_rooms[i]['parts'] if p[2] >= p[0] and p[3] >= p[1] and p[6] != 7):
                o = tex_offset(attr)
                v = part_layer(alpha, u0 + o, v0, u1 + o, v1, attr, values=True)
                ys, xs = np.nonzero(v)
                pts = list(zip((xs + x + sx).tolist(), (ys + y + sy).tolist()))
                pix.update(pts)
                grey.update(p for p, k in zip(pts, (v[ys, xs] == 3).tolist()) if k)   # value 3: the grey outline
        return pix, grey
    hud = {(x + i, y + j) for x, y, w, h in HUD for j in range(h) for i in range(w)} if small else set()
    named = {r['idx']: r for r in overlay['rooms'] if r['name'] and r['page'] == page and r['idx'] in cells}
    room_marks = lambda idxs: {(m['x'] + sx + i, m['y'] + sy + j) for m in overlay['markers'] if m['page'] == page and m['kind'] != 'enemy'
                               and m.get('idx') in idxs for i in range(-4, 5) for j in range(-4, 5)}
    out = {}
    for lang in langs:
        label = lambda r: names['rooms'][r['name']] if lang == 'ko' else (r['name'] if small else abbr(r['name']))
        fixed, done = [], {}
        for f in floors:
            shown = [i for i in cells if floor[i] in (-1, f)]
            todo = [i for i in named if floor[i] == f or (floor[i] == -1 and i not in done)]
            if not todo: continue
            pix, grey = picture(shown)
            rows = [dict(key=i, name=label(named[i]), cells=cells[i]) for i in todo]
            occ = {c: i for i in todo for c in cells[i]}
            other = {c for i in shown if i not in todo for c in cells[i]}
            bc = {(x + i, y + j) for x, y in pix | room_marks(set(shown)) for j in (-1, 0, 1) for i in (-1, 0, 1) if 0 <= x + i < W and 0 <= y + j < H} | hud
            blocked = room_layout.Sat(bc, (H + 2, W + 2))
            common_fixed = [(done[i]['box'], done[i]['cells']) for i in done if floor[i] == -1 and 'box' in done[i]]
            placed = place(rows, size_of, occ, grey, blocked, W, H, edge_mids, refine=(lang == 'en'), fixed=common_fixed, other=other)
            forced = {k for k, o in placed.items() if o.get('forced')}
            if forced and lang == 'en' and small:   # full names first on small maps; abbreviate only what found no place
                for r in rows:
                    if r['key'] in forced: r['name'] = abbr(named[r['key']]['name'])
                placed = place(rows, size_of, occ, grey, blocked, W, H, edge_mids, refine=True, fixed=common_fixed, other=other)
                if any(o.get('forced') for o in placed.values()):   # still crowded: every name abbreviated, keep the better result
                    for r in rows: r['name'] = abbr(named[r['key']]['name'])
                    again = place(rows, size_of, occ, grey, blocked, W, H, edge_mids, refine=True, fixed=common_fixed, other=other)
                    if sum(o.get('forced', False) for o in again.values()) < sum(o.get('forced', False) for o in placed.values()):
                        placed = again
            done.update(placed)
            print(f'page {page} {lang} floor {f}: {len(placed)} names, forced {[o["text"] for o in placed.values() if o.get("forced")]}', flush=True)
        colour(done)
        for idx, o in done.items():
            out.setdefault(str(idx), {})[lang] = dict(
                text=o['text'], x=(o['box'][0] - sx) if o.get('box') else round(o['x'] - sx - size_of(o['text'])[0] / 2),
                y=(o['box'][1] - sy) if o.get('box') else round(o['y'] - sy - size_of(o['text'])[1] / 2), colour=PAL.index(o['col']), floor=floor[idx],
                leader=[[x - sx, y - sy] for x, y in (o.get('poly') or [])], forced=bool(o.get('forced')))
    return out


def _job(args):
    page, lang = args
    overlay = json.loads((ROOT / 'data/overlay.json').read_text())
    pages_map = json.loads((ROOT / 'data/map-pages.json').read_text())
    names = json.loads((ROOT / 'data/names.json').read_text())
    return page, page_layout(page, overlay, pages_map, names, (lang,))


def main():
    """Every (page, language) is independent: run them in parallel processes, slowest (English, big pages) first."""
    from concurrent.futures import ProcessPoolExecutor
    overlay = json.loads((ROOT / 'data/overlay.json').read_text())
    pages = sorted({r['page'] for r in overlay['rooms'] if r['name']})
    only = [int(a) for a in sys.argv[1:]]
    path = ROOT / 'data/sd-layout.json'
    result = json.loads(path.read_text()) if path.exists() and only else {}
    jobs = [(p, l) for l in ('en', 'ko') for p in (only or pages)]
    for p in only or pages: result[str(p)] = {}
    with ProcessPoolExecutor() as pool:
        for page, out in pool.map(_job, jobs):
            for idx, by in out.items(): result[str(page)].setdefault(idx, {}).update(by)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=0, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
