"""Terminal playback exporter using ANSI escape codes and paced frame timing."""

from __future__ import annotations

import sys
import time
from collections.abc import Iterable

from ascii_motion.core.color import ANSI_RESET
from ascii_motion.core.converter import AsciiFrame

CURSOR_HIDE = "\033[?25l"
CURSOR_SHOW = "\033[?25h"
CURSOR_HOME = "\033[H"
CLEAR_SCREEN = "\033[2J"


def play_in_terminal(
    frames: Iterable[AsciiFrame],
    fps: float,
    background_hex: str | None = None,
    loop: bool = False,
) -> int:
    """Stream and display ASCII frames directly in the terminal in real time.

    Args:
        frames: Iterable or generator of rendered AsciiFrame objects.
        fps: Target frames per second for playback pacing.
        background_hex: Optional hex background color.
        loop: Whether to loop cached frames (only applicable if frames is a list).

    Returns:
        Number of frames displayed.
    """
    is_tty = sys.stdout.isatty()
    frame_interval = 1.0 / max(fps, 1.0)
    frame_count = 0

    if not is_tty:
        # Non-interactive mode (e.g. piped to file or CI)
        for frame in frames:
            sys.stdout.write(frame.to_ansi(background_hex=background_hex) + "\n")
            frame_count += 1
        sys.stdout.flush()
        return frame_count

    # Interactive TTY playback
    try:
        # Hide cursor and clear screen once
        sys.stdout.write(CURSOR_HIDE + CLEAR_SCREEN)
        sys.stdout.flush()

        cached_frames: list[AsciiFrame] = [] if loop else []
        keep_playing = True

        while keep_playing:
            source = cached_frames if (loop and cached_frames) else frames
            next_frame_time = time.perf_counter()

            for frame in source:
                if loop and not cached_frames:
                    cached_frames.append(frame)

                # Move cursor home and draw frame
                ansi_output = frame.to_ansi(background_hex=background_hex)
                sys.stdout.write(CURSOR_HOME + ansi_output)
                sys.stdout.flush()
                frame_count += 1

                # Frame timing pacing
                next_frame_time += frame_interval
                now = time.perf_counter()
                sleep_duration = next_frame_time - now
                if sleep_duration > 0:
                    time.sleep(sleep_duration)
                else:
                    # Dropping sleep if falling behind
                    next_frame_time = now

            if not loop:
                keep_playing = False

    except KeyboardInterrupt:
        pass
    finally:
        # Restore terminal state: show cursor, reset styles, new line
        sys.stdout.write(CURSOR_SHOW + ANSI_RESET + "\n")
        sys.stdout.flush()

    return frame_count
