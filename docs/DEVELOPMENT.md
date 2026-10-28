# Development

`build.py` writes only `build/` and `dist/`. It never installs into the game.

```sh
python3 -m venv local/.venv
local/.venv/bin/pip install capstone unicorn==2.1.4 ziglang pillow numpy
local/.venv/bin/python build.py
```

`build.py` compiles `src/re3_map.c` with the pinned `src/assets.h` and packages the HD files in `build/hires/misc/`. A fresh clone cannot regenerate every HD file: the Disused Plant map header needs `assets/map/clock-header-reference.webp`, which comes from an installed HD texture pack and is not included.

## Data and assets

Room data comes from the game's room scripts: `tools/rofs.py` extracts the archives, an external SCD decompiler produces scripts, and `tools/extract_scd.py` → `build_room_data.py` → `decode_map.py` → `build_overlay.py` → `pack_icons.py` → `build_assets.py` regenerate the overlay. Extracted game files stay in `local/` and are never committed. `tools/gen_wiki.py` regenerates `docs/wiki/` from the compiled overlay.

## Tests

Tests read a legally owned `BIOHAZARD(R) 3 PC.exe` (SourceNext) and never modify it.

```sh
export RE3_GAME='/path/to/game'
export RE3_GAME_EXE="$RE3_GAME/BIOHAZARD(R) 3 PC.exe"
for t in tests/test_*.py; do local/.venv/bin/python "$t" || break; done
```

Unicorn tests execute the actual x86 map code and check overlay state, flags, scope, controls and primitive submission. They do not verify GPU output or behavior in a running game.
