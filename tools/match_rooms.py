"""Propose RE3 room id -> Evil Resource room matches (data/room-match.json) for manual review.

Signals: fixed anchors (fandom background file names), door graph vs Evil Resource
"linked to" lists, and pickup/file contents. Output is a proposal, not ground truth.
"""
import json, re, itertools
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALIAS = {
    'f. aid spray': 'first aid spray', 'h. gun bullets': 'hand gun bullets', 'h.g. bullets e': 'hand gun bullets',
    'g. launcher': 'hk-p grenade launcher', 'magnum': 's&w m629c', 'shotgun': 'benelli m3s',
    'r. launcher': 'm66 rocket launcher', 'm.t. rounds': 'mine thrower rounds', 's.g. shell e': 'shotgun shells',
    'clock t. key': 'clock tower key', 'bezel key': 'clock tower key', 'winder key': 'clock tower key',
    'park key': 'park key', 'main gate key': 'park key', 'rear gate key': 'park key', 'graveyard key': 'park key',
    'ｓｔａｒｓ card': 's.t.a.r.s. card', 'system disc': 'system disk', 'lighter': 'lighter', 'empty lighter': 'lighter',
    'blue gem': 'sapphire', 'green gem': 'emerald', 'crank': 'square crank', 'rusted crank': 'rust hex crank',
    'bronze book': 'book of wisdom', 'bronze compass': 'future compass', 'fax from kendo': 'fax from kendo gun shop',
    'fax from the h.q.': 'fax from headquarters', 'med. instr. manual': 'medical instruction manual',
    "merc's diary": "mercenary's diary", "merc's pocketbook": "mercenary's pocketbook",
    'written order': 'written order to supervisors', 'warehouse key': 'backdoor key', 'emblem key': 's.t.a.r.s. key',
    'blue herbs': 'blue herb', 'green herbs': 'green herb', 'red herbs': 'red herb', "gun powder a's": 'gun powder a',
    "gun powder b's": 'gun powder b',
}
ANCHORS = {'100': 'uptown-and-downtown/uptown/warehouse-office', '101': 'uptown-and-downtown/uptown/warehouse'}


def canon(name):
    n = re.sub(r'\s*\(.*\)$', '', name.strip().lower())
    n = re.sub(r'^[0-9∞]+\s+', '', n)
    return ALIAS.get(n, n)


def variants():
    """biorand rdt.json `linkedRoom`: same location in another story state -> canonical id."""
    t = (ROOT / 'local/reference/biorand-classic/IntelOrca.Biohazard.BioRand/data/re3/rdt.json').read_text(encoding='utf-8-sig')
    t = re.sub(r',(\s*[}\]])', r'\1', re.sub(r'(?m)//.*$', '', t))
    alias = {}
    for rid, r in json.loads(t)['rooms'].items():
        if 'linkedRoom' in r:
            a, b = sorted((rid, r['linkedRoom']))
            alias[b] = alias.get(a, a)
    return alias


def scd_rooms():
    alias = variants()
    rooms = defaultdict(lambda: dict(doors=set(), items=set(), ids=set()))
    for ds in ('DATA_J', 'DATA_AJ'):
        for rid, r in json.loads((ROOT / f'data/rooms-{ds}.json').read_text()).items():
            g = alias.get(rid, rid)
            rooms[g]['ids'].add(rid)
            rooms[g]['doors'] |= {alias.get(d['target'], d['target']) for d in r['doors']} - {g}
            rooms[g]['items'] |= {canon(i['name']) for i in r['items'] if not i['name'].endswith(' Map')}
    for rid, r in rooms.items():  # undirected
        for t in r['doors']:
            if t in rooms:
                rooms[t]['doors'].add(rid)
    return rooms


def er_rooms():
    rooms = {}
    for r in json.loads((ROOT / 'data/evilresource-rooms.json').read_text()):
        items = {canon(c['name']) for c in r['contents'] if c['kind'] in ('items', 'weaponry', 'files')}
        rooms[r['key']] = dict(title=r['title'], links=set(r['linked']), items=items)
    for k, r in rooms.items():
        for t in r['links']:
            rooms[t]['links'].add(k)
    return rooms


def main():
    S, E = scd_rooms(), er_rooms()
    freq = defaultdict(int)
    for r in E.values():
        for i in r['items']:
            freq[i] += 1
    def content(s, e):
        a, b = S[s]['items'], E[e]['items']
        shared = sum(1.0 / freq[i] for i in a & b if freq[i])
        return shared - 0.15 * len(a ^ b)
    match = dict(ANCHORS)
    changed = True
    while changed:
        changed = False
        best = []
        used = set(match.values())
        for s, e in list(match.items()):
            for sn, en in itertools.product(S[s]['doors'] - match.keys(), E[e]['links'] - used):
                # neighbour consistency: matched neighbours of sn that map onto neighbours of en
                agree = sum(1 for x in S[sn]['doors'] if x in match and match[x] in E[en]['links'])
                conflict = sum(1 for x in S[sn]['doors'] if x in match and match[x] not in E[en]['links'])
                c = content(sn, en)
                ok = agree >= 2 or c >= 1 or (agree >= 1 and c > 0) or (len(E[en]['links'] - used) == 1 and len(S[s]['doors'] - match.keys()) == 1)
                if ok and not conflict:
                    best.append((2 * agree + c, sn, en))
        for score, sn, en in sorted(best, reverse=True):
            if sn not in match and en not in set(match.values()):
                match[sn] = en
                changed = True
                break
    out = {s: dict(ids=sorted(S[s]['ids']), er=e, title=E[e]['title'], anchor=s in ANCHORS,
                   scd_items=sorted(S[s]['items']), er_items=sorted(E[e]['items']))
           for s, e in sorted(match.items())}
    unmatched_s = sorted(set(S) - match.keys())
    unmatched_e = sorted(set(E) - set(match.values()))
    (ROOT / 'data/room-match.json').write_text(json.dumps(dict(match=out, unmatched_scd=unmatched_s,
                                                                unmatched_er=unmatched_e), indent=1) + '\n')
    print(len(out), 'matched;', len(unmatched_s), 'scd unmatched;', len(unmatched_e), 'er unmatched')


if __name__ == '__main__':
    main()
