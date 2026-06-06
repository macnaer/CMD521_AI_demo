#!/usr/bin/env python3
"""Backup helper — saves device configs with timestamps.

Usage:
    python scripts/backup_helper.py --device rtr-core01 --host 10.0.0.1 --platform cisco_ios
    python scripts/backup_helper.py --device rtr-core01 --host 10.0.0.1 --platform cisco_ios --dry-run
"""
import argparse
import datetime
import os
import sys
from pathlib import Path


def get_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_filename(hostname: str) -> str:
    return f"{get_timestamp()}_{hostname}.cfg"


def backup_netmiko(host: str, username: str, password: str, platform: str, output_dir: str, dry_run: bool = False) -> str:
    try:
        from netmiko import ConnectHandler
    except ImportError:
        raise SystemExit("Install netmiko: pip install netmiko")

    if dry_run:
        fn = backup_filename("dryrun")
        return f"[DRY-RUN] Would backup from {host} to {output_dir}/{fn}"

    conn = ConnectHandler(device_type=platform, host=host, username=username, password=password)
    config = conn.send_command("show running-config")
    conn.disconnect()

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    fn = backup_filename(host.split(".")[0])
    (Path(output_dir) / fn).write_text(config)
    return f"Backup saved: {output_dir}/{fn}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup network device config")
    parser.add_argument("--device", required=True, help="Device hostname")
    parser.add_argument("--host", required=True, help="Device IP")
    parser.add_argument("--platform", default="cisco_ios", help="Device platform")
    parser.add_argument("--output-dir", default="backups", help="Backup output dir")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    username = os.environ.get("NET_USER", "")
    password = os.environ.get("NET_PASS", "")

    if not args.dry_run and (not username or not password):
        print("Error: Set NET_USER and NET_PASS env vars (or use --dry-run)")
        return 1

    result = backup_netmiko(args.host, username, password, args.platform, args.output_dir, args.dry_run)
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
