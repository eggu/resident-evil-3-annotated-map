# RE3 Annotated Map - Survivor's Notes — Resident Evil 3 (1999)

English | [한국어](README.md)

<p align="center"><img src="docs/logo.png" alt="RE3 Annotated Map — Survivor’s Notes" width="320"></p>

A Korean/English ASI map mod for the original Resident Evil 3 PC release (SourceNext `BIOHAZARD(R) 3 PC.exe` + Classic REbirth 1.0.3). Adds room names, locked doors and keys, items, documents/maps, puzzles/Live Selections, typewriters, item boxes and monsters to the game's map. Not for the 2020 remake.

- Annotations appear on the game's own map. Picked-up items, opened doors, completed puzzles and defeated monsters disappear from the map.
- Choose visited rooms, rooms revealed by an area map, or all rooms.
- Pixel icons represent items, facilities and monsters.

## Screenshots

![Uptown — all rooms, enemies on](docs/screenshots/1.png)

| | Visited rooms | All rooms |
|---|---|---|
| Zoomed in | ![Uptown zoomed in — visited rooms](docs/screenshots/2-1-uptown-zoom-in-visited.png) | ![Uptown zoomed in — all rooms](docs/screenshots/2-2-uptown-zoom-in-all.png) |
| Zoomed out | ![Uptown zoomed out — visited rooms](docs/screenshots/3-1-uptown-zoom-out-visited.png) | ![Uptown zoomed out — all rooms](docs/screenshots/3-2-uptown-zoom-out-all.png) |

![Around the Uptown store room — puzzles and enemies](docs/screenshots/4.png)

## Visibility and defaults

A new configuration starts in **English, name size 100%, opacity 70%, visited rooms only, with only Rooms on**. Press `9` for Korean and `2`–`7` to turn on other categories. Press `8` to change scope. **All rooms** reveals unexplored rooms and items and contains spoilers.

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

## Wiki and support

[English wiki](docs/wiki/README.en.md) · [한국어 위키](docs/wiki/README.md): rooms, locks/keys, items, puzzles/events, documents/maps, save points and monsters. Tables contain spoilers.

When reporting an issue, describe the location and what is missing or incorrect, with a screenshot.

## Build

To build from source, see the [development guide](docs/DEVELOPMENT.md).

## Other map mods

- [RE1 Annotated Map - Survivor's Notes](https://github.com/eggu/resident-evil-annotated-map) — Resident Evil (1996)
- [RE2 Annotated Map - Survivor's Notes](https://github.com/eggu/resident-evil-2-annotated-map) — Resident Evil 2 (1998)

## Credits and rights

Created by **커트씨**. An unofficial fan mod, unaffiliated with Capcom or Classic REbirth. Source code is under the [MIT License](LICENSE). References and font credits are listed in [NOTICE](NOTICE.md).
