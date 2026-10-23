"""Integration tests for the command-line interface."""

from pathlib import Path

import pytest

from ascii_motion.cli import main
from ascii_motion.utils.synthetic import create_synthetic_video


@pytest.fixture(scope="module")
def cli_test_video(tmp_path_factory: pytest.TempPathFactory) -> Path:
    temp_dir = tmp_path_factory.mktemp("cli_test")
    p = temp_dir / "cli_sample.mp4"
    create_synthetic_video(p, duration=1.0, fps=15.0, width=320, height=180)
    return p


def test_cli_help() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0


def test_cli_save_config(tmp_path: Path) -> None:
    cfg_file = tmp_path / "saved_config.json"
    code = main(["--save-config", str(cfg_file), "--preset", "high", "--style", "green"])
    assert code == 0
    assert cfg_file.is_file()
    assert '"preset": "high"' in cfg_file.read_text(encoding="utf-8")


def test_cli_export_with_report(cli_test_video: Path, tmp_path: Path) -> None:
    out_mp4 = tmp_path / "rendered.mp4"
    report_json = tmp_path / "report.json"

    code = main(
        [
            str(cli_test_video),
            "-o",
            str(out_mp4),
            "--preset",
            "low",
            "--style",
            "color",
            "--report",
            str(report_json),
            "--quiet",
        ]
    )
    assert code == 0
    assert out_mp4.is_file()
    assert report_json.is_file()
    assert '"format": "mp4"' in report_json.read_text(encoding="utf-8")


def test_cli_nonexistent_input() -> None:
    code = main(["does_not_exist_xyz.mp4", "-o", "out.mp4"])
    assert code != 0
