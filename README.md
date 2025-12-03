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
- **Helper scripts:** `ACTIVATE_SANDBOX_ENV.bash`, `RUN_PLAYBOOK.bash`, `DECRYPT_VAULTED_ITEMS.py`
- **Testing:** Molecule scenarios + Bash & Python unit tests
- **Linting:** `.ansible-lint`, `.yamllint`
- **Container build:** `containerfile` (used by `RUN_PLAYBOOK.bash` to create `ansible_target`)
- **Dynamic assets (generated, not committed):** `ssh_keys/`, `vault-pw.txt`, virtualenv `.venv`

## Design Philosophy (Condensed)
No `ansible.cfg` is committed—enterprise environments often disallow it. All configuration is set via exported environment variables in `ACTIVATE_SANDBOX_ENV.bash` (session-scoped, auditable, isolated). `.gitignore` blocks accidental `ansible.cfg` addition.

Key exported examples:
```bash
export ANSIBLE_ROLES_PATH=roles
export ANSIBLE_VAULT_PASSWORD_FILE="$PLAYBOOK_PATH/vault-pw.txt"
export ANSIBLE_LOG_PATH=./ansible.log
```

## Prerequisites
- Python >3.9 and <3.15 (auto-selected by activation script; typically 3.10–3.14)
- ansible-core >= 2.14 (installed via `requirements.txt`)
- Optional: Podman or Docker (for container-based testing via `RUN_PLAYBOOK.bash`)
- Dependencies from `requirements.txt` (auto-installed by activation script)

## Usage (Typical Flow)
```bash
git clone <repo>
cd ans_dev_sandbox_playbook
source ACTIVATE_SANDBOX_ENV.bash        # creates .venv, installs deps
ansible-galaxy install -r roles/requirements.yml --roles-path roles
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml
```
Wrapper (builds container + runs playbook):
```bash
./RUN_PLAYBOOK.bash
```
Limit to localhost only:
```bash
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -l localhost
```

## Quick Commands
- **Full workflow:** `./RUN_PLAYBOOK.bash`
- **Localhost only:** `ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -l localhost`
- **Container target only:** `ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -l ansible_target`

## Container Workflow (Brief)
`RUN_PLAYBOOK.bash` builds an image via `containerfile`, starts `ansible_target` (SSH exposed on host port 2222), generates ephemeral `ssh_keys/`, installs required collections (`ansible.posix`, `community.general`), and runs the playbook across `localhost` + `ansible_target` (unless limited). These artifacts are transient.

## Testing & Linting
Run core tests:
```bash
bash tests/test_activate_sandbox_env.bash
bash tests/test_run_playbook.bash
python3 -m unittest -v test_DECRYPT_VAULTED_ITEMS.py
```
Run Molecule default scenario:
```bash
source ACTIVATE_SANDBOX_ENV.bash
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
- `ssh_keys/` created only by `RUN_PLAYBOOK.bash` (excluded from repo)
- `vault-pw.txt` demo password file—replace or manage securely in production
- Temporary virtualenv `.venv` created automatically, removable at will

## Troubleshooting (Selected)
| Symptom | Cause | Resolution |
|---------|-------|-----------|
| `molecule: command not found` | Not activated venv | `source ACTIVATE_SANDBOX_ENV.bash` |
| Idempotence fails | Non-declarative task | Adjust module params / `changed_when` |
| Vault decrypt error | Wrong vault id/password | Verify vault block & `vault-pw.txt` |
| Python selection unexpected | Older interpreter first | Install newer Python ≥3.10 |

## Security & Compliance
No persistent config overrides (`ansible.cfg` avoided). Generated SSH keys & demo vault password are sandbox-only. Environment variable configuration is ephemeral and auditable.

## Contributing (Short)
1. Branch & modify.
2. Run lint + unit + Molecule.
3. Open PR with concise summary.

---
