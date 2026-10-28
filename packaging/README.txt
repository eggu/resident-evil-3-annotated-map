RE3 Annotated Map - Survivor's Notes — 한국어

## 설치 (Windows · Steam)

### 1. 게임 준비

1. Steam에서 **Resident Evil 3 Nemesis (1999)**를 설치합니다.
2. [Mulderland](https://www.mulderland.com/en/games/resident-evil-3-nemesis)에서 **Steam Enhancement Pack**을 받아 안내에 따라 설치합니다. 지도 모드에 필요한 Classic REbirth와 모드 로더, HD 텍스처를 함께 준비할 수 있습니다.
3. 설치 항목에서 **Graphical improvements**(HD 텍스처)를 켭니다. 이미 이 팩을 사용 중이면 다시 설치하지 않아도 됩니다.

### 2. 게임 폴더 열기

Steam 라이브러리에서 게임을 마우스 오른쪽 버튼으로 클릭하고 **관리 → 로컬 파일 탐색**을 선택합니다. 열린 폴더 안의 **`rebirth` 폴더**를 여세요. `BIOHAZARD(R) 3 PC.exe`가 보이면 맞는 위치입니다.

### 3. 지도 모드 복사

1. 게임을 종료합니다.
2. 지도 모드 ZIP을 마우스 오른쪽 버튼으로 클릭하고 **모두 압축 풀기**를 선택합니다. `Source code`는 설치 파일이 아닙니다.
3. 압축을 푼 폴더의 **`RE3.AnnotatedMap.asi` 파일과 `hires` 폴더**를 위에서 연 `rebirth` 폴더에 복사합니다. 기존 `hires` 폴더와 합치고 같은 이름의 파일은 교체합니다. 다른 HD 모드를 사용한다면 먼저 기존 `hires` 폴더를 백업하세요.
4. 평소처럼 Steam에서 게임을 실행하고 **Classic REbirth**로 시작합니다. 게임 안에서 지도를 열면 표시됩니다. 한글 번역 모드는 필수가 아닙니다.

복사 후 폴더 모양은 다음과 같습니다.

```text
rebirth/
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
| 7 | 적(기본 끔) |
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

## Installation (Windows · Steam)

### 1. Prepare the game

1. Install **Resident Evil 3 Nemesis (1999)** in Steam.
2. Download the **Steam Enhancement Pack** from [Mulderland](https://www.mulderland.com/en/games/resident-evil-3-nemesis) and follow its installer. It provides Classic REbirth, the mod loader and HD textures needed for the map mod.
3. Enable **Graphical improvements** (HD textures). If you already use this pack, you do not need to reinstall it.

### 2. Open the game folder

Right-click the game in your Steam library and choose **Manage → Browse local files**. Open the **`rebirth` folder** inside. You should see `BIOHAZARD(R) 3 PC.exe` there.

### 3. Copy the map mod

1. Close the game.
2. Right-click the map mod ZIP and choose **Extract All**. `Source code` is not the install package.
3. Copy **`RE3.AnnotatedMap.asi` and the `hires` folder** from the extracted files into `rebirth`. Merge the folders and replace matching files. If you use another HD mod, back up your existing `hires` folder first.
4. Launch the game through Steam as usual and choose **Classic REbirth**. Open the in-game map to see the annotations. The Korean translation mod is not required.

The resulting folder should look like this:

```text
rebirth/
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
| 7 | Enemies (off by default) |
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
