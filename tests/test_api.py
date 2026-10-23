"""Integration tests for the FastAPI web backend."""

import io
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ascii_motion.api.app import app
from ascii_motion.utils.synthetic import create_synthetic_video


@pytest.fixture(scope="module")
def api_client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def api_test_video(tmp_path_factory: pytest.TempPathFactory) -> Path:
    temp_dir = tmp_path_factory.mktemp("api_test")
    p = temp_dir / "api_sample.mp4"
    create_synthetic_video(p, duration=1.0, fps=15.0, width=320, height=180)
    return p


def test_api_ramps(api_client: TestClient) -> None:
    res = api_client.get("/api/ramps")
    assert res.status_code == 200
    data = res.json()
    assert "standard_10" in data
    assert "blocks" in data


def test_api_sample_video(api_client: TestClient) -> None:
    res = api_client.get("/api/sample")
    assert res.status_code == 200
    data = res.json()
    assert "path" in data
    assert data["metadata"]["width"] == 640


def test_api_preview(api_client: TestClient, api_test_video: Path) -> None:
    res = api_client.post(
        "/api/preview",
        json={
            "video_path": str(api_test_video),
            "timestamp": 0.2,
            "config": {
                "preset": "low",
                "width": 50,
                "style": "color",
            },
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["width"] == 50
    assert len(data["lines"]) > 0


def test_api_upload_invalid_extension(api_client: TestClient) -> None:
    file_bytes = io.BytesIO(b"fake data")
    res = api_client.post(
        "/api/upload",
        files={"file": ("malicious.exe", file_bytes, "application/octet-stream")},
    )
    assert res.status_code == 400
    assert "Unsupported video format" in res.json()["detail"]


def test_api_convert_and_poll(api_client: TestClient, api_test_video: Path) -> None:
    res = api_client.post(
        "/api/convert",
        json={
            "video_path": str(api_test_video),
            "export_format": "html",
            "config": {
                "preset": "low",
                "width": 40,
                "max_frames": 4,
            },
        },
    )
    assert res.status_code == 200
    job_id = res.json()["job_id"]

    for _ in range(25):
        time.sleep(0.1)
        st = api_client.get(f"/api/jobs/{job_id}").json()
        if st["status"] in ("completed", "failed"):
            break

    assert st["status"] == "completed"
    assert st["output_available"] is True

    # Test download
    dl = api_client.get(f"/api/jobs/{job_id}/download")
    assert dl.status_code == 200
    assert len(dl.content) > 500
