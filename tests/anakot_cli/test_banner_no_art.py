"""The banner ships no ASCII art.

The wordmark that used to print at the top of the CLI banner was 113 columns
of mixed-weight glyphs (U+2588 full blocks interleaved with U+2554/2557/255A/
255D box-drawing) whose rows were 106/109/110/113 columns wide from ragged
trailing whitespace. FiraCode Nerd Font draws those two glyph families at
different visual weights and the ragged rows sheared the letters out of
alignment, so the banner was unreadable. It is now removed outright; a skin
may still set `banner_logo` to opt back in.

The braille caduceus was 15x30 of scattered dots and is gone for the same
reason.
"""

from pathlib import Path

import anakot_cli.banner as banner


def test_no_builtin_wordmark():
    assert banner.ANAKOT_AGENT_LOGO == ""


def test_no_caduceus_hero():
    assert banner.ANAKOT_CADUCEUS == ""


def test_module_ships_no_block_or_box_glyph_art():
    """Guard against art creeping back in as module-level literals."""
    art = [
        line
        for name in dir(banner)
        if name.isupper() and isinstance(getattr(banner, name), (str, tuple, list))
        for line in (getattr(banner, name) if isinstance(getattr(banner, name), str)
                     else "".join(str(x) for x in getattr(banner, name)))
    ]
    joined = "".join(art)
    assert "█" not in joined
    assert not any(ch in joined for ch in "╔╗╚╝║═")
    assert not any(0x2800 <= ord(ch) <= 0x28FF for ch in joined), "braille art crept back in"


def test_no_builtin_skin_ships_banner_art():
    """No built-in skin may set banner_logo / banner_hero.

    Four skins (ares, poseidon, sisyphus, charizard) carried 113-column
    ASCII wordmarks plus braille hero glyphs. FiraCode Nerd Font renders
    them as unreadable mush, and they are ~8 lines of data per skin that
    no test exercised.
    """
    from anakot_cli.skin_engine import _BUILTIN_SKINS, load_skin

    for name in _BUILTIN_SKINS:
        skin = load_skin(name)
        assert skin.banner_logo == "", f"{name} still ships a banner_logo"
        assert skin.banner_hero == "", f"{name} still ships a banner_hero"


def test_skin_engine_module_has_no_art_glyphs():
    """Guard against block/box/braille art creeping back into a skin."""
    from anakot_cli import skin_engine

    src = Path(skin_engine.__file__).read_text(encoding="utf-8")

    assert not any(ch in src for ch in "█░▀▄▌▐▁▂▃▄▅▆▇"), "block art crept back in"
    assert not any(ch in src for ch in "╔╗╚╝║═╠╣╦╩╬"), "box-drawing art crept back in"
    assert not any(0x2800 <= ord(ch) <= 0x28FF for ch in src), "braille art crept back in"


def test_skin_supplied_logo_still_accepted():
    """Opt-in art via a skin's banner_logo must remain a supported path."""
    from anakot_cli.skin_engine import _build_skin_config

    skin = _build_skin_config({"name": "art", "banner_logo": "[bold #ff0000]ART[/]"})

    assert skin.banner_logo == "[bold #ff0000]ART[/]"
