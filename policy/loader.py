"""Loads Policy objects from YAML files under configs/.

Business logic (gateway, ledger, future policy engine) must go through this
loader rather than constructing Policy() or reading YAML directly, so that
"policy lives in configs/, not scattered in source" (spec §14) stays true.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import ValidationError

from policy.models import Policy


def _default_configs_dir() -> Path:
    env_path = os.environ.get("CONFIGS_DIR")
    if env_path:
        return Path(env_path)
    cwd_path = Path.cwd() / "configs"
    if cwd_path.exists():
        return cwd_path
    return Path(__file__).resolve().parent.parent / "configs"


CONFIGS_DIR = _default_configs_dir()


class PolicyLoadError(RuntimeError):
    """Raised when a policy file is missing or fails schema validation."""


def load_policy(tenant_id: str, configs_dir: Path = CONFIGS_DIR) -> Policy:
    path = configs_dir / f"{tenant_id}.yaml"
    if not path.exists():
        raise PolicyLoadError(f"no policy config for tenant '{tenant_id}' at {path}")

    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise PolicyLoadError(f"invalid YAML in {path}: {exc}") from exc

    try:
        return Policy.model_validate(raw)
    except ValidationError as exc:
        raise PolicyLoadError(f"policy schema validation failed for {path}: {exc}") from exc


def load_all_policies(configs_dir: Path = CONFIGS_DIR) -> dict[str, Policy]:
    policies: dict[str, Policy] = {}
    for path in sorted(configs_dir.glob("*.yaml")):
        tenant_id = path.stem
        policies[tenant_id] = load_policy(tenant_id, configs_dir)
    return policies
