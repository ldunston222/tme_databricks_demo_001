from __future__ import annotations

import configparser
import os
import subprocess
from pathlib import Path
from typing import Any


def _run_cli(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, check=False, capture_output=True, text=True)
    except FileNotFoundError as e:
        # Many Databricks runtimes don't ship cloud CLIs (aws/az/gcloud).
        # Treat as a normal command failure so callers can surface a clean status.
        return subprocess.CompletedProcess(cmd, 127, stdout="", stderr=str(e))


def _ensure_aws_sso_profile(
    *,
    profile: str,
    sso_start_url: str | None,
    sso_region: str | None,
    sso_account_id: str | None,
    sso_role_name: str | None,
) -> None:
    if not (sso_start_url and sso_region and sso_account_id and sso_role_name):
        return

    aws_dir = Path("~/.aws").expanduser()
    aws_dir.mkdir(parents=True, exist_ok=True)
    config_path = aws_dir / "config"

    cfg = configparser.RawConfigParser()
    if config_path.exists():
        cfg.read(config_path)

    section = f"profile {profile}" if profile != "default" else "default"
    if not cfg.has_section(section):
        cfg.add_section(section)

    cfg.set(section, "sso_start_url", sso_start_url)
    cfg.set(section, "sso_region", sso_region)
    cfg.set(section, "sso_account_id", sso_account_id)
    cfg.set(section, "sso_role_name", sso_role_name)
    cfg.set(section, "region", sso_region)

    with config_path.open("w", encoding="utf-8") as f:
        cfg.write(f)


def auth_sso(
    cloud: str,
    *,
    enabled: bool,
    aws_profile: str = "default",
    aws_sso_start_url: str | None = None,
    aws_sso_region: str | None = None,
    aws_sso_account_id: str | None = None,
    aws_sso_role_name: str | None = None,
    aws_sso_no_browser: bool = True,
    az_tenant_id: str | None = None,
) -> dict[str, Any]:
    """Attempt interactive/cloud-CLI auth and return metadata-only status.

    This function never returns credentials/tokens; it only returns metadata like
    provider, method, status, and optional error text.
    """

    cloud_norm = (cloud or "").lower().strip()
    info: dict[str, Any] = {
        "provider": cloud_norm,
        "method": None,
        "status": "skipped",
        "profile": aws_profile if cloud_norm == "aws" else None,
    }

    if not enabled:
        return info

    if cloud_norm == "aws":
        info["method"] = "aws-cli sso login"
        os.environ["AWS_PROFILE"] = aws_profile
        _ensure_aws_sso_profile(
            profile=aws_profile,
            sso_start_url=aws_sso_start_url,
            sso_region=aws_sso_region,
            sso_account_id=aws_sso_account_id,
            sso_role_name=aws_sso_role_name,
        )

        p = _run_cli(["aws", "--version"])
        if p.returncode != 0:
            info["status"] = "failed"
            info["error"] = "aws CLI not available on PATH"
            return info

        cmd = ["aws", "sso", "login", "--profile", aws_profile]
        if aws_sso_no_browser:
            cmd.append("--no-browser")
        p = _run_cli(cmd)
        info["status"] = "ok" if p.returncode == 0 else "failed"
        if p.returncode != 0:
            info["error"] = (p.stderr or p.stdout or "aws sso login failed").strip()
        return info

    if cloud_norm == "azure":
        info["method"] = "az login --use-device-code"
        cmd = ["az", "login", "--use-device-code"]
        if az_tenant_id:
            cmd += ["--tenant", az_tenant_id]
        p = _run_cli(cmd)
        info["status"] = "ok" if p.returncode == 0 else "failed"
        if p.returncode != 0:
            info["error"] = (p.stderr or p.stdout or "az login failed").strip()
        return info

    if cloud_norm == "gcp":
        info["method"] = "gcloud auth login --no-launch-browser"
        p = _run_cli(["gcloud", "auth", "login", "--no-launch-browser"])
        info["status"] = "ok" if p.returncode == 0 else "failed"
        if p.returncode != 0:
            info["error"] = (p.stderr or p.stdout or "gcloud auth login failed").strip()
        return info

    info["status"] = "failed"
    info["error"] = f"Unsupported cloud: {cloud_norm}"
    return info
