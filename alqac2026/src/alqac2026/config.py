from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def load_env_file(path: str | Path) -> dict[str, str]:
    values: dict[str, str] = {}
    env_path = Path(path)
    if not env_path.exists():
        return values
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


@dataclass(frozen=True)
class ApiConfig:
    base_url: str
    token: str = field(repr=False)
    timeout_s: float = 30.0
    min_interval_s: float = 6.0
    max_calls_per_case: int = 2

    @classmethod
    def from_project(cls, project_root: str | Path) -> "ApiConfig":
        file_values = load_env_file(Path(project_root) / ".env")
        base_url = os.environ.get(
            "ALQAC_API_BASE",
            file_values.get("ALQAC_API_BASE", "https://alqac-api.ngrok.pro"),
        )
        token = os.environ.get(
            "ALQAC_TEAM_TOKEN", file_values.get("ALQAC_TEAM_TOKEN", "")
        )
        return cls(base_url=base_url.rstrip("/"), token=token)

    def require_token(self) -> None:
        if not self.token:
            raise ValueError("ALQAC_TEAM_TOKEN is required for network retrieval")
