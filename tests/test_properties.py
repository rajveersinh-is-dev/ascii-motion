"""Property-based invariant tests for ascii-motion engine."""

import numpy as np

from ascii_motion.config import RenderConfig
from ascii_motion.core.converter import FrameConverter
from ascii_motion.core.dithering import apply_bayer_dithering, apply_floyd_steinberg_dithering
from ascii_motion.core.perceptual import adjust_tone


def test_invariant_characters_belong_to_ramp() -> None:
    """Property: All characters in an AsciiFrame must originate from the specified ramp."""
    custom_ramp = " .oO8@"
    cfg = RenderConfig(width=50, custom_ramp=custom_ramp, edge_mode="none")
    conv = FrameConverter(cfg)

    # Test random noise images across various distributions
    np.random.seed(42)
    for _ in range(5):
        random_img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        frame = conv.convert_frame(random_img)

        unique_in_frame = set(frame.chars.flatten())
        allowed = set(custom_ramp)
        assert unique_in_frame.issubset(allowed)


def test_invariant_dimensions_match_config() -> None:
    """Property: Output grid width strictly equals config.width, and height is >= 1."""
    for width in [10, 37, 80, 123, 200]:
        cfg = RenderConfig(width=width)
        conv = FrameConverter(cfg)
        test_img = np.zeros((120, 200, 3), dtype=np.uint8)
        frame = conv.convert_frame(test_img)
        assert frame.width == width
        assert frame.height >= 1
        assert frame.chars.shape == (frame.height, width)
        assert frame.colors.shape == (frame.height, width, 3)


def test_invariant_tone_mapping_bounds() -> None:
    """Property: Adjusted luminance is strictly bounded within [0.0, 1.0] under extreme values."""
    grid = np.linspace(-1.0, 2.0, 1000, dtype=np.float32)

    # Test extreme multiplier combinations
    for b in [0.0, 0.1, 1.0, 5.0, 100.0]:
        for c in [0.0, 0.5, 1.0, 5.0, 50.0]:
            for g in [0.1, 0.5, 1.0, 2.0, 10.0]:
                for inv in [False, True]:
                    out = adjust_tone(grid, brightness=b, contrast=c, gamma=g, invert=inv)
                    assert np.all(out >= 0.0), f"Negative value found with b={b}, c={c}, g={g}"
                    assert np.all(out <= 1.0), f"Value > 1.0 found with b={b}, c={c}, g={g}"
                    assert not np.any(np.isnan(out)), f"NaN found with b={b}, c={c}, g={g}"


def test_invariant_dithering_bounds() -> None:
    """Property: Dithered luminance grids remain bounded in [0.0, 1.0]."""
    np.random.seed(123)
    grid = np.random.uniform(0.0, 1.0, (24, 24)).astype(np.float32)

    for levels in [2, 5, 10, 70]:
        bayer_out = apply_bayer_dithering(grid, num_levels=levels, strength=1.0)
        assert np.all(bayer_out >= 0.0)
        assert np.all(bayer_out <= 1.0)

        fs_out = apply_floyd_steinberg_dithering(grid, num_levels=levels, strength=1.0)
        assert np.all(fs_out >= 0.0)
        assert np.all(fs_out <= 1.0)
