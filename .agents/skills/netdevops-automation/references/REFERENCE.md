# NetDevOps Reference Guide

Detailed reference for the netdevops-automation skill.

## Common Device Commands

### Cisco IOS/IOS-XE
```bash
show running-config
show ip interface brief
show version
show cdp neighbors
show ip route
copy running-config startup-config
```

### Cisco NX-OS
```bash
show running-config
show interface status
show version
show cdp neighbors
copy running-config startup-config
```

### Arista EOS
```bash
show running-config
show ip interface brief
show version
show lldp neighbors
show mac address-table
```

### Juniper Junos
```bash
show configuration
show interfaces terse
show version
show route
configure private
commit check
commit and-quit
```

### Nokia SR OS
```bash
show running-config
show router interface
show version
admin save
```

## PyATS Quick Reference

```python
from pyats import topology
from pyats.topology import loader

# Load testbed
testbed = loader.load('testbed.yaml')

# Connect
device = testbed.devices['rtr-core01']
device.connect()

# Parse show commands
output = device.parse('show ip route')

# Compare configs
from pyats.aeread import CustomFile
before = CustomFile('before.cfg')
after = CustomFile('after.cfg')
diff = before.difference(after)
```

## Backup Patterns

```python
import datetime
from pathlib import Path

def backup_device(device, backup_dir="backups"):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    config = device.get_config()
    filename = f"{timestamp}_{device.hostname}.cfg"
    Path(backup_dir).mkdir(exist_ok=True)
    (Path(backup_dir) / filename).write_text(config)
    return filename
```

## Jinja2 Template Example

```jinja2
{# templates/ospf_interface.j2 #}
interface {{ interface }}
  ip ospf 1 area {{ area }}
  {% if passive %}ip ospf passive{% endif %}
  {% if cost is defined %}ip ospf cost {{ cost }}{% endif %}
```

## Inventory YAML Format

```yaml
# inventory/devices.yaml
---
devices:
  rtr-core01:
    hostname: rtr-core01.lab.local
    platform: cisco_ios
    ip_address: 10.0.0.1
    port: 22
    group: core
  rtr-branch01:
    hostname: rtr-branch01.lab.local
    platform: arista_eos
    ip_address: 10.0.1.1
    port: 22
    group: branch

groups:
  core:
    username: ${NET_USER}
  branch:
    username: ${NET_USER}
```

## Error Handling Pattern

```python
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def handle_device_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ConnectionException as e:
            logger.error(f"Connection failed: {e}")
            logger.info("Check: SSH access, credentials, device reachability")
            raise
        except CommandException as e:
            logger.error(f"Command failed: {e}")
            logger.info("Check: command syntax, device OS version")
            raise
    return wrapper
```

## Testing Patterns

```python
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_device():
    device = MagicMock()
    device.get_config.return_value = "hostname test-sw01\ninterface Eth1\n switchport mode access"
    device.hostname = "test-sw01"
    return device

def test_backup_creates_file(mock_device, tmp_path):
    from src.core.backup import backup_device
    filename = backup_device(mock_device, backup_dir=str(tmp_path))
    assert (tmp_path / filename).exists()
```

## Rollback Strategy

1. Script saves pre-change snapshot to `backups/` with timestamp.
2. Script logs all changes made (diff of before/after).
3. Rollback command loads the snapshot and pushes it back:
   ```bash
   python -m src.cli rollback --snapshot-id 20260606_143000_rtr-core01.cfg --apply
   ```
4. Verify rollback with show commands.
