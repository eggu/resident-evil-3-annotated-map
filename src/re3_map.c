/* Annotated Map for Resident Evil 3 (SourceNext BIOHAZARD(R) 3 PC.exe + Classic REbirth 1.0.3).
 * ASI plugin: draws room names, locked doors, items, files, puzzles, save points and monsters over the
 * native status-screen map. No CRT; KERNEL32/USER32 only. */
#include <windows.h>
#include <stdint.h>
#include "assets.h"

#define G8(a) (*(volatile uint8_t *)(a))
#define G16(a) (*(volatile int16_t *)(a))
#define G32(a) (*(volatile uint32_t *)(a))
#define FLAG_TABLE 0x52EAAC          /* SCD ck/set bank pointers */
#define VISITED 0xA6752C             /* map visited bits, page*2 dwords */
#define MAP_OWNED 0xA67574           /* Flg_ck(MAP_OWNED, page) */
#define STAGE_NO 0xA673C6
#define DATA_AJ 0xA67A44
#define OT2 0xA5FBC0
#define ATLAS_X0 64                  /* VRAM x of atlas page 0 (4bpp: 64 words per page) */
#define CLUT_X 0
#define CLUT_Y 0
#define MAX_PRIMS 1400

static const uintptr_t hook_sites[2] = {0x461780, 0x4617C5};
static const uintptr_t map_draw_va = 0x4EAC60;

typedef int(__cdecl *flg_ck_fn)(void *, unsigned);
typedef int(__cdecl *room_fn)(unsigned, unsigned);
typedef void(__cdecl *prim_fn)(void *);
typedef void(__cdecl *add_prim_fn)(void *, void *);
typedef void(__cdecl *load_image_fn)(const int16_t *, const void *);
static flg_ck_fn flg_ck = (flg_ck_fn)0x428DE0;
static room_fn room_exists = (room_fn)0x4EB9F0;
static prim_fn set_poly_ft4 = (prim_fn)0x425640;
static add_prim_fn add_prim = (add_prim_fn)0x425580;
static load_image_fn load_image = (load_image_fn)0x425450;
static void(__cdecl *map_draw)(void *) = (void(__cdecl *)(void *))0x4EAC60;

void *__cdecl memset(void *d, int c, size_t n) { unsigned char *p = d; while (n--) *p++ = (unsigned char)c; return d; }

#include "settings.h"

/* ---------- flags */
static int bank_bit(unsigned bank, unsigned bit) {
    if (bank >= 50) return 0;
    uint32_t *p = (uint32_t *)G32(FLAG_TABLE + bank * 4);
    return p && (p[(bit >> 5) & 7] & (0x80000000u >> (bit & 31))) != 0;
}
static int same_place(const Marker *a, const Marker *b) {
    return a->kind == b->kind && a->page == b->page && a->idx == b->idx && a->x == b->x && a->y == b->y &&
           a->extra == b->extra && a->flag == b->flag && a->sets == b->sets;
}
static int guard_ok(const Marker *m) {
    for (unsigned c = 0; c < m->nclause; c++) {
        const Clause *cl = &clauses[m->clause + c];
        int any = 0;
        for (unsigned l = 0; l < cl->count && !any; l++) {
            const Literal *lit = &literals[cl->first + l];
            if (lit->bank < 50) any = bank_bit(lit->bank, lit->bit) == lit->value;
            else {
                int v = G16(0xA67396 + lit->bit * 2), n = lit->value;
                switch (lit->bank - 50) {
                case 0: any = v == n; break;
                case 1: any = v > n; break;
                case 2: any = v >= n; break;
                case 3: any = v < n; break;
                case 4: any = v <= n; break;
                case 5: any = v != n; break;
                case 6: any = (v & n) != 0; break;
                case 7: any = (v & n) == 0; break;
                }
            }
        }
        if (!any) return 0;
    }
    return 1;
}
static int second_set(unsigned stage) { return stage >= 2 && !(G8(0xA61CA0) & 0x80); }  /* exe 0x46EAE0 / 0x46DEC6 */
static int picked(const Marker *m) { return bank_bit(second_set(m->sets >> 4) ? 8 : 7, m->flag); }
static int visited(unsigned page, unsigned idx) {
    return (G32(VISITED + (page * 2 + (idx >> 5)) * 4) & (0x80000000u >> (idx & 31))) != 0;
}
/* 0x4EB9F0 is the native per-room gate: story state and, on multi-floor pages, the displayed floor. */
static int room_shown(unsigned page, unsigned idx) {
    if (!room_exists(page, idx)) return 0;
    return scope >= 3 || visited(page, idx) || (scope == 2 && flg_ck((void *)MAP_OWNED, page));
}

/* ---------- primitives */
typedef struct { uint32_t tag; uint8_t r, g, b, code; int16_t x0, y0; uint8_t u0, v0; uint16_t clut;
                 int16_t x1, y1; uint8_t u1, v1; uint16_t tpage; int16_t x2, y2; uint8_t u2, v2; uint16_t pad1;
                 int16_t x3, y3; uint8_t u3, v3; uint16_t pad2; } PolyFT4;
static PolyFT4 prims[2][MAX_PRIMS];
static PolyFT4 *frame_prims;
static unsigned prim_count;
static int clip_x0, clip_y0, clip_x1 = 320, clip_y1 = 240;

enum { CLUT_UI, CLUT_NAMES, CLUT_ICONS };
static void quad_row(int x, int y, unsigned sprite_id, int w, int h, unsigned row) {
    if (prim_count >= MAX_PRIMS || sprite_id >= SPRITE_COUNT) return;
    if (x + w <= clip_x0 || y + h <= clip_y0 || x >= clip_x1 || y >= clip_y1) return;
    const Sprite *s = &sprites[sprite_id];
    PolyFT4 *p = &frame_prims[prim_count++];
    memset(p, 0, sizeof *p);
    set_poly_ft4(p);
    p->r = p->g = p->b = 0x80;
    p->x0 = p->x2 = (int16_t)x; p->x1 = p->x3 = (int16_t)(x + w);
    p->y0 = p->y1 = (int16_t)y; p->y2 = p->y3 = (int16_t)(y + h);
    p->u0 = p->u2 = s->u; p->u1 = p->u3 = (uint8_t)(s->u + s->w);
    p->v0 = p->v1 = s->v; p->v2 = p->v3 = (uint8_t)(s->v + s->h);
    p->clut = (uint16_t)(((CLUT_Y + row) << 6) | (CLUT_X >> 4));
    p->tpage = (uint16_t)((ATLAS_X0 / 64) + s->page);
}
/* A 1 px leader at any angle: one POLY_FT4 as a parallelogram one pixel wide across its major axis, every corner
 * sampling the middle of the solid leader sprite. Steep segments widen along x, shallow ones along y. */
static void line_quad(int x0, int y0, int x1, int y1) {
    if (prim_count >= MAX_PRIMS) return;
    int dx = x1 - x0, dy = y1 - y0, steep = (dx < 0 ? -dx : dx) <= (dy < 0 ? -dy : dy);
    if (steep ? y1 < y0 : x1 < x0) { int t = x0; x0 = x1; x1 = t; t = y0; y0 = y1; y1 = t; }
    const Sprite *s = &sprites[LEADER_SPRITE];
    PolyFT4 *p = &frame_prims[prim_count++];
    memset(p, 0, sizeof *p);
    set_poly_ft4(p);
    p->r = p->g = p->b = 0x80;
    if (steep) { p->x0 = (int16_t)x0; p->y0 = (int16_t)y0; p->x1 = (int16_t)(x0 + 1); p->y1 = (int16_t)y0;
                 p->x2 = (int16_t)x1; p->y2 = (int16_t)(y1 + 1); p->x3 = (int16_t)(x1 + 1); p->y3 = (int16_t)(y1 + 1); }
    else       { p->x0 = (int16_t)x0; p->y0 = (int16_t)y0; p->x1 = (int16_t)(x1 + 1); p->y1 = (int16_t)y1;
                 p->x2 = (int16_t)x0; p->y2 = (int16_t)(y0 + 1); p->x3 = (int16_t)(x1 + 1); p->y3 = (int16_t)(y1 + 1); }
    p->u0 = p->u1 = p->u2 = p->u3 = (uint8_t)(s->u + s->w / 2);
    p->v0 = p->v1 = p->v2 = p->v3 = (uint8_t)(s->v + s->h / 2);
    p->clut = (uint16_t)(((CLUT_Y + CLUT_NAMES) << 6) | (CLUT_X >> 4));
    p->tpage = (uint16_t)((ATLAS_X0 / 64) + s->page);
}
/* TestLeaders=1: a fan of 24 directions, two bent leaders and a shallow/steep pair, for SD/HD rasterisation checks. */
/* Names (room, marker) take the name-opacity CLUT, icons the icon-opacity CLUT, the legend the opaque base. */
static void quad(int x, int y, unsigned id, int w, int h) { quad_row(x, y, id, w, h, sprites[id].page >= NAME_PAGE_FIRST ? CLUT_NAMES : CLUT_UI); }
static void icon_quad(int x, int y, unsigned id, int side) { quad_row(x, y, id, side, side, CLUT_ICONS); }
/* Marker icons follow the map zoom (status +0xA4 animates 50..100%): full size zoomed in, smaller zoomed out. */
static int map_zoom = 100;
static int zoomed(int size) { int z = (size * map_zoom + 50) / 100; return z < 3 ? 3 : z; }
/* Names shrink less than icons: 100% when zoomed in, 70% at the native 50% zoom-out. */
static int name_dimension(int v) { int scaled = (v * name_size * NAME_BASE + 5000) / 10000;   /* setting 100 = the old 80% */ int z = (scaled * (100 - (100 - map_zoom) * 3 / 5) + 50) / 100; return z < 1 ? 1 : z; }

/* ---------- map transform (exe 0x4EAF50 / 0x4EB6A0) */
static int div100(int v) { return v / 100; }
static int map_x(const unsigned char *s, int x) { int o = *(int *)(s + 0x94); return div100((x + o) * *(int *)(s + 0xA4)) + *(int *)(s + 0x7C) - o + 160; }
static int map_y(const unsigned char *s, int y) { int o = *(int *)(s + 0x98); return div100((y + o) * *(int *)(s + 0xA4)) + *(int *)(s + 0x80) - o + 120; }

/* ---------- atlas upload: once per map session (VRAM x 64.. is free while the status screen is open) */
static int uploaded;
static int sd_decide(void);
static void upload_sd(void);
static void upload_atlas(void) {
    if (sd_decide()) { upload_sd(); uploaded = 1; return; }
    for (int p = 0; p < ATLAS_PAGES; p++) {
        int16_t rect[4] = {(int16_t)(ATLAS_X0 + 64 * p), 0, 64, 256};
        load_image(rect, atlas_pixels[p]);
    }
    int16_t clut_rect[4] = {CLUT_X, CLUT_Y + CLUT_UI, 16, 1};
    load_image(clut_rect, atlas_clut);
    int16_t name_rect[4] = {CLUT_X, CLUT_Y + CLUT_NAMES, 16, 1};
    load_image(name_rect, name_cluts[name_opacity / 10 - 1]);
    int16_t icon_rect[4] = {CLUT_X, CLUT_Y + CLUT_ICONS, 16, 1};
    load_image(icon_rect, icon_cluts[icon_opacity / 10 - 1]);
    uploaded = 1;
}

/* Classic REbirth draws the map text from the hires/misc .webp files only with HDTextures=1 in its config.ini [DLL]; without it
 * the overlay is the 4bpp atlas scaled up, i.e. blurry (community report 2026-11-06). -1 = key not found. */
static char config_path[MAX_PATH];
static int rebirth_hd_textures(void) { return (int)GetPrivateProfileIntA("DLL", "HDTextures", -1, config_path); }
__declspec(dllexport) int __cdecl AnnotatedMapTestHdTextures(void) { return rebirth_hd_textures(); }
static unsigned frame_no, shown_counts[11];
#include "marks.h"
#include "live_enemies.h"
/* HD textures off: a plain-pixel notice on the map (the HD-only text would be unreadable). Re-read config.ini at most
 * once a second, so opening the map after the file changed is enough; only an explicit HDTextures=0 shows it. */
static int hd_notice, hd_checked_at = -1;
static int hd_off_now(void) {
    DWORD now = GetTickCount();
    if (hd_checked_at < 0 || now - (DWORD)hd_checked_at >= 1000) { hd_notice = rebirth_hd_textures() == 0; hd_checked_at = (int)now; }
    return hd_notice;
}
static Rect notice_rect(void) {
    const Sprite *n = &sprites[NOTICE_SPRITE];
    return (Rect){3, 3, (int16_t)(3 + n->w + 4), (int16_t)(3 + n->h + 4)};   /* top-left: legend is bottom-left, scale bar bottom-right */
}

/* ---------- panels: legend bottom-left, readouts bottom-right (RE0 candidate 49 layout, 320x240 lines of 7 px) */
static void panel(int x, int y, int w, int h) {
    if (sd_mode > 0) { sd_panel(x, y, w, h); return; }
    quad(x, y, ICON_PANEL, w, h);
    if (!prim_count) return;
    PolyFT4 *p = &frame_prims[prim_count - 1];   /* semi-transparent, sampled inside the panel tile */
    p->code |= 2; p->u1 = p->u3 = (uint8_t)(sprites[ICON_PANEL].u + 2); p->v2 = p->v3 = (uint8_t)(sprites[ICON_PANEL].v + 2);
    p->u0 += 1; p->u2 += 1; p->v0 += 1; p->v1 += 1;
}
#define LEGEND_ROWS_Y (240 - 4 - 6 * 7)
/* The legend and its readouts are laid out at full size, then drawn at 90% anchored at their bottom-left corner
 * (user, candidate 4 live: the merged panel covered too much map). */
#define LEGEND_SCALE 90
static int lx(int x) { return 3 + ((x - 3) * LEGEND_SCALE + 50) / 100; }
static int ly(int y) { return 239 - ((239 - y) * LEGEND_SCALE + 50) / 100; }
static Rect lrect(Rect r) { return (Rect){(int16_t)lx(r.l), (int16_t)ly(r.t), (int16_t)lx(r.r), (int16_t)ly(r.b)}; }
/* Position and size are scaled separately: a size taken from the difference of two rounded edges was 5 or 6 px for the same
 * sprite depending on its row (candidate 12), so equal sprites now draw equally tall. */
static void lquad(int x, int y, unsigned id, int w, int h) { quad(lx(x), ly(y + h) - (h * LEGEND_SCALE + 50) / 100, id, (w * LEGEND_SCALE + 50) / 100, (h * LEGEND_SCALE + 50) / 100); }
/* Two columns (user 2026-11-08, as RE0): [0]..[4] and [H] item names under them | [5]..[8], [9] scope and [\\] language
 * under them. Each column fits every state of its labels (all three item-name states, every scope text), so the panel
 * does not resize when [H] or [9] cycles. */
static int legend_cell_w(unsigned id) { return sprites[id].w; }
static void legend_columns(int widths[2]) {
    widths[0] = widths[1] = 0;
    for (unsigned r = 0; r < 9; r++) { int w = legend_cell_w(legend_sprites[r][korean][1]); int c = r < 5 ? 0 : 1; if (w > widths[c]) widths[c] = w; }
    for (unsigned n = 0; n < 3; n++) if (legend_cell_w(hint_names[korean][n]) > widths[0]) widths[0] = legend_cell_w(hint_names[korean][n]);
    for (unsigned sc = 0; sc < 3; sc++) if (legend_cell_w(legend_scope[sc][korean]) > widths[1]) widths[1] = legend_cell_w(legend_scope[sc][korean]);
    if (legend_cell_w(legend_lang[korean]) > widths[1]) widths[1] = legend_cell_w(legend_lang[korean]);
}
/* Title line close above the rows (user, candidate 2 live: the gap read as a separate block). */
static int legend_top(void) { return LEGEND_ROWS_Y - sprites[legend_title[korean]].h - 1 - 3; }
static Rect legend_rect(void) {
    if (!legend_on) {
        const Sprite *f = &sprites[hint_fold[korean]];
        return (Rect){3, (int16_t)(240 - 4 - f->h - 3), (int16_t)(3 + f->w + 6), 239};
    }
    int widths[2]; legend_columns(widths);
    int w = widths[0] + widths[1] + 8;
    int head = sprites[legend_title[korean]].w + 6 + sprites[hint_hide[korean]].w;
    if (head > w) w = head;
    return (Rect){3, (int16_t)legend_top(), (int16_t)(3 + w + 6), 239};
}
static int value_width(void) { return sprites[value_sprites[19]].w; }   /* "200%" */
/* Readouts sit on the legend's right side, rows level with its first four rows, one background with it (user,
 * candidate 2 live: bottom-right they covered the game's own scale bar). */
static Rect readout_rect(void) {
    if (!legend_on) return (Rect){0, 0, 0, 0};
    Rect l = legend_rect();
    l.t = (int16_t)(LEGEND_ROWS_Y + 2 * 7 - 3);   /* its own panel starts at the first row: no empty band above 'Name opacity' */
    int w = 0;
    for (unsigned r = 0; r < 4; r++) if (sprites[readout_hints[r][korean][modifier_ctrl]].w > w) w = sprites[readout_hints[r][korean][modifier_ctrl]].w;
    w += 4 + value_width() + 6;
    return (Rect){l.r, l.t, (int16_t)(l.r + w), l.b};
}
static void legend(void) {
    Rect b = legend_rect();
    Rect p = lrect(b);
    panel(p.l, p.t, p.r - p.l, p.b - p.t);
    if (!legend_on) { unsigned f = hint_fold[korean]; lquad(6, b.t + 3, f, sprites[f].w, sprites[f].h); return; }
    int x = 6, y = LEGEND_ROWS_Y;
    unsigned title = legend_title[korean], hide = hint_hide[korean];
    int title_y = y - sprites[title].h - 1;
    lquad(x, title_y, title, sprites[title].w, sprites[title].h);
    /* Same top: both sprites are rendered on the title font's baseline frame (tools/build_assets.py framed_sprite). */
    lquad(x + sprites[title].w + 6, title_y, hide, sprites[hide].w, sprites[hide].h);
    int widths[2]; legend_columns(widths);
    int xs[2] = {x, x + widths[0] + 8};
    for (unsigned r = 0; r < 9; r++) {
        unsigned id = legend_sprites[r][korean][toggles[r] && (r == T_ALL || toggles[T_ALL])];
        lquad(xs[r < 5 ? 0 : 1], y + (int)(r < 5 ? r : r - 5) * 7, id, sprites[id].w, sprites[id].h);
    }
    unsigned names = hint_names[korean][item_names], scope_id = legend_scope[scope - 1][korean], lang = legend_lang[korean];
    lquad(xs[0], y + 5 * 7, names, sprites[names].w, sprites[names].h);   /* [H] under [4] */
    lquad(xs[1], y + 4 * 7, scope_id, sprites[scope_id].w, sprites[scope_id].h);   /* [9] under [8] */
    lquad(xs[1], y + 5 * 7, lang, sprites[lang].w, sprites[lang].h);   /* [\\] under [9], same size and colour as [H] */
}
/* Readout rows are bottom-aligned: the last one level with the legend's last row (user, candidate 4). */
static void readouts(void) {
    if (!legend_on) return;
    Rect b = readout_rect();
    Rect p = lrect(b);
    panel(p.l, p.t, p.r - p.l, p.b - p.t);
    const int values[4] = {name_opacity, name_size, icon_opacity, icon_size};
    for (unsigned r = 0; r < 4; r++) {
        int y = LEGEND_ROWS_Y + (int)(r + 2) * 7;
        unsigned hint = readout_hints[r][korean][modifier_ctrl], v = value_sprites[values[r] / 10 - 1];
        lquad(b.l + 3, y, hint, sprites[hint].w, sprites[hint].h);
        lquad(b.r - 3 - sprites[v].w, y, v, sprites[v].w, sprites[v].h);   /* right-aligned in the 200% column */
    }
}

/* ---------- room names: fixed when generated (tools/room_layout.py) and drawn first. RE0 rule 11 (user 2026-11-07):
 * they are not collision targets, so no mark or item name moves because of one; anything drawn later may cover them. */
static int test_no_room_names;   /* tests: draw without room names, everything else unchanged */
static void room_names(const unsigned char *s, unsigned page, const uint8_t *nemesis_badges) {
    for (unsigned i = 0; i < ROOM_COUNT; i++) {
        const RoomLabel *r = &room_labels[i];
        if (r->page != page || !room_shown(r->page, r->idx)) continue;
        shown_counts[9]++;
        if (test_no_room_names) continue;
        unsigned id = r->label[korean];
        int sw = sprites[id].w, sh = sprites[id].h, w = name_dimension(sw), h = name_dimension(sh), cx, cy;
        const int16_t *ln = r->line[korean];
        if (r->lead[korean]) {   /* the leader's end stays put; a resized name grows away from it */
            int ex = map_x(s, ln[2]), ey = map_y(s, ln[3]);
            cx = ex + (r->x2[korean] - 2 * ln[2]) * w / (2 * sw);
            cy = ey + (r->y2[korean] - 2 * ln[3]) * h / (2 * sh);
        } else {
            cx = map_x(s, r->x2[korean] >> 1); cy = map_y(s, r->y2[korean] >> 1);
        }
        int badge = r->idx < 80 && nemesis_badges[r->idx] ? mark_side(8) + 2 : 0;
        Rect box = {(int16_t)(cx - w / 2), (int16_t)(cy - h / 2), (int16_t)(cx - w / 2 + w + badge), (int16_t)(cy - h / 2 + h)};
        if (rects_hit(box, panel_boxes[0]) || rects_hit(box, panel_boxes[1]) || rects_hit(box, panel_boxes[2])) continue;   /* never under the legend */
        if (r->lead[korean]) {
            int x0 = map_x(s, ln[0]), y0 = map_y(s, ln[1]), x1 = map_x(s, ln[2]), y1 = map_y(s, ln[3]);
            int l = x0 < x1 ? x0 : x1, t = y0 < y1 ? y0 : y1;
            quad(l, t, LEADER_SPRITE, (x0 > x1 ? x0 - x1 : x1 - x0) + 1, (y0 > y1 ? y0 - y1 : y1 - y0) + 1);
        }
        quad(box.l, box.t, id, w, h);
        if (badge) icon_quad(box.l + w + 2, box.t + h / 2 - (badge - 2) / 2, monster_icons[M_NEMESIS], badge - 2);
    }
}

/* RE1 HD lock style (INI LockMarker=Unvisited): on the destination side of the door unless only it was visited. */
static void lock_point(unsigned i, const Marker *m, int *x, int *y) {
    if (!lock_far_side) return;
    for (unsigned k = 0; k < LOCK_FAR_COUNT; k++) if (lock_far[k].marker == i) {
        if (visited(m->page, lock_far[k].idx) && !visited(m->page, m->idx)) return;
        *x = lock_far[k].x; *y = lock_far[k].y;
        return;
    }
}

static DWORD last_draw_tick;
static void overlay(unsigned char *s) {
    unsigned page = G8((uintptr_t)s + 0xAB);
    if (page >= 7) page -= 7;   /* segments 7/8 repeat Uptown/Downtown room tables */
    frame_prims = prims[G8(0xA61C90) & 1];
    map_zoom = *(int *)(s + 0xA4);
    if (map_zoom < 50) map_zoom = 50;
    if (map_zoom > 100) map_zoom = 100;
    prim_count = 0;
    unsigned set_bit = G32(DATA_AJ) ? 2 : 1;
    int all = toggles[T_ALL];
    for (unsigned i = 0; i < 11; i++) shown_counts[i] = 0;
    occ_count = 0; mark_count = 0; mark_dups = 0;
    if (sd_mode > 0) { panel_boxes[0] = sd_legend_rect(); panel_boxes[1] = panel_boxes[2] = (Rect){0, 0, 0, 0}; }
    else {
        panel_boxes[0] = lrect(legend_rect()); panel_boxes[1] = legend_on ? lrect(readout_rect()) : readout_rect();
        panel_boxes[2] = hd_off_now() ? notice_rect() : (Rect){0, 0, 0, 0};
    }
    occupy(panel_boxes[0], 8); occupy(panel_boxes[1], 8);
    occupy(panel_boxes[2], 8);
    /* painter order: room names, then marks with their names (lowest tier first), legend and readouts last (top) */
    unsigned live_count = 0;
    live_nemesis_cell = -1;
    if (all && toggles[T_MONSTERS]) live_count = live_enemies(s, page);
    uint8_t nemesis_cells[80] = {0}, nemesis_badges[80] = {0};
    int group_drawn = 0;   /* markers of one placement differ only by call chain guard: draw the run once */
    for (unsigned i = 0; all && i < MARKER_COUNT; i++) {
        const Marker *m = &markers[i];
        if (!(i && same_place(m, m - 1))) group_drawn = 0;
        if (group_drawn) continue;
        if (m->page != page || !(m->sets & set_bit) || !room_shown(m->page, m->idx) || !guard_ok(m)) continue;
        int mx = m->x, my = m->y;
        unsigned item = m->extra;
        switch (m->kind) {
        case K_TYPEWRITER: if (!toggles[T_ROOMS]) continue; push_mark(CAT_FACILITY, 0, map_x(s, mx), map_y(s, my), ICON_TYPEWRITER, 8, m->kind, 0); break;
        case K_ITEMBOX: if (!toggles[T_ROOMS]) continue; push_mark(CAT_FACILITY, 0, map_x(s, mx), map_y(s, my), ICON_ITEMBOX, 8, m->kind, 0); break;
        case K_LOCK:   /* the item that unlocks it */
            if (!toggles[T_LOCKS] || bank_bit(9, m->flag)) continue;
            lock_point(i, m, &mx, &my);
            push_mark(CAT_LOCK, 0, map_x(s, mx), map_y(s, my), item_icons[item < 134 ? item : 0], 7, m->kind, item); break;
        case K_KEY:    /* weapons are key items too (tools/build_overlay.py COMMON) */
            if (!toggles[T_KEY] || picked(m)) continue;
            push_mark(CAT_KEY, 0, map_x(s, mx), map_y(s, my), item_icons[item < 134 ? item : 0], 7, m->kind, item); break;
        case K_FILE: if (!toggles[T_DOCS] || picked(m)) continue; push_mark(CAT_FILE, 0, map_x(s, mx), map_y(s, my), ICON_DOCUMENT, 8, m->kind, item); break;
        case K_MAP: if (!toggles[T_DOCS] || picked(m)) continue; push_mark(CAT_FILE, 0, map_x(s, mx), map_y(s, my), ICON_MAP, 7, m->kind, item); break;
        case K_PUZZLE:
            if (!toggles[T_PUZZLES]) continue;
            /* R509 reader has only room-local completion: remote eligibility cannot be proven. */
            if (m->page == 4 && m->idx == 9 && item == 96 &&
                (G16(0xA673C6) != 4 || G16(0xA673C8) != 9 || bank_bit(4, 26))) continue;
            push_mark(CAT_PUZZLE, 0, map_x(s, mx), map_y(s, my), m->page == 4 && m->idx == 17 && item == 127 ? item_icons[10] : ICON_PUZZLE_MARKER, 8, m->kind,
                      puzzle_names[i] ? puzzle_names[i] : item); break;   /* named after the puzzle, not the item it needs */
        case K_LIVE:
            if (!toggles[T_EVENTS]) continue;
            /* Bank 4 belongs to the loaded room: never apply its completion state remotely. */
            if (item == 9 && G16(0xA673C6) == 4 && G16(0xA673C8) == 0x0D && (bank_bit(4, 5) || (bank_bit(4, 4) && bank_bit(2, 7)))) continue;
            if (item == 5 && G16(0xA673C6) == 1 && G16(0xA673C8) == 0x15 && bank_bit(2, 7)) continue;
            push_mark(CAT_EVENT, 1, map_x(s, mx), map_y(s, my), ICON_SELECTION_MARKER, 8, m->kind, item); break;   /* purple ? diamond */
        case K_ENEMY:
            if (!toggles[T_MONSTERS] || item >= 12 ||
                (m->flag != 255 && bank_bit(second_set(m->sets >> 4) ? 6 : 5, m->flag))) continue;
            if (item == M_NEMESIS) {
                if (m->idx >= 80 || (int)m->idx == live_nemesis_cell || nemesis_cells[m->idx]) continue;
                nemesis_cells[m->idx] = 1;
            }
            if (item == M_NEMESIS && (m->sets & 4) && toggles[T_ROOMS])
                nemesis_badges[m->idx] = 1;
            else push_mark(CAT_ENEMY, 0, map_x(s, mx), map_y(s, my), monster_icons[item], 8, m->kind, item); break;
        case K_COMMON: if (!toggles[T_COMMON] || picked(m)) continue; push_mark(CAT_ITEM, 0, map_x(s, mx), map_y(s, my), item_icons[item < 134 ? item : 0], 7, m->kind, item); break;
        default: continue;
        }
        shown_counts[m->kind]++;
        group_drawn = 1;
    }
    shown_counts[K_ENEMY] += live_count;
    if (all && toggles[T_ROOMS]) { if (sd_mode > 0) sd_room_names(s, page); else room_names(s, page, nemesis_badges); }
    draw_marks();
    if (sd_mode > 0) sd_draw_legend(); else { legend(); readouts(); }
    if (sd_mode <= 0 && hd_off_now()) { Rect n = notice_rect(); panel(n.l, n.t, n.r - n.l, n.b - n.t); quad(n.l + 2, n.t + 2, NOTICE_SPRITE, sprites[NOTICE_SPRITE].w, sprites[NOTICE_SPRITE].h); }
    /* Insert after the native player arrow slot (exe 0x4EB0AE); later inserts are drawn earlier, so
     * walk our painter-ordered list from the top down. */
    void *anchor = (void *)G32(G32(OT2) + 4);
    for (unsigned i = prim_count; i-- > 0;) add_prim(anchor, &frame_prims[i]);
    static unsigned logged_context = ~0u;
    unsigned context = (unsigned)(uint16_t)G16(STAGE_NO) << 16 | (unsigned)(uint16_t)G16(0xA673C8) << 8 | page;
    if (logged_context != context || frame_no % 300 == 0) {
        logged_context = context;
        log_fmt("Nemesis context stage=%d room=%d event=%d phase=%d", G16(STAGE_NO), G16(0xA673C8), G16(0xA67396 + 39 * 2), G16(0xA67396 + 42 * 2));
        uintptr_t enemy_end = G32(0xA6228C);
        log_fmt("Nemesis table end=%x live=%d cell=%d total enemies=%d", (int)enemy_end, live_count, live_nemesis_cell, shown_counts[K_ENEMY]);
        if (enemy_end >= 0xA621EC && enemy_end <= 0xA6226C && !(enemy_end & 3))
            for (uintptr_t slot = 0xA621EC; slot < enemy_end; slot += 4) {
                uintptr_t em = G32(slot);
                if (em && enemy_kind(G8(em + 0x4A)) == M_NEMESIS) {
                    log_fmt("Nemesis actor type=%x flags=%x ai=%x life=%d", G8(em + 0x4A), G32(em), G8(em + 0x47), (uint16_t)G16(em + 0xCC));
                    log_fmt("Nemesis position x=%d z=%d kill=%d dead=%d", G32(em + 0x34), G32(em + 0x3C), G8(em + 0x147), G8(em + 0x147) != 255 && bank_bit(second_set(G16(STAGE_NO)) ? 6 : 5, G8(em + 0x147)));
                }
            }
        if (mark_drops) log_fmt("marks over the %d cap: %d", MAX_MARKS, (int)mark_drops, 0, 0);
        log_fmt("map page=%d prims=%d rooms=%d markers=%d", (int)page, (int)prim_count, (int)shown_counts[9],
                (int)(shown_counts[0] + shown_counts[1] + shown_counts[2] + shown_counts[3] + shown_counts[4] + shown_counts[5] + shown_counts[6] + shown_counts[7] + shown_counts[8] + shown_counts[10]));
    }
}

static void __cdecl hook_map(void *s) {
    AnnotatedMapTestKeys(keys_down());
    map_draw(s);
    frame_no++;
    DWORD now = GetTickCount();
    if (now - last_draw_tick > 200) uploaded = 0;   /* map reopened after a gap: VRAM may have been reused */
    last_draw_tick = now;
    /* REbirth re-resolves a page's HD replacement only when the page pixels are uploaded again, so an
     * opacity change re-uploads the whole atlas (as reopening the map does), not just the CLUT row. */
    if (!uploaded || clut_dirty) upload_atlas();
    clut_dirty = 0;
    overlay((unsigned char *)s);
}

/* ---------- test exports (tests/test_native.py drives these under Unicorn) */
__declspec(dllexport) void __cdecl AnnotatedMapTestDraw(void *s) { hook_map(s); }
__declspec(dllexport) unsigned __cdecl AnnotatedMapTestPrims(void **out) { *out = frame_prims; return prim_count; }
/* tests: force HD (0) or SD (1) for the rest of the run; the atlas is uploaded again on the next frame. -1 only reads. */
__declspec(dllexport) int __cdecl AnnotatedMapTestSdMode(int m) { if (m >= 0) { sd_mode = m; uploaded = 0; } return sd_mode; }
__declspec(dllexport) int __cdecl AnnotatedMapTestSize(void) { return name_size; }
__declspec(dllexport) int __cdecl AnnotatedMapTestScope(void) { return scope; }
__declspec(dllexport) void __cdecl AnnotatedMapTestLoadSettings(void) { load_settings(); }
__declspec(dllexport) int __cdecl AnnotatedMapTestOpacity(void) { return name_opacity; }
/* 0 name size, 1 name opacity, 2 icon size, 3 icon opacity, 4 item names, 5 legend, 6 Ctrl modifier, 7 lock far side */
__declspec(dllexport) int __cdecl AnnotatedMapTestSetting(int which) {
    const int v[8] = {name_size, name_opacity, icon_size, icon_opacity, item_names, legend_on, modifier_ctrl, lock_far_side};
    return which >= 0 && which < 8 ? v[which] : -1;
}
/* The marks of the last draw: count, and their array (Mark layout in src/marks.h) for full-data checks. */
__declspec(dllexport) unsigned __cdecl AnnotatedMapTestMarks(void **out) { *out = marks; return mark_count | mark_dups << 16; }
__declspec(dllexport) void __cdecl AnnotatedMapTestNoRoomNames(int off) { test_no_room_names = off; }
__declspec(dllexport) void __cdecl AnnotatedMapTestOptions(int names, int legend, int far_side) { item_names = names; legend_on = legend; lock_far_side = far_side; }
__declspec(dllexport) unsigned __cdecl AnnotatedMapTestCount(unsigned kind) { return kind < 11 ? shown_counts[kind] : 0; }
__declspec(dllexport) void __cdecl AnnotatedMapTestSet(int all_on, int s, int ko) {
    for (int i = 0; i < T_COUNT; i++) toggles[i] = all_on;
    scope = s; korean = ko;
}

/* ---------- install */
static int patch_call(uintptr_t site, uintptr_t expected, void *hook) {
    unsigned char *p = (unsigned char *)site;
    if (p[0] != 0xE8 || site + 5 + *(int32_t *)(p + 1) != expected) return 0;
    DWORD old;
    if (!VirtualProtect(p, 5, PAGE_EXECUTE_READWRITE, &old)) return 0;
    *(int32_t *)(p + 1) = (int32_t)((uintptr_t)hook - (site + 5));
    VirtualProtect(p, 5, old, &old);
    FlushInstructionCache(GetCurrentProcess(), p, 5);
    return 1;
}
/* Native geometry has separate ownership/visit gates from overlay marker scope. */
static int __cdecl outline_owned(void *flags, unsigned page) {
    if (toggles[T_ALL] && scope == 3 && (uintptr_t)flags == MAP_OWNED) return 1;
    return flg_ck(flags, page);
}
static int __cdecl outline_visited(unsigned page, unsigned idx) {
    if (toggles[T_ALL] && scope == 3) return 1;
    return ((room_fn)0x4EB9C0)(page, idx);
}
static int install_outline_scope(void) {
    const uintptr_t sites[] = {0x4EAD35, 0x4EBB9C, 0x4EAD7A};
    const uintptr_t targets[] = {0x428DE0, 0x428DE0, 0x4EB9C0};
    void *hooks[] = {(void *)outline_owned, (void *)outline_owned, (void *)outline_visited};
    for (unsigned i = 0; i < 3; i++) {
        const unsigned char *p = (const unsigned char *)sites[i];
        if (p[0] != 0xE8 || sites[i] + 5 + *(const int32_t *)(p + 1) != targets[i]) return 0;
    }
    for (unsigned i = 0; i < 3; i++) if (!patch_call(sites[i], targets[i], hooks[i])) return 0;
    return 1;
}
__declspec(dllexport) int __cdecl AnnotatedMapTestInstallOutlineScope(void) { return install_outline_scope(); }
static int supported_exe(void) {
    unsigned char *base = (unsigned char *)GetModuleHandleA(NULL);
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    /* SourceNext BIOHAZARD(R) 3 PC.exe: image base 0x400000, these call sites and the flag checker bytes */
    if ((uintptr_t)base != 0x400000 || nt->FileHeader.TimeDateStamp != 0x44642AACu || nt->OptionalHeader.SizeOfImage != 0xB01000u) return 0;
    static const unsigned char flg[] = {0x8B, 0x54, 0x24, 0x08, 0xB8, 0x00, 0x00, 0x00, 0x80};   /* Flg_ck 0x428DE0 */
    static const unsigned char draw[] = {0x83, 0xEC, 0x28, 0x53, 0x55, 0x56, 0x8B, 0x74};        /* map draw 0x4EAC60 */
    static const unsigned char actor[] = {0x8B,0x0F,0x81,0xE1,0xFF,0xFF,0xFF,0xCF,0x8A,0xC1,0x89,0x0F,0xA8,0x01,0x74,0x42,0xF6,0x47,0x47,0x80,0x75,0x3C};
    for (unsigned i = 0; i < sizeof flg; i++) if (((unsigned char *)0x428DE0)[i] != flg[i]) return 0;
    for (unsigned i = 0; i < sizeof draw; i++) if (((unsigned char *)0x4EAC60)[i] != draw[i]) return 0;
    for (unsigned i = 0; i < sizeof actor; i++) if (((unsigned char *)0x42DCAE)[i] != actor[i]) return 0;
    return 1;
}

BOOL WINAPI DllMain(HINSTANCE module, DWORD reason, LPVOID reserved) {
    (void)reserved;
    if (reason != DLL_PROCESS_ATTACH) return TRUE;
    DisableThreadLibraryCalls(module);
    char own[MAX_PATH];
    GetModuleFileNameA(module, own, sizeof own);
    char *slash = own;
    for (char *p = own; *p; p++) if (*p == '\\' || *p == '/') slash = p + 1;
    lstrcpyA(slash, "RE3.AnnotatedMap.ini"); lstrcpyA(ini_path, own);
    lstrcpyA(slash, "RE3.AnnotatedMap.ini.tmp"); lstrcpyA(tmp_path, own);
    lstrcpyA(slash, "RE3.AnnotatedMap.log"); lstrcpyA(log_path, own);
    lstrcpyA(slash, "config.ini"); lstrcpyA(config_path, own);
    DeleteFileA(log_path);
    load_settings();
    { int hd = rebirth_hd_textures();
      if (hd == 0) log_text("Classic REbirth config.ini has HDTextures=0: the map text is drawn from the low-resolution atlas (blurry). Set HDTextures=1.");
      else if (hd < 0) log_text("Classic REbirth config.ini [DLL] HDTextures not found: HD map text needs HDTextures=1 (or the file is missing)."); }
    if (!supported_exe()) { log_text("Unsupported executable; no patch applied"); return TRUE; }
    for (unsigned i = 0; i < 2; i++) {
        unsigned char *p = (unsigned char *)hook_sites[i];
        if (p[0] != 0xE8 || hook_sites[i] + 5 + *(int32_t *)(p + 1) != map_draw_va) { log_text("Unexpected map call site; no patch applied"); return TRUE; }
    }
    if (!install_outline_scope()) { log_text("Unexpected native outline gates; no map hook applied"); return TRUE; }
    for (unsigned i = 0; i < 2; i++) patch_call(hook_sites[i], map_draw_va, (void *)hook_map);
    log_fmt("RE3 Annotated Map loaded: markers=%d rooms=%d atlas pages=%d lang=%d", MARKER_COUNT, ROOM_COUNT, ATLAS_PAGES, korean);
    log_text("Monster icons: scoped conditional encounters; Nemesis uses guarded encounters and active native actor.");
    return TRUE;
}
