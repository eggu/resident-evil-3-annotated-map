# Release notes

## 1.2.1

**Upgrading:** replace `RE3.AnnotatedMap.asi` in the game folder. Your `RE3.AnnotatedMap.ini` stays as it is.

- **Auto display mode.** With `DisplayMode=Auto` (the default), the map uses HD only when Classic REbirth is running with `HDTextures = 1` and both `RetroMode` and `LowResEnable` are off. In every other case it uses SD: `HDTextures = 0` or missing, retro or low-resolution mode on, or playing without Classic REbirth (a leftover `config.ini` no longer turns HD on). `DisplayMode=HD` or `SD` still forces one.

---

## 1.2.1 (한국어)

**업그레이드:** 게임 폴더의 `RE3.AnnotatedMap.asi`만 바꾸면 됩니다. `RE3.AnnotatedMap.ini`는 그대로 둡니다.

- **자동 표시 방식.** `DisplayMode=Auto`(기본)는 Classic REbirth가 `HDTextures = 1`이고 `RetroMode`·`LowResEnable`이 모두 꺼진 상태로 실행될 때만 HD를 씁니다. 그 밖의 경우는 모두 SD입니다: `HDTextures = 0`이거나 항목이 없을 때, 레트로·저해상도 모드가 켜져 있을 때, Classic REbirth 없이 실행할 때(남아 있는 `config.ini`만으로는 더 이상 HD가 켜지지 않음). `DisplayMode=HD`나 `SD`로 고정할 수 있습니다.

---

## 1.2.0

**Upgrading:** copy the ZIP contents into the game folder (`RE3.AnnotatedMap.asi` and the `hires` folder) and keep your existing `RE3.AnnotatedMap.ini`. Your settings stay as they are; the new `DisplayMode` setting starts at `Auto` (the included INI explains it).

- **SD mode.** If you play with Classic REbirth's `HDTextures = 0` (or the key is missing), the map no longer shows blurry HD text. It switches to 1x pixel markers and a pixel font (Galmuri9) drawn at the game's own resolution. Room names sit next to their room with a short line and appear at 100% zoom or more; at 50% only the markers are shown. In SD, name and icon size, opacity and item names are not available.
- **SD markers** use the same shapes as the RE1 and RE2 map mods: key items are circles, locked doors are padlocks in the colour of their key, herbs are inverted triangles, ammo is a cartridge box in the ammo's colour, and enemies are a small red X.
- **`DisplayMode`** in the INI: `Auto` (default) follows `HDTextures`; `HD` or `SD` forces one.
- **Uptown** now names the police station block.
- **Room shapes** are read more accurately from the game's map textures, so some room names in HD sit better.

---

## 1.2.0 (한국어)

**업그레이드:** ZIP의 내용(`RE3.AnnotatedMap.asi`, `hires` 폴더)을 게임 폴더에 복사하고 기존 `RE3.AnnotatedMap.ini`는 그대로 두세요. 설정은 그대로 유지되고, 새 `DisplayMode` 설정은 `Auto`로 시작합니다(포함된 INI에 설명이 있습니다).

- **SD 모드.** Classic REbirth의 `HDTextures = 0`(또는 키 없음)으로 플레이하면 흐릿한 HD 글자 대신 게임 해상도에 맞춘 1배 픽셀 표식과 픽셀 글꼴(Galmuri9)로 표시합니다. 방 이름은 방 옆에 짧은 선으로 붙고 확대 100% 이상에서 표시되며, 50%에서는 표식만 표시합니다. SD에서는 이름·아이콘 크기, 불투명도, 아이템 이름을 쓸 수 없습니다.
- **SD 표식**은 RE1·RE2 지도 모드와 같은 모양입니다: 핵심 아이템은 원, 잠긴 문은 열쇠 색의 자물쇠, 허브는 역삼각형, 탄약은 탄약 색의 탄약 상자, 적은 작은 빨간 X.
- **INI의 `DisplayMode`**: `Auto`(기본)는 `HDTextures`를 따르고, `HD`나 `SD`는 해당 모드를 강제합니다.
- **업타운** 지도에 경찰서 구역 이름을 표시합니다.
- 게임 지도 텍스처에서 **방 모양**을 더 정확히 읽어 HD의 일부 방 이름 위치가 나아졌습니다.

---

## 1.1.0

**Upgrading:** copy the ZIP contents into the game folder (`RE3.AnnotatedMap.asi`, the `hires` folder, `dsound.dll`, `scripts`), and keep your existing `RE3.AnnotatedMap.ini`. Your settings are converted automatically the first time you open the map (Events starts with your old Puzzles setting; name and item-icon sizes look the same as before). The ZIP now also contains a default `RE3.AnnotatedMap.ini` with every setting explained; copy it only if you do not have one yet.

- **New keys.** `6` is now **Events**, a new category that is off by default; `7` is common items, `8` enemies and `9` the scope (visited / revealed / all rooms). The language switch moved from `9` to `\` (`₩` on Korean keyboards). The legend shows `[H]` item names and `[\]` language together in its right column.
- **Events.** Orange `!` still marks puzzles. The purple `?` now marks story scenes that can spoil the game: the Live Selections and the places where a movie or long cutscene starts (17 scenes found in the game data). A marker disappears once the scene has played. Scenes the game gives no way to detect are not marked. Event markers have no name.
- **Item names (`H`)** now cycle through three states: all names, all except common items, all hidden. The legend shows the current state. In the INI, `ItemNames` is 0 (hidden), 1 (all) or 2 (no common items).
- **Puzzle markers** show the name of the device (for example Book Stand, Fire Hydrant) instead of the item it needs.
- **Sizes re-based.** The old 80% name size is now 100% and the old 130% item-icon size is now 100% (item icons only; puzzle markers, documents and enemies keep their size). The name size range is 50-200%. Your saved sizes are converted so nothing changes on screen.
- **Legend and colors.** Common items use a cool grey on the map and in the legend; switched-off legend rows use a darker grey. All legend, hint and readout lines share one text size, and the size/opacity panel no longer has an empty band above its first line.
- **Names stay with their marker.** Item and puzzle names always sit next to their own marker.
- **ASI loader included.** The download now includes Ultimate ASI Loader v9.7.4 (MIT) as `dsound.dll`, so you no longer need to install one yourself. If you already have Ultimate ASI Loader installed as `dsound.dll`, keep yours and skip `dsound.dll`. If you have a different `dsound.dll` (for example DSOAL), do not overwrite it: copy the included one as `winmm.dll`.
- **HD textures notice.** If `HDTextures` is 0 in Classic REbirth's `config.ini`, the map shows a notice at the top left, because the map text would look blurry.

---

## 1.1.0 (한국어)

**업그레이드:** ZIP의 내용(`RE3.AnnotatedMap.asi`, `hires` 폴더, `dsound.dll`, `scripts`)을 게임 폴더에 복사하고, 기존 `RE3.AnnotatedMap.ini`는 그대로 두세요. 지도를 처음 열 때 설정이 자동으로 변환됩니다(이벤트는 예전 퍼즐 설정값으로 시작하고, 이름·아이템 아이콘 크기는 이전과 똑같이 보입니다). ZIP에는 모든 설정과 설명이 든 기본 `RE3.AnnotatedMap.ini`도 들어 있습니다. 아직 INI가 없을 때만 복사하세요.

- **키가 바뀌었습니다.** `6`은 새 분류인 **이벤트**(기본 꺼짐), `7`은 일반 아이템, `8`은 적, `9`는 범위(방문한 방 / 공개된 방 / 모든 방)입니다. 언어 전환은 `9`에서 `\`(한국 키보드에서는 `₩`)로 옮겼습니다. 범례 오른쪽 열에 `[H]` 아이템 이름과 `[\]` 언어가 함께 표시됩니다.
- **이벤트.** 주황색 `!`는 계속 퍼즐입니다. 보라색 `?`는 이제 스포일러가 될 수 있는 이야기 장면을 표시합니다: Live Selection, 그리고 영상이나 긴 연출이 시작되는 자리(게임 데이터에서 찾은 17개 장면). 장면이 끝나면 표식이 사라집니다. 게임이 봤는지 알려주지 않는 장면은 표시하지 않습니다. 이벤트 표식에는 이름이 없습니다.
- **아이템 이름(`H`)**이 3단계로 바뀝니다: 모두 표시 → 일반 아이템 제외 → 모두 숨김. 범례에 현재 상태가 표시됩니다. INI의 `ItemNames`는 0(숨김), 1(모두), 2(일반 제외)입니다.
- **퍼즐 표식**은 필요한 아이템 대신 장치 이름(예: 책 받침대, 소화전)을 표시합니다.
- **크기 기준 변경.** 예전 이름 크기 80%가 새 100%, 예전 아이템 아이콘 130%가 새 100%입니다(아이템 아이콘만, 퍼즐·문서·적은 크기 그대로). 이름 크기 범위는 50-200%입니다. 저장된 크기는 화면에서 달라지지 않도록 자동 변환됩니다.
- **범례와 색.** 일반 아이템은 지도와 범례에서 차가운 회색, 꺼진 범례 줄은 더 어두운 회색으로 표시합니다. 범례·힌트·수치 줄의 글자 크기를 하나로 맞췄고, 크기·불투명도 패널 첫 줄 위의 빈 공간을 없앴습니다.
- **이름이 표식 옆에 표시됩니다.** 아이템·퍼즐 이름이 항상 자기 표식 옆에 표시됩니다.
- **ASI 로더 포함.** 다운로드에 Ultimate ASI Loader v9.7.4(MIT)를 `dsound.dll`로 포함했으므로 따로 설치하지 않아도 됩니다. 이미 Ultimate ASI Loader를 `dsound.dll`로 설치했다면 기존 것을 그대로 두고 `dsound.dll`은 건너뛰세요. 다른 `dsound.dll`(예: DSOAL)이 있으면 덮어쓰지 말고 포함된 파일을 `winmm.dll` 이름으로 복사하세요.
- **HD 텍스처 안내.** Classic REbirth `config.ini`의 `HDTextures`가 0이면 지도 글자가 흐릿해 보이므로 지도 왼쪽 위에 안내를 표시합니다.
