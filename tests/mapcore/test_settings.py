

def test_every_number_setting_fits_its_step():
    """P2-T17m: a number box goes in whole numbers unless its setting gives a step, such as the
    beacon's 0.5 seconds; the desktop showed 0 for 0.5 in a whole number box. The smallest, the
    largest and the default are each a whole number of steps from the smallest."""
    from mapcore import settings as settings_mod

    for f in settings_mod.fields().values():
        if f["kind"] != "number":
            continue
        step = f.get("step", 1)
        for value in (f["max"], f["default"]):
            steps = (value - f["min"]) / step
            assert steps == int(steps), (f["id"], value)
        if step == 1:
            assert f["min"] == int(f["min"]) and f["max"] == int(f["max"]), f["id"]
