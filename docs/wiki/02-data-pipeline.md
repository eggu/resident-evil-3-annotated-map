# 데이터와 표 읽기

[한국어](README.md) | [English](README.en.md) · [Index](README.md)

스포일러 포함. 현재 data/overlay.json의 조건별 표식 행이며 고유 아이템 수나 동시 출현 수가 아닙니다. 런타임 추가 판정은 아래 설명과 기술 문서를 참고하세요.

원본 RDT → 외부 SCD 디컴파일 → 방 데이터/호출 조건 → 지도 좌표·표식 → atlas/ASI 순서입니다. 이 위키는 `python3 tools/gen_wiki.py`로 생성합니다.

`page:idx` = logical map cell, not output pixels or a floor label. `Rxxx` = source room script. `sets`: 1=DATA_J, 2=DATA_AJ, 3=both. Coordinates are logical map coordinates, not PC/console output resolution.

`guard` is raw compiled JSON: outer groups are AND, alternatives inside each group are OR; each [bank,bit,value] is one test. [] has no compiled guard, but pickup/kill/scope/floor/runtime gates still apply. Special banks encode additional comparisons; do not interpret every triple as a literal save flag.

`flag` = pickup flag; `lock` = unlock identifier; `kill` = kill flag (255 means no ordinary kill flag). `item` is a decimal item ID. `use`/`event` and anchors identify runtime puzzle/event handling. Retain raw metadata to avoid implying complete runtime semantics.
