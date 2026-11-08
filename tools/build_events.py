"""Story events (spoiler scenes) from the room scripts -> data/story-events.json (user 2026-11-08).

An event is a scripted scene the player walks into: an SCE_EVENT trigger area whose script plays a movie
(movie_on), a long camera/voice sequence (cut_chg / xa_on), or an automatic on-entry movie. Live Selections
(sel_evt_on, data/live-selections.json) and puzzle devices are excluded; Nemesis stays an enemy marker.
Event markers carry no name on the map (RE0 rule: only the purple ? diamond); name_en/name_ko are the room, for these tables only.
Each event needs a persistent done-flag (a flag the scene sets) so the marker disappears once it happened;
scenes without one are listed under "skipped" with the reason. Positions are the trigger area's centre
(trigger) or, for scenes that start on entering the room, the room anchor (approximate).
Read-only on the game data; run: python tools/build_events.py
"""
import json, re, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERSISTENT = {0, 3, 5, 6, 7, 8, 9}   # flag banks that survive leaving the room (1 status, 2 stop, 4 room-local do not)
CK = re.compile(r'ck\((\d+), (\d+), (\d)\)')
FIRST_ID = 20                         # event ids 0..9 are the Live Selections


def procs_of(path):
    return {n: b for n, b in re.findall(r'^proc (\w+)\n(.*?)(?=^proc |\Z)', path.read_text(), re.M | re.S)}


def reach(proc, d, seen=None):
    seen = set() if seen is None else seen
    if proc in seen or proc not in d:
        return seen
    seen.add(proc)
    for m in re.findall(r'I_GOSUB, (\w+)|^\s*(main_[0-9A-F]+)\(\);', d[proc], re.M):
        for c in m:
            if c:
                reach(c, d, seen)
    return seen


def features(procs, d):
    text = '\n'.join(d[p] for p in procs)
    return {op: len(re.findall(rf'\b{op}\(', text)) for op in ('cut_chg', 'xa_on', 'movie_on', 'sel_evt_on', 'plc_motion')}


def literals(conds):
    """Persistent ck() literals of a list of 'if (...)' conditions; anything else is unknown at map time and dropped."""
    out = []
    for c in conds:
        if c.startswith('else[') or not c.startswith('if'):
            continue
        out += [[int(b), int(i), int(v)] for b, i, v in CK.findall(c) if int(b) in PERSISTENT]
    return out


def dedupe(seq):
    seen, out = set(), []
    for x in seq:
        k = json.dumps(x)
        if k not in seen:
            seen.add(k); out.append(x)
    return out


def done_flag(sets, aot_lits):
    """A persistent flag the scene sets to 1; prefer one the trigger itself tests as 'not yet' (ck(b, i, 0))."""
    mine = [tuple(r['args'][:2]) for r in sets if r['args'][2] == 1 and r['args'][0] in PERSISTENT]
    for b, i, v in aot_lits:
        if v == 0 and (b, i) in mine:
            return [b, i]
    return list(mine[0]) if mine else None


def room_name(rid, ids, er, ko):
    en = er.get(ids.get(rid), rid)
    return en, ko.get(en, en)


def main():
    scd = json.loads((ROOT / 'data/scd-rooms.json').read_text())
    ids = json.loads((ROOT / 'data/room-ids.json').read_text())
    er = {r['key']: r['title'].split(' - ')[0] for r in json.loads((ROOT / 'data/evilresource-rooms.json').read_text())}
    ko = json.loads((ROOT / 'data/names.json').read_text())['rooms']
    puzzle_keys = {tuple(k.split('/')[:2]) for k in json.loads((ROOT / 'data/puzzle-names.json').read_text())['names']}
    from build_overlay import EVENT_PUZZLES, ITEM_USE_PHASES
    puzzle_aots = {(r, str(a)) for r, a in list(EVENT_PUZZLES) + list(ITEM_USE_PHASES)} | puzzle_keys
    events, skipped = {}, []
    for dsbit, ds in ((1, 'DATA_J'), (2, 'DATA_AJ')):
        rooms = json.loads((ROOT / f'data/rooms-{ds}.json').read_text())
        for rid, room in sorted(rooms.items()):
            if rid[0] not in '12345':
                continue
            d = procs_of(ROOT / 'local/scd' / ds / f'R{rid}.bio')
            records = scd['DATA_J' if ds == 'DATA_J' else 'DATA_AJ'][rid]
            sets = [r for r in records if r['op'] == 'set' and len(r['args']) == 3]
            name_en, name_ko = room_name(rid, ids, er, ko)
            seen_holders = set()
            for a in room['aots']:
                if a['sce'] != 'SCE_EVENT' or a['data'][2] != 'I_GOSUB':
                    continue
                proc = a['data'][3]
                pr = reach(proc, d)
                f = features(pr, d)
                key = dict(rdt=rid, aot=a['aot'], proc=proc)
                holders = {p for p in pr if 'movie_on(' in d[p]}
                seen_holders |= holders
                if f['sel_evt_on'] or (rid, str(a['aot'])) in puzzle_aots:
                    continue
                if not (f['movie_on'] or f['cut_chg'] >= 7 or (f['cut_chg'] >= 5 and (f['xa_on'] >= 1 or f['plc_motion'] >= 5)) or f['xa_on'] >= 4):
                    continue
                lits = literals(a['cond'])
                flag = done_flag([r for r in sets if r['proc'] in pr], lits)
                if flag is None:
                    skipped.append(dict(key, name_en=name_en, name_ko=name_ko, reason='the scene sets no persistent flag, so it cannot be hidden once played',
                                        features=f)); continue
                chains = a['callconds'] or [[]]
                guards = dedupe([dedupe(lits + literals(ch)) for ch in chains])
                for g in guards:
                    g = [lit for lit in g if lit[:2] != flag] + [[*flag, 0]]
                    k = (rid, a['aot'], proc, json.dumps(g), a['x'], a['z'])
                    e = events.setdefault(k, dict(kind='trigger', rdt=rid, aot=a['aot'], proc=proc, x=a['x'], z=a['z'], w=a['w'], d=a['d'],
                                                  floor=a['floor'], guard=g, done=flag, movie=f['movie_on'], cuts=f['cut_chg'], voices=f['xa_on'],
                                                  name_en=name_en, name_ko=name_ko, sets=0))
                    e['sets'] |= dsbit
            # scenes that start by themselves when the room loads: a movie in a script no trigger area reaches
            for p in sorted(p for p, b in d.items() if 'movie_on(' in b and p not in seen_holders):
                pr = reach(p, d)
                f = features(pr, d)
                if f['sel_evt_on']:
                    continue
                sr = [r for r in sets if r['proc'] in pr]
                call = next((r['callconds'] for r in records if r['proc'] == p and r['callconds']), None)
                flag = done_flag(sr, [])
                key = dict(rdt=rid, aot=None, proc=p)
                if flag is None:
                    skipped.append(dict(key, name_en=name_en, name_ko=name_ko, reason='starts when the room loads and sets no persistent flag', features=f)); continue
                for chain in (call or [[]]):
                    g = dedupe(literals(chain))
                    g = [lit for lit in g if lit[:2] != flag] + [[*flag, 0]]
                    k = (rid, None, p, json.dumps(g))
                    e = events.setdefault(k, dict(kind='room', rdt=rid, aot=None, proc=p, guard=g, done=flag, movie=f['movie_on'], cuts=f['cut_chg'],
                                                  voices=f['xa_on'], name_en=name_en, name_ko=name_ko, sets=0))
                    e['sets'] |= dsbit
    out, ident = [], {}
    for e in sorted(events.values(), key=lambda e: (e['rdt'], e['aot'] if e['aot'] is not None else -1, e['proc'], json.dumps(e['guard']))):
        # one id per physical trigger area (or per automatic scene): story variants of it share the marker
        out.append(dict(id=ident.setdefault((e['rdt'], e['aot'] if e['aot'] is not None else e['proc']), FIRST_ID + len(ident)), **e))
    skipped = [dict(t) for t in {json.dumps(s, sort_keys=True) for s in skipped} and (json.loads(x) for x in {json.dumps(s, sort_keys=True) for s in skipped})]
    (ROOT / 'data/story-events.json').write_text(json.dumps(dict(
        note='Story scenes found in the room scripts (tools/build_events.py); markers use kind "live" with these ids. "skipped" lists scenes found but not placed.',
        events=out, skipped=sorted(skipped, key=lambda s: (s['rdt'], str(s['aot']), s['proc']))), ensure_ascii=False, indent=1) + '\n')
    print(len(out), 'event guards,', len(ident), 'ids,', len(skipped), 'skipped')


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT / 'tools'))
    main()
