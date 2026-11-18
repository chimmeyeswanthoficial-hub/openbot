"""Fixed synthetic/owned-media engine. Never an arbitrary command execution API.

Scoped disk spooling avoids loading uploads/output into RAM. Public/customer
media and hostile-input security acceptance remain disabled (S09 dependency).
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import shutil
import tempfile
import threading
import time
import zipfile
from pathlib import Path

from ffmpeg_runner import MediaError, run_process, tool_paths

MAX_INPUT = 260 << 20
MAX_OUTPUT = 300 << 20
MAX_DISK = MAX_INPUT + MAX_OUTPUT + (2 << 20)
FORMATS = "wav,mp3,mov,matroska,ogg"
_LOCK = threading.Lock()


def acquire_spool(root):
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise MediaError("symlinked_spool", 503)
    descriptor = os.open(
        root / ".media.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600
    )
    try:
        if os.fstat(descriptor).st_nlink != 1:
            raise MediaError("unsafe_spool_lock", 503)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return descriptor
    except BlockingIOError as exc:
        os.close(descriptor)
        raise MediaError("media_capacity_busy", 429) from exc
    except BaseException:
        os.close(descriptor)
        raise


def finite(value, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise MediaError("out_of_range")
    return value


class MediaEngine:
    """A private lease owns input, outputs and receipts. Always close the lease."""

    def __init__(self, root, *, timeout=30.0, cancelled=None):
        self.root = Path(root)
        if not self.root.is_absolute() or self.root.is_symlink():
            raise MediaError("private_absolute_spool_required", 503)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.root.stat().st_mode & 0o077 or self.root.stat().st_uid != os.getuid():
            raise MediaError("private_spool_required", 503)
        if not _LOCK.acquire(blocking=False):
            raise MediaError("media_capacity_busy", 429)
        self.closed = False
        self.descriptor = None
        try:
            self.descriptor = acquire_spool(self.root)
            self.directory = Path(tempfile.mkdtemp(prefix="media-", dir=self.root))
            self.tools = tool_paths()
            self.cancelled = cancelled or (lambda: False)
            self.timeout = finite(timeout, 0.1, 120)
            self.deadline = time.monotonic() + self.timeout
            self.receipts = []
            self.input_bytes = 0
        except BaseException:
            if hasattr(self, "directory"):
                shutil.rmtree(self.directory)
            if self.descriptor is not None:
                os.close(self.descriptor)
            _LOCK.release()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()

    def close(self):
        if not self.closed:
            self.closed = True
            try:
                shutil.rmtree(self.directory)
            finally:
                os.close(self.descriptor)
                _LOCK.release()

    @staticmethod
    def recover(root):
        """Trusted startup only, before accepting jobs; never delete arbitrary paths."""
        root = Path(root)
        if not root.exists():
            return []
        if root.is_symlink() or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
            raise MediaError("unsafe_recovery_root", 503)
        descriptor = acquire_spool(root)
        try:
            removed = []
            for child in root.iterdir():
                if child.name.startswith("media-") and child.is_dir() and not child.is_symlink():
                    shutil.rmtree(child)
                    removed.append(child.name)
            return removed
        finally:
            os.close(descriptor)

    def check_disk(self):
        total = 0
        for entry in self.directory.iterdir():
            if entry.is_symlink() or not entry.is_file():
                raise MediaError("unexpected_spool_entry")
            total += entry.stat().st_size
        if total > MAX_DISK:
            raise MediaError("disk_limit", 413)
        if self.cancelled() or time.monotonic() > self.deadline:
            raise MediaError("cancelled_or_deadline", 408)

    def append(self, handle, block, *, cap=MAX_INPUT):
        if not isinstance(block, bytes):
            raise MediaError("invalid_input")
        self.input_bytes += len(block)
        if self.input_bytes > min(cap, MAX_INPUT):
            raise MediaError("Upload exceeded maximum allowed size", 413)
        for offset in range(0, len(block), 65536):
            handle.write(memoryview(block)[offset : offset + 65536])
        self.check_disk()

    def call(self, tool, args, *, output_cap=128 << 10):
        self.check_disk()
        remaining = self.deadline - time.monotonic()
        record = {"tool": tool}
        self.receipts.append(record)
        data = b"".join(
            run_process(
                self.tools[tool],
                args,
                cwd=self.directory,
                timeout=max(0.01, remaining),
                cancelled=self.cancelled,
                max_output=output_cap,
                disk_check=self.check_disk,
                receipt=record,
            )
        )
        self.check_disk()
        return data

    def probe(self, name):
        result = self.call(
            "ffprobe",
            [
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-format_whitelist",
                FORMATS,
                "-threads",
                "1",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                name,
            ],
        )
        try:
            value = json.loads(result)
            duration = float(value["format"]["duration"])
            finite(duration, 0.01, 1800)
            if not 1 <= len(value["streams"]) <= 4:
                raise ValueError("streams")
            for stream in value["streams"]:
                if stream["codec_type"] not in {"audio", "video"}:
                    raise ValueError("stream_type")
                if stream["codec_type"] == "video":
                    finite(stream["width"], 2, 3840)
                    finite(stream["height"], 2, 2160)
                else:
                    finite(stream["channels"], 1, 8)
                    finite(int(stream["sample_rate"]), 8000, 192000)
        except (ValueError, KeyError, TypeError) as exc:
            raise MediaError("unsupported_or_invalid_media") from exc
        return value

    def ffmpeg(self, inputs, output):
        return self.call(
            "ffmpeg",
            [
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-y",
                "-filter_threads",
                "1",
                "-filter_complex_threads",
                "1",
                *inputs,
                "-threads",
                "1",
                *output,
            ],
            output_cap=4096,
        )

    def source(self, name="input.media"):
        return [
            "-protocol_whitelist",
            "file,pipe",
            "-format_whitelist",
            FORMATS,
            "-threads",
            "1",
            "-i",
            name,
        ]

    def video_encoding(self):
        return [
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-movflags",
            "+faststart",
        ]

    def verify(self, name):
        value = self.probe(name)
        self.ffmpeg(self.source(name), ["-map", "0:v:0?", "-map", "0:a:0?", "-f", "null", "-"])
        path = self.directory / name
        with path.open("rb") as handle:
            sha = hashlib.file_digest(handle, "sha256").hexdigest()
        return {
            "name": name,
            "bytes": path.stat().st_size,
            "sha256": sha,
            "duration": float(value["format"]["duration"]),
            "streams": [
                {
                    "type": s["codec_type"],
                    "codec": s["codec_name"],
                    **(
                        {"width": s["width"], "height": s["height"]}
                        if s["codec_type"] == "video"
                        else {}
                    ),
                }
                for s in value["streams"]
            ],
            "decode_readback": True,
        }

    def _concat_sources(self):
        archive = self.directory / "input.media"
        try:
            with zipfile.ZipFile(archive) as bundle:
                items = bundle.infolist()
                expected = [f"part-{i:02}.mp4" for i in range(len(items))]
                if not 2 <= len(items) <= 8 or [i.filename for i in items] != expected:
                    raise MediaError("fixed_concat_parts_required")
                if sum(i.file_size for i in items) + self.input_bytes > MAX_INPUT:
                    raise MediaError("concat_input_limit", 413)
                for item in items:
                    if (item.external_attr >> 16) & 0o170000 == 0o120000:
                        raise MediaError("concat_symlink_refused")
                    with (
                        bundle.open(item) as source,
                        (self.directory / item.filename).open("xb") as dest,
                    ):
                        while block := source.read(65536):
                            self.append(dest, block)
        except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
            raise MediaError("invalid_concat_archive") from exc
        probes = [self.probe(name) for name in expected]

        def layout(value):
            return [
                (
                    s["codec_type"],
                    s["codec_name"],
                    s.get("width"),
                    s.get("height"),
                    s.get("sample_rate"),
                    s.get("channels"),
                )
                for s in value["streams"]
            ]

        if any(layout(p) != layout(probes[0]) for p in probes):
            raise MediaError("concat_requires_compatible_streams")
        if sum(float(p["format"]["duration"]) for p in probes) > 1800:
            raise MediaError("concat_duration_limit")
        (self.directory / "concat.txt").write_text("".join(f"file '{n}'\n" for n in expected))
        return [
            "-protocol_whitelist",
            "file,pipe",
            "-threads",
            "1",
            "-f",
            "concat",
            "-safe",
            "1",
            "-i",
            "concat.txt",
        ]

    def run(self, operation, options=None):
        options = options or {}
        allowed = {
            "audio": {"format", "bitrate"},
            "convert": {"format", "bitrate"},
            "compress": {"format", "bitrate"},
            "cut": {"start", "duration"},
            "scale": {"width", "height"},
            "captions": {"text"},
            "concat": set(),
            "split": {"segment_seconds", "format"},
        }
        if (
            operation not in allowed
            or not isinstance(options, dict)
            or set(options) - allowed[operation]
        ):
            raise MediaError("unsupported_operation")
        if not (self.directory / "input.media").is_file() or not self.input_bytes:
            raise MediaError("nonempty_owned_input_required")
        if operation == "concat":
            source = self._concat_sources()
        else:
            self.probe("input.media")
            source = self.source()
        output_name, media_type = "result.mp4", "video/mp4"
        outputs = []
        if operation in {"audio", "convert", "compress"}:
            fmt = options.get("format", "mp3")
            rate = options.get("bitrate", "128k")
            if fmt not in {"mp3", "wav"} or rate not in {"64k", "96k", "128k", "192k"}:
                raise MediaError("allowlisted_audio_format_and_bitrate_required")
            output_name, media_type = "result." + fmt, "audio/" + fmt
            encoding = (
                ["-c:a", "pcm_s16le"] if fmt == "wav" else ["-c:a", "libmp3lame", "-b:a", rate]
            )
            self.ffmpeg(source, ["-map", "0:a:0", "-vn", *encoding, output_name])
        elif operation == "split":
            seconds = finite(options.get("segment_seconds", 60), 1, 900)
            if options.get("format", "mp3") != "mp3":
                raise MediaError("only_mp3_segments_supported")
            self.ffmpeg(
                source,
                [
                    "-map",
                    "0:a:0",
                    "-vn",
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    "128k",
                    "-f",
                    "segment",
                    "-segment_time",
                    str(seconds),
                    "-segment_start_number",
                    "0",
                    "-reset_timestamps",
                    "1",
                    "segment-%03d.mp3",
                ],
            )
            names = sorted(p.name for p in self.directory.glob("segment-*.mp3"))
            if not names or len(names) > 1801:
                raise MediaError("invalid_segment_count")
            outputs = [self.verify(name) for name in names]
            manifest = {
                "schema": "openbot.media-segments/1",
                "operation": "split",
                "segment_seconds": seconds,
                "segments": outputs,
            }
            (self.directory / "manifest.json").write_text(json.dumps(manifest, sort_keys=True))
            output_name, media_type = "segments.zip", "application/zip"
            with zipfile.ZipFile(
                self.directory / output_name, "x", compression=zipfile.ZIP_STORED
            ) as bundle:
                for name in ["manifest.json", *names]:
                    with (self.directory / name).open("rb") as src, bundle.open(name, "w") as dest:
                        while block := src.read(65536):
                            dest.write(block)
                            self.check_disk()
            # ZIP is an extra copy. Enforce aggregate disk as well as every file.
        else:
            extra = []
            if operation == "cut":
                start = finite(options.get("start", 0), 0, 1799)
                duration = finite(options.get("duration", 1), 0.1, 1800 - start)
                extra = ["-ss", str(start), "-t", str(duration)]
            elif operation == "scale":
                width, height = options.get("width", 640), options.get("height", 360)
                if any(type(n) is not int or n % 2 for n in (width, height)):
                    raise MediaError("even_integer_dimensions_required")
                finite(width, 2, 1920)
                finite(height, 2, 1080)
                extra = ["-vf", f"scale={width}:{height}"]
            elif operation == "captions":
                text = options.get("text", "")
                if (
                    not isinstance(text, str)
                    or not 1 <= len(text) <= 160
                    or any(ord(c) < 32 and c != "\n" for c in text)
                ):
                    raise MediaError("plain_bounded_caption_required")
                (self.directory / "caption.txt").write_text(text)
                extra = [
                    "-vf",
                    "drawtext=textfile=caption.txt:expansion=none:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.6:x=10:y=10",
                ]
            self.ffmpeg(source, [*extra, *self.video_encoding(), output_name])
        if not outputs:
            outputs = [self.verify(output_name)]
        self.check_disk()
        path = self.directory / output_name
        if path.stat().st_size > MAX_OUTPUT:
            raise MediaError("output_limit", 413)
        return {
            "path": path,
            "media_type": media_type,
            "outputs": outputs,
            "input_bytes": self.input_bytes,
            "processes": self.receipts,
            "customer_uploads_enabled": False,
            "hostile_isolation_accepted": False,
        }
