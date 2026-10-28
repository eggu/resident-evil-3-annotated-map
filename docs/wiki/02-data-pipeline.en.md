# Data and table notation

[한국어](README.md) | [English](README.en.md) · [Index](README.en.md)

Spoilers. Rows are conditional variants from current data/overlay.json, not unique item counts or simultaneous spawns. Additional runtime gates apply; see the notes and technical documents.

Pipeline: original RDT → external SCD decompiler → room data/call predicates → map coordinates/markers → atlas/ASI. Regenerate with `python3 tools/gen_wiki.py`.

`page:idx` = logical map cell, not output pixels or a floor label. `Rxxx` = source room script. `sets`: 1=DATA_J, 2=DATA_AJ, 3=both. Coordinates are logical map coordinates, not PC/console output resolution.

`guard` is raw compiled JSON: outer groups are AND, alternatives inside each group are OR; each [bank,bit,value] is one test. [] has no compiled guard, but pickup/kill/scope/floor/runtime gates still apply. Special banks encode additional comparisons; do not interpret every triple as a literal save flag.

`flag` = pickup flag; `lock` = unlock identifier; `kill` = kill flag (255 means no ordinary kill flag). `item` is a decimal item ID. `use`/`event` and anchors identify runtime puzzle/event handling. Retain raw metadata to avoid implying complete runtime semantics.
