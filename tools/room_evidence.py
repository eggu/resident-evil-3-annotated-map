"""Print compact per-room evidence (SCD + SDK English room text) for manual room naming."""
import json, re, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
XML = ROOT / 'local/reference/re3-mod-sdk/xml_eng/rdt'
J = json.loads((ROOT / 'data/rooms-DATA_J.json').read_text())

def msgs(rid, n=3):
    p = XML / f'R{rid}.xml'
    if not p.exists(): return []
    t = re.findall(r'<Text>(.*?)</Text>', p.read_text(encoding='utf-8-sig'), re.S)
    t = [re.sub(r'\{[^}]*\}', '', s).replace('\\n', ' ').strip() for s in t]
    return [s[:60] for s in t if s][:n]

for rid in sorted(J):
    if not rid.startswith(sys.argv[1]): continue
    r = J[rid]
    doors = sorted({d['target'] + ('*' if d['key'] else '') for d in r['doors']})
    items = sorted({i['name'] for i in r['items']})
    en = collections.Counter(e['type'].replace('ENEMY_', '') for e in r['enemies'])
    sce = collections.Counter(a['sce'][4:] for a in r['aots'] if a['sce'] in ('SCE_SAVE', 'SCE_ITEMBOX', 'SCE_FLAG_CHG'))
    print(f"{rid} doors={','.join(doors)} sce={dict(sce)}\n   items={'; '.join(items)}\n   enemies={dict(en)}\n   text={msgs(rid)}")
