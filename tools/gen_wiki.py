"""Generate bilingual reference tables from the current compiled overlay; no game files needed."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    overlay = json.loads((ROOT / 'data/overlay.json').read_text())
    names = json.loads((ROOT / 'data/names.json').read_text())
    fallback = json.loads((ROOT / 'data/item-names-en.json').read_text())
    rooms = {(r['page'], r['idx']): r for r in overlay['rooms']}
    markers = overlay['markers']
    groups = [
        ('03-rooms', '방 목록', 'Rooms', None),
        ('04-locks-keys', '잠긴 문과 열쇠', 'Locks and keys', {'lock'}),
        ('05-key-items', '핵심 아이템', 'Key items', {'key'}),
        ('06-puzzles-events', '퍼즐과 Live Selection', 'Puzzles and Live Selections', {'puzzle', 'live'}),
        ('07-documents-maps', '문서와 지도', 'Documents and maps', {'file', 'map'}),
        ('08-common-items', '일반 아이템', 'Common items', {'common'}),
        ('09-save-points', '타자기와 아이템 상자', 'Typewriters and item boxes', {'typewriter', 'itembox'}),
        ('11-monsters', '몬스터', 'Monsters', {'enemy'}),
    ]
    assert len(rooms) == len(overlay['rooms']), 'duplicate map cells'
    assert all((m['page'], m['idx']) in rooms for m in markers), 'unknown marker cell'
    assert set.union(*(g[3] for g in groups if g[3])) == {m['kind'] for m in markers}
    out = ROOT / 'docs/wiki'
    out.mkdir(exist_ok=True)
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    def table(headers, rows):
        return '\n'.join('| ' + ' | '.join(map(cell, row)) + ' |' for row in [headers, ['---'] * len(headers), *rows])
    for ko in (True, False):
        suffix = '.md' if ko else '.en.md'
        nav = f'[한국어](README.md) | [English](README.en.md) · [Index](README{suffix})\n\n'
        caveat = ('스포일러 포함. 현재 data/overlay.json의 조건별 표식 행이며 고유 아이템 수나 동시 출현 수가 아닙니다. 런타임 추가 판정은 아래 설명과 기술 문서를 참고하세요.' if ko else
                  'Spoilers. Rows are conditional variants from current data/overlay.json, not unique item counts or simultaneous spawns. Additional runtime gates apply; see the notes and technical documents.')
        def write(stem, title, body):
            (out / (stem + suffix)).write_text(f'# {title}\n\n{nav}{body}\n')
        entries = [('01-native-map', '원작 지도와 표시 범위', 'Native map and scope'), ('02-data-pipeline', '데이터와 표 읽기', 'Data and table notation')]
        entries += [(g[0], g[1], g[2]) for g in groups]
        entries += [('10-sources', '출처와 배포 권리', 'Sources and distribution rights')]
        write('README', 'RE3 지도 모드 위키' if ko else 'RE3 map mod wiki', caveat + '\n\n' + table(
            ['문서' if ko else 'Page'], [[f'[{e[1 if ko else 2]}]({e[0]}{suffix})'] for e in entries]) +
            '\n\n[README](../../README' + suffix + ')')
        write('01-native-map', entries[0][1 if ko else 2],
              ('게임 자체의 지도에 주석을 겹칩니다. `8`은 방문 → 지역 지도로 공개 → 전체를 순환합니다. 전체는 미방문 윤곽도 공개하지만 층·진행별 원작 방 선택을 없애지 않습니다. 기본은 한국어·방문 범위·이름100%·불투명도70%, 몬스터만 끔입니다.\n\n`0`은 주석 전체, `1`–`7`은 분류, `9`는 언어입니다. 이름 크기는 -/=, 불투명도는 Shift와 함께 조절합니다. RE1 전용 전체 화면 지도·RE2 랭크 기능은 없습니다.' if ko else
               'Annotations overlay the native map. `8` cycles visited → revealed by an area map → all. All reveals unexplored outlines but preserves native floor/story variants. Defaults: Korean, visited scope, size100%, opacity70%; monsters off, other categories on.\n\n`0` toggles all, `1`–`7` categories, `9` language. -/= changes size; hold Shift for opacity. No RE1 full-screen map or RE2 rank feature.'))
        write('02-data-pipeline', entries[1][1 if ko else 2], caveat + '\n\n' +
              ('원본 RDT → 외부 SCD 디컴파일 → 방 데이터/호출 조건 → 지도 좌표·표식 → atlas/ASI 순서입니다. 이 위키는 `python3 tools/gen_wiki.py`로 생성합니다.\n\n' if ko else
               'Pipeline: original RDT → external SCD decompiler → room data/call predicates → map coordinates/markers → atlas/ASI. Regenerate with `python3 tools/gen_wiki.py`.\n\n') +
              '`page:idx` = logical map cell, not output pixels or a floor label. `Rxxx` = source room script. `sets`: 1=DATA_J, 2=DATA_AJ, 3=both. Coordinates are logical map coordinates, not PC/console output resolution.\n\n' +
              '`guard` is raw compiled JSON: outer groups are AND, alternatives inside each group are OR; each [bank,bit,value] is one test. [] has no compiled guard, but pickup/kill/scope/floor/runtime gates still apply. Special banks encode additional comparisons; do not interpret every triple as a literal save flag.\n\n' +
              '`flag` = pickup flag; `lock` = unlock identifier; `kill` = kill flag (255 means no ordinary kill flag). `item` is a decimal item ID. `use`/`event` and anchors identify runtime puzzle/event handling. Retain raw metadata to avoid implying complete runtime semantics.')
        for stem, title_ko, title_en, kinds in groups:
            if kinds is None:
                rows = [[f"{r['page']}:{r['idx']}", ', '.join('R'+v for v in r['rdts']) or '—',
                         (names['rooms'].get(r['name'], r['name']) if ko else r['name']) or '—'] for r in overlay['rooms']]
                headers = ['Cell', 'RDT', '방' if ko else 'Room']
            else:
                rows = []
                for m in markers:
                    if m['kind'] not in kinds:
                        continue
                    r = rooms[m['page'], m['idx']]
                    room = names['rooms'].get(r['name'], r['name']) if ko else r['name']
                    item = m.get('item')
                    if item is not None:
                        pair = names['items'].get(str(item))
                        label = pair[1 if ko else 0] if pair else fallback[item] if item < len(fallback) else str(item)
                    else:
                        label = m.get('monster', m['kind'])
                    meta = {k:v for k,v in m.items() if k not in {'page','idx','rdt','kind','x','y','sets','guard'}}
                    rows.append([f"{m['page']}:{m['idx']}", 'R'+m['rdt'], room or '—', label,
                                 f"{m['x']},{m['y']}", m['sets'], json.dumps(m['guard'], separators=(',', ':')),
                                 json.dumps(meta, ensure_ascii=False, separators=(',', ':'))])
                assert len(rows) == sum(m['kind'] in kinds for m in markers)
                headers = ['Cell', 'RDT', '방' if ko else 'Room', '표식' if ko else 'Marker', 'x,y', 'sets', 'guard', 'metadata']
            intro = caveat
            if stem == '06-puzzles-events':
                intro += '\n\nOrange ! = puzzle; purple ? = Live Selection. Room anchors are approximate; no activation-time or outcome prediction.'
            if stem == '11-monsters':
                intro += '\n\nOrdinary monsters follow conditional scoped placements, including unloaded rooms. Unknown conditions are omitted. These rows exclude dynamically added live actors. Only some upcoming Nemesis appearances are shown.'
            write(stem, title_ko if ko else title_en, intro + '\n\n' + table(headers, rows))
        write('10-sources', '출처와 배포 권리' if ko else 'Sources and distribution rights',
              '[NOTICE](../../NOTICE.md) · [Icons](../../assets/README.md)\n\n' +
              ('소스 라이선스, 글꼴 고지, HD 팩 파생 헤더의 재배포 권리를 공개 배포 전에 확인해야 합니다. 원본 게임 데이터나 다운로드한 참고 이미지는 위키/배포물에 포함하지 않습니다.' if ko else
               'Confirm source licensing, font notices and redistribution rights for the HD-pack-derived header before publication. Do not bundle original game data or downloaded reference images.'))
    print(f'Generated {2 * (len(groups) + 4)} wiki pages; {len(rooms)} cells; {len(markers)} conditional marker rows.')


if __name__ == '__main__':
    main()
