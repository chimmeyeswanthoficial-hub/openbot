"""Fixed zero-cost local tool. No model, network, shell or arbitrary file interface.

Only the reviewed parent launches this Linux worker. SSE is actually written to a
pipe and consumed by the parent; this is not a claim of a live AG-UI model server.
"""
from __future__ import annotations

import ctypes
import json
import os
import resource
import signal
import sys
import time


def main() -> None:
    parent = int(sys.argv[1])
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0 or os.getppid() != parent:
        raise SystemExit("Parent-death guard unavailable; refusing execution")
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024, 128 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (16, 16))
    # 8192 input bytes may expand sixfold as JSON-escaped control characters.
    raw = sys.stdin.buffer.read(65537)
    if len(raw) > 65536:
        raise SystemExit("Input limit")
    body = json.loads(raw)
    rid = body["request_id"]

    def emit(kind: str, **fields) -> None:
        event = {"type": kind, "runId": rid, **fields}
        print("data: " + json.dumps(event, separators=(",", ":")) + "\n", flush=True)

    emit("RUN_STARTED", threadId=rid)
    emit("TOOL_CALL_START", toolCallId=rid + ":count", toolCallName="local.wordcount")
    time.sleep(body["delay_ms"] / 1000)
    result = {"words": len(body["text"].split()), "characters": len(body["text"]),
              "worker_pid": os.getpid(),
              "minimal_environment": set(os.environ) <= {"PATH", "LANG", "LC_CTYPE", "PYTHONNOUSERSITE", "PYTHONDONTWRITEBYTECODE"}}
    emit("TOOL_CALL_END", toolCallId=rid + ":count")
    emit("TEXT_MESSAGE_START", messageId=rid + ":output", role="assistant")
    emit("TEXT_MESSAGE_CONTENT", messageId=rid + ":output", delta=json.dumps(result, sort_keys=True))
    emit("TEXT_MESSAGE_END", messageId=rid + ":output")
    emit("RUN_FINISHED", threadId=rid)


if __name__ == "__main__":
    main()
