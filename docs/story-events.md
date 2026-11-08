# Story events (spoiler scenes)

Generated from `data/story-events.json` (`tools/build_events.py`). Markers are the purple `?` of the [6] Events toggle (kind `live`, ids from 20; ids 0-9 are the Live Selections). Event markers have no name on the map (only the diamond). Trigger = the scene's SCE_EVENT area (centre drawn); room = the scene starts when the room loads (approximate room anchor). Done-flag `bank:bit` is set by the scene itself; the marker is hidden once it is 1.

| id | 방 / Room | RDT | 자리 / Spot | 완료 플래그 / Done-flag | 영상·컷·음성 / movies·cuts·voices |
|---|---|---|---|---|---|
| 20 | 영업소 창고 / Sales Office Storeroom | R11C | room anchor (starts on entering) | 3:99 | 1 / 1 / 1 |
| 21 | 노면전차 승강장 / Cable Car Area | R20B | trigger area x=-16009, z=-2735, w=4550, d=3280 (aot 7) | 3:202 | 0 / 16 / 9 |
| 22 | 노면전차 / Cable Car Rear Carriage | R20C | trigger area x=-1259, z=-26295, w=770, d=4600 (aot 10) | 3:30 | 0 / 5 / 7 |
| 23 | 노면전차 / Cable Car Rear Carriage | R20C | trigger area x=-7494, z=-26151, w=800, d=4500 (aot 11) | 3:31 | 0 / 3 / 7 |
| 24 | 주유소 매점 / Gas Station Shop | R20D | trigger area x=-26206, z=-17899, w=5480, d=4700 (aot 4) | 3:43 | 0 / 5 / 1 |
| 24 | 주유소 매점 / Gas Station Shop | R20D | trigger area x=-26206, z=-17899, w=5480, d=4700 (aot 4) | 3:45 | 0 / 9 / 10 |
| 25 | 주유소 매점 / Gas Station Shop | R20D | trigger area x=-26312, z=-21941, w=4800, d=2800 (aot 5) | 3:44 | 0 / 6 / 4 |
| 26 | 주유소 매점 / Gas Station Shop | R20D | trigger area x=-22053, z=-17619, w=3790, d=3800 (aot 6) | 3:46 | 0 / 7 / 2 |
| 27 | 주유소 / Gas Station | R217 | trigger area x=-7040, z=-16894, w=5750, d=5264 (aot 9) | 3:157 | 1 / 3 / 3 |
| 27 | 주유소 / Gas Station | R217 | trigger area x=-7040, z=-16894, w=5750, d=5264 (aot 9) | 3:157 | 1 / 4 / 0 |
| 28 | 식당 / Dining Room | R302 | trigger area x=-10394, z=-6764, w=4800, d=1800 (aot 3) | 3:167 | 0 / 8 / 12 |
| 29 | 작은 서재 / Small Library | R307 | trigger area x=-26200, z=-17000, w=7800, d=6900 (aot 8) | 3:39 | 0 / 6 / 7 |
| 30 | 중앙 홀 / Main Hall | R316 | trigger area x=-11237, z=-15462, w=4500, d=10900 (aot 2) | 3:122 | 0 / 7 / 0 |
| 31 | 묘지 / Graveyard | R415 | trigger area x=5466, z=-8117, w=7800, d=4500 (aot 12) | 3:196 | 1 / 2 / 0 |
| 32 | 묘지 / Graveyard | R415 | trigger area x=5845, z=-14469, w=7500, d=5400 (aot 13) | 3:196 | 1 / 2 / 0 |
| 33 | 묘지 / Graveyard | R415 | trigger area x=5745, z=-1919, w=7500, d=5400 (aot 14) | 3:196 | 1 / 2 / 0 |
| 34 | 공원 골목 / Park Alleyway | R417 | room anchor (starts on entering) | 3:187 | 1 / 1 / 0 |
| 35 | 처리실 입구 / Treatment Room Entry | R508 | trigger area x=-6771, z=-27715, w=8271, d=9215 (aot 10) | 3:183 | 0 / 6 / 0 |
| 35 | 처리실 입구 / Treatment Room Entry | R508 | trigger area x=-6771, z=-27715, w=8271, d=9215 (aot 10) | 3:183 | 0 / 6 / 0 |
| 36 | 헬기 착륙장 / Helicopter Landing Zone | R50E | trigger area x=-21037, z=-21154, w=6500, d=1800 (aot 0) | 0:17 | 0 / 4 / 8 |

## Found but not placed

| 방 / Room | RDT | script | 이유 / Reason |
|---|---|---|---|
| T자 쓰레기통 골목 / 'T' Dumpster Alley | R10D | main_0B (trigger aot 1) | the scene sets no persistent flag, so it cannot be hidden once played (movies 0, cuts 7, voices 0) |
| 노면전차 / Cable Car Rear Carriage | R215 | main_12 (trigger aot 6) | the scene sets no persistent flag, so it cannot be hidden once played (movies 1, cuts 1, voices 3) |
| 노면전차 / Cable Car Rear Carriage | R215 | main_17 (on room load) | starts when the room loads and sets no persistent flag (movies 1, cuts 0, voices 0) |
| 노면전차 / Cable Car Rear Carriage | R215 | main_34 (on room load) | starts when the room loads and sets no persistent flag (movies 1, cuts 0, voices 0) |
| 시계실 / Clock Room | R309 | main_46 (trigger aot 21) | the scene sets no persistent flag, so it cannot be hidden once played (movies 0, cuts 21, voices 0) |
| 30D / 30D | R30D | main_08 (on room load) | starts when the room loads and sets no persistent flag (movies 1, cuts 21, voices 5) |
| 처리실 입구 / Treatment Room Entry | R508 | main_04 (on room load) | starts when the room loads and sets no persistent flag (movies 1, cuts 1, voices 1) |
| 레일 캐논실 / Rail Cannon Room | R50D | main_19 (trigger aot 2) | the scene sets no persistent flag, so it cannot be hidden once played (movies 0, cuts 6, voices 3) |

Not extracted by design: Nemesis appearances and other enemy introductions stay enemy markers; Live Selections keep their own data (`data/live-selections.json`); puzzle devices stay puzzles.
