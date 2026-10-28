RE3 Annotated Map - Survivor's Notes — 한국어

## 설치

1. **Classic REbirth**(바이오하자드 3용, 1.0.3에서 확인)를 먼저 설치합니다. [공식 다운로드](https://classicrebirth.com/index.php/downloads/resident-evil-3-classic-rebirth/)
2. 게임을 종료하고 [Releases](https://github.com/eggu/resident-evil-3-annotated-map/releases/latest)에서 `RE3-Annotated-Map-<버전>.zip`을 받아 압축을 풉니다. `Source code`는 설치 파일이 아닙니다.
3. **`RE3.AnnotatedMap.asi` 파일과 `hires` 폴더**를 `BIOHAZARD(R) 3 PC.exe`가 있는 게임 폴더에 복사합니다. 기존 `hires` 폴더가 있으면 합치고, 같은 이름의 파일은 교체합니다. 다른 HD 모드를 사용한다면 먼저 기존 `hires` 폴더를 백업하세요.
4. Classic REbirth로 게임을 실행하고 지도를 열면 표시됩니다. 한글 번역 모드는 필수가 아닙니다.

```text
게임 폴더/
├─ BIOHAZARD(R) 3 PC.exe
├─ RE3.AnnotatedMap.asi
└─ hires/
   └─ misc/
      └─ 지도 모드의 .webp 파일들
```

업그레이드할 때는 `RE3.AnnotatedMap.ini`를 지우지 마세요. 지도 표시 설정이 들어 있습니다.

제거: `RE3.AnnotatedMap.asi`, `.ini`, `.log`와 지도 모드 ZIP에 포함된 `.webp` 파일만 지우세요. 기존 HD 파일을 백업했다면 복원합니다. `hires` 폴더 전체를 지우면 다른 HD 모드도 영향을 받습니다.

## 단축키

지도 화면에서만 작동하며, 현재 상태가 범례에 표시됩니다.

| 키 | 동작 |
|---|---|
| 0 | 전체 표시 켜기/끄기 |
| 1 | 방 이름·타자기·아이템 상자 |
| 2 | 잠긴 문·필요한 열쇠 |
| 3 | 핵심 아이템 |
| 4 | 문서·지도 |
| 5 | 퍼즐·Live Selection |
| 6 | 일반 아이템(탄약·회복·리본·화약) |
| 7 | 적 |
| 8 | 방문한 방 → 공개된 방(지역 지도 획득) → 모든 방 |
| 9 | 한국어 / English |
| - / = (+), 숫자패드 - / + | 이름 크기 10%씩(50–150%) |
| Shift + 위 키 | 이름 불투명도 10%씩(10–100%) |

## 설정

지도 화면에서 바꾼 설정은 자동으로 저장됩니다. 설정 파일은 게임 폴더의 `RE3.AnnotatedMap.ini`입니다. 직접 편집하려면 게임을 종료한 뒤 메모장으로 여세요.

이름을 크게 하면 서로 겹칠 수 있습니다.

## 표시 안내

주황색 `!`는 퍼즐, 보라색 `?`는 Live Selection(선택 이벤트)입니다. 이벤트 표시는 대략적인 위치를 안내하며, 선택 결과는 알려주지 않습니다.

몬스터 표시는 일부 출현을 빠뜨릴 수 있습니다. 네메시스의 예정 출현 위치는 일부만 표시하며, 네메시스가 떨어뜨리는 아이템은 표시하지 않습니다.



RE3 Annotated Map - Survivor's Notes — English

## Installation

1. Install **Classic REbirth** for Resident Evil 3 first (tested with 1.0.3). [Official download](https://classicrebirth.com/index.php/downloads/resident-evil-3-classic-rebirth/)
2. Close the game. Download `RE3-Annotated-Map-<version>.zip` from [Releases](https://github.com/eggu/resident-evil-3-annotated-map/releases/latest) and extract it. `Source code` is not the install package.
3. Copy **`RE3.AnnotatedMap.asi` and the `hires` folder** into the game folder containing `BIOHAZARD(R) 3 PC.exe`. Merge with an existing `hires` folder and replace matching files. If you use another HD mod, back up your existing `hires` folder first.
4. Launch the game with Classic REbirth and open the map. The Korean translation mod is not required.

```text
game folder/
├─ BIOHAZARD(R) 3 PC.exe
├─ RE3.AnnotatedMap.asi
└─ hires/
   └─ misc/
      └─ the map mod's .webp files
```

Keep `RE3.AnnotatedMap.ini` when upgrading to preserve your map settings.

Uninstall: remove `RE3.AnnotatedMap.asi`, `.ini`, `.log` and only the `.webp` files included in the map ZIP. Restore backed-up HD files if applicable. Do not delete the entire `hires` folder: other HD mods also use it.

## Controls

Keys work on the map screen only. The legend shows the current state.

| Key | Action |
|---|---|
| 0 | All annotations on/off |
| 1 | Room names, typewriters and item boxes |
| 2 | Locked doors and required keys |
| 3 | Key items |
| 4 | Documents and maps |
| 5 | Puzzles and Live Selections |
| 6 | Common items (ammo, healing, ribbons, gunpowder) |
| 7 | Enemies |
| 8 | Visited → revealed by an area map → all rooms |
| 9 | Korean / English |
| - / = (+), numpad - / + | Name size in 10% steps (50–150%) |
| Shift + those keys | Name opacity in 10% steps (10–100%) |

## Settings

Changes made on the map are saved automatically to `RE3.AnnotatedMap.ini` in the game folder. Close the game before opening it in Notepad to edit it manually.

Enlarged names may overlap.

## Marker guide

Orange `!` marks puzzles; purple `?` marks Live Selections (choice events). Event markers show approximate locations, not choice outcomes.

Some monster encounters may be missing. Only some upcoming Nemesis appearances are shown. Items dropped by Nemesis are not shown.



Created by 커트씨. Unofficial fan mod, unaffiliated with Capcom or Classic REbirth.
