"""Parse saved Evil Resource RE3 room pages into data/evilresource-rooms.json (cross-check reference only)."""
import html, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'local/reference/evilresource/rooms'

def text(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()

def parse(path):
    t = path.read_text()
    title = text(re.search(r'<h1[^>]*>(.*?)</h1>', t, re.S).group(1))
    slug = path.stem.split('_')
    links = re.search(r'linked to the following locations:(.*?)</ul>', t, re.S)
    linked = re.findall(r'href="/resident-evil-3-nemesis/maps/([^"#]+)"', links.group(1)) if links else []
    contents = []
    for li in re.findall(r'<li data-gamemode="(gm\d+)">(.*?)</li>', t, re.S):
        mode_id, body = li
        name = text(re.search(r'<h4[^>]*>(.*?)</h4>', body, re.S).group(1))
        mode = re.search(r'title="Game mode: ([^"]+)"', body)
        note = re.search(r'<div class="text">(.*?)</div>', body, re.S)
        kind = re.search(r'href="/resident-evil-3-nemesis/([a-z-]+)/[^"]*" class="btn[^"]*icon-link', body)
        contents.append(dict(name=name, mode=mode.group(1) if mode else None, kind=kind.group(1) if kind else None,
                             note=text(note.group(1)) if note else ''))
    return dict(title=title, area=slug[0], floor=slug[1], slug=slug[2], key='/'.join(slug), linked=linked, contents=contents)

rooms = [parse(p) for p in sorted(SRC.glob('*.html'))]
out = ROOT / 'data/evilresource-rooms.json'
out.write_text(json.dumps(rooms, ensure_ascii=False, indent=1) + '\n')
print(len(rooms), sum(len(r['contents']) for r in rooms), out)
