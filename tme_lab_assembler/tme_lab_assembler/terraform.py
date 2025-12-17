from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class TerraformResult:
    returncode: int
    stdout: str
    stderr: str


def run_terraform(tf_dir: str | Path, args: Iterable[str]) -> TerraformResult:
    tf_dir_path = Path(tf_dir).resolve()
    proc = subprocess.run(
        ["terraform", *list(args)],
        cwd=str(tf_dir_path),
        check=True,
        capture_output=True,
        text=True,
    )
    return TerraformResult(proc.returncode, proc.stdout, proc.stderr)


def init(tf_dir: str | Path) -> TerraformResult:
    return run_terraform(tf_dir, ["init", "-upgrade"])


def apply(tf_dir: str | Path, *, env_name: str, cloud: str) -> TerraformResult:
    return run_terraform(
        tf_dir,
        ["apply", "-auto-approve", "-var", f"env_name={env_name}", "-var", f"cloud={cloud}"],
    )


def destroy(tf_dir: str | Path, *, env_name: str, cloud: str) -> TerraformResult:
    return run_terraform(
        tf_dir,
        ["destroy", "-auto-approve", "-var", f"env_name={env_name}", "-var", f"cloud={cloud}"],
    )


def output_json(tf_dir: str | Path) -> dict[str, Any]:
    out = run_terraform(tf_dir, ["output", "-json"]).stdout
    return json.loads(out) if out.strip() else {}
