"""mapdata inspect writes a point as people say it (DMT-2)."""
from mapdata.__main__ import place_words


def test_north_and_east():
    assert place_words(68.234, 14.568) == "68.234 north, 14.568 east"


def test_south_and_west():
    assert place_words(-90.0, 0.0) == "90.0 south, 0.0 east"
    assert place_words(-16.84, -179.995) == "16.84 south, 179.995 west"


def test_inspect_reads_a_format_2_pack(tmp_path, capsys):
    import argparse

    import shapely

    from mapcore.packs import coords, pack, selfcheck, tiles
    from mapdata.__main__ import cmd_inspect

    path = tmp_path / "t.pack"
    w = pack.PackWriter(path)
    numbers = w.add_features(selfcheck.sample_features())
    square = coords.encode(coords.rings_of(shapely.box(0, 45, 10, 55)))
    w.add_tile(3, 4, 6, [(numbers["test:regions:3"], tiles.COMPACT, square),
                         (numbers["test:countries:3"], tiles.COVERED, b"")])
    w.finish(selfcheck.MANIFEST, selfcheck.ATTRIBUTION, selfcheck.LAYERS)
    assert cmd_inspect(argparse.Namespace(pack=str(path), lat=50.0, lon=5.0)) == 0
    assert capsys.readouterr().out.splitlines() == [
        "At 50.0 north, 5.0 east, smallest first:",
        "Country 3: countries, test area, 1,003 km2, test:countries:3.",
        "Région 3: regions, test area, 1,003 km2, test:regions:3.",
    ]
    assert cmd_inspect(argparse.Namespace(pack=str(path), lat=50.0, lon=12.0)) == 0
    assert capsys.readouterr().out.splitlines() == [
        "At 50.0 north, 12.0 east, smallest first:",
        "Country 3: countries, test area, 1,003 km2, test:countries:3.",
    ]
