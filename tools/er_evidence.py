"""Print compact Evil Resource room evidence for an area/floor prefix."""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
for r in json.loads((ROOT / 'data/evilresource-rooms.json').read_text()):
    if not r['key'].startswith(sys.argv[1]): continue
    c = sorted({re.sub(r'\s*\(.*\)$', '', x['name']) + ('' if x['mode'] == 'Hard' else '') for x in r['contents'] if x['kind'] != 'characters'})
    print(f"{r['slug']} -> {','.join(l.split('/')[-1] for l in r['linked'])}\n   {'; '.join(c)[:300]}")
