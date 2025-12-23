# ans_dev_sandbox_playbook

[![Molecule Tests](https://github.com/briankearney/ans_dev_sandbox_playbook/actions/workflows/molecule.yml/badge.svg)](https://github.com/briankearney/ans_dev_sandbox_playbook/actions/workflows/molecule.yml)
[![Unit Tests](https://github.com/briankearney/ans_dev_sandbox_playbook/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/briankearney/ans_dev_sandbox_playbook/actions/workflows/unit-tests.yml)

Lightweight Ansible playbook sandbox for developing and validating the GitHub-hosted role `briankearney/ans_dev_sandbox_role` using environment‑based configuration, Molecule scenarios, and unit tests.

## Documentation & Wiki
For setup, architecture, and usage guides, see:
- [Getting Started](https://github.com/briankearney/ans_dev_sandbox_playbook/wiki/Getting-Started)
- [Architecture](https://github.com/briankearney/ans_dev_sandbox_playbook/wiki/Architecture)
- [Project Wiki](https://github.com/briankearney/ans_dev_sandbox_playbook/wiki) (full index)

## Quick Map
- **Playbook:** `playbooks/sample_playbook.yml`
- **Inventory:** `inventory/main.yml` (`local` group contains `localhost` and dynamic container host `ansible_target`)
- **Role requirements:** `roles/requirements.yml`
- **Helper CLI:** `sandbox.py` (`activate`/`run` subcommands), `DECRYPT_VAULTED_ITEMS.py`
- **Testing:** Molecule scenarios + Python unit tests
- **Linting:** `.ansible-lint`, `.yamllint`
- **Container build:** `containerfile` (used by `python sandbox.py run` to create `ansible_target`)
- **Dynamic assets (generated, not committed):** `ssh_keys/`, `vault-pw.txt`, virtualenv `.venv`

## Design Philosophy (Condensed)
No `ansible.cfg` is committed—enterprise environments often disallow it. All configuration is set via environment variables written to `.env` by `python sandbox.py activate` (session-scoped, auditable, isolated). `.gitignore` blocks accidental `ansible.cfg` addition.

Key exported examples:
```bash
export ANSIBLE_ROLES_PATH=roles
export ANSIBLE_VAULT_PASSWORD_FILE="$PLAYBOOK_PATH/vault-pw.txt"
export ANSIBLE_LOG_PATH=./ansible.log
```

## Prerequisites
- Python >3.9 and <3.15 (auto-selected by `python sandbox.py activate`; typically 3.10–3.14)
- ansible-core >= 2.14 (installed via `requirements.txt`)
- Optional: Podman or Docker (for container-based testing via `python sandbox.py run`)
- Dependencies from `requirements.txt` (auto-installed by `python sandbox.py activate`)

## Usage (Typical Flow)
```bash
git clone <repo>
cd ans_dev_sandbox_playbook
python sandbox.py activate               # creates .venv, installs deps, writes .env for run
source .venv/bin/activate                # ensure the virtualenv is active
```
**Full workflow** (orchestrates container-based testing + localhost execution):
```bash
python sandbox.py run                    # uses .env defaults; prefers podman on port 2222
```
The CLI performs the following steps automatically:
1. **Generates ephemeral SSH keys** (`ssh_keys/` directory with ed25519 key pair)
2. **Builds container image** from `containerfile` (Fedora-based SSH target)
3. **Starts `ansible_target` container** (SSH exposed on host port 2222, auto-removed on exit)
4. **Creates vault password file** (`vault-pw.txt` with demo password if missing)
5. **Installs role dependencies** (from `roles/requirements.yml` or symlinks `../ans_dev_sandbox_role/`)
6. **Installs required collections** (`ansible.posix` and `community.general`)
7. **Runs playbook** against both `localhost` and `ansible_target` hosts
8. **Cleanup** (container auto-stopped via trap on exit)

**Limit to localhost only** (skips container setup):
```bash
python sandbox.py run --skip-container --limit localhost
```

## Quick Commands
- **Activate env:** `python sandbox.py activate && source .venv/bin/activate`
- **Full workflow:** `python sandbox.py run` (after activation)
- **Localhost only:** `python sandbox.py run --skip-container --limit localhost`
- **Container target only:** `ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -l ansible_target`

## Container Workflow (Brief)
`python sandbox.py run` builds an image via `containerfile`, starts `ansible_target` (SSH exposed on host port 2222), generates ephemeral `ssh_keys/`, installs required collections (`ansible.posix`, `community.general`), and runs the playbook across `localhost` + `ansible_target` (unless limited). These artifacts are transient.

## Testing & Linting
Run core tests:
```bash
python -m unittest -v tests/test_sandbox.py
python -m unittest -v test_DECRYPT_VAULTED_ITEMS.py
```
Run Molecule default scenario (after `python sandbox.py activate` and `source .venv/bin/activate` to enter the venv):
```bash
molecule test -s default
```
Lint (Molecule ≥25 removed built-in lint stage):
```bash
yamllint .
ansible-lint playbooks/ molecule/
```
Molecule tests use **pytest-testinfra** for Python-based system state verification. See `molecule/README.md` for details.

## Vault Decryption Utility
Inspect encrypted blocks:
```bash
python3 DECRYPT_VAULTED_ITEMS.py --file path/to/vars.yml --vault-id dev
python3 DECRYPT_VAULTED_ITEMS.py --file path/to/vars.yml --vault-id dev --decode
```
Features: graceful errors, optional base64 decode, colorized output unless `--no-color`.

## Inventory Notes
`inventory/main.yml` includes both `localhost` (connection local) and `ansible_target` (container host with forwarded SSH on port 2222). Use `-l` to scope runs.

## Dynamic / Demo Artefacts
- `ssh_keys/` created only by `python sandbox.py run` (excluded from repo)
- `vault-pw.txt` demo password file—replace or manage securely in production
- Temporary virtualenv `.venv` created automatically, removable at will

## Troubleshooting (Selected)
| Symptom | Cause | Resolution |
|---------|-------|-----------|
| `molecule: command not found` | Not activated venv | `python sandbox.py activate` then `source .venv/bin/activate` |
| Idempotence fails | Non-declarative task | Adjust module params / `changed_when` |
| Vault decrypt error | Wrong vault id/password | Verify vault block & `vault-pw.txt` |
| Python selection unexpected | Older interpreter first | Install newer Python ≥3.10 |
| [DEPRECATION WARNING]: The 'ansible.posix.profile_tasks' callback plugin implements the following deprecated method(s): playbook_on_stats. This feature will be removed from the callback plugin API in ansible-core version 2.23. Implement the `v2_*` equivalent callback method(s) instead. | `ansible.posix.profile_tasks` keeps a legacy `playbook_on_stats` shim for backward compatibility even though it implements v2 hooks | Safe to ignore while keeping the callback; optionally pin `ansible-core<2.23` until ansible.posix removes the shim and the warning disappears |

## Security & Compliance
No persistent config overrides (`ansible.cfg` avoided). Generated SSH keys & demo vault password are sandbox-only. Environment variable configuration is ephemeral and auditable.

## Contributing (Short)
1. Branch & modify.
2. Run lint + unit + Molecule.
3. Open PR with concise summary.

---
