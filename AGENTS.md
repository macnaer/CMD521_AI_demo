# AGENTS.md — NetDevOps + Database Automation Project

## System Prompt

This project's AI assistant is configured via `system_prompt.md`.
Read and follow it at the start of every session.

## Agent Skills

Skills live in `.agents/skills/` (agentskills.io format).

| Skill | Trigger | Purpose |
|-------|---------|---------|
| `netdevops-automation` | Python + network + config + device | Network automation with netmiko, nornir, napalm, scrapli |
| `mssql-database` | SQL + database + query + table + MSSQL | MSSQL operations: queries, tables, data generation, backups |
| `swapi-client` | Star Wars + SWAPI + people + starships + planets | SWAPI fetcher, query, stats, JSON/CSV/DB export |

Read the relevant `SKILL.md` before performing tasks. Scripts and references are in each skill's subdirectories.

## Conventions

### Naming

| Item | Convention | Example |
|------|-----------|---------|
| Python modules | `snake_case` | `config_deployer.py` |
| Python classes | `PascalCase` | `NetworkDevice`, `ConfigDeployer` |
| CLI commands | `kebab-case` via click/typer | `deploy-config`, `backup-all` |
| Inventory files | `snake_case.yaml` | `site_a_devices.yaml` |
| Jinja2 templates | `snake_case.j2` | `ospf_interface.j2` |
| Backup snapshots | `YYYYMMDD_HHMMSS_<device>.cfg` | `20260606_143000_rtr-core01.cfg` |
| Log files | `YYYY-MM-DD_<module>.log` | `2026-06-06_deploy.log` |
| SQL files | `snake_case.sql` | `sample-queries.sql` |

### Directory Structure

```
.agents/skills/          # Agent Skills (netdevops-automation, mssql-database, swapi-client)
src/                     # Main source — Python package
│   └── starwars_importer.py   # Interactive SWAPI → Starwars DB importer
tests/                   # pytest suite (unit/ + integration/)
inventory/               # Device inventory YAMLs, group_vars
templates/               # Jinja2 templates for configs
backups/                 # Config/DB backups (gitignored)
logs/                    # Runtime logs (gitignored)
docs/                    # Documentation, runbooks
```

### Key Rules

1. **Dry-run is the default.** Every state-changing script must accept
   `--dry-run` (print plan/preview) and require `--apply` to execute.
2. **No secrets in code.** Use `${ENV_VAR}` placeholders; resolve at runtime.
3. **No credentials in inventory.** Inventory files contain hostnames,
   platforms, and connection parameters — never passwords or keys.
4. **Backups before changes.** Every deploy/modify operation must snapshot
   the current state before pushing the new one.
5. **Verify after apply.** Never trust exit codes alone — always run a
   post-change verification (show commands, SELECT queries, state comparison).
6. **Idempotent scripts.** Re-running a script must not create duplicate
   configs or cause errors on an already-configured device/database.
7. **Parameterized SQL only.** Never interpolate user input into SQL strings.
8. **Close DB connections** in `finally` blocks or use context managers.

### Git Hygiene

- **Never commit:** `.env`, `backups/`, `logs/`, `__pycache__/`, `*.pyc`,
  credentials, private keys, tokens.
- **Always commit:** `pyproject.toml`, lock files, tests, documentation,
  `.agents/skills/`.
- **Commit message format:** `<type>(<scope>): <description>` —
  e.g., `feat(deploy): add NX-OS config push`, `fix(db): handle connection timeout`.

### Pre-commit Checklist

```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/
pytest -q -m "not integration"
```

All four must pass before committing.

### Adding New Vendor Support

1. Create adapter in `src/vendors/<vendor>.py`.
2. Implement common interface or subclass base adapter.
3. Register in `src/vendors/__init__.py`.
4. Add unit tests in `tests/unit/test_<vendor>.py`.
5. Update inventory schema if needed.
6. Document vendor-specific notes in `docs/vendors/<vendor>.md`.

### Adding New Automation Script

1. Place in `src/cli.py` (entry point) or `src/core/` (logic).
2. Add CLI with `--dry-run` / `--apply` flags.
3. Use pydantic models for input validation.
4. Add unit tests in `tests/unit/`.
5. Add integration test (marked `@pytest.mark.integration`) if lab available.
6. Update README with usage example.

### Adding New Agent Skill

1. Create `.agents/skills/<skill-name>/SKILL.md` with frontmatter.
2. Add `scripts/` for executable helpers.
3. Add `references/` for detailed docs (keep SKILL.md under 500 lines).
4. Add `assets/` for templates, schemas, sample data.
5. Follow agentskills.io format.
