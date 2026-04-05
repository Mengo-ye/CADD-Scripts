"""Shared utilities for CADD-Scripts."""

import shlex
import subprocess


def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a subprocess command, printing it for transparency."""
    print(f"Running: {shlex.join(cmd)}")
    return subprocess.run(cmd, check=check)
