/* Native em_set/update eligibility; the SCD VM has already evaluated encounter conditions. */
static int enemy_kind(unsigned type) {
    if ((type >= 0x10 && type <= 0x1F) || type == 0x58 || type == 0x59) return M_ZOMBIE;
    switch (type) {
    case 0x20: return M_DOG;
    case 0x21: return M_CROW;
    case 0x22: return M_HUNTER;
    case 0x23: case 0x27: return M_BRAIN;
    case 0x24: return M_HUNTER_GAMMA;
    case 0x25: return M_SPIDER;
    case 0x26: return M_SMALL_SPIDER;
    case 0x28: return M_DRAIN;
    case 0x30: return M_GRAVE;
    case 0x32: return M_WORM;
    case 0x34: case 0x36: case 0x38: return M_NEMESIS;
    default: return -1;
    }
}

static int live_nemesis_cell;

static unsigned live_enemies(const unsigned char *s, unsigned page) {
    live_nemesis_cell = -1;
    const uintptr_t first = 0xA621EC;
    uintptr_t end = G32(0xA6228C);
    if (end < first || end > first + 32 * 4 || ((end - first) & 3)) return 0;
    unsigned drawn = 0;
    int nemesis_drawn = 0;
    for (uintptr_t slot = first; slot < end; slot += 4) {
        uintptr_t em = G32(slot);
        if (!em || !(G32(em) & 1) || (G8(em + 0x47) & 0x80)) continue;
        int duplicate = 0;
        for (uintptr_t prev = first; prev < slot; prev += 4) if (G32(prev) == em) { duplicate = 1; break; }
        if (duplicate) continue;
        int kind = enemy_kind(G8(em + 0x4A));
        if (kind != M_NEMESIS || !*(volatile uint16_t *)(em + 0xCC) || (kind == M_NEMESIS && nemesis_drawn)) continue;
        unsigned stage = (uint16_t)G16(STAGE_NO), room = (uint16_t)G16(0xA673C8);
        unsigned kill = G8(em + 0x147);
        if (kill != 255 && bank_bit(second_set(stage) ? 6 : 5, kill)) continue;
        int x = (int32_t)G32(em + 0x34), z = (int32_t)G32(em + 0x3C);
        unsigned pg = stage, idx = room;
        /* Same position-dependent cells and X correction as 0x4ED650 / 0x4EAF50. */
        if (stage == 1 && room == 0x0F && x >= -8822) { idx = 0x10; x += 9501; }
        if (stage == 3 && room == 0x15 && x >= 800) { idx = 0x11; x -= 9000; }
        if (stage == 4 && room == 2 && bank_bit(4, 31)) idx = 0x11;
        if (stage == 2 && room == 0x17 && z > -11301 && !bank_bit(3, 200)) idx = 2;
        if (pg >= 5) pg -= 5;
        for (uintptr_t r = 0x5351AC; r < 0x5351AC + 64 * 4 && G8(r) != 255; r += 4) {
            if (G8(r) == pg && G8(r + 1) == idx) { pg = G8(r + 2); idx = G8(r + 3); break; }
        }
        if (pg != page || !room_shown(pg, idx)) continue;
        uintptr_t proj = *(const uint32_t *)(s + 0xB4);
        if (!proj || idx >= 80) continue;
        unsigned offset = G32(proj);
        if (offset < 4 || offset > 4096 || (offset & 1)) continue;
        proj += offset + idx * 8;
        int mx = G16(proj) + (x - G16(proj + 4)) / 450;
        int my = G16(proj + 2) - (z - G16(proj + 6)) / 450;
        icon_at(map_x(s, mx), map_y(s, my), monster_icons[kind], 8);
        live_nemesis_cell = (int)idx;
        drawn++;
        if (kind == M_NEMESIS) nemesis_drawn = 1;
    }
    return drawn;
}
