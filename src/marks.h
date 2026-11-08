/* Marks and their names, RE0 HD map rules (user 2026-11-07 default for every mod; RE0 src/core/frame.c marker_ops):
 * key items and puzzles are never covered; locks and documents next; common items and enemies may be covered or
 * hidden. Names choose among 8 spots touching the mark by weighted overlap, tier by tier; painted lowest first. */
enum { CAT_LOCK, CAT_KEY, CAT_FILE, CAT_PUZZLE, CAT_ITEM, CAT_ENEMY, CAT_FACILITY, CAT_EVENT };
static int top_tier(unsigned c) { return c == CAT_KEY || c == CAT_PUZZLE || c == CAT_EVENT; }
static int common_cat(unsigned c) { return c == CAT_ITEM || c == CAT_ENEMY; }

typedef struct { int16_t l, t, r, b; } Rect;
static int rects_hit(Rect a, Rect b) { return a.l < b.r && b.l < a.r && a.t < b.b && b.t < a.b; }
typedef struct { Rect box; uint8_t weight; } Occ;
#define MAX_OCC (MAX_MARKS * 2 + 256)
#define MAX_MARKS 512
static Occ occ[MAX_OCC];
static unsigned occ_count;
static void occupy(Rect r, unsigned weight) { if (occ_count < MAX_OCC) occ[occ_count++] = (Occ){r, (uint8_t)weight}; }
static int overlap_score(Rect b, unsigned n, unsigned min_weight) {
    int s = 0;
    for (unsigned i = 0; i < n; i++) if (occ[i].weight >= min_weight) {
        int w = (b.r < occ[i].box.r ? b.r : occ[i].box.r) - (b.l > occ[i].box.l ? b.l : occ[i].box.l);
        int h = (b.b < occ[i].box.b ? b.b : occ[i].box.b) - (b.t > occ[i].box.t ? b.t : occ[i].box.t);
        if (w > 0 && h > 0) s += w * h * occ[i].weight;
    }
    return s;
}

enum { DROP, KEEP, NAMED };
typedef struct { Rect m, name; int16_t cx, cy; uint16_t sprite; uint8_t cat, event, state, slot, ringed, kind, item; } Mark;
static Mark marks[MAX_MARKS];
static unsigned mark_count, mark_drops, mark_dups;
#define DUP_MAP_PX 4
static Rect panel_boxes[3];   /* legend, readout panel (empty when folded), HD-off notice (empty when not shown) */

/* Mark side: the zoom-following base size (zoomed) times the icon size setting. */
static int mark_side(int base) { int s = (zoomed(base) * icon_size + 50) / 100; return s < 3 ? 3 : s; }
/* Item icons (keys, lock keys, common items) are drawn at ITEM_ICON_BASE percent of that: setting 100 = the old 130%. */
static int item_side(int base) { int s = (zoomed(base) * icon_size * ITEM_ICON_BASE + 5000) / 10000; return s < 3 ? 3 : s; }
static void push_mark(unsigned cat, int event, int cx, int cy, unsigned sprite, int base, unsigned kind, unsigned item) {
    int side = kind == K_KEY || kind == K_LOCK || kind == K_COMMON ? item_side(base) : mark_side(base);
    Rect m = {(int16_t)(cx - side / 2), (int16_t)(cy - side / 2), (int16_t)(cx - side / 2 + side), (int16_t)(cy - side / 2 + side)};
    /* off screen when zoomed, or under the legend or the readouts: neither the mark nor a name pulled back */
    if (m.l < 0 || m.t < 0 || m.r > 320 || m.b > 240 || rects_hit(m, panel_boxes[0]) || rects_hit(m, panel_boxes[1]) || rects_hit(m, panel_boxes[2])) return;
    /* RE0 rule 14: the same item at the same spot is shown once. RE3 lists side-by-side pickups of one item 1-4 map
     * px apart (two red herbs, flags 55/56) and a lock from both sides of its door; their icons stack, so a second
     * name would only repeat the first. Each row has already decided its own visibility. */
    const int tol = cat == CAT_ENEMY ? 0 : (DUP_MAP_PX * map_zoom + 50) / 100;   /* RE0: enemies only at the very same spot */
    for (unsigned j = 0; j < mark_count; j++)
        if (marks[j].kind == kind && marks[j].item == item && marks[j].cx - cx <= tol && cx - marks[j].cx <= tol &&
            marks[j].cy - cy <= tol && cy - marks[j].cy <= tol) { mark_dups++; return; }
    if (mark_count >= MAX_MARKS) { mark_drops++; return; }
    marks[mark_count++] = (Mark){m, {0, 0, 0, 0}, (int16_t)cx, (int16_t)cy, (uint16_t)sprite, (uint8_t)cat, (uint8_t)event, KEEP, 0, 0, (uint8_t)kind, (uint8_t)item};
}

static const MarkName *mark_name(const Mark *k) {
    if (k->event || k->cat == CAT_ENEMY || k->cat == CAT_FACILITY) return 0;   /* enemies and events show no name */
    for (unsigned i = 0; i < MARK_NAME_COUNT; i++) if (mark_names[i].kind == k->kind && mark_names[i].item == k->item) return &mark_names[i];
    return 0;
}
/* A name is one or two lines; the 1px raster margins overlap between them. */
static void name_box_size(const MarkName *n, int *w, int *h) {
    unsigned a = n->line[korean][0], b = n->line[korean][1];
    *w = name_dimension(sprites[a].w); *h = name_dimension(sprites[a].h);
    if (b != NO_LINE) { int w2 = name_dimension(sprites[b].w); if (w2 > *w) *w = w2; *h += name_dimension(sprites[b].h) - 1; }
}
/* Touching the mark, no gap: right, left, below, above, then below or above running from the mark's edge. */
static void name_candidates(Rect m, int w, int h, Rect out[8]) {
    int cx = (m.l + m.r) / 2, cy = (m.t + m.b) / 2;
    const int x[8] = {m.r, m.l - w, cx - w / 2, cx - w / 2, m.l, m.r - w, m.l, m.r - w};
    const int y[8] = {cy - h / 2, cy - h / 2, m.b, m.t - h, m.b, m.b, m.t - h, m.t - h};
    for (unsigned i = 0; i < 8; i++) out[i] = (Rect){(int16_t)x[i], (int16_t)y[i], (int16_t)(x[i] + w), (int16_t)(y[i] + h)};
}
static Rect clamp_screen(Rect b) {
    int w = b.r - b.l, h = b.b - b.t;
    if (b.l < 1) { b.l = 1; b.r = (int16_t)(1 + w); } if (b.r > 319) { b.r = 319; b.l = (int16_t)(319 - w); }
    if (b.t < 1) { b.t = 1; b.b = (int16_t)(1 + h); } if (b.b > 239) { b.b = 239; b.t = (int16_t)(239 - h); }
    return b;
}
static void place_name(Mark *k, unsigned weight) {
    const MarkName *n = mark_name(k);
    if (!n) return;
    int w, h; name_box_size(n, &w, &h);
    Rect c[8], best = {0, 0, 0, 0}; int least = -1;
    name_candidates(k->m, w, h, c);
    for (unsigned j = 0; j < 8; j++) {
        Rect b = clamp_screen(c[j]); int a = overlap_score(b, occ_count, 1);
        if (least < 0 || a < least) { least = a; best = b; k->slot = (uint8_t)j; }
        if (!a) break;
    }
    k->ringed = 0;
    /* No second ring: a name always touches its own mark, even where that covers other things (RE0 rule: names adjacent to their icons). */
    k->name = best; k->state = NAMED; occupy(best, weight);
}
static void draw_name(const Mark *k) {
    const MarkName *n = mark_name(k);
    unsigned a = n->line[korean][0], b = n->line[korean][1];
    int w = k->name.r - k->name.l;
    int w1 = name_dimension(sprites[a].w), h1 = name_dimension(sprites[a].h);
    /* follows the mark's side: right of it left-aligned, left of it right-aligned, otherwise centred */
    int x1 = k->slot == 0 ? k->name.l : k->slot == 1 ? k->name.r - w1 : k->name.l + (w - w1) / 2;
    quad(x1, k->name.t, a, w1, h1);
    if (b == NO_LINE) return;
    int w2 = name_dimension(sprites[b].w), h2 = name_dimension(sprites[b].h);
    int x2 = k->slot == 0 ? k->name.l : k->slot == 1 ? k->name.r - w2 : k->name.l + (w - w2) / 2;
    quad(x2, k->name.b - h2, b, w2, h2);
}

static void draw_marks(void) {
    const unsigned marks_first = occ_count;
    for (unsigned i = 0; i < mark_count; i++) occupy(marks[i].m, top_tier(marks[i].cat) ? 8 : 1);
    /* An event on a key item stands beside it (right when it fits, else left), so both can be seen. */
    for (unsigned i = 0; i < mark_count; i++) if (marks[i].event)
        for (unsigned j = 0; j < mark_count; j++) if (marks[j].cat == CAT_KEY && !marks[j].event && rects_hit(marks[i].m, marks[j].m)) {
            int ew = marks[i].m.r - marks[i].m.l, left = marks[j].m.r + ew <= 320 ? marks[j].m.r : marks[j].m.l - ew;
            marks[i].m = (Rect){(int16_t)left, marks[j].m.t, (int16_t)(left + ew), marks[j].m.b};
            occ[marks_first + i].box = marks[i].m;
            break;
        }
    const unsigned marks_end = occ_count;
    /* Names by tier: key items, puzzles, then locks and documents. */
    static const uint8_t tiers[4] = {CAT_KEY, CAT_PUZZLE, CAT_LOCK, CAT_FILE};
    if (item_names) for (unsigned t = 0; t < 4; t++) for (unsigned i = 0; i < mark_count; i++)
        if (marks[i].cat == tiers[t] && !marks[i].event) place_name(&marks[i], t < 2 ? 8 : 2);
    /* A lower icon on a key or puzzle mark, or under an unmoved key name, is not drawn; a document or facility
     * centred on one moves to a badge down and right. Decided on each icon's middle, so a bigger picture never
     * hides a row; a lock's key stays on its door. */
    const int core = mark_side(8) * 7 / 36 + 1;
    for (unsigned i = 0; i < mark_count; i++) {
        Mark *k = &marks[i];
        if (top_tier(k->cat) || k->cat == CAT_LOCK) continue;
        int cx = (k->m.l + k->m.r) / 2, cy = (k->m.t + k->m.b) / 2, covered = 0, centred = 0;
        Rect mi = {(int16_t)(cx - core), (int16_t)(cy - core), (int16_t)(cx + core), (int16_t)(cy + core)};
        for (unsigned j = 0; j < mark_count; j++) {
            const Mark *o = &marks[j];
            if (!top_tier(o->cat) || o->event) continue;   /* an event sits over a mark, it does not displace it */
            int jx = (o->m.l + o->m.r) / 2, jy = (o->m.t + o->m.b) / 2;
            if (rects_hit(mi, (Rect){(int16_t)(jx - core), (int16_t)(jy - core), (int16_t)(jx + core), (int16_t)(jy + core)})) {
                covered = 1;
                if (cx - jx > -core && cx - jx < core && cy - jy > -core && cy - jy < core) centred = 1;
            }
            if (o->state == NAMED && !o->ringed && o->cat == CAT_KEY && rects_hit(mi, o->name)) covered = 1;
        }
        if (!covered) continue;
        if (common_cat(k->cat) || !centred) { k->state = DROP; continue; }
        int d = mark_side(8) * 3 / 5;
        k->m.l += d; k->m.r += d; k->m.t += d; k->m.b += d;
        if (k->state == NAMED) { k->name.l += d; k->name.r += d; k->name.t += d; k->name.b += d; }   /* its name was placed first: it follows the badge */
    }
    /* Common item names last: only into space that covers nothing above them, otherwise hidden. */
    if (item_names == 1) for (unsigned i = 0; i < mark_count; i++) {   /* state 2 leaves common items unnamed */
        Mark *k = &marks[i];
        const MarkName *n = k->state == KEEP && k->cat == CAT_ITEM ? mark_name(k) : 0;
        if (!n) continue;
        int w, h; name_box_size(n, &w, &h);
        Rect c[8]; name_candidates(k->m, w, h, c);
        int best = -1, least = 0;
        for (unsigned j = 0; j < 8; j++) {
            if (c[j].l < 0 || c[j].t < 0 || c[j].r > 320 || c[j].b > 240 || overlap_score(c[j], occ_count, 2) > 0) continue;
            int a = overlap_score(c[j], marks_end, 1);
            if (best < 0 || a < least) { best = (int)j; least = a; }
        }
        if (best < 0) continue;
        k->name = c[best]; k->slot = (uint8_t)best; k->state = NAMED; occupy(c[best], 2);
    }
    /* Painted lowest priority first, so what must never be covered ends on top; a mark and its name together. */
    for (unsigned pass = 0; pass < 2; pass++) for (unsigned i = 0; i < mark_count; i++) {
        const Mark *k = &marks[i];
        if (k->state == DROP || (unsigned)top_tier(k->cat) != pass) continue;
        icon_quad(k->m.l, k->m.t, k->sprite, k->m.r - k->m.l);
        if (k->state == NAMED) draw_name(k);
    }
}
