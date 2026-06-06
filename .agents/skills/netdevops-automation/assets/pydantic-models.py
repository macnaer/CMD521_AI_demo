"""Pydantic models for NetDevOps inventory and config validation.

Copy these into your project or import directly.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Platform(str, Enum):
    CISCO_IOS = "cisco_ios"
    CISCO_NXOS = "cisco_nxos"
    CISCO_XR = "cisco_xr"
    ARISTA_EOS = "arista_eos"
    JUNIPER_JUNOS = "juniper_junos"
    NOKIA_SROS = "nokia_sros"
    HUAWEI_VRP = "huawei_vrp"
    MIKROTIK_ROUTEROS = "mikrotik_routeros"


class Device(BaseModel):
    hostname: str = Field(..., min_length=1, max_length=63, pattern=r"^[a-zA-Z0-9._-]+$")
    platform: Platform
    ip_address: str
    port: int = Field(default=22, ge=1, le=65535)
    group: str = "default"
    connection_options: dict[str, dict] = {}

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        parts = v.split(".")
        if len(parts) != 4:
            raise ValueError(f"Invalid IP: {v}")
        for part in parts:
            if not part.isdigit() or not 0 <= int(part) <= 255:
                raise ValueError(f"Invalid IP octet: {part}")
        return v


class Group(BaseModel):
    username: str = Field(default="${NET_USER}")
    connection_options: dict[str, dict] = {}


class Inventory(BaseModel):
    devices: dict[str, Device]
    groups: dict[str, Group] = {}


class ConfigChange(BaseModel):
    device: str
    config_lines: list[str]
    dry_run: bool = True
    backup_id: Optional[str] = None
    description: str = ""

    @field_validator("config_lines")
    @classmethod
    def not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("config_lines must not be empty")
        return v


class DeployResult(BaseModel):
    device: str
    success: bool
    diff: str = ""
    error: str = ""
    backup_file: Optional[str] = None
    applied_at: Optional[str] = None
