from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LabArtifact:
    env_name: str
    cloud: str
    resources: dict[str, Any]
    access: dict[str, str]
    create_at: str

    @staticmethod
    def build(*, env_name: str, cloud: str, resources: dict[str, Any], access: dict[str, str]) -> "LabArtifact":
        return LabArtifact(
            env_name=env_name,
            cloud=cloud,
            resources=resources,
            access=access,
            create_at=date.today().isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "env_name": self.env_name,
            "cloud": self.cloud,
            "resources": self.resources,
            "access": self.access,
            "create_at": self.create_at,
        }


def write_local_json(path: str | Path, artifact: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
