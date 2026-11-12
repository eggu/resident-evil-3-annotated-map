/* Settings, keys and RE3.AnnotatedMap.ini (RE0 HD map rules, user 2026-11-07): RE0 keys with Shift as the default
 * modifier (Ctrl through the INI), a Version key with a one-time migration, atomic saves and a per-key debounce. */
#define SETTINGS_VERSION 4   /* 4: [6] Events split from puzzles, name/icon size baselines, [\\] language key */
#define DEBOUNCE_MS 350            /* RE0: one press once arrived three times, 200 ms apart */
enum { T_ALL, T_ROOMS, T_LOCKS, T_KEY, T_DOCS, T_PUZZLES, T_EVENTS, T_COMMON, T_MONSTERS, T_COUNT };   /* legend [0]..[8] */
static const char *const toggle_names[T_COUNT] = {"All", "Rooms", "Locks", "KeyItems", "Documents", "Puzzles", "Events", "CommonItems", "Monsters"};
static const int toggle_default[T_COUNT] = {1, 1, 0, 0, 0, 0, 0, 0, 0};   /* RE1 parity: Rooms only */
/* name/icon opacity: percent, 10..100 step 10; name size 50..200, icon size 50..200. Sizes are relative to baselines:
 * name 100 = the old 80% (NAME_BASE), item icon 100 = the old 130% (ITEM_ICON_BASE); other icons are unscaled. */
#define NAME_BASE 80
#define ITEM_ICON_BASE 130
static int toggles[T_COUNT], scope = 1, korean, name_size = 100, name_opacity = 70, icon_size = 100, icon_opacity = 100;
static int display_mode;   /* DisplayMode: 0 Auto (Classic REbirth HDTextures), 1 HD, 2 SD */
static int item_names, legend_on = 1, modifier_ctrl, lock_far_side, clut_dirty;
static char ini_path[MAX_PATH], tmp_path[MAX_PATH], log_path[MAX_PATH];
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

static void put_int(const char *key, int v) { char o[12]; wsprintfA(o, "%d", v); WritePrivateProfileStringA("AnnotatedMap", key, o, tmp_path); }
/* Every key goes to a temporary file that then replaces the INI in one step; a failed save keeps the old file. */
static void save_settings(void) {
    DeleteFileA(tmp_path);
    CopyFileA(ini_path, tmp_path, FALSE);   /* start from the current file so its comments and unknown keys survive */
    put_int("Version", SETTINGS_VERSION);
    for (int i = 0; i < T_COUNT; i++) put_int(toggle_names[i], toggles[i]);
    put_int("Scope", scope);
    WritePrivateProfileStringA("AnnotatedMap", "Language", korean ? "ko" : "en", tmp_path);
    put_int("NameSize", name_size); put_int("NameOpacity", name_opacity);
    put_int("IconSize", icon_size); put_int("IconOpacity", icon_opacity);
    put_int("ItemNames", item_names); put_int("Legend", legend_on);
    WritePrivateProfileStringA("AnnotatedMap", "Modifier", modifier_ctrl ? "Ctrl" : "Shift", tmp_path);
    WritePrivateProfileStringA("AnnotatedMap", "LockMarker", lock_far_side ? "Unvisited" : "Door", tmp_path);
    WritePrivateProfileStringA("AnnotatedMap", "DisplayMode", display_mode == 1 ? "HD" : display_mode == 2 ? "SD" : "Auto", tmp_path);
    WritePrivateProfileStringA(NULL, NULL, NULL, tmp_path);   /* flush */
    if (!MoveFileExA(tmp_path, ini_path, MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
        DeleteFileA(tmp_path);
        log_text("Settings not saved: RE3.AnnotatedMap.ini could not be replaced; the previous file is kept");
    }
}
static int get_step(const char *key, int def, int lo, int hi) {
    int v = ((int)GetPrivateProfileIntA("AnnotatedMap", key, def, ini_path) + 5) / 10 * 10;
    return v < lo ? lo : v > hi ? hi : v;
}
static void load_settings(void) {
    int version = (int)GetPrivateProfileIntA("AnnotatedMap", "Version", 0, ini_path);
    for (int i = 0; i < T_COUNT; i++) toggles[i] = GetPrivateProfileIntA("AnnotatedMap", toggle_names[i], toggle_default[i], ini_path) != 0;
    scope = (int)GetPrivateProfileIntA("AnnotatedMap", "Scope", 1, ini_path);
    if (scope < 1 || scope > 3) scope = 1;
    /* Name pages' HD replacements bake the name opacity in, icon pages the icon opacity (one file per 10% step). */
    name_size = get_step("NameSize", 100, 50, 200);
    name_opacity = get_step("NameOpacity", 70, 10, 100);
    icon_size = get_step("IconSize", 100, 50, 200);
    icon_opacity = get_step("IconOpacity", 100, 10, 100);
    /* ItemNames: 0 = all hidden, 1 = all shown, 2 = all except common items. Versions 1-2 stored on/off as 0/1, which
     * already means hidden/all; the migration below only rewrites the file as version 3 (a stray larger value was "on"). */
    item_names = (int)GetPrivateProfileIntA("AnnotatedMap", "ItemNames", 0, ini_path);
    item_names = item_names < 0 ? 0 : item_names > 2 ? (version < 3 ? 1 : 0) : item_names;
    legend_on = GetPrivateProfileIntA("AnnotatedMap", "Legend", 1, ini_path) != 0;
    char text[16];
    GetPrivateProfileStringA("AnnotatedMap", "Language", "en", text, sizeof text, ini_path);
    korean = text[0] != 'e';
    GetPrivateProfileStringA("AnnotatedMap", "DisplayMode", "Auto", text, sizeof text, ini_path);
    display_mode = text[0] == 'H' || text[0] == 'h' ? 1 : text[0] == 'S' || text[0] == 's' ? 2 : 0;
    GetPrivateProfileStringA("AnnotatedMap", "Modifier", "Shift", text, sizeof text, ini_path);
    modifier_ctrl = text[0] == 'C' || text[0] == 'c';
    GetPrivateProfileStringA("AnnotatedMap", "LockMarker", "Door", text, sizeof text, ini_path);
    lock_far_side = text[0] == 'U' || text[0] == 'u';
    /* Older files are written once with Version=4. Versions before 4 had no Events toggle (live selections were
     * puzzles: Events takes the Puzzles value) and sizes relative to the old baselines: NameSize s -> s / 0.8,
     * IconSize s -> s / 1.3 (rounded to the 10% step) keeps names and item icons the size they were. */
    if (version < 4) {
        toggles[T_EVENTS] = toggles[T_PUZZLES];
        /* a key that is not in the file keeps its default: a new install is not "migrated" */
        int n = (int)GetPrivateProfileIntA("AnnotatedMap", "NameSize", -1, ini_path), i = (int)GetPrivateProfileIntA("AnnotatedMap", "IconSize", -1, ini_path);
        if (n >= 0) { n = (n * 100 + NAME_BASE * 5) / (NAME_BASE * 10) * 10; name_size = n < 50 ? 50 : n > 200 ? 200 : n; }
        if (i >= 0) { i = (i * 100 + ITEM_ICON_BASE * 5) / (ITEM_ICON_BASE * 10) * 10; icon_size = i < 50 ? 50 : i > 200 ? 200 : i; }
    }
    if (version < SETTINGS_VERSION) { save_settings(); log_fmt("Settings migrated from version %d to %d", version, SETTINGS_VERSION, 0, 0); }
}

/* ---------- input: edge-triggered keys while the map is drawn */
enum { KB_PLUS = 10, KB_MINUS, KB_MOD, KB_LBRACKET, KB_RBRACKET, KB_H, KB_TILDE, KB_BACKSLASH, KB_COUNT };   /* bits 0..8 toggles, 9 scope */
static unsigned keys_held, keys_seen;
static DWORD last_press[KB_COUNT];
static unsigned keys_down(void) {
    unsigned k = 0;
    for (int i = 0; i <= 9; i++) if (GetAsyncKeyState('0' + i) & 0x8000) k |= 1u << i;
    if ((GetAsyncKeyState(VK_OEM_PLUS) | GetAsyncKeyState(VK_ADD)) & 0x8000) k |= 1u << KB_PLUS;
    if ((GetAsyncKeyState(VK_OEM_MINUS) | GetAsyncKeyState(VK_SUBTRACT)) & 0x8000) k |= 1u << KB_MINUS;
    if (GetAsyncKeyState(modifier_ctrl ? VK_CONTROL : VK_SHIFT) & 0x8000) k |= 1u << KB_MOD;
    if (GetAsyncKeyState(VK_OEM_4) & 0x8000) k |= 1u << KB_LBRACKET;
    if (GetAsyncKeyState(VK_OEM_6) & 0x8000) k |= 1u << KB_RBRACKET;
    if (GetAsyncKeyState('H') & 0x8000) k |= 1u << KB_H;
    if (GetAsyncKeyState(VK_OEM_3) & 0x8000) k |= 1u << KB_TILDE;
    if (GetAsyncKeyState(VK_OEM_5) & 0x8000) k |= 1u << KB_BACKSLASH;   /* \ (Korean keyboards: the won sign key) */
    return k;
}
static void step(int *v, unsigned pressed, unsigned up, unsigned down, int lo, int hi, int *dirty) {
    int old = *v;
    if ((pressed & (1u << up)) && *v < hi) *v += 10;
    if ((pressed & (1u << down)) && *v > lo) *v -= 10;
    if (dirty && *v != old) *dirty = 1;
}
__declspec(dllexport) void __cdecl AnnotatedMapTestKeys(unsigned down);
void __cdecl AnnotatedMapTestKeys(unsigned down) {
    unsigned pressed = down & ~keys_held & ~(1u << KB_MOD);
    keys_held = down;
    if (!pressed) return;
    DWORD now = GetTickCount();
    for (unsigned i = 0; i < KB_COUNT; i++) if (pressed & (1u << i)) {
        if ((keys_seen & (1u << i)) && now - last_press[i] < DEBOUNCE_MS) pressed &= ~(1u << i);
        else { last_press[i] = now; keys_seen |= 1u << i; }
    }
    if (!pressed) return;
    for (int i = 0; i < T_COUNT; i++) if (pressed & (1u << i)) toggles[i] = !toggles[i];
    if (pressed & (1u << 9)) scope = scope % 3 + 1;
    if (pressed & (1u << KB_BACKSLASH)) korean = !korean;
    if (down & (1u << KB_MOD)) {   /* modifier: icons */
        step(&icon_size, pressed, KB_PLUS, KB_MINUS, 50, 200, 0);
        step(&icon_opacity, pressed, KB_RBRACKET, KB_LBRACKET, 10, 100, &clut_dirty);
    } else {
        step(&name_size, pressed, KB_PLUS, KB_MINUS, 50, 200, 0);
        step(&name_opacity, pressed, KB_RBRACKET, KB_LBRACKET, 10, 100, &clut_dirty);
    }
    if (pressed & (1u << KB_H)) item_names = (item_names + 1) % 3;   /* hidden -> all -> no common -> hidden */
    if (pressed & (1u << KB_TILDE)) legend_on = !legend_on;
    save_settings();
}
