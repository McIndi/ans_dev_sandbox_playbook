# Copilot Instructions for ans_dev_sandbox_playbook

## Project Architecture

This is an **Ansible playbook sandbox** for developing and testing the GitHub-hosted role `briankearney/ans_dev_sandbox_role`. The project uses **environment variables instead of `ansible.cfg`** for enterprise compliance—never create or suggest `ansible.cfg` files.

### Key Components

- **External Role Testing**: The role under test (`ans_dev_sandbox_role`) is hosted separately on GitHub and pulled via `roles/requirements.yml`; during development `roles/` may contain symlinks.
- **Dual-Target Architecture**: Playbooks run against both `localhost` (connection: local) and `ansible_target` (containerized SSH target on port 2222).
- **Container-Based Testing**: `python sandbox.py run` orchestrates building the Fedora container, generating ephemeral SSH keys, installing Ansible collections, and running the playbook.
- **Environment-Driven Config**: `python sandbox.py activate` writes `.env` with ANSIBLE_* variables (session-scoped, auditable) and prepares the virtualenv.

### Critical Files

- `sandbox.py` - CLI entrypoint with `activate` (venv + .env) and `run` (container + playbook) subcommands
- `DECRYPT_VAULTED_ITEMS.py` - Utility for inspecting Ansible vault blocks with optional base64 decoding
- `containerfile` - Fedora-based SSH target for Ansible testing (exposes port 22, runs sshd in foreground)
- `inventory/main.yml` - Defines `all` group with `localhost` + `ansible_target` (grouped under `local`)
- `playbooks/sample_playbook.yml` - Reference playbook applying `ans_dev_sandbox_role` to all hosts

## Development Workflows

### Initial Setup

```bash
git clone <repo>
cd ans_dev_sandbox_playbook
python sandbox.py activate               # Creates .venv, installs deps, writes .env
source .venv/bin/activate                # Enter the venv for manual commands
ansible-galaxy install -r roles/requirements.yml --roles-path roles  # optional if not using sandbox run
```

### Running Playbooks

**Full workflow (container + localhost):**
```bash
python sandbox.py run
```

**Localhost only (skip container):**
```bash
python sandbox.py run --skip-container --limit localhost
```

**Container target only:**
```bash
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -l ansible_target
```

### Testing Strategy

**Unit tests (Python):**
```bash
python -m unittest -v tests/test_sandbox.py
python -m unittest -v test_DECRYPT_VAULTED_ITEMS.py
```

**Molecule scenarios:**
- `molecule/default/` - Core localhost scenario
- `molecule/localhost-only/` - Minimal localhost-only tests
- `molecule/with-linting/` - Includes yamllint + ansible-lint

```bash
python sandbox.py activate
source .venv/bin/activate
molecule test -s default                       # Full test sequence
molecule test -s with-linting                  # With lint checks
```

**Linting (run separately since Molecule ≥25 removed lint stage):**
```bash
yamllint .
ansible-lint playbooks/ molecule/
```

### Container Workflow Details

`sandbox.py run` prefers Podman (falls back to Docker) with SELinux-friendly mounts when using Podman. Lifecycle:
1. Build `ansible_target` image from `containerfile`
2. Generate ephemeral ed25519 SSH key pair in `ssh_keys/`
3. Run container with `ssh_keys/` mounted read-only, default host port 2222
4. Install `ansible.posix` and `community.general` collections
5. Ensure role dependencies (symlink sibling repo if present; otherwise galaxy install)
6. Execute playbook against both targets
7. Cleanup on exit (container stopped)

## Project-Specific Conventions

### Configuration Management

**NEVER create `ansible.cfg`** — explicitly blocked in `.gitignore`. Configuration is stored in `.env` by `python sandbox.py activate`:
- `ANSIBLE_ROLES_PATH=roles`
- `ANSIBLE_VAULT_PASSWORD_FILE=$PLAYBOOK_PATH/vault-pw.txt`
- `ANSIBLE_CALLBACKS_ENABLED='profile_tasks'`
- `ANSIBLE_LOG_PATH=./ansible.log`
- and related ANSIBLE_* defaults

### Python Version Selection

`python sandbox.py activate` auto-selects the newest Python within **>3.9 and <3.15**:
- Scans `/usr/bin/`, `/usr/local/bin/`, `/opt/*/bin/` for `python3*`
- Parses semantic versions, selects highest `< 3.15.0`
- Falls back to `python3` in PATH if no candidates found
- Automatically uninstalls `pytest-ansible` after pip install to prevent plugin conflicts with `pytest-testinfra`

### YAML Formatting

- **Document start**: Required (`---`)
- **Document end**: Forbidden (`.yamllint` sets `document-end: false`)
- **Line length**: 160 chars (warning level)
- **Indentation**: 2 spaces, indent sequences
- **Truthy**: Allow `yes/no/true/false/on/off` (keys unchecked)

### Ansible Lint Configuration

- Profile: `production`
- Skip rules: `role-name`, `galaxy[no-changelog]`, `fqcn[action-core]`
- Warn-only: `experimental`, `jinja[spacing]`, `name[casing]`
- Excluded paths: `.venv/`, `roles/ans_dev_sandbox_role/`, `.molecule/`, `tests/`

### Role Dependency Pattern

External role installed via `roles/requirements.yml`:
```yaml
- src: https://github.com/briankearney/ans_dev_sandbox_role
  scm: git
  name: ans_dev_sandbox_role
  version: main
```

During development, `python sandbox.py run` (or manual setup) creates a symlink if `roles/` is empty and a sibling `../ans_dev_sandbox_role/` exists:
```bash
ln -snf ../ans_dev_sandbox_role roles/ans_dev_sandbox_role
```

### Vault Usage

Demo vault password (`password`) stored in `vault-pw.txt` (git-ignored). Decrypt vaulted variables:
```bash
python3 DECRYPT_VAULTED_ITEMS.py --file vars/file.yml --vault-id dev [--decode] [--color]
```

### Container Workflow Tips

- Default container name: `ansible_target`; host SSH port: `2222` (override via `.env` or `--container-host-port`).
- Podman preferred; falls back to Docker if unavailable.
- Host key checking disabled for sandbox runs.

### Troubleshooting Context

- **"molecule: command not found"** → Run `python sandbox.py activate` then `source .venv/bin/activate`
- **argparse.ArgumentError with --ansible-inventory** → `python sandbox.py activate` removes pytest-ansible
- **Vault decrypt errors** → Verify vault-id matches block header (`vault_id: !vault |`)
- **Container port conflicts** → Override with `python sandbox.py run --container-host-port 2223`
- **Python version issues** → Activation selects 3.10–3.14 automatically; ensure a compatible version is installed

### Development Guidelines

1. **Always activate environment first**: `python sandbox.py activate` before Ansible commands
2. **Test changes across scenarios**: Run at least `molecule test -s default` before committing
3. **Lint before commit**: Use `yamllint` and `ansible-lint`
4. **Document vault changes**: Update vault-id references if modifying encrypted variables
5. **Keep role external**: Never inline the role code—it lives in `briankearney/ans_dev_sandbox_role` repo
