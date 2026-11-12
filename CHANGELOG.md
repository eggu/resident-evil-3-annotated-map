# Changelog

## 1.2.0

- SD mode: with Classic REbirth's `HDTextures = 0` (or missing) the map uses 1x pixel markers and a pixel font (Galmuri9) instead of blurry HD text. Room names sit next to their room on a short line and show only at 100% zoom or more. `DisplayMode` in the INI can force HD or SD.
- SD markers share their shapes with the RE1 and RE2 map mods: key items are circles, locked doors are padlocks in the key's colour, herbs are inverted triangles, ammo is a cartridge box, enemies are a small red X.
- The Uptown map names the police station block.
- Room shapes are read more accurately from the game's map textures, so some room names in HD sit better.

- SD 모드: Classic REbirth의 `HDTextures = 0`(또는 없음)이면 흐릿한 HD 글자 대신 1배 픽셀 표식과 픽셀 글꼴(Galmuri9)을 씁니다. 방 이름은 방 옆에 짧은 선으로 붙고, 확대 100% 이상에서만 표시됩니다. INI의 `DisplayMode`로 HD나 SD를 강제할 수 있습니다.
- SD 표식은 RE1·RE2 지도 모드와 같은 모양: 핵심 아이템은 원, 잠긴 문은 열쇠 색의 자물쇠, 허브는 역삼각형, 탄약은 탄약 상자, 적은 작은 빨간 X.
- 업타운 지도에 경찰서 구역 이름 표시.
- 게임 지도 텍스처에서 방 모양을 더 정확히 읽어 HD의 일부 방 이름 위치가 나아졌습니다.

## 1.1.0

- New keys: `6` Events (new category, off by default), `7` common items, `8` enemies, `9` scope. Language switch moved to `\` (`₩` on Korean keyboards).
- Events: the purple `?` marks story scenes that can spoil the game (Live Selections and the start of movies or long cutscenes, 17 scenes). Markers disappear once the scene has played.
- Item names (`H`) cycle through all, all except common items, and hidden.
- Puzzle markers show the name of the device instead of the item it needs.
- Name and item-icon sizes re-based to 100%; saved settings are converted automatically (INI Version 4).
- Common items use a grey; one text size for the whole legend; item and puzzle names always sit next to their marker.
- A default `RE3.AnnotatedMap.ini` is included in the ZIP.
- A notice appears on the map if `HDTextures` is 0 in Classic REbirth's `config.ini`.
- The download now includes Ultimate ASI Loader v9.7.4 (MIT) as `dsound.dll`, so no separate ASI loader is needed. If you already have Ultimate ASI Loader installed as `dsound.dll`, keep yours; if you have a different `dsound.dll` (e.g. DSOAL), copy the included one as `winmm.dll` instead.

- 새 키: `6` 이벤트(새 분류, 기본 꺼짐), `7` 일반 아이템, `8` 적, `9` 범위. 언어 전환은 `\`(한국 키보드에서는 `₩`)로 이동.
- 이벤트: 보라색 `?`가 스포일러가 될 수 있는 이야기 장면(Live Selection, 영상·긴 연출 시작 자리, 17개 장면)을 표시하며, 장면이 끝나면 사라집니다.
- 아이템 이름(`H`): 모두 표시 → 일반 아이템 제외 → 모두 숨김.
- 퍼즐 표식이 필요한 아이템 대신 장치 이름을 표시.
- 이름·아이템 아이콘 크기 기준을 100%로 조정하고, 저장된 설정은 자동 변환(INI Version 4).
- 일반 아이템 회색 표시, 범례 글자 크기 통일, 아이템·퍼즐 이름이 항상 표식 옆에 표시.
- ZIP에 기본 `RE3.AnnotatedMap.ini` 포함.
- Classic REbirth `config.ini`의 `HDTextures`가 0이면 지도에 안내 표시.
- 다운로드에 Ultimate ASI Loader v9.7.4(MIT)를 `dsound.dll`로 포함해 별도의 ASI 로더가 필요 없습니다. 이미 Ultimate ASI Loader를 `dsound.dll`로 설치했다면 기존 것을 그대로 쓰세요. 다른 `dsound.dll`(예: DSOAL)이 있으면 포함된 파일을 `winmm.dll` 이름으로 복사하세요.

## 1.0.2

- Corrected the installation guide: the map mod only needs Classic REbirth (tested with 1.0.3). The mod itself is unchanged from 1.0.1.

- 설치 안내를 고쳤습니다. 지도 모드에 필요한 것은 Classic REbirth(1.0.3에서 확인)뿐입니다. 모드 자체는 1.0.1과 같습니다.

## 1.0.1

- New installs now start in English with only room names shown. An existing `RE3.AnnotatedMap.ini` keeps its settings.

- 새로 설치할 때의 기본 설정을 바꿨습니다. 이제 영어, 방 이름만 표시로 시작합니다. 기존 `RE3.AnnotatedMap.ini`가 있으면 그 설정을 그대로 씁니다.

## 1.0.0

- First release: room names, locked doors and keys, items, documents and maps, puzzles and Live Selections, typewriters, item boxes and monsters on the Resident Evil 3 map.
- Visited rooms / revealed rooms / all rooms scope; Korean / English; adjustable name size and opacity.
- Picked-up items, opened doors, solved puzzles and defeated monsters disappear from the map.
- Known limitation: some monster encounters and upcoming Nemesis appearances may not be shown.

- 방 이름, 잠긴 문과 열쇠, 아이템, 문서·지도, 퍼즐·Live Selection, 타자기·아이템 상자, 몬스터를 표시하는 첫 정식 버전입니다.
- 방문한 방 / 공개된 방 / 모든 방 범위 선택, 한국어 / English, 이름 크기·불투명도 조절.
- 주운 아이템, 열린 문, 완료한 퍼즐, 쓰러뜨린 몬스터는 지도에서 사라집니다.
- 알려진 제한: 일부 몬스터 출현과 네메시스의 예정 출현 위치는 표시되지 않을 수 있습니다.
