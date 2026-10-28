# Icons

`icons/*.png` are 32×32 RGBA pixel-art icons drawn for this mod: items, facilities, legend symbols, puzzle/Live Selection markers and 12 enemy types. They are newly drawn, not resized game sprites. Original RE3 inventory images and [Evil Resource enemy images](https://www.evilresource.com/resident-evil-3-nemesis/enemies) served as identity references only and are not included.

- `manifest.json`: crop bounds, item IDs and replacements used by `tools/pack_icons.py`.
- `icon-hashes.json`: hashes of the packed PNGs.
- `key-sources.json`, `monster-sources.json`: reference sources for key and enemy icons.
- `previews/key-resolution-v1/C/`: key icon masters checked by `tests/test_icons.py`.
- `icons-preview.png`, `monster-heads-preview.png`: static previews, not game screenshots.

The source artwork sheets used by `tools/pack_icons.py` are not included; the packed icons in `icons/` are the build input.
