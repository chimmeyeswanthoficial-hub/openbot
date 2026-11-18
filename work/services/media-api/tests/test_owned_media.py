"""Real owned media. No mocked output, no hostile/customer security acceptance."""

from __future__ import annotations

import io
import json
import os
import subprocess
import threading
import time
import zipfile
from pathlib import Path

import pytest
from ffmpeg_runner import MediaError, run_ffmpeg_stream, run_process, tool_paths
from media_worker import validate
from owned_media import MediaEngine


@pytest.fixture(scope="session")
def owned_video(tmp_path_factory):
    tools = tool_paths()
    folder = tmp_path_factory.mktemp("synthetic-video")
    target = folder / "owned.mp4"
    env = {**os.environ, "LD_LIBRARY_PATH": os.environ.get("MEDIA_LIBRARY_PATH", "")}
    subprocess.run(
        [
            tools["ffmpeg"],
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=160x96:rate=10:duration=2.4",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=2.4",
            "-threads",
            "1",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(target),
        ],
        check=True,
        env=env,
        timeout=20,
    )
    return target


def put(engine, content):
    with (engine.directory / "input.media").open("xb") as dest:
        for offset in range(0, len(content), 65536):
            engine.append(dest, content[offset : offset + 65536])


@pytest.mark.parametrize(
    "operation,options",
    [
        ("audio", {"format": "wav"}),
        ("convert", {"format": "mp3"}),
        ("compress", {"bitrate": "64k"}),
        ("cut", {"start": 0.5, "duration": 0.7}),
        ("scale", {"width": 80, "height": 48}),
        ("captions", {"text": "Owned sample: 42% {not an expression}"}),
        ("split", {"segment_seconds": 1}),
        ("concat", {}),
    ],
)
def test_real_edits_are_decoded_and_scoped(tmp_path, owned_video, operation, options):
    root = tmp_path / "spool"
    root.mkdir(mode=0o700)
    content = owned_video.read_bytes()
    if operation == "concat":
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            for i in range(2):
                archive.writestr(f"part-{i:02}.mp4", content)
        content = buf.getvalue()
    with MediaEngine(root, timeout=30) as engine:
        put(engine, content)
        result = engine.run(operation, options)
        assert result["path"].stat().st_size > 44
        assert all(p["reaped"] for p in result["processes"])
        assert all(p["stderr_bytes"] <= 65536 for p in result["processes"])
        assert all(p["decode_readback"] for p in result["outputs"])
        assert result["hostile_isolation_accepted"] is False
        if operation == "split":
            assert len(result["outputs"]) == 3
            with zipfile.ZipFile(result["path"]) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                assert manifest["segments"] == result["outputs"]
                assert len(archive.namelist()) == 4
        if operation == "cut":
            assert abs(result["outputs"][0]["duration"] - 0.7) < 0.2
        if operation == "scale":
            video = next(s for s in result["outputs"][0]["streams"] if s["type"] == "video")
            assert (video["width"], video["height"]) == (80, 48)
        if operation == "concat":
            assert result["outputs"][0]["duration"] > 4.5
        directory = engine.directory
    assert not directory.exists() and not list(root.glob("media-*"))


@pytest.mark.parametrize(
    "operation,options",
    [
        ("shell", {}),
        ("scale", {"width": 81, "height": 48}),
        ("audio", {"format": "hls"}),
        ("audio", {"format": "http://example.invalid"}),
        ("captions", {"text": "\x00secret"}),
        ("audio", {"bitrate": "999999k"}),
        ("split", {"segment_seconds": float("nan")}),
        ("cut", {"start": -1}),
        ("audio", {"program": "ffmpeg"}),
        ("split", {"format": "mp4"}),
    ],
)
def test_allowlist_refuses_unsafe_operations(tmp_path, owned_video, operation, options):
    root = tmp_path / "spool"
    root.mkdir(mode=0o700)
    with MediaEngine(root) as engine:
        put(engine, owned_video.read_bytes())
        with pytest.raises(MediaError):
            engine.run(operation, options)
    assert not list(root.glob("media-*"))


def test_malformed_input_and_oversize_are_refused_and_removed(tmp_path):
    root = tmp_path / "spool"
    root.mkdir(mode=0o700)
    with MediaEngine(root) as engine:
        put(engine, b"not a playable file")
        with pytest.raises(MediaError):
            engine.run("audio")
        assert all(r["reaped"] for r in engine.receipts)
    with MediaEngine(root) as engine, (engine.directory / "input.media").open("xb") as handle:
        with pytest.raises(MediaError) as exc:
            engine.append(handle, b"x" * 101, cap=100)
        assert exc.value.status == 413
    assert not list(root.glob("media-*"))


def test_missing_or_tampered_tools_are_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_TOOL_LOCK", str(tmp_path / "missing"))
    with pytest.raises(MediaError) as exc:
        tool_paths()
    assert exc.value.status == 503


def test_pipes_drain_before_whole_input_is_written():
    seen = []

    def source():
        for i in range(256):
            seen.append(i)
            yield b"\0" * 8192

    stream = run_ffmpeg_stream(
        ["-f", "s16le", "-ar", "48000", "-ac", "2", "-i", "pipe:0", "-f", "wav", "pipe:1"], source()
    )
    assert next(stream)
    assert len(seen) < 256  # the old sequential writer deadlocked here
    assert sum(map(len, stream)) > 1000000


def test_cancel_deadline_and_slow_consumer_reap_real_process():
    ffmpeg = tool_paths()["ffmpeg"]
    args = [
        "-v",
        "error",
        "-nostdin",
        "-re",
        "-f",
        "lavfi",
        "-i",
        "sine=sample_rate=48000:duration=30",
        "-threads",
        "1",
        "-f",
        "s16le",
        "pipe:1",
    ]
    stop = threading.Event()
    timer = threading.Timer(0.2, stop.set)
    timer.start()
    receipt = {}
    start = time.monotonic()
    with pytest.raises(MediaError):
        list(
            run_process(
                ffmpeg, args, cancelled=stop.is_set, timeout=5, max_output=4 << 20, receipt=receipt
            )
        )
    timer.join()
    assert receipt["reaped"] and time.monotonic() - start < 3
    assert not Path(f"/proc/{receipt['pid']}").exists()
    receipt = {}
    stream = run_process(ffmpeg, args, timeout=0.4, receipt=receipt, max_output=4 << 20)
    assert next(stream)
    time.sleep(0.7)  # watchdog must run while the consumer does not request more
    with pytest.raises(MediaError):
        list(stream)
    assert receipt["reaped"] and not Path(f"/proc/{receipt['pid']}").exists()


def test_private_recovery_and_capacity_refusal(tmp_path):
    root = tmp_path / "spool"
    root.mkdir(mode=0o700)
    stale = root / "media-abandoned"
    stale.mkdir()
    (stale / "partial").write_bytes(b"incomplete")
    unrelated = root / "keep"
    unrelated.write_text("not owned by recovery")
    assert MediaEngine.recover(root) == ["media-abandoned"]
    assert unrelated.exists()
    with MediaEngine(root):
        with pytest.raises(MediaError) as exc:
            MediaEngine(root)
        assert exc.value.status == 429


@pytest.mark.parametrize("change", [{"cpu": 0}, {"pids": 10000}, {"memory": True}, {"file": 0}])
def test_fixed_wrapper_limits_cannot_be_widened(change):
    with pytest.raises(ValueError):
        validate({"memory": 1536 << 20, "cpu": 30, "pids": 128, "file": 300 << 20, **change})
