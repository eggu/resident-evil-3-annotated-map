# Notice

This project's source code is released under the [MIT License](LICENSE). It covers only this repository's own code, data and documentation.

- **Resident Evil / Biohazard** and related names, characters, item designs and game data are trademarks and copyrighted works of Capcom Co., Ltd. This is an unofficial fan mod, not affiliated with or endorsed by Capcom or the Classic REbirth project. No game executable, room scripts, original textures or audio are included. Item, door, enemy and puzzle positions and flags were analyzed from a legally installed PC game; only derived overlay tables are included.
- **Room script decompilation**: [BioRand biohazard-utils](https://github.com/IntelOrca/biorand) (MIT) was used as an external tool. Its code is not included.
- **Addresses and item identifiers**: consulted from [RE3-Mod-SDK](https://github.com/Gemini-Loboto3/RE3-Mod-SDK). The ROFS reader in `tools/rofs.py` follows its archive format.
- **Room names and contents**: cross-checked against [Evil Resource](https://www.evilresource.com/resident-evil-3-nemesis). The site's text and images are not included.
- **Icons**: pixel art drawn for this mod with AI assistance. Original inventory images and Evil Resource enemy images were used as visual reference only. See [assets/README.md](assets/README.md).
- **Fonts**: map labels and the legend are rasterized with Pretendard Medium (SIL Open Font License 1.1, https://github.com/orioncactus/pretendard). The font and its license are in `fonts/`.
- **Build and test tools**: Zig (via `ziglang`), Capstone, Unicorn, Pillow and NumPy are installed separately under their own licenses.
