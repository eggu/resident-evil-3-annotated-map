/* ---------- SD mode (Classic REbirth HDTextures=0, user decisions 2026-11-12): the SD atlas (sd_assets.h,
 * tools/build_sd.py) replaces the HD atlas in the same VRAM pages and CLUT rows. 1x markers, Galmuri9 names placed
 * outside their rooms on coloured leaders, names only at full zoom, no item names, no size or opacity settings. */
#include "sd_assets.h"

static int sd_mode = -1;   /* -1 undecided; fixed for the session (REbirth cannot switch HD while running) */
static int sd_decide(void) {
    if (sd_mode < 0) {
        int hd = rebirth_hd_textures();
        sd_mode = display_mode == 2 || (display_mode == 0 && hd <= 0);   /* HDTextures missing counts as SD */
        log_text(sd_mode ? "SD mode: 1x markers and names (HDTextures=0 or DisplayMode=SD)" : "HD mode");
    }
    return sd_mode;
}
#define SD_CLUT_X 192   /* the CLUT spot the live test proved (TestSD, 2026-11-12) */
#define SD_CLUT_Y 256
enum { SD_ROW_ICONS = 5, SD_ROW_LEGEND = 6 };   /* CLUT rows 0-4: one per leader colour */
static void upload_sd(void) {
    for (int p = 0; p < SD_PAGES; p++) { int16_t r[4] = {sd_vram[p][0], sd_vram[p][1], 64, sd_vram[p][2]}; load_image(r, sd_pixels[p]); }
    for (int i = 0; i < 7; i++) { int16_t r[4] = {SD_CLUT_X, (int16_t)(SD_CLUT_Y + i), 16, 1}; load_image(r, sd_cluts[i]); }
}
static PolyFT4 *sd_prim(const SdSprite *s, unsigned row) {
    if (prim_count >= MAX_PRIMS) return 0;
    PolyFT4 *p = &frame_prims[prim_count++];
    memset(p, 0, sizeof *p);
    set_poly_ft4(p);
    p->r = p->g = p->b = 0x80;
    p->clut = (uint16_t)(((SD_CLUT_Y + row) << 6) | (SD_CLUT_X >> 4));
    p->tpage = (uint16_t)((sd_vram[s->page][0] / 64) | (sd_vram[s->page][1] / 256) << 4);
    return p;
}
/* 1:1 texels; colour picks the CLUT row of an ink sprite (room names), other sprites use their own row */
static void sd_quad_c(int x, int y, unsigned id, unsigned colour) {
    const SdSprite *s = &sd_sprites[id];
    if (x + s->w <= clip_x0 || y + s->h <= clip_y0 || x >= clip_x1 || y >= clip_y1) return;
    PolyFT4 *p = sd_prim(s, s->row == 1 ? SD_ROW_ICONS : s->row == 2 ? SD_ROW_LEGEND : colour);
    if (!p) return;
    p->x0 = p->x2 = (int16_t)x; p->x1 = p->x3 = (int16_t)(x + s->w);
    p->y0 = p->y1 = (int16_t)y; p->y2 = p->y3 = (int16_t)(y + s->h);
    p->u0 = p->u2 = s->u; p->u1 = p->u3 = (uint8_t)(s->u + s->w);
    p->v0 = p->v1 = s->v; p->v2 = p->v3 = (uint8_t)(s->v + s->h);
}
static void sd_quad(int x, int y, unsigned id) { sd_quad_c(x, y, id, 0); }
static void sd_line(int x0, int y0, int x1, int y1, unsigned colour) {   /* line_quad on the middle of the 4x4 leader tile */
    if ((x0 < clip_x0 && x1 < clip_x0) || (y0 < clip_y0 && y1 < clip_y0) || (x0 >= clip_x1 && x1 >= clip_x1) || (y0 >= clip_y1 && y1 >= clip_y1)) return;
    unsigned before = prim_count;
    line_quad(x0, y0, x1, y1);
    if (prim_count == before) return;
    const SdSprite *s = &sd_sprites[SD_LEADER];
    PolyFT4 *p = &frame_prims[prim_count - 1];
    p->u0 = p->u1 = p->u2 = p->u3 = (uint8_t)(s->u + 2); p->v0 = p->v1 = p->v2 = p->v3 = (uint8_t)(s->v + 2);
    p->clut = (uint16_t)(((SD_CLUT_Y + colour) << 6) | (SD_CLUT_X >> 4));
    p->tpage = (uint16_t)((sd_vram[s->page][0] / 64) | (sd_vram[s->page][1] / 256) << 4);
}
static void sd_panel(int x, int y, int w, int h) {   /* semi-transparent dark tile, as the HD panel */
    const SdSprite *s = &sd_sprites[SD_PANEL];
    PolyFT4 *p = sd_prim(s, SD_ROW_LEGEND);
    if (!p) return;
    p->code |= 2;
    p->x0 = p->x2 = (int16_t)x; p->x1 = p->x3 = (int16_t)(x + w);
    p->y0 = p->y1 = (int16_t)y; p->y2 = p->y3 = (int16_t)(y + h);
    p->u0 = p->u1 = p->u2 = p->u3 = (uint8_t)(s->u + 2); p->v0 = p->v1 = p->v2 = p->v3 = (uint8_t)(s->v + 2);
}
/* Mark sprite for SD by what the mark is; 0xFFFF = not shown in SD. */
static unsigned sd_icon(unsigned kind, unsigned item, int event) {
    if (event) return SD_EVENT;
    switch (kind) {
    case K_TYPEWRITER: return SD_TYPEWRITER;
    case K_ITEMBOX: return SD_ITEMBOX;
    case K_KEY: return SD_KEY;
    case K_FILE: return SD_FILE;
    case K_MAP: return SD_MAP;
    case K_PUZZLE: return SD_PUZZLE;
    case K_LIVE: return SD_EVENT;
    case K_ENEMY: return SD_ENEMY;
    case K_LOCK: case K_COMMON: return item < 134 ? sd_item_icon[item] : 0xFFFF;
    default: return 0xFFFF;
    }
}
/* Room names and leaders fixed at build time (tools/sd_layout.py, user 2026-11-12): only at full zoom, each room in its
 * own leader colour (a CLUT row per colour). */
static void sd_room_names(const unsigned char *s, unsigned page) {
    for (unsigned i = 0; i < SD_ROOM_COUNT; i++) {
        const SdRoom *r = &sd_rooms[i];
        if (r->page != page || !room_shown(r->page, r->idx)) continue;
        shown_counts[9]++;
        if (map_zoom < 100) continue;
        const SdSprite *sp = &sd_sprites[r->sprite[korean]];
        unsigned c = r->colour[korean], n = r->points[korean];
        int pts[6], x = map_x(s, r->x[korean]), y = map_y(s, r->y[korean]);
        for (unsigned k = 0; k < n; k++) { pts[2 * k] = map_x(s, r->pt[korean][2 * k]); pts[2 * k + 1] = map_y(s, r->pt[korean][2 * k + 1]); }
        /* Scrolled maps (user 2026-11-12): a name cut by the screen edge or under the legend moves inside, and its
         * leader ends on the moved name's nearest edge. A room itself off screen keeps its name off screen. */
        if (n && pts[0] >= 0 && pts[0] < 320 && pts[1] >= 0 && pts[1] < 240) {
            int nx = x < 2 ? 2 : x + sp->w > 318 ? 318 - sp->w : x, ny = y < 2 ? 2 : y + sp->h > 238 ? 238 - sp->h : y;
            Rect b = {(int16_t)nx, (int16_t)ny, (int16_t)(nx + sp->w), (int16_t)(ny + sp->h)};
            if (rects_hit(b, panel_boxes[0])) { ny = panel_boxes[0].t - 2 - sp->h; b.t = (int16_t)ny; b.b = (int16_t)(ny + sp->h); }
            if (nx != x || ny != y) {
                int px = pts[2 * n - 4 < 0 ? 0 : 2 * n - 4], py = pts[2 * n - 3 < 1 ? 1 : 2 * n - 3];
                pts[2 * n - 2] = px < nx ? nx - 1 : px >= nx + sp->w ? nx + sp->w : px;
                pts[2 * n - 1] = py < ny ? ny - 1 : py >= ny + sp->h ? ny + sp->h : py;
                x = nx; y = ny;
            }
        }
        for (unsigned k = 1; k < n; k++) sd_line(pts[2 * k - 2], pts[2 * k - 1], pts[2 * k], pts[2 * k + 1], c);
        sd_quad_c(x, y, r->sprite[korean], c);
    }
}
/* Legend: two columns of 11 px rows, bottom-left; no item-name, size or opacity rows in SD. */
#define SD_ROW 11
static int sd_col_width(unsigned c) {
    int w = 0;
    for (unsigned r = c ? 5 : 0; r < (c ? 9u : 5u); r++) for (unsigned on = 0; on < 2; on++) if (sd_sprites[sd_legend[r][korean][on]].w > w) w = sd_sprites[sd_legend[r][korean][on]].w;
    if (c) { for (unsigned s = 0; s < 3; s++) if (sd_sprites[sd_scope[s][korean]].w > w) w = sd_sprites[sd_scope[s][korean]].w;
             if (sd_sprites[sd_lang[korean]].w > w) w = sd_sprites[sd_lang[korean]].w; }
    return w;
}
static Rect sd_legend_rect(void) {
    if (!legend_on) { const SdSprite *f = &sd_sprites[sd_fold[korean]]; return (Rect){2, (int16_t)(238 - f->h - 4), (int16_t)(2 + f->w + 6), 238}; }
    int w = sd_col_width(0) + 8 + sd_col_width(1), head = sd_sprites[sd_title[korean]].w + 8 + sd_sprites[sd_hide[korean]].w;
    if (head > w) w = head;
    return (Rect){2, (int16_t)(238 - 7 * SD_ROW - 6), (int16_t)(2 + w + 6), 238};
}
static void sd_draw_legend(void) {
    Rect b = sd_legend_rect();
    sd_panel(b.l, b.t, b.r - b.l, b.b - b.t);
    if (!legend_on) { sd_quad(b.l + 3, b.t + 2, sd_fold[korean]); return; }
    int x = b.l + 3, y = b.t + 3;
    sd_quad(x, y, sd_title[korean]);
    sd_quad(x + sd_sprites[sd_title[korean]].w + 8, y, sd_hide[korean]);
    int xs[2] = {x, x + sd_col_width(0) + 8};
    for (unsigned r = 0; r < 9; r++)
        sd_quad(xs[r < 5 ? 0 : 1], y + SD_ROW * (int)(1 + (r < 5 ? r : r - 5)), sd_legend[r][korean][toggles[r] && (r == T_ALL || toggles[T_ALL])]);
    sd_quad(xs[1], y + SD_ROW * 5, sd_scope[scope - 1][korean]);
    sd_quad(xs[1], y + SD_ROW * 6, sd_lang[korean]);
}
