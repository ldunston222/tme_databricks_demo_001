from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class TerraformResult:
    returncode: int
    stdout: str
    stderr: str


def _is_databricks() -> bool:
    return bool(os.environ.get("DATABRICKS_RUNTIME_VERSION"))


def ensure_terraform_available() -> str:
    """Return the terraform executable path.

    On many Databricks runtimes, `terraform` is not installed. For convenience,
    this function can auto-download a Terraform binary into `/tmp`.
    """

    existing = shutil.which("terraform")
    if existing:
        return existing

    auto_install = os.environ.get("TERRAFORM_AUTO_INSTALL", "1" if _is_databricks() else "0") == "1"
    if not auto_install:
        raise RuntimeError(
            "Terraform CLI not found on PATH. "
            "Install `terraform` on the cluster driver (recommended via cluster init script), "
            "or set TERRAFORM_AUTO_INSTALL=1 to let this notebook download a temporary binary."
        )

    if platform.system().lower() != "linux":
        raise RuntimeError(
            "Terraform CLI not found on PATH and auto-install is only supported on Linux. "
            "Install `terraform` on PATH or run on Databricks/Linux."
        )

    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        tf_arch = "amd64"
    elif machine in ("aarch64", "arm64"):
        tf_arch = "arm64"
    else:
        raise RuntimeError(f"Unsupported architecture for terraform auto-install: {platform.machine()}")

    version = os.environ.get("TERRAFORM_VERSION", "1.8.5")
    cache_dir = Path("/tmp") / "tme_lab_assembler" / "terraform" / version
    tf_bin = cache_dir / "terraform"
    if tf_bin.exists():
        tf_bin.chmod(0o755)
        return str(tf_bin)

    cache_dir.mkdir(parents=True, exist_ok=True)
    zip_name = f"terraform_{version}_linux_{tf_arch}.zip"
    url = f"https://releases.hashicorp.com/terraform/{version}/{zip_name}"
    zip_path = cache_dir / zip_name

    try:
        urllib.request.urlretrieve(url, str(zip_path))
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extract("terraform", path=str(cache_dir))
        tf_bin.chmod(0o755)
        return str(tf_bin)
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Failed to auto-install terraform. "
            "Recommended fix: install terraform via a Databricks init script. "
            "This repo includes `tme_lab_assembler/infra/databricks/init-scripts/install_terraform.sh`. "
            f"Underlying error: {e}"
        )


def run_terraform(tf_dir: str | Path, args: Iterable[str]) -> TerraformResult:
    tf_dir_path = Path(tf_dir).resolve()
    terraform_bin = ensure_terraform_available()
    proc = subprocess.run(
        [terraform_bin, *list(args)],
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
