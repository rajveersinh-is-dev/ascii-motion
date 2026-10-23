"""Configuration models and presets for ascii-motion."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

ResolutionPreset = Literal["low", "medium", "high", "ultra", "custom"]
ColorStyle = Literal["monochrome", "color", "green", "amber", "custom"]
DitherMode = Literal["none", "bayer", "floyd_steinberg"]
EdgeMode = Literal["none", "sobel"]

PRESET_WIDTHS: dict[str, int] = {
    "low": 60,
    "medium": 100,
    "high": 160,
    "ultra": 240,
}


class RenderConfig(BaseModel):
    """Configuration for rendering video frames to ASCII."""

    # Resolution & Geometry
    preset: ResolutionPreset = "medium"
    width: int = Field(default=100, ge=10, le=400, description="Character columns")
    height: int | None = Field(
        default=None, ge=5, le=300, description="Character rows (None = auto)"
    )
    char_aspect_ratio: float = Field(
        default=0.5,
        gt=0.1,
        lt=2.0,
        description="Width-to-height ratio of a single character cell (typically ~0.5 for monospace fonts)",
    )

    # Frame Rate & Trimming
    target_fps: float | None = Field(
        default=None,
        gt=0.1,
        le=120.0,
        description="Target rendering FPS (None = source FPS)",
    )
    trim_start: float = Field(default=0.0, ge=0.0, description="Start time in seconds")
    trim_end: float | None = Field(default=None, gt=0.0, description="End time in seconds")
    max_duration: float | None = Field(
        default=None, gt=0.0, description="Maximum output duration in seconds"
    )
    max_frames: int | None = Field(default=None, ge=1, description="Maximum frame count limit")

    # Visual Adjustments
    brightness: float = Field(default=1.0, ge=0.1, le=3.0, description="Brightness multiplier")
    contrast: float = Field(default=1.0, ge=0.1, le=3.0, description="Contrast factor")
    gamma: float = Field(default=1.0, ge=0.1, le=3.0, description="Gamma correction exponent")
    invert: bool = Field(default=False, description="Invert luminance mapping")

    # Character Ramp
    ramp_name: str = Field(
        default="standard_10",
        description="Name of predefined character ramp (e.g. 'standard_10', 'standard_70', 'blocks')",
    )
    custom_ramp: str | None = Field(
        default=None,
        description="User-defined character ramp string from dark to light",
    )

    # Color & Palette
    style: ColorStyle = Field(default="color", description="Rendering visual style")
    foreground_color: str = Field(
        default="#FFFFFF",
        description="Hex foreground color for monochrome/custom style",
    )
    background_color: str = Field(
        default="#000000",
        description="Hex background color",
    )

    # Advanced Quality Features
    dithering: DitherMode = Field(default="none", description="Dithering algorithm")
    edge_mode: EdgeMode = Field(default="none", description="Edge enhancement mode")
    edge_strength: float = Field(
        default=0.5, ge=0.0, le=2.0, description="Edge enhancement strength"
    )
    temporal_smoothing: float = Field(
        default=0.0,
        ge=0.0,
        le=0.9,
        description="Temporal stabilization factor (0.0 = disabled, up to 0.9 = heavy)",
    )

    @field_validator("custom_ramp")
    @classmethod
    def validate_custom_ramp(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.replace("\r", "").replace("\n", "")
            if len(set(cleaned)) < 2:
                raise ValueError("Custom ramp must contain at least 2 distinct characters.")
            return cleaned
        return v

    def apply_preset(self) -> None:
        """Update width if preset is not custom."""
        if self.preset in PRESET_WIDTHS:
            self.width = PRESET_WIDTHS[self.preset]
