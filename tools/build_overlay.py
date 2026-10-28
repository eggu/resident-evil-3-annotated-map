"""Project SCD markers onto RE3 map pages: data/overlay.json.

Each marker: page, map cell index, map-space point (exe integer projection), guard in CNF
(list of clauses, each a list of [bank, bit, value] literals that must have one true),
data-set mask (1 = DATA_J, 2 = DATA_AJ) and category-specific fields.
"""
import json, re, sys, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import pe
from enemy_conditions import guard as enemy_guard
from build_room_data import const_items, item_id, build, item_names
from extract_scd import parse_room, reach, call_conditions

COMMON = {0x15, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F,  # ammo
          0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2A,  # spray, herbs
          0x61, 0x62, 0x63, 0x81}                                              # gunpowder A/B/C, ink ribbon
NPC = ('CARLOS', 'NIKOLAI', 'MIKHAIL', 'JILL', 'BRAD_VICKERS', 'DARIO_ROSSO', 'MARVIN', 'TYRELL', 'MURPHY',
       'PROMO_GIRL')
MONSTERS = ['zombie', 'dog', 'crow', 'hunter', 'drain', 'spider', 'worm', 'nemesis',
            'hunter_gamma', 'brain', 'small_spider', 'grave']
MONSTER = [('NEMESIS', 'nemesis'), ('ZOMBIE_DOG', 'dog'), ('CROW', 'crow'), ('HUNTER_GAMMA', 'hunter_gamma'),
           ('HUNTER', 'hunter'), ('BS23', 'brain'), ('BS28', 'drain'), ('MINI_BRAINSUCKER', 'brain'),
           ('SPIDER', 'spider'), ('MINI_SPIDER', 'small_spider'), ('SLIDING_WORM', 'worm'), ('GRAVE_DIGGER', 'grave'), ('ZOMBIE', 'zombie'),
           ('BRAD_ZOMBIE', 'zombie'), ('DARIO_ZOMBIE', 'zombie')]


# Real event interactions and extra persistent phase guards; placement guards still apply.
EVENT_PUZZLES = {
    ('113', 8): [(9, 1, 0)],
    ('11B', 18): [(9, 27, 0)],
    # Both melody references stay useful until the Cog Room music-box puzzle is solved.
    ('304', 14): [(3, 136, 0)], ('304', 15): [(3, 136, 0)],
    ('406', 1): [(3, 117, 1), (3, 178, 0)],
    **{('406', aot): [(3, 117, 0)] for aot in range(10, 14)},
    ('40B', 1): [], ('40B', 2): [],
    # Valves remain useful for leaving the room after the power console is completed.
    **{('502', aot): [] for aot in range(10, 15)},
    ('502', 15): [(3, 213, 0)],
    ('506', 18): [],
}


# SCD can create an item-use AOT unconditionally, then switch it off later in the same room.
ITEM_USE_PHASES = {
    **{('109', aot): [(3, 28, 0)] for aot in (4, 6)},
    **{('123', aot): [(3, 28, 0)] for aot in (4, 5, 6)},
    ('203', 12): [(3, 107, 0)],
    ('205', 15): [(7, 68, 1)], ('205', 16): [(7, 67, 1)],
    **{('218', aot): [(3, 186, 0), (7, 65, 0)] for aot in (16, 17)},
    ('310', 4): [(3, 172, 0)],
    ('404', 15): [(3, 80, 0)],
    ('502', 23): [(9, 33, 0)],
    ('506', 15): [(3, 244, 0)],
}


def remap_table(img):
    out, a = {}, 0x5351AC
    while img.read(a, 1)[0] != 0xFF:
        s, r, p, i = img.read(a, 4)
        out[(s, r)] = (p, i)
        a += 4
    return out


def cells(stage, room, x, z, table, floor=None):
    """All (page, idx, extra_guard_clauses) the exe 0x4ED650 can produce for this RDT and point."""
    if stage == 1 and room == 0x0F and x >= -8822:
        room = 0x10
    if stage == 3 and room == 0x15 and x >= 0x320:
        room = 0x11
    variants = [(room, [])]
    if stage == 4 and room == 2:
        # The two levels share one RDT; bank4:31 belongs to the loaded room only.
        variants = [(0x11 if floor == 0 else 2, [])] if floor is not None else [(2, []), (0x11, [])]
    if stage == 2 and room == 0x17 and z > -11301:
        variants = [(2, [[[3, 200, 0]]]), (0x17, [[[3, 200, 1]]])]
    out = []
    for r, g in variants:
        p, i = table.get((stage, r), (stage, r))
        out.append((p, i, g))
    return out


def tdiv(n, d):
    q = abs(n) // d
    return q if n >= 0 else -q


def project(proj, x, z):
    """Exe 0x4EAF50: hi32(v * 0x91A2B3C5) + v, sar 8, round toward zero."""
    def f(v):
        hi = (v * (0x91A2B3C5 - (1 << 32))) >> 32
        t = (hi + v) >> 8
        return t + (1 if t < 0 else 0)
    return proj['mx'] + f(x - proj['wx']), proj['my'] - f(z - proj['wz'])


CK = re.compile(r'ck\((\d+), (\d+), (\d)\)')


def guard(cond):
    clauses = []
    for c in cond:
        neg = c.startswith('else[')
        terms = [[int(b), int(n), int(v)] for b, n, v in CK.findall(c)]
        other = re.sub(r'ck\(\d+, \d+, \d\)|\s|&&|if|\(|\)|else\[|\]', '', c)
        if neg:
            if terms and not other:
                clauses.append([[b, n, 1 - v] for b, n, v in terms])
        else:
            if not c.startswith('if') or other:  # switch/case/while/cmp: unknown at map time -> assume true
                terms = [t for t in terms] if c.startswith('if') and not other else []
            clauses += [[t] for t in terms]
    return clauses


def center(rec):
    if 'quad' in rec:
        xs, zs = zip(*rec['quad'])
        return sum(xs) // 4, sum(zs) // 4
    return rec['x'] + rec['w'] // 2, rec['z'] + rec['d'] // 2


def aot_switches(bio):
    """Per proc, the `if` conditions around each aot_on(n) and aot_reset(n, SCE_AUTO) (switch-off),
    in the same string form as record conditions ('if (..)' / 'else[if (..)]')."""
    on, off = collections.defaultdict(dict), collections.defaultdict(dict)
    for name, body in re.findall(r'^proc (\w+)\n(.*?)(?=^proc |\Z)', bio.read_text(), re.M | re.S):
        stack, last = [], None
        for line in (l.strip() for l in body.splitlines()):
            if line.startswith(('if (', 'else')):
                last = line if line.startswith('if') else f'else[{last}]' if last else 'else'
            elif line == '{':
                stack.append(last)
                last = None
            elif line == '}':
                last = stack.pop() if stack else None
                last = last if last and last.startswith('if') else None
            elif m := re.match(r'aot_on\((\d+)\)', line):
                on[int(m[1])].setdefault(name, [c for c in stack if c])
            elif m := re.match(r'aot_reset\((\d+), SCE_AUTO', line):
                off[int(m[1])].setdefault(name, [c for c in stack if c])
    return on, off


def revealed_by(bio):
    """Item aot -> procs that switch it on (items held by a corpse/event until searched)."""
    return aot_switches(bio)[0]


def item_switch_conds(i, spot, shown, switched_off, procs):
    """Extra conditions for when the item is really obtainable: the `if`s around the aot_on that
    reveals it, and the negation of an `if` that switches it off right where it is placed."""
    # skip temporary banks (1 status, 2 stop, 4 room-local) and its own pickup flag (runtime checks that)
    skip = re.compile(rf'ck\([124], \d+, \d\)|ck\([78], {i["flag"]}, \d\)')
    extra = []
    if spot is not i and spot.get('sce') == 'SCE_EVENT':
        reached = reach_from(spot['data'][3], procs)
        extra += [c for c in next((c for p, c in shown[i['aot']].items() if p in reached), []) if not skip.search(c)]
    off = switched_off[i['aot']].get(i['proc'])
    if off and len(off) == 1 and off[0].startswith('if') and not skip.search(off[0]):   # ponytail: single if only
        extra.append(f'else[{off[0]}]')
    return extra


def reach_from(proc, procs):
    seen, todo = set(), [proc]
    while todo:
        p = todo.pop()
        if p not in seen:
            seen.add(p)
            todo += procs.get(p, ())
    return seen


def held_spot(aot, aots, shown, procs):
    """Where an item without its own position is picked up: an object it is attached to
    (data[2] names the item aot) or an event whose script reaches aot_on(item)."""
    for a in aots:
        if a['path'] is None:
            continue
        if a['sce'] == 'SCE_DAMAGE' and a['data'][2] == aot:
            return a
        if a['sce'] == 'SCE_EVENT' and a['data'][2] == 'I_GOSUB' and reach_from(a['data'][3], procs) & set(shown[aot]):
            return a
    return None


def merge_variants(markers, tol=3):
    """One physical thing set by several story variants of a room (e.g. the Lockpick door in Book Shop Street
    R10A and R124, same lock id 1px apart) becomes one marker: same kind, cell, item, flag/lock and guard.
    Explicit event AOT identities keep neighbouring controls (e.g. steam valves) separate
    within `tol` map pixels."""
    kept = []
    for m in markers:
        ident = (m['kind'], m['page'], m['idx'], m.get('item'), m.get('flag', m.get('lock', m.get('kill'))), m.get('aot'), m.get('event'), json.dumps(m['guard']))
        for k in kept:
            if k[0] == ident and abs(k[1]['x'] - m['x']) <= tol and abs(k[1]['y'] - m['y']) <= tol:
                k[1]['sets'] |= m['sets']
                break
        else:
            kept.append((ident, m))
    return [m for _, m in kept]


def main():
    img = pe.Image()
    table = remap_table(img)
    pages = json.loads((ROOT / 'data/map-pages.json').read_text())
    names = json.loads((ROOT / 'data/item-names-en.json').read_text())
    ids = json.loads((ROOT / 'data/room-ids.json').read_text())
    er = {r['key']: r['title'].split(' - ')[0] for r in json.loads((ROOT / 'data/evilresource-rooms.json').read_text())}
    consts = const_items()
    markers = collections.OrderedDict()
    unresolved = []
    def add(kind, ds, stage, room, x, z, cond, chains=None, floor=None, **kw):
        # one marker per call chain (call-site conditions + local ones); the runtime draws a run of
        # identical markers once
        for alt in (chains or [[]]):
            add_one(kind, ds, stage, room, x, z, alt + cond, floor=floor, **kw)
    def add_one(kind, ds, stage, room, x, z, cond, floor=None, **kw):
        for page, idx, extra in cells(stage, room, x, z, table, floor):
            if page >= len(pages) or idx >= len(pages[page]['rooms']) or not pages[page]['rooms'][idx]['parts']:
                continue
            px = x
            if kind == 'enemy':
                if stage == 1 and room == 0x0F and x >= -8822: px += 9501
                if stage == 3 and room == 0x15 and x >= 800: px -= 9000
            mx, my = project(pages[page]['rooms'][idx]['proj'], px, z)
            g = (enemy_guard(cond) if kind == 'enemy' else guard(cond)) + extra
            if kw.get('monster') == 'nemesis' and any(lit[0] in (4, 47, 48) for cl in g for lit in cl):
                g += [[]]  # Room-local state cannot establish an unloaded encounter.
            if kind == 'enemy' and [] in g:
                unresolved.append(dict(dataset=ds, rdt=f'{stage + 1:X}{room:02X}', monster=kw['monster'], conditions=cond))
            key = json.dumps([kind, page, idx, mx, my, g, sorted(kw.items())])
            if key in markers:
                markers[key]['sets'] |= ds
            else:
                markers[key] = dict(kind=kind, page=page, idx=idx, x=mx, y=my, guard=g, sets=ds, rdt=f'{stage + 1:X}{room:02X}', **kw)
    for ds, name in ((1, 'DATA_J'), (2, 'DATA_AJ')):
        rooms = json.loads((ROOT / f'data/rooms-{name}.json').read_text())
        for rid, r in rooms.items():
            stage, room = int(rid[0]) - 1, int(rid[1:], 16)
            if stage > 4:
                continue
            bio = ROOT / 'local/scd' / name / f'R{rid}.bio'
            procs, records, calls = parse_room(bio, strict=True)
            shown, switched_off = aot_switches(bio)
            for i in r['items']:
                if i['path'] is None or (i['x'] == -32000 and i['z'] == -32000):
                    continue
                spot = i
                if i['w'] <= 1 and i['d'] <= 1:   # no pickup area: placeholder (origin, or mirrored coords as in R211)
                    spot = held_spot(i['aot'], r['aots'], shown, procs) or next(
                        # handed over in a cutscene: place it on the character set up alongside it
                        (dict(e, w=0, d=0) for e in r['enemies'] if e['proc'] == i['proc'] and e['cond'] == i['cond']
                         and (e['x'], e['z']) != (0, 0)), None)
                    if spot is None:
                        continue
                x, z = center(spot)
                cond = i['cond'] + item_switch_conds(i, spot, shown, switched_off, procs) + (['if (ck(0, 23, 0))'] if i['item'] == 0x81 else [])
                if rid == '502' and i['item'] == 10:
                    cond += ['if (ck(9, 34, 1))']  # Secret locker opened with the processed Facility Key.
                cat = 'map' if 0xA4 <= i['item'] <= 0xAA else 'file' if 0x86 <= i['item'] <= 0xA3 else \
                      'common' if i['item'] in COMMON else 'key'
                chains = i['callconds']
                if rid == '502' and spot['floor'] == 0:
                    # The elevator changes its layer flag while these lower-level AOTs remain active.
                    chains = [[c for c in chain if 'ck(3, 239,' not in c] for chain in chains]
                add(cat, ds, stage, room, x, z, cond, chains, floor=spot['floor'], item=i['item'], flag=i['flag'])
            for d in r['doors']:
                if d['path'] is None or not (0 < d['key'] < 254) or d['key'] == consts['ITEM_DUMMY_KEY']:
                    continue
                spot = d
                if d['w'] <= 1 and d['d'] <= 1:
                    # Some door AOTs are positionless: the real event area invokes them with aot_on.
                    spot = held_spot(d['aot'], r['aots'], shown, procs)
                    if spot is None:
                        continue
                x, z = center(spot)
                add('lock', ds, stage, room, x, z, d['cond'], d['callconds'], floor=spot['floor'], item=d['key'], lock=d['lock_id'] & 0x3F, to=d['target'])
            for a in r['aots']:
                if a['path'] is None:
                    continue
                x, z = center(a)
                if a['sce'] == 'SCE_MOVE':
                    add('typewriter', ds, stage, room, x, z, a['cond'], a['callconds'], floor=a['floor'])
                elif a['sce'] == 'SCE_SAVE':
                    add('itembox', ds, stage, room, x, z, a['cond'], a['callconds'], floor=a['floor'])
                elif a['sce'] == 'SCE_EVENT' and (rid, a['aot']) in EVENT_PUZZLES:
                    pending = [f'if (ck({b}, {n}, {v}))' for b, n, v in EVENT_PUZZLES[(rid, a['aot'])]]
                    add('puzzle', ds, stage, room, x, z, a['cond'] + pending, a['callconds'], floor=a['floor'], aot=a['aot'])
                elif a['sce'] == 'SCE_EVENT' and (rid, a['aot']) in (('20D', 2), ('30C', 9), ('40D', 2)):
                    # These real interaction areas invoke separate, positionless puzzle UIs.
                    pending = ['if (ck(3, 224, 0))'] if rid == '40D' else []
                    add('puzzle', ds, stage, room, x, z, a['cond'] + pending, a['callconds'], floor=a['floor'])
                elif rid == '214' and a['sce'] == 'SCE_EVENT' and a['aot'] in (10, 11):
                    # AOT 19 is a positionless voltage UI; AOT 11 invokes it, AOT 10 supplies power.
                    pending = 'if (ck(3, 92, 0))' if a['aot'] == 10 else 'else[if (ck(3, 94, 1) && ck(3, 95, 1))]'
                    add('puzzle', ds, stage, room, x, z, a['cond'] + [pending], a['callconds'], floor=a['floor'])
                elif rid == '11B' and a['aot'] == 4 and a['sce'] == 'SCE_ITEMBOX':
                    # Computer password UI uses SCE_ITEMBOX; the storeroom opens at bank 9 bit 27.
                    add('puzzle', ds, stage, room, x, z, a['cond'] + ['if (ck(9, 27, 0))'], a['callconds'], floor=a['floor'])
                elif rid == '309' and a['aot'] == 28 and a['sce'] == 'SCE_FLAG_CHG':
                    # The bell's push area uses a flag trigger, not an item-use opcode.
                    add('puzzle', ds, stage, room, x, z, ['if (ck(3, 55, 1))', 'if (ck(3, 126, 0))'], aot=28)
                elif a['sce'] == 'SCE_FLAG_CHG' and a['data'][0] == 44:
                    if (rid, a['aot']) in (('40B', 4), ('506', 17)):
                        continue  # The event marker covers insertion through actual puzzle completion.
                    pending = [f'if (ck({b}, {n}, {v}))' for b, n, v in ITEM_USE_PHASES.get((rid, a['aot']), [])]
                    chains = a['callconds']
                    if rid == '502' and a['floor'] == 0:
                        chains = [[c for c in chain if 'ck(3, 239,' not in c] for chain in chains]
                    add('puzzle', ds, stage, room, x, z, a['cond'] + pending, chains, floor=a['floor'], item=item_id(a['data'][2], consts))
            paths, chains = reach(procs), call_conditions(calls, limit=256)
            for rec in records:
                rec['path'], rec['callconds'] = paths.get(rec['proc']), chains.get(rec['proc'], [])
            enemies = build({rid: records}, item_names(), consts)[rid]['enemies']
            for e in enemies:
                t = e['type'].replace('ENEMY_', '')
                if e['path'] is None or t.startswith(NPC) or t[:2].isdigit() or len(t) == 2:
                    continue
                cat = next((c for p, c in MONSTER if t.startswith(p)), None)
                if cat == 'nemesis' and e['ai'] & 128:
                    continue  # Dormant/cinematic actors need a later activation, not just their em_set guard.
                if cat and (e['x'], e['z']) not in ((0, 0), (-32000, -32000)):
                    cond = e['cond']
                    chains = e['callconds']
                    if rid == '317' and e['proc'] in ('main_12', 'main_13'):
                        # Player Z selects which half is loaded, not which scoped encounter exists.
                        chains = [[c for c in chain if 'memb_cmp(0, 11, 3, 240, 216)' not in c] for chain in chains]
                    if stage == 2 and room >= 0x0E:
                        cond = ['if (ck(3, 55, 1))'] + cond
                    elif rid in ('301', '302'):
                        cond += ['if (ck(3, 55, 0))']
                    add('enemy', ds, stage, room, e['x'], e['z'], cond, chains, floor=e['floor'], monster=cat, kill=e['kill'])
    # Curated prospective event locations: never pass unknown event predicates through guard().
    from build_assets import anchor as room_anchor
    events = json.loads((ROOT / 'data/live-selections.json').read_text())['events']
    for ds, name in ((1, 'DATA_J'), (2, 'DATA_AJ')):
        rooms = json.loads((ROOT / f'data/rooms-{name}.json').read_text())
        for event in events:
            for rid in event['rdts']:
                if rid not in rooms:
                    continue
                stage, room = int(rid[0]) - 1, int(rid[1:], 16)
                page, idx = table.get((stage, room), (stage, room))
                cell = pages[page]['rooms'][idx]
                if event['aot'] is not None:
                    spot = next(a for a in rooms[rid]['aots'] if a['aot'] == event['aot'] and a['sce'] == 'SCE_EVENT')
                    mx, my = project(cell['proj'], *center(spot))
                else:
                    # Transparent map texels carve courtyards/corridors; rectangle centres can be another room.
                    counts = collections.Counter(tuple(p[:6]) for r in pages[page]['rooms'] for p in r['parts'])
                    shared = {p for p, n in counts.items() if n > 1}
                    mx, my = room_anchor(cell, shared, page, 8, 8)
                g = event['guard'] + [[[54, 24, event['last_stage']]]]
                key = json.dumps(['live', event['id'], page, idx, mx, my, g])
                if key in markers:
                    markers[key]['sets'] |= ds
                else:
                    markers[key] = dict(kind='live', page=page, idx=idx, x=mx, y=my, guard=g, sets=ds,
                                        rdt=rid, event=event['id'], anchor='trigger' if event['aot'] is not None else 'room')
    # R208 main_34 reconstructs local4:0 from these four persistent pickups;
    # main_1C creates Nemesis at 0,0 and main_1D/1F position/activate it later.
    page, idx = table[(1, 8)] if (1, 8) in table else (1, 8)
    cell = pages[page]['rooms'][idx]
    counts = collections.Counter(tuple(p[:6]) for r in pages[page]['rooms'] for p in r['parts'])
    mx, my = room_anchor(cell, {p for p, n in counts.items() if n > 1}, page, 8, 8)
    eligible = [[[7, n, 1]] for n in (47, 34, 35, 36)] + [[[54, 24, 1]]]
    markers['nemesis-room-208'] = dict(kind='enemy', page=page, idx=idx, x=mx, y=my,
        guard=eligible + [[[3, 125, 1]]],
        sets=3, rdt='208', monster='nemesis', kill=140, anchor='room')
    # First event main_20 has one fixed spawn; later entries select one of five positions.
    sx, sy = project(cell['proj'], -25208, -19828)
    markers['nemesis-spawn-208'] = dict(kind='enemy', page=page, idx=idx, x=sx, y=sy,
        guard=eligible + [[[3, 125, 0]]],
        sets=3, rdt='208', monster='nemesis', kill=140, anchor='spawn')
    rooms_out = []
    for page in pages[:7]:
        for r in page['rooms']:
            if not r['parts']:
                continue
            rdts = sorted(k for k in ids if any((p, i) == (page['page'], r['index']) for p, i, _ in cells(int(k[0]) - 1, int(k[1:], 16), 0, 0, table)))
            rooms_out.append(dict(page=page['page'], idx=r['index'], rdts=rdts,
                                  name='Weapons Storage' if page['page'] == 4 and r['index'] == 17 else er[ids[rdts[0]]] if rdts else None))
    out = dict(markers=merge_variants(list(markers.values())), rooms=rooms_out)
    (ROOT / 'data/overlay.json').write_text(json.dumps(out, indent=0, ensure_ascii=False) + '\n')
    enemies = [m for m in out['markers'] if m['kind'] == 'enemy']
    audit = dict(placements=len(enemies), compiled=sum([] not in m['guard'] for m in enemies),
                 unresolved=unresolved)
    (ROOT / 'data/enemy-condition-audit.json').write_text(json.dumps(audit, indent=1) + '\n')
    c = collections.Counter(m['kind'] for m in out['markers'])
    print(dict(c), 'named rooms', sum(1 for r in rooms_out if r['name']), '/', len(rooms_out))


if __name__ == '__main__':
    main()
