#!/usr/bin/env python3
"""Compatibility entry point for current local package checks (not native launch)."""

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("verify-local-packages.py")), run_name="__main__")
