"""Unit tests for RenderConfig model and validation."""

import pytest
from pydantic import ValidationError

from ascii_motion.config import PRESET_WIDTHS, RenderConfig


def test_default_config() -> None:
    cfg = RenderConfig()
    assert cfg.preset == "medium"
    assert cfg.width == 100
    assert cfg.char_aspect_ratio == 0.5
    assert cfg.style == "color"


def test_preset_application() -> None:
    cfg = RenderConfig(preset="ultra")
    cfg.apply_preset()
    assert cfg.width == PRESET_WIDTHS["ultra"]
    assert cfg.width == 240


def test_custom_ramp_validation() -> None:
    # Valid custom ramp
    cfg = RenderConfig(custom_ramp=" .:-+#")
    assert cfg.custom_ramp == " .:-+#"

    # Invalid: fewer than 2 distinct characters
    with pytest.raises(ValidationError):
        RenderConfig(custom_ramp="aaa")


def test_bounds_validation() -> None:
    # Width too small (< 10)
    with pytest.raises(ValidationError):
        RenderConfig(width=5)

    # Brightness negative or out of bounds (< 0.1)
    with pytest.raises(ValidationError):
        RenderConfig(brightness=0.0)
