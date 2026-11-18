"""Fixed local-media exec wrapper; rlimits are NOT hostile-code/cgroup isolation."""

from __future__ import annotations

import ctypes
import json
import os
import resource
import signal
import sys


def validate(value):
    if not isinstance(value, dict) or set(value) != {"memory", "cpu", "file", "pids"}:
        raise ValueError("fixed_limits_required")
    for name, lower, upper in [
        ("memory", 128 << 20, 2 << 30),
        ("cpu", 1, 120),
        ("file", 1 << 20, 320 << 20),
        ("pids", 2, 256),
    ]:
        if type(value[name]) is not int or not lower <= value[name] <= upper:
            raise ValueError("invalid_limits")
    return value


def main():
    parent = int(os.environ["MEDIA_PARENT_PID"])
    if ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "parent_death_signal_required")
    if os.getppid() != parent:
        raise SystemExit(71)
    limits = validate(json.loads(sys.argv[1]))
    executable = sys.argv[2]
    if not os.path.isabs(executable) or os.path.basename(executable) not in {"ffmpeg", "ffprobe"}:
        raise ValueError("fixed_executable_required")
    for kind, number in [
        (resource.RLIMIT_AS, limits["memory"]),
        (resource.RLIMIT_CPU, limits["cpu"]),
        (resource.RLIMIT_FSIZE, limits["file"]),
        (resource.RLIMIT_NPROC, limits["pids"]),
        (resource.RLIMIT_NOFILE, 64),
        (resource.RLIMIT_CORE, 0),
    ]:
        resource.setrlimit(kind, (number, number))
    os.umask(0o077)
    os.execve(executable, [executable, *sys.argv[3:]], os.environ.copy())


if __name__ == "__main__":
    main()
