#!/usr/bin/env python3
"""Validate inventory YAML files against the expected schema.

Usage:
    python scripts/validate_inventory.py inventory/devices.yaml
    python scripts/validate_inventory.py inventory/ --recursive
"""
import sys
from pathlib import Path

try:
    from pydantic import BaseModel, Field, field_validator
except ImportError:
    print("Install pydantic: pip install pydantic")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("Install pyyaml: pip install pyyaml")
    sys.exit(1)


class Device(BaseModel):
    hostname: str = Field(..., pattern=r"^[a-zA-Z0-9._-]+$")
    platform: str
    ip_address: str
    port: int = 22
    group: str = "default"

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        supported = {
            "cisco_ios", "cisco_nxos", "cisco_xr",
            "arista_eos", "juniper_junos",
            "nokia_sros", "huawei_vrp",
            "mikrotik_routeros",
        }
        if v not in supported:
            raise ValueError(f"Unsupported platform: {v}. Supported: {sorted(supported)}")
        return v


class Inventory(BaseModel):
    devices: dict[str, Device]
    groups: dict[str, dict] = {}


def validate_file(path: Path) -> list[str]:
    errors = []
    try:
        data = yaml.safe_load(path.read_text())
        if not data or "devices" not in data:
            errors.append(f"{path}: missing 'devices' key")
            return errors
        Inventory(**data)
    except Exception as e:
        errors.append(f"{path}: {e}")
    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: validate_inventory.py <path>")
        return 1

    target = Path(sys.argv[1])
    recursive = "--recursive" in sys.argv

    files = []
    if target.is_dir():
        pattern = "**/*.yaml" if recursive else "*.yaml"
        files = list(target.glob(pattern))
    elif target.is_file():
        files = [target]
    else:
        print(f"Path not found: {target}")
        return 1

    all_errors: list[str] = []
    for f in files:
        all_errors.extend(validate_file(f))

    if all_errors:
        print("Validation errors:")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    print(f"Validated {len(files)} file(s) successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
