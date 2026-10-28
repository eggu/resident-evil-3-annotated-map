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

/* ---------- settings */
enum { T_ALL, T_ROOMS, T_LOCKS, T_KEY, T_DOCS, T_PUZZLES, T_COMMON, T_MONSTERS, T_COUNT };
static const char *const toggle_names[T_COUNT] = {"All", "Rooms", "Locks", "KeyItems", "Documents", "Puzzles", "CommonItems", "Monsters"};
static const int toggle_default[T_COUNT] = {1, 1, 1, 1, 1, 1, 1, 0};
static int toggles[T_COUNT], scope = 1, korean, name_size = 100, name_opacity = 70, name_clut_dirty;   /* opacity: percent, 10..100 step 10 */
static char ini_path[MAX_PATH], log_path[MAX_PATH];
static unsigned log_lines;

static void log_text(const char *s) {
    if (log_lines++ > 300) return;
    HANDLE h = CreateFileA(log_path, FILE_APPEND_DATA, FILE_SHARE_READ, NULL, OPEN_ALWAYS, 0, NULL);
    if (h == INVALID_HANDLE_VALUE) return;
    DWORD w;
    WriteFile(h, s, (DWORD)lstrlenA(s), &w, NULL);
    WriteFile(h, "\r\n", 2, &w, NULL);
    CloseHandle(h);
}
static void log_fmt(const char *fmt, int a, int b, int c, int d) { char buf[256]; wsprintfA(buf, fmt, a, b, c, d); log_text(buf); }

static void save_settings(void) {
    char v[2] = {0, 0};
    for (int i = 0; i < T_COUNT; i++) { v[0] = (char)('0' + toggles[i]); WritePrivateProfileStringA("AnnotatedMap", toggle_names[i], v, ini_path); }
    v[0] = (char)('0' + scope); WritePrivateProfileStringA("AnnotatedMap", "Scope", v, ini_path);
    WritePrivateProfileStringA("AnnotatedMap", "Language", korean ? "ko" : "en", ini_path);
    char o[8]; wsprintfA(o, "%d", name_size); WritePrivateProfileStringA("AnnotatedMap", "NameSize", o, ini_path);
    wsprintfA(o, "%d", name_opacity); WritePrivateProfileStringA("AnnotatedMap", "NameOpacity", o, ini_path);
}
static void load_settings(void) {
    for (int i = 0; i < T_COUNT; i++) toggles[i] = GetPrivateProfileIntA("AnnotatedMap", toggle_names[i], toggle_default[i], ini_path) != 0;
    scope = GetPrivateProfileIntA("AnnotatedMap", "Scope", 1, ini_path);
    if (scope < 1 || scope > 3) scope = 1;
    name_size = GetPrivateProfileIntA("AnnotatedMap", "NameSize", 100, ini_path);
    if (name_size < 50) name_size = 50;
    if (name_size > 150) name_size = 150;
    name_size = (name_size + 5) / 10 * 10;
    char lang[8];
    GetPrivateProfileStringA("AnnotatedMap", "Language", "ko", lang, sizeof lang, ini_path);
    korean = lang[0] != 'e';
    /* Name pages' HD replacements bake this opacity in (one file per 10% step), see tools/build_assets.py. */
    name_opacity = (GetPrivateProfileIntA("AnnotatedMap", "NameOpacity", 70, ini_path) + 5) / 10 * 10;
    if (name_opacity < 10) name_opacity = 10;
    if (name_opacity > 100) name_opacity = 100;
}

/* ---------- input: edge-triggered keys while the map is drawn */
static unsigned keys_held;
static unsigned keys_down(void) {
    unsigned k = 0;
    for (int i = 0; i <= 9; i++) if (GetAsyncKeyState('0' + i) & 0x8000) k |= 1u << i;
    if ((GetAsyncKeyState(VK_OEM_PLUS) | GetAsyncKeyState(VK_ADD)) & 0x8000) k |= 1u << 10;
    if ((GetAsyncKeyState(VK_OEM_MINUS) | GetAsyncKeyState(VK_SUBTRACT)) & 0x8000) k |= 1u << 11;
    if (GetAsyncKeyState(VK_SHIFT) & 0x8000) k |= 1u << 12;
    return k;
}
__declspec(dllexport) void __cdecl AnnotatedMapTestKeys(unsigned down);
void __cdecl AnnotatedMapTestKeys(unsigned down) {
    unsigned pressed = down & ~keys_held;
    keys_held = down;
    if (!pressed) return;
    for (int i = 0; i < T_COUNT; i++) if (pressed & (1u << i)) toggles[i] = !toggles[i];
    if (pressed & (1u << 8)) scope = scope % 3 + 1;
    if (pressed & (1u << 9)) korean = !korean;
    if (down & (1u << 12)) {   /* Shift + +/-: name opacity in 10% steps (one HD variant per step) */
        if ((pressed & (1u << 10)) && name_opacity < 100) { name_opacity += 10; name_clut_dirty = 1; }
        if ((pressed & (1u << 11)) && name_opacity > 10) { name_opacity -= 10; name_clut_dirty = 1; }
    } else {
        if ((pressed & (1u << 10)) && name_size < 150) name_size += 10;
        if ((pressed & (1u << 11)) && name_size > 50) name_size -= 10;
    }
    save_settings();
}

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

static void quad(int x, int y, unsigned sprite_id, int w, int h) {
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
    p->clut = (uint16_t)(((CLUT_Y + (s->page >= NAME_PAGE_FIRST)) << 6) | (CLUT_X >> 4));
    p->tpage = (uint16_t)((ATLAS_X0 / 64) + s->page);
}
/* occupied screen rectangles this frame: room names and icons first, then item names avoid them */
typedef struct { int16_t x, y, w, h; } Box;
static Box boxes[MAX_PRIMS];
static unsigned box_count;
static void reserve(int x, int y, int w, int h) { if (box_count < MAX_PRIMS) boxes[box_count++] = (Box){(int16_t)x, (int16_t)y, (int16_t)w, (int16_t)h}; }
static int overlap(int x, int y, int w, int h) {
    int sum = 0;
    for (unsigned i = 0; i < box_count; i++) {
        const Box *b = &boxes[i];
        int l = x > b->x ? x : b->x, t = y > b->y ? y : b->y;
        int r = x + w < b->x + b->w ? x + w : b->x + b->w, d = y + h < b->y + b->h ? y + h : b->y + b->h;
        if (r > l && d > t) sum += (r - l) * (d - t);
    }
    return sum;
}
static void sprite_at(int cx, int cy, unsigned id) { const Sprite *s = &sprites[id]; quad(cx - s->w / 2, cy - s->h / 2, id, s->w, s->h); reserve(cx - s->w / 2, cy - s->h / 2, s->w, s->h); }
/* Marker icons follow the map zoom (status +0xA4 animates 50..100%): full size zoomed in, smaller zoomed out. */
static int map_zoom = 100;
static int zoomed(int size) { int z = (size * map_zoom + 50) / 100; return z < 3 ? 3 : z; }
static void icon_at(int cx, int cy, unsigned id, int size) {
    size = zoomed(size);
    quad(cx - size / 2, cy - size / 2, id, size, size); reserve(cx - size / 2, cy - size / 2, size, size);
}
/* room name centred on its anchor, nudged to the least-covered of a few nearby spots */
/* Names shrink less than icons: 100% when zoomed in, 70% at the native 50% zoom-out. */
static int name_dimension(int v) { int scaled = (v * name_size + 50) / 100; int z = (scaled * (100 - (100 - map_zoom) * 3 / 5) + 50) / 100; return z < 1 ? 1 : z; }
static void room_label(int cx, int cy, unsigned id, int nemesis) {
    int w = name_dimension(sprites[id].w), h = name_dimension(sprites[id].h);
    int badge = nemesis ? zoomed(8) + 2 : 0;
    int total_w = w + badge;
    static const int8_t off[7][2] = {{0, 0}, {0, -5}, {0, 5}, {-8, 0}, {8, 0}, {0, -9}, {0, 9}};
    int best = 0, score = 0x7fffffff;
    for (int k = 0; k < 7; k++) {
        int o = overlap(cx - total_w / 2 + off[k][0], cy - h / 2 + off[k][1], total_w, h > zoomed(8) ? h : zoomed(8)) + k;
        if (o < score) { score = o; best = k; }
    }
    int x = cx - total_w / 2 + off[best][0], y = cy - h / 2 + off[best][1];
    quad(x, y, id, w, h);
    reserve(x, y, w, h);
    if (nemesis) icon_at(x + w + 2 + zoomed(8) / 2, y + h / 2, monster_icons[M_NEMESIS], 8);
}
static void label_near(int cx, int cy, int r, unsigned id) {
    int w = name_dimension(sprites[id].w), h = name_dimension(sprites[id].h);
    const int xs[4] = {cx + r + 1, cx - r - 1 - w, cx - w / 2, cx - w / 2};
    const int ys[4] = {cy - h / 2, cy - h / 2, cy + r + 1, cy - r - 1 - h};
    int best = 0, score = 0x7fffffff;
    for (int k = 0; k < 4; k++) {
        int o = overlap(xs[k], ys[k], w, h) + (xs[k] < 0 || xs[k] + w > 320 || ys[k] < 0 || ys[k] + h > 240 ? 100000 : 0);
        if (o < score) { score = o; best = k; }
        if (!o) break;
    }
    quad(xs[best], ys[best], id, w, h);
    reserve(xs[best], ys[best], w, h);
}

/* ---------- map transform (exe 0x4EAF50 / 0x4EB6A0) */
static int div100(int v) { return v / 100; }
static int map_x(const unsigned char *s, int x) { int o = *(int *)(s + 0x94); return div100((x + o) * *(int *)(s + 0xA4)) + *(int *)(s + 0x7C) - o + 160; }
static int map_y(const unsigned char *s, int y) { int o = *(int *)(s + 0x98); return div100((y + o) * *(int *)(s + 0xA4)) + *(int *)(s + 0x80) - o + 120; }

/* ---------- atlas upload: once per map session (VRAM x 64.. is free while the status screen is open) */
static int uploaded;
static void upload_atlas(void) {
    for (int p = 0; p < ATLAS_PAGES; p++) {
        int16_t rect[4] = {(int16_t)(ATLAS_X0 + 64 * p), 0, 64, 256};
        load_image(rect, atlas_pixels[p]);
    }
    int16_t clut_rect[4] = {CLUT_X, CLUT_Y, 16, 1};
    load_image(clut_rect, atlas_clut);
    int16_t name_rect[4] = {CLUT_X, CLUT_Y + 1, 16, 1};
    load_image(name_rect, name_cluts[name_opacity / 10 - 1]);
    uploaded = 1;
}

#include "live_enemies.h"

static const ItemLabel *item_label(unsigned item) {
    for (unsigned i = 0; i < ITEM_LABEL_COUNT; i++) if (item_labels[i].item == item) return &item_labels[i];
    return 0;
}

/* ---------- legend (bottom-left, two columns) */
static void legend_box(int *x0, int *y0, int *w, int *h) {
    int widths[2] = {0, 0};
    for (unsigned r = 0; r < 8; r++) { int lw = sprites[legend_sprites[r][korean][1]].w; if (lw > widths[r / 4]) widths[r / 4] = lw; }
    *x0 = 3; *y0 = 240 - 4 - 5 * 7 - 14; *w = widths[0] + widths[1] + 14; *h = 240 - *y0 - 1;
}
static void legend(void) {
    const unsigned rows = 8;
    int y = 240 - 4 - (int)(rows / 2 + 1) * 7, x = 6;
    int bx, by, bw, bh;
    legend_box(&bx, &by, &bw, &bh);
    quad(bx, by, ICON_PANEL, bw, bh);
    if (prim_count) { frame_prims[prim_count - 1].code |= 2; frame_prims[prim_count - 1].u1 = frame_prims[prim_count - 1].u3 = (uint8_t)(sprites[ICON_PANEL].u + 2); frame_prims[prim_count - 1].v2 = frame_prims[prim_count - 1].v3 = (uint8_t)(sprites[ICON_PANEL].v + 2); frame_prims[prim_count - 1].u0 += 1; frame_prims[prim_count - 1].u2 += 1; frame_prims[prim_count - 1].v0 += 1; frame_prims[prim_count - 1].v1 += 1; }
    sprite_at(x + sprites[legend_title[korean]].w / 2, y - 8, legend_title[korean]);
    unsigned op = legend_opacity[name_opacity / 10 - 1][korean];
    unsigned sz = legend_size[(name_size - 50) / 10][korean];
    int settings_x = x + sprites[legend_title[korean]].w + 6;
    quad(settings_x, y - 12, op, sprites[op].w, sprites[op].h);
    quad(settings_x, y - 6, sz, sprites[sz].w, sprites[sz].h);
    int widths[2] = {0, 0};
    for (unsigned r = 0; r < rows; r++) { int w = sprites[legend_sprites[r][korean][1]].w; if (w > widths[r / 4]) widths[r / 4] = w; }
    for (unsigned r = 0; r < rows; r++) {
        int on = toggles[r] && (r == T_ALL || toggles[T_ALL]);
        unsigned id = legend_sprites[r][korean][on];
        int cx = r < 4 ? x : x + widths[0] + 8, cy = y + (int)(r % 4) * 7;
        quad(cx, cy, id, sprites[id].w, sprites[id].h);
    }
    int cy = y + 4 * 7, cx = x;
    quad(cx, cy, legend_scope[scope - 1][korean], sprites[legend_scope[scope - 1][korean]].w, sprites[legend_scope[scope - 1][korean]].h);
    cx += widths[0] + 8;
    quad(cx, cy, legend_lang[korean], sprites[legend_lang[korean]].w, sprites[legend_lang[korean]].h);

}

static unsigned frame_no, shown_counts[11];
#define MAX_PENDING 128
typedef struct { int16_t x, y; uint16_t id; } Pending;
static Pending pending[MAX_PENDING];
static unsigned pending_count;
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
    box_count = 0; pending_count = 0;
    { int bx, by, bw, bh; legend_box(&bx, &by, &bw, &bh); reserve(bx, by, bw, bh); }
    /* painter order: room names, then markers, then their names, legend last (top) */
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
        int x = map_x(s, m->x), y = map_y(s, m->y);
        switch (m->kind) {
        case K_TYPEWRITER: if (!toggles[T_ROOMS]) continue; icon_at(x, y, ICON_TYPEWRITER, 8); break;
        case K_ITEMBOX: if (!toggles[T_ROOMS]) continue; icon_at(x, y, ICON_ITEMBOX, 8); break;
        case K_LOCK: {
            if (!toggles[T_LOCKS] || bank_bit(9, m->flag)) continue;
            icon_at(x, y, item_icons[m->extra < 134 ? m->extra : 0], 7);   /* the item that unlocks it */
            const ItemLabel *l = item_label(m->extra);
            if (l && pending_count < MAX_PENDING) pending[pending_count++] = (Pending){(int16_t)x, (int16_t)y, l->lock_label[korean]};
            break;
        }
        case K_KEY: {
            if (!toggles[T_KEY] || picked(m)) continue;
            icon_at(x, y, item_icons[m->extra < 134 ? m->extra : 0], 7);   /* same size as common items */
            const ItemLabel *l = item_label(m->extra);
            if (l && pending_count < MAX_PENDING) pending[pending_count++] = (Pending){(int16_t)x, (int16_t)y, l->label[korean]};
            break;
        }
        case K_FILE: if (!toggles[T_DOCS] || picked(m)) continue; icon_at(x, y, ICON_DOCUMENT, 8); break;
        case K_MAP: if (!toggles[T_DOCS] || picked(m)) continue; icon_at(x, y, ICON_MAP, 7); break;
        case K_PUZZLE:
            if (!toggles[T_PUZZLES]) continue;
            /* R509 reader has only room-local completion: remote eligibility cannot be proven. */
            if (m->page == 4 && m->idx == 9 && m->extra == 96 &&
                (G16(0xA673C6) != 4 || G16(0xA673C8) != 9 || bank_bit(4, 26))) continue;
            icon_at(x, y, m->page == 4 && m->idx == 17 && m->extra == 127 ? item_icons[10] : ICON_PUZZLE_MARKER, 8); break;
        case K_LIVE:
            if (!toggles[T_PUZZLES]) continue;
            /* Bank 4 belongs to the loaded room: never apply its completion state remotely. */
            if (m->extra == 9 && G16(0xA673C6) == 4 && G16(0xA673C8) == 0x0D && (bank_bit(4, 5) || (bank_bit(4, 4) && bank_bit(2, 7)))) continue;
            if (m->extra == 5 && G16(0xA673C6) == 1 && G16(0xA673C8) == 0x15 && bank_bit(2, 7)) continue;
            icon_at(x, y, ICON_SELECTION_MARKER, 8); break;
        case K_ENEMY:
            if (!toggles[T_MONSTERS] || m->extra >= 12 ||
                (m->flag != 255 && bank_bit(second_set(m->sets >> 4) ? 6 : 5, m->flag))) continue;
            if (m->extra == M_NEMESIS) {
                if (m->idx >= 80 || (int)m->idx == live_nemesis_cell || nemesis_cells[m->idx]) continue;
                nemesis_cells[m->idx] = 1;
            }
            if (m->extra == M_NEMESIS && (m->sets & 4) && toggles[T_ROOMS])
                nemesis_badges[m->idx] = 1;
            else icon_at(x, y, monster_icons[m->extra], 8); break;
        case K_COMMON: if (!toggles[T_COMMON] || picked(m)) continue; icon_at(x, y, item_icons[m->extra < 134 ? m->extra : 0], 7); break;
        default: continue;
        }
        shown_counts[m->kind]++;
        group_drawn = 1;
    }
    shown_counts[K_ENEMY] += live_count;
    if (all && toggles[T_ROOMS])
        for (unsigned i = 0; i < ROOM_COUNT; i++) {
            const RoomLabel *r = &room_labels[i];
            if (r->page != page || !room_shown(r->page, r->idx)) continue;
            room_label(map_x(s, r->x[korean]), map_y(s, r->y[korean]), r->label[korean], r->idx < 80 && nemesis_badges[r->idx]);
            shown_counts[9]++;
        }
    for (unsigned i = 0; i < pending_count; i++) label_near(pending[i].x, pending[i].y, zoomed(7) / 2 + 1, pending[i].id);
    legend();
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
    if (!uploaded || name_clut_dirty) upload_atlas();
    name_clut_dirty = 0;
    overlay((unsigned char *)s);
}

/* ---------- test exports (tests/test_native.py drives these under Unicorn) */
__declspec(dllexport) void __cdecl AnnotatedMapTestDraw(void *s) { hook_map(s); }
__declspec(dllexport) unsigned __cdecl AnnotatedMapTestPrims(void **out) { *out = frame_prims; return prim_count; }
__declspec(dllexport) int __cdecl AnnotatedMapTestSize(void) { return name_size; }
__declspec(dllexport) int __cdecl AnnotatedMapTestScope(void) { return scope; }
__declspec(dllexport) void __cdecl AnnotatedMapTestLoadSettings(void) { load_settings(); }
__declspec(dllexport) int __cdecl AnnotatedMapTestOpacity(void) { return name_opacity; }
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
    lstrcpyA(slash, "RE3.AnnotatedMap.log"); lstrcpyA(log_path, own);
    DeleteFileA(log_path);
    load_settings();
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
