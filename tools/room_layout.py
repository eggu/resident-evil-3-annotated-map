"""Room names fixed when data is generated (RE0 HD map rules, 2026-11-07 default for every mod), in map pixels.

Names never move at runtime. Tightest rooms first; at the pole of inaccessibility of the room's real shape (texture
alpha, not the bounding box), then the interior spot nearest it whose box covers the most of the room; a one-line
name wider than 150% of its room wraps between words; a corridor too narrow for its name gets an axis-aligned leader
into free space instead. Names ignore markers (drawn first, anything may cover them) and keep off each other.
RE3 specifics: 1 cell = 1 map pixel (screen pixel at the native 100% zoom); rooms whose shapes overlap are story or
floor variants that the native map never draws together, so their names may overlap.
"""
import numpy as np

LEADER_MAX = 20     # RE0's 60 canvas px of 720 -> 20 of RE3's 240 lines
LONG_LEADER = 2 * LEADER_MAX   # only when no spot within LEADER_MAX exists; reported by check_page
SHIFTS = (0, 4, -4, 8, -8, 12, -12)
EXCLUSIVE = .2      # shared area / smaller shape above this: never on screen together


class Sat:
    def __init__(self, cells, shape):
        m = np.zeros(shape, np.int32)
        for x, y in cells:
            m[y, x] = 1
        self.ii = np.pad(m.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        self.h, self.w = shape

    def sum(self, x, y, w, h):
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, self.w), min(y + h, self.h)
        if x1 <= x0 or y1 <= y0:
            return 0
        ii = self.ii
        return int(ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0])


def hit(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def depth_map(mask):
    """Chamfer (3-4) distance from each shape pixel to the nearest pixel outside it, in pixels."""
    big = 10 ** 6
    d = np.where(np.pad(mask, 1), big, 0).astype(np.int64)
    h, w = d.shape
    for y in range(1, h):
        for x in range(1, w - 1):
            if d[y, x]:
                d[y, x] = min(d[y, x], d[y, x - 1] + 3, d[y - 1, x] + 3, d[y - 1, x - 1] + 4, d[y - 1, x + 1] + 4)
    for y in range(h - 2, -1, -1):
        for x in range(w - 2, 0, -1):
            if d[y, x]:
                d[y, x] = min(d[y, x], d[y, x + 1] + 3, d[y + 1, x] + 3, d[y + 1, x + 1] + 4, d[y + 1, x - 1] + 4)
    return d[1:-1, 1:-1] / 3


def pole(cells, origin, mask):
    """The shape pixel farthest from its edge; ties nearest the centroid."""
    depth = depth_map(mask)
    cx, cy = np.mean([c[0] for c in cells]), np.mean([c[1] for c in cells])
    ox, oy = origin
    return max(cells, key=lambda p: (depth[p[1] - oy, p[0] - ox], -((p[0] - cx) ** 2 + (p[1] - cy) ** 2)))


def interior_spot(cells, sat, centre, lw, lh, placed):
    """Name centre on the shape with the most of its box on the shape (within .05 of the best, or full), nearest
    the pole; None when every spot hits a placed name."""
    found = []
    for px, py in cells:
        box = (px - lw // 2, py - lh // 2, lw, lh)
        if any(hit(box, b) for b in placed):
            continue
        found.append((sat.sum(*box) / (lw * lh), px, py))
    if not found:
        return None
    top = max(f[0] for f in found)
    floor = 1.0 if top >= 1.0 else top - .05
    c = min((f for f in found if f[0] >= floor), key=lambda f: (f[1] - centre[0]) ** 2 + (f[2] - centre[1]) ** 2)
    return c[1], c[2], c[0]


def line_box(line):
    x0, x1 = sorted((line[0], line[2]))
    y0, y1 = sorted((line[1], line[3]))
    return x0, y0, x1 - x0 + 1, y1 - y0 + 1


def near_spot(own, occ, blocked, lw, lh, placed, lines, bounds, kmax=LEADER_MAX):
    """Shortest axis-aligned leader from an edge pixel of the room, through empty map, to a free box."""
    best = None
    W, H = bounds
    for sx, sy in sorted(own):
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            if (sx + dx, sy + dy) in own:
                continue
            for k in range(2, kmax + 1):
                if best and k >= best[0]:
                    break
                ex, ey = sx + dx * k, sy + dy * k
                if (ex, ey) in occ:
                    break
                line = (sx, sy, ex, ey)
                for sh in SHIFTS:
                    if (abs(sh) > lw // 2 - 2 and dy) or (abs(sh) > lh // 2 - 1 and dx):
                        continue
                    if dy:
                        box = (ex - lw // 2 + sh, ey - lh + 1 if dy < 0 else ey, lw, lh)
                    else:
                        box = (ex - lw + 1 if dx < 0 else ex, ey - lh // 2 + sh, lw, lh)
                    if box[0] < 0 or box[1] < 0 or box[0] + lw > W or box[1] + lh > H or blocked.sum(*box):
                        continue
                    if any(hit(box, b) or hit(line_box(line), b) for b in placed) or any(hit(box, line_box(o)) for o in lines):
                        continue
                    cost = k + abs(sh) * .1
                    if best is None or cost < best[0]:
                        best = (cost, box[0] + lw / 2, box[1] + lh / 2, line, box)
    return best


def split(text):
    """Two lines between the words nearest the middle; None for one word."""
    parts = text.split(' ')
    if len(parts) < 2:
        return None
    at = min(range(1, len(parts)), key=lambda i: abs(len(' '.join(parts[:i])) - len(' '.join(parts[i:]))))
    return ' '.join(parts[:at]) + '\n' + ' '.join(parts[at:])


def exclusive(a, b):
    shared = len(a & b)
    return shared > EXCLUSIVE * min(len(a), len(b))


def place_page(rows, size_of):
    """rows: [{'key', 'name', 'cells': set of (x, y)}], one page in one language. size_of(text) -> (w, h).
    Returns {key: dict(text, x, y, line)}: x, y the name's centre; line (sx, sy, ex, ey) or None."""
    occ = {}
    for r in rows:
        for c in r['cells']:
            occ.setdefault(c, r['key'])
    xs = [c[0] for c in occ]; ys = [c[1] for c in occ]
    W, H = max(xs) + 64, max(ys) + 64
    blocked_cells = {(x + i, y + j) for x, y in occ for j in (-1, 0, 1) for i in (-1, 0, 1) if x + i >= 0 and y + j >= 0}
    blocked = Sat(blocked_cells, (H + 2, W + 2))
    placed, lines, out, later = [], [], {}, []
    def free(r):   # boxes of names this one may not overlap
        return [p[1] for p in placed if not exclusive(p[0]['cells'], r['cells'])]
    for r in sorted(rows, key=lambda r: len(r['cells'])):
        cs = sorted(r['cells'])
        x0, x1 = min(c[0] for c in cs), max(c[0] for c in cs)
        y0, y1 = min(c[1] for c in cs), max(c[1] for c in cs)
        bw, bh = x1 - x0 + 1, y1 - y0 + 1
        text = r['name']
        lw, lh = size_of(text)
        if lw > 1.5 * bw and split(text):
            text = split(text); lw, lh = size_of(text)
        mask = np.zeros((bh, bw), bool)
        for x, y in cs:
            mask[y - y0, x - x0] = True
        sat = Sat(cs, (y1 + lh + 2, x1 + lw + 2))
        centre = pole(cs, (x0, y0), mask)
        ideal = interior_spot(cs, sat, centre, lw, lh, [])
        corridor = min(bw, bh) < lh * 2 and ideal[2] < .5
        spot = None if corridor else interior_spot(cs, sat, centre, lw, lh, free(r))
        if spot:
            out[r['key']] = dict(text=text, x=spot[0] - lw // 2 + lw / 2, y=spot[1] - lh // 2 + lh / 2, line=None, at=spot[:2])
            placed.append((r, (spot[0] - lw // 2, spot[1] - lh // 2, lw, lh)))
            continue
        later.append((r, text))
    forced = []
    for r, text in sorted(later, key=lambda q: (min(c[1] for c in q[0]['cells']), min(c[0] for c in q[0]['cells']))):
        lw, lh = size_of(text)
        best = near_spot(r['cells'], occ, blocked, lw, lh, free(r), lines, (W, H)) or \
            near_spot(r['cells'], occ, blocked, lw, lh, free(r), lines, (W, H), LONG_LEADER)
        if best:
            _, x, y, line, box = best
            out[r['key']] = dict(text=text, x=x, y=y, line=line)
            placed.append((r, box)); lines.append(line)
            continue
        # No free spot inside or on a short leader: the pole, overlapping, and reported by check_page.
        cs = sorted(r['cells'])
        x0, y0 = min(c[0] for c in cs), min(c[1] for c in cs)
        mask = np.zeros((max(c[1] for c in cs) - y0 + 1, max(c[0] for c in cs) - x0 + 1), bool)
        for x, y in cs:
            mask[y - y0, x - x0] = True
        px, py = pole(cs, (x0, y0), mask)
        out[r['key']] = dict(text=text, x=px - lw // 2 + lw / 2, y=py - lh // 2 + lh / 2, line=None, at=(px, py), forced=True)
        placed.append((r, (px - lw // 2, py - lh // 2, lw, lh))); forced.append(r['key'])
    return out


def check_page(rows, out, size_of):
    """The rules restated apart from the search; returns a list of defects (empty = pass)."""
    bad, boxes = [], {}
    occ = {c for r in rows for c in r['cells']}
    for r in rows:
        o = out[r['key']]
        lw, lh = size_of(o['text'])
        b = (int(o['x'] - lw / 2), int(o['y'] - lh / 2), lw, lh)
        boxes[r['key']] = b
        if o.get('forced'):
            bad.append(f"forced: {r['name']}")
        elif o['line']:
            sx, sy, ex, ey = o['line']
            if (sx, sy) not in r['cells']:
                bad.append(f"leader starts off its room: {r['name']}")
            if abs(ex - sx) + abs(ey - sy) > LONG_LEADER or (sx != ex and sy != ey):
                bad.append(f"leader too long or bent: {r['name']}")
            elif abs(ex - sx) + abs(ey - sy) > LEADER_MAX:
                bad.append(f"long leader: {r['name']}")
            if any((x, y) in occ for y in range(b[1], b[1] + lh) for x in range(b[0], b[0] + lw)):
                bad.append(f"outside name on a room: {r['name']}")
        elif tuple(o['at']) not in r['cells']:
            bad.append(f"anchor outside its room: {r['name']}")
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if hit(boxes[a['key']], boxes[b['key']]) and not exclusive(a['cells'], b['cells']):
                bad.append(f"names overlap: {a['name']} / {b['name']}")
    return bad
