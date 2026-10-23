"""Unit tests for character ramps and glyph density evaluation."""

from ascii_motion.core.ramps import (
    PREDEFINED_RAMPS,
    build_calibrated_ramp,
    get_ramp,
    measure_glyph_densities,
)


def test_predefined_ramps_exist() -> None:
    assert "standard_10" in PREDEFINED_RAMPS
    assert "standard_70" in PREDEFINED_RAMPS
    assert "blocks" in PREDEFINED_RAMPS
    assert "minimal" in PREDEFINED_RAMPS
    assert "matrix" in PREDEFINED_RAMPS


def test_get_ramp_default() -> None:
    ramp = get_ramp("standard_10")
    assert ramp == " .:-=+*#%@"
    assert len(ramp) == 10


def test_get_ramp_custom_and_invert() -> None:
    custom = " .oO@"
    ramp = get_ramp(custom=custom, invert=False)
    assert ramp == " .oO@"

    inverted = get_ramp(custom=custom, invert=True)
    assert inverted == "@Oo. "


def test_measure_glyph_densities() -> None:
    # Space should have 0 density
    densities = measure_glyph_densities(" @")
    assert len(densities) == 2
    # First character should have lower density than second
    ch_low, d_low = densities[0]
    ch_high, d_high = densities[1]
    assert ch_low == " "
    assert d_low == 0.0
    assert ch_high == "@"
    assert d_high > 0.0


def test_build_calibrated_ramp() -> None:
    calibrated = build_calibrated_ramp(" #.")
    assert len(calibrated) == 3
    # Space should be first
    assert calibrated[0] == " "
