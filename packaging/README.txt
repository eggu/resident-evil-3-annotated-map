RE3 Annotated Map - Survivor's Notes — 한국어

## HD와 SD

게임을 시작할 때 Classic REbirth `config.ini`의 `HDTextures` 설정을 따릅니다.

- **HD** (`HDTextures = 1`): `hires\misc\`의 `.webp` 파일로 글자와 아이콘을 선명하게 표시합니다.
- **SD** (`HDTextures = 0`이거나 항목이 없을 때): 저해상도용 1배 픽셀 마커와 픽셀 글꼴(Galmuri9)로 표시합니다. 방 이름은 짧은 선으로 방 옆에 붙고, 지도를 축소하면 숨겨집니다. SD에서는 이름·아이콘 크기, 불투명도, 아이템 이름을 쓸 수 없습니다.

## 설치

1. **Classic REbirth**(바이오하자드 3용, 1.0.3에서 확인)를 먼저 설치합니다. [공식 다운로드](https://classicrebirth.com/index.php/downloads/resident-evil-3-classic-rebirth/)
2. 게임을 종료하고 [Releases](https://github.com/eggu/resident-evil-3-annotated-map/releases/latest)에서 `RE3-Annotated-Map-<버전>.zip`을 받아 압축을 풉니다. `Source code`는 설치 파일이 아닙니다.
3. ZIP의 내용(`dsound.dll`, `RE3.AnnotatedMap.asi`, `hires`, `scripts`)을 `BIOHAZARD(R) 3 PC.exe`가 있는 게임 폴더에 폴더 구조 그대로 복사합니다. ASI 로더인 [Ultimate ASI Loader](https://github.com/ThirteenAG/Ultimate-ASI-Loader) v9.7.4(MIT)가 `dsound.dll`로 포함되어 있습니다. 기존 `hires` 폴더가 있으면 합치고, 같은 이름의 파일은 교체합니다. 다른 HD 모드를 사용한다면 먼저 기존 `hires` 폴더를 백업하세요. 기본 설정 파일 `RE3.AnnotatedMap.ini`는 게임 폴더에 아직 없을 때만 복사하세요. 이미 있으면 덮어쓰지 마세요(내 설정이 사라집니다).
   - 한글 패치 등으로 Ultimate ASI Loader가 이미 `dsound.dll`로 설치되어 있으면 기존 것을 그대로 두고 `dsound.dll`은 건너뛰세요.
   - ASI 로더가 아닌 다른 `dsound.dll`(예: DSOAL)이 있으면 덮어쓰지 말고, 포함된 `dsound.dll`을 `winmm.dll` 이름으로 복사하세요.
4. Classic REbirth로 게임을 실행하고 지도를 열면 표시됩니다. 한글 번역 모드는 필수가 아닙니다.

```text
게임 폴더/
├─ BIOHAZARD(R) 3 PC.exe
├─ dsound.dll   (Ultimate ASI Loader, 이미 있으면 건너뜀)
├─ RE3.AnnotatedMap.asi
├─ RE3.AnnotatedMap.ini   (기본 설정, 이미 있으면 덮어쓰지 않음)
├─ scripts/
│  └─ UltimateASILoader-LICENSE.txt
└─ hires/
   └─ misc/
      └─ 지도 모드의 .webp 파일들
```

업그레이드할 때는 기존 `RE3.AnnotatedMap.ini`를 지우거나 ZIP의 기본 파일로 덮어쓰지 마세요. 지도 표시 설정이 들어 있습니다.

제거: `RE3.AnnotatedMap.asi`, `.ini`, `.log`, `scripts/UltimateASILoader-LICENSE.txt`(다른 ASI 모드가 없으면 `dsound.dll`도)와 지도 모드 ZIP에 포함된 `.webp` 파일만 지우세요. 기존 HD 파일을 백업했다면 복원합니다. `hires` 폴더 전체를 지우면 다른 HD 모드도 영향을 받습니다.

## 문제 해결

- **지도가 전혀 나오지 않을 때**: 이 모드는 SourceNext `BIOHAZARD(R) 3 PC.exe`의 한 가지 빌드(실행 파일 시간표시 `0x44642AAC`, 이미지 크기 `0xB01000`)에서만 동작합니다. 다른 빌드에서는 아무것도 그리지 않고 `RE3.AnnotatedMap.log`에 `Unsupported executable`을 남깁니다. 또 Classic REbirth 1.0.3의 `ddraw.dll`에는 ASI 로더가 들어 있지 않아, ZIP에 Ultimate ASI Loader를 `dsound.dll`로 포함했습니다. `dsound.dll`이 `BIOHAZARD(R) 3 PC.exe`와 같은 폴더에 있는지, 다른 `dsound.dll`로 바뀌지 않았는지 확인하세요.
- **`HDTextures = 1`인데 지도 글자·아이콘이 흐릿할 때**: 선명한 글자는 REbirth가 `hires\misc\`의 `.webp` 파일을 읽어야 나옵니다. `hires\misc\`에 이 모드의 `.webp` 파일이 들어 있는지(`.asi`만 복사하면 흐릿합니다), REbirth 설정에서 저해상도·레트로 모드가 꺼져 있는지 확인하세요. `HDTextures = 0`이면 SD용 픽셀 마커와 글꼴로 표시됩니다.

## 단축키

지도 화면에서만 작동하며, 현재 상태가 범례에 표시됩니다.

| 키 | 동작 |
|---|---|
| 0 | 전체 표시 켜기/끄기 |
| 1 | 방 이름·타자기·아이템 상자 |
| 2 | 잠긴 문·필요한 열쇠 |
| 3 | 핵심 아이템 |
| 4 | 문서·지도 |
| 5 | 퍼즐(아이템이나 풀이가 필요한 장치) |
| 6 | 이벤트(스포일러가 되는 장면, Live Selection) |
| 7 | 일반 아이템(탄약·회복·리본·화약) |
| 8 | 적 |
| 9 | 방문한 방 → 공개된 방(지역 지도 획득) → 모든 방 |
| \\(₩) | 한국어 / English |
| - · = (+), 숫자패드 - · + | 이름 크기 10%씩(50–200%) |
| [ · ] | 이름 불투명도 10%씩(10–100%) |
| Shift + - · = (+) | 아이콘 크기 10%씩(50–200%) |
| Shift + [ · ] | 아이콘 불투명도 10%씩(10–100%) |
| H | 아이템 이름 3단계 전환: 모두 표시 → 일반 아이템 제외 → 모두 숨김(열쇠·잠긴 문·문서·퍼즐·일반 아이템) |
| ~ | 범례와 범례 오른쪽의 크기·불투명도 수치 접기/펴기 |

## 설정

지도 화면에서 바꾼 설정은 자동으로 저장됩니다. 설정 파일은 게임 폴더의 `RE3.AnnotatedMap.ini`입니다. 직접 편집하려면 게임을 종료한 뒤 메모장으로 여세요. 설정 파일에서만 바꿀 수 있는 항목:

- `Modifier=Shift`: 아이콘 크기·불투명도에 함께 누르는 키. `Ctrl`로 바꿀 수 있습니다.
- `LockMarker=Door`: 잠긴 문 아이콘을 문 위치에 표시합니다. `Unvisited`로 바꾸면 문 너머 방(그 방만 방문했다면 문 이쪽)에 표시합니다.
- `DisplayMode=Auto`: `HDTextures`를 따릅니다(HD와 SD 참고). `HD`나 `SD`로 고정할 수 있습니다.

이전 버전에서 업그레이드하면 기존 설정은 유지되며 한 번 자동 변환됩니다. 이벤트는 예전 퍼즐 설정값으로 시작하고, 이름·아이템 아이콘 크기는 지금 보이는 크기가 유지됩니다. 열쇠·잠긴 문 이름은 꺼진 상태로 시작합니다(`H`로 켬). 이름 불투명도는 이제 `[` · `]`이고, Shift + `-` · `+`는 아이콘 크기입니다.

이름을 크게 하면 서로 겹칠 수 있습니다.

## 표시 안내

방 이름은 방 안의 정해진 자리에 표시되고, 너무 좁은 방은 짧은 선으로 이어진 바깥 자리에 표시됩니다. 아이콘과 아이템 이름이 방 이름을 가릴 수 있습니다. 퍼즐 표식은 필요한 아이템이 아니라 그 자리의 장치 이름(예: 책 받침대, 소화전)을 표시합니다. 같은 자리에 두 번 놓인 같은 아이템은 이름을 한 번만 표시합니다. 핵심 아이템·퍼즐 아이콘과 겹친 일반 아이템·적 아이콘은 숨기고, 범례·수치 패널 아래에 오는 표시는 그리지 않습니다.

주황색 `!`는 퍼즐, 보라색 `?`는 이벤트(Live Selection 선택 장면과 영상·긴 연출이 시작되는 자리)입니다. 이벤트는 스포일러가 될 수 있어 기본으로 꺼져 있고(`6`), 한 번 지나가면 사라집니다. 이벤트 표식에는 이름이 없고(`H`로도 나타나지 않음) 보라색 `?`만 표시됩니다. 이벤트 표시는 대략적인 위치를 안내하며, 선택 결과는 알려주지 않습니다. 게임 데이터에서 찾을 수 있는 장면만 표시하며(일부 장면은 한 번 봤는지 알 수 없어 제외), 방에 들어가면 자동으로 시작되는 장면은 방 대략 위치에 표시합니다.

몬스터 표시는 일부 출현을 빠뜨릴 수 있습니다. 네메시스의 예정 출현 위치는 일부만 표시하며, 네메시스가 떨어뜨리는 아이템은 표시하지 않습니다.



RE3 Annotated Map - Survivor's Notes — English

## HD and SD

The mod follows Classic REbirth's `HDTextures` setting in `config.ini` at game start.

- **HD** (`HDTextures = 1`): sharp text and icons from the `.webp` files in `hires\misc\`.
- **SD** (`HDTextures = 0` or missing): low-resolution 1x pixel markers and a pixel font (Galmuri9). Room names sit next to their room on a short line and are hidden when the map is zoomed out. In SD, name and icon size, opacity and item names are not available.

## Installation

1. Install **Classic REbirth** for Resident Evil 3 first (tested with 1.0.3). [Official download](https://classicrebirth.com/index.php/downloads/resident-evil-3-classic-rebirth/)
2. Close the game. Download `RE3-Annotated-Map-<version>.zip` from [Releases](https://github.com/eggu/resident-evil-3-annotated-map/releases/latest) and extract it. `Source code` is not the install package.
3. Copy the ZIP contents (`dsound.dll`, `RE3.AnnotatedMap.asi`, `hires`, `scripts`) into the game folder containing `BIOHAZARD(R) 3 PC.exe`, preserving the folder structure. [Ultimate ASI Loader](https://github.com/ThirteenAG/Ultimate-ASI-Loader) v9.7.4 (MIT) is included as `dsound.dll`. Merge with an existing `hires` folder and replace matching files. If you use another HD mod, back up your existing `hires` folder first. Copy the default settings file `RE3.AnnotatedMap.ini` only if the game folder does not have one yet. Never overwrite an existing one (it holds your settings).
   - If Ultimate ASI Loader is already installed as `dsound.dll` (e.g. by a translation patch), keep yours and skip `dsound.dll`.
   - If you have a different `dsound.dll` (e.g. DSOAL), do not overwrite it: copy the included one as `winmm.dll`.
4. Launch the game with Classic REbirth and open the map. The Korean translation mod is not required.

```text
game folder/
├─ BIOHAZARD(R) 3 PC.exe
├─ dsound.dll   (Ultimate ASI Loader; skip if you already have it)
├─ RE3.AnnotatedMap.asi
├─ RE3.AnnotatedMap.ini   (default settings; never overwrite an existing one)
├─ scripts/
│  └─ UltimateASILoader-LICENSE.txt
└─ hires/
   └─ misc/
      └─ the map mod's .webp files
```

When upgrading, keep your existing `RE3.AnnotatedMap.ini`: do not delete it or overwrite it with the default file from the ZIP. It holds your map settings.

Uninstall: remove `RE3.AnnotatedMap.asi`, `.ini`, `.log`, `scripts/UltimateASILoader-LICENSE.txt` (and `dsound.dll` if no other ASI mod uses it) and only the `.webp` files included in the map ZIP. Restore backed-up HD files if applicable. Do not delete the entire `hires` folder: other HD mods also use it.

## Troubleshooting

- **Nothing appears on the map**: the mod only runs on one build of the SourceNext `BIOHAZARD(R) 3 PC.exe` (PE timestamp `0x44642AAC`, image size `0xB01000`). On any other build it draws nothing and writes `Unsupported executable` to `RE3.AnnotatedMap.log`. Classic REbirth 1.0.3's `ddraw.dll` does not load `.asi` files, so the ZIP includes Ultimate ASI Loader as `dsound.dll`. Check that `dsound.dll` sits next to `BIOHAZARD(R) 3 PC.exe` and was not replaced by a different `dsound.dll`.
- **Map text or icons look blurry with `HDTextures = 1`**: sharp text needs REbirth to read the `.webp` files in `hires\misc\`. Check that this mod's `.webp` files are in `hires\misc\` (copying only the `.asi` looks blurry) and that REbirth's low-resolution and retro modes are off. With `HDTextures = 0` the mod uses its SD pixel markers and font instead.

## Controls

Keys work on the map screen only. The legend shows the current state.

| Key | Action |
|---|---|
| 0 | All annotations on/off |
| 1 | Room names, typewriters and item boxes |
| 2 | Locked doors and required keys |
| 3 | Key items |
| 4 | Documents and maps |
| 5 | Puzzles (devices that need an item or a solution) |
| 6 | Events (story scenes that can spoil, Live Selections) |
| 7 | Common items (ammo, healing, ribbons, gunpowder) |
| 8 | Enemies |
| 9 | Visited → revealed by an area map → all rooms |
| \\(₩) | Korean / English |
| - · = (+), numpad - · + | Name size in 10% steps (50–200%) |
| [ · ] | Name opacity in 10% steps (10–100%) |
| Shift + - · = (+) | Icon size in 10% steps (50–200%) |
| Shift + [ · ] | Icon opacity in 10% steps (10–100%) |
| H | Item names, 3 states per press: all → all except common items → hidden (keys, locked doors, documents, puzzles, common items) |
| ~ | Fold or unfold the legend and the size and opacity readouts beside it |

## Settings

Changes made on the map are saved automatically to `RE3.AnnotatedMap.ini` in the game folder. Close the game before opening it in Notepad to edit it manually. Options available only in the file:

- `Modifier=Shift`: the key held for icon size and opacity. It can be `Ctrl`.
- `LockMarker=Door`: locked-door icons sit on the door. With `Unvisited` they sit in the room beyond the door (or on this side if only that room was visited).
- `DisplayMode=Auto`: follows `HDTextures` (see HD and SD). `HD` or `SD` forces one.

When upgrading from an earlier version, your settings are kept and converted once: Events starts with your old Puzzles setting, and name and item-icon sizes keep the size you had. Key and locked-door names start off (press `H`). Name opacity is now `[` · `]`; Shift + `-` · `+` changes icon size.

Enlarged names may overlap.

## Marker guide

Room names sit at a fixed spot inside their room; a room too narrow for its name gets a short line to a spot outside. Icons and item names may cover room names. Puzzle markers show the name of the device (for example Book Stand, Fire Hydrant), not the item it needs. The same item listed twice at one spot is named once. Common item and enemy icons that fall on a key item or puzzle icon are hidden, and nothing is drawn under the legend or the readouts.

Orange `!` marks puzzles; purple `?` marks events (Live Selection scenes and the spots where a movie or long cutscene starts). Events can spoil the story, so they start off (`6`) and disappear once you have passed them. Event markers have no name (the `H` toggle does not add one), only the purple `?`. Event markers show approximate locations, not choice outcomes. Only scenes that can be found in the game data are marked (some scenes are left out because the game gives no way to tell whether you have seen them); scenes that start by themselves when you enter a room are marked at the room's approximate centre.

Some monster encounters may be missing. Only some upcoming Nemesis appearances are shown. Items dropped by Nemesis are not shown.



Created by 커트씨. Unofficial fan mod, unaffiliated with Capcom or Classic REbirth.
