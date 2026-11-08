# Release notes

## 1.0.2 (in preparation)

- **Legend and keys changed.** `6` is now Events (a new category, off by default), `7` common items, `8` enemies, `9` the scope. The language switch moved from `9` to the `\` key (`₩` on Korean keyboards). `[H]` item names and `[\]` language sit together in the right column of the legend. Saved settings are converted once (the INI is now Version 4; Events starts as your old Puzzles setting).
- **Events** (purple `?`) are split from puzzles (orange `!`): they mark story scenes that can spoil, the Live Selections and now also the places where a movie or a long cutscene starts (found in the game's room scripts; 23 markers for 17 scenes), and disappear once the scene has played. Scenes the game gives no flag for are not marked.
- Event markers have no name; only the purple `?` is drawn.
- **Sizes re-based:** the old 80% name size is now 100% and the old 130% item-icon size is now 100% (item icons only; puzzle markers, documents and enemies keep their size per setting). Your saved NameSize/IconSize are converted so names and item icons keep their current size; the name size range is now 50-200.
- Item names (`H`) now cycle through three states: all names, all except common items, all hidden. The legend row shows the state. `ItemNames` in `RE3.AnnotatedMap.ini` is 0 (hidden), 1 (all) or 2 (no common items); old on/off settings keep working (on = all, off = hidden).
- A default `RE3.AnnotatedMap.ini` with every setting and a short comment is included. Keep your existing INI when upgrading.
- Common items use a cool grey (#B8BCC4) in the legend and on the map; switched-off legend rows use a darker grey (#6A6A6A).
- All legend, hint and readout lines use one text size; the size/opacity panel no longer has an empty band above its first line.
- Item and puzzle names always sit next to their own marker.
- If Classic REbirth's `HDTextures` is 0 in `config.ini`, the map shows a notice at the top left.

---

## 1.0.2 (준비 중)

- **범례와 키가 바뀌었습니다.** `6`이 이벤트(새 분류, 기본 꺼짐), `7` 일반 아이템, `8` 적, `9` 범위입니다. 언어 전환은 `9`에서 `\` 키(한국 키보드에서는 `₩`)로 옮겼습니다. 범례 오른쪽 열에 `[H]` 아이템 이름과 `[\]` 언어가 함께 있습니다. 저장된 설정은 한 번 자동 변환됩니다(INI 버전 4, 이벤트는 예전 퍼즐 설정값으로 시작).
- **이벤트**(보라색 `?`)를 퍼즐(주황색 `!`)에서 분리했습니다. 스포일러가 될 수 있는 장면(Live Selection, 그리고 영상이나 긴 연출이 시작되는 자리 — 게임 방 스크립트에서 찾은 17개 장면, 표식 23개)을 표시하고, 장면이 끝나면 사라집니다. 게임이 끝났다는 표시를 남기지 않는 장면은 표시하지 않습니다.
- 이벤트 표식에는 이름이 없고 보라색 `?`만 그립니다.
- **크기 기준 변경:** 예전 이름 크기 80%가 새 100%, 예전 아이템 아이콘 130%가 새 100%입니다(아이템 아이콘만, 퍼즐·문서·적은 설정값 그대로). 저장된 NameSize/IconSize는 지금 보이는 크기가 유지되도록 변환되며, 이름 크기 범위는 50–200%입니다.
- 아이템 이름(`H`)이 3단계로 바뀝니다: 모두 표시 → 일반 아이템 제외 → 모두 숨김. 범례 줄에 현재 상태가 표시됩니다. `RE3.AnnotatedMap.ini`의 `ItemNames`는 0(숨김), 1(모두), 2(일반 제외)이며, 예전 켜기/끄기 설정은 그대로 동작합니다(켬 = 모두, 끔 = 숨김).
- 모든 설정과 짧은 설명이 든 기본 `RE3.AnnotatedMap.ini`를 함께 제공합니다. 업그레이드할 때는 기존 INI를 유지하세요.
- 일반 아이템을 범례와 지도에서 차가운 회색(#B8BCC4)으로 표시하고, 꺼진 범례 줄은 더 어두운 회색(#6A6A6A)으로 표시합니다.
- 범례·힌트·수치 줄의 글자 크기를 하나로 맞추고, 크기·불투명도 패널 첫 줄 위의 빈 공간을 없앴습니다.
- 아이템·퍼즐 이름이 항상 자기 표식 옆에 표시됩니다.
- Classic REbirth `config.ini`의 `HDTextures`가 0이면 지도 왼쪽 위에 안내를 표시합니다.
