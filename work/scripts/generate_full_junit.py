"""Execute the actual full pytest suite and preserve its unchanged JUnit artifact.

Never infer outcomes from collection, hardcode counts/timings, or overwrite old
proof. Nonzero pytest status is propagated, even when a report was produced.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

from verification_evidence import read_junit

ROOT = pathlib.Path(__file__).resolve().parent.parent


def generate(output_path: pathlib.Path) -> dict:
    output_path = pathlib.Path(output_path).absolute()
    if output_path.exists() or output_path.is_symlink():
        raise FileExistsError('new evidence path required; existing proof retained')
    if any(p.is_symlink() for p in output_path.parents):
        raise ValueError('symlinked evidence directory')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Atomically reserve ownership; a competing generator can never truncate proof.
    os.close(os.open(output_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
    proc = subprocess.run(
        [sys.executable, '-m', 'pytest', '--junitxml=' + str(output_path)],
        cwd=ROOT, capture_output=True, text=True, check=False, timeout=600,
    )
    # Parse, do not reconstruct, relabel or alter pytest's bytes.
    result = read_junit(output_path)
    result.update(exit_code=proc.returncode, junit_artifact=str(output_path),
                  runner_stdout=proc.stdout, runner_stderr=proc.stderr)
    if proc.returncode == 0 and result['python']['failed']:
        raise ValueError('pytest exit/report disagree; no green receipt')
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=pathlib.Path,
                        help='NEW XML path; existing evidence is never overwritten')
    args = parser.parse_args()
    result = generate(args.output)
    sys.stdout.write(result.pop('runner_stdout'))
    sys.stderr.write(result.pop('runner_stderr'))
    print(json.dumps(result, indent=2))
    return result['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
