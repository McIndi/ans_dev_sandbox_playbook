# Copilot Instructions for ans_dev_sandbox_playbook

## Project Architecture

This is an **Ansible playbook sandbox** for developing and testing the GitHub-hosted role `briankearney/ans_dev_sandbox_role`. The project uses **environment variables instead of `ansible.cfg`** for enterprise compliance—never create or suggest `ansible.cfg` files.

### Key Components

- **External Role Testing**: The role under test (`ans_dev_sandbox_role`) is hosted separately on GitHub and pulled via `roles/requirements.yml`. The local `roles/` directory only contains symlinks during development
- **Dual-Target Architecture**: Playbooks run against both `localhost` (connection: local) and `ansible_target` (containerized SSH target on port 2222)
- **Container-Based Testing**: `RUN_PLAYBOOK.bash` orchestrates: building Fedora container → generating ephemeral SSH keys → installing Ansible collections → running playbook
- **Environment-Driven Config**: All Ansible configuration happens via exported variables in `ACTIVATE_SANDBOX_ENV.bash` (session-scoped, auditable)

### Critical Files

- `ACTIVATE_SANDBOX_ENV.bash` - Sources this first; sets up venv, exports ~15 ANSIBLE_* variables, selects Python 3.10-3.12 (excludes 3.13+), removes pytest-ansible to avoid plugin conflicts
- `RUN_PLAYBOOK.bash` - End-to-end workflow script (builds container, generates SSH keys, installs roles/collections, runs playbook)
- `DECRYPT_VAULTED_ITEMS.py` - Utility for inspecting Ansible vault blocks with optional base64 decoding
- `containerfile` - Fedora-based SSH target for Ansible testing (exposes port 22, runs sshd in foreground)
- `inventory/main.yml` - Defines `all` group with `localhost` + `ansible_target` (grouped under `local`)
- `playbooks/sample_playbook.yml` - Reference playbook applying `ans_dev_sandbox_role` to all hosts

## Development Workflows

### Initial Setup

```bash
source ACTIVATE_SANDBOX_ENV.bash              # Creates .venv, exports ANSIBLE_* vars
ansible-galaxy install -r roles/requirements.yml --roles-path roles
```

### Running Playbooks

**Full workflow (container + localhost):**
```bash
./RUN_PLAYBOOK.bash
```

**Localhost only (skip container):**
```bash
source ACTIVATE_SANDBOX_ENV.bash
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -l localhost
```

**Container target only:**
```bash
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -l ansible_target
```

### Testing Strategy

**Unit tests (bash + Python):**
```bash
bash tests/test_activate_sandbox_env.bash      # Tests Python selection logic
bash tests/test_run_playbook.bash              # End-to-end script validation
python3 -m unittest -v test_DECRYPT_VAULTED_ITEMS.py
```

**Molecule scenarios:**
- `molecule/default/` - Core localhost scenario
- `molecule/localhost-only/` - Minimal localhost-only tests
- `molecule/with-linting/` - Includes yamllint + ansible-lint

```bash
source ACTIVATE_SANDBOX_ENV.bash
molecule test -s default                       # Full test sequence
molecule test -s with-linting                  # With lint checks
```

**Linting (run separately since Molecule ≥25 removed lint stage):**
```bash
yamllint .
ansible-lint playbooks/ molecule/
```

### Container Workflow Details

`RUN_PLAYBOOK.bash` uses Podman (prefers) or Docker with SELinux context handling (`:z` flag for Podman). Container lifecycle:
1. Build `ansible_target` image from `containerfile`
2. Generate ephemeral ed25519 SSH key pair in `ssh_keys/`
3. Run container with `ssh_keys/` mounted read-only
4. Install `ansible.posix` and `community.general` collections
5. Execute playbook against both targets
6. Cleanup on exit (container auto-removed via `--rm`)

## Project-Specific Conventions

### Configuration Management

**NEVER create `ansible.cfg`** — explicitly blocked in `.gitignore`. All configuration via environment variables:
- `ANSIBLE_ROLES_PATH=roles`
- `ANSIBLE_VAULT_PASSWORD_FILE=$PLAYBOOK_PATH/vault-pw.txt`
- `ANSIBLE_CALLBACKS_ENABLED='profile_tasks'`
- `ANSIBLE_LOG_PATH=./ansible.log`
- *(See `ACTIVATE_SANDBOX_ENV.bash` lines 22-30 for complete list)*

### Python Version Selection

The activation script auto-selects newest Python **3.10-3.12** (excludes 3.13+). Logic in `select_python()` function:
- Scans `/usr/bin/`, `/usr/local/bin/`, `/opt/*/bin/` for `python3*`
- Parses semantic versions, selects highest `< 3.13.0`
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

During development, `RUN_PLAYBOOK.bash` creates symlink if `roles/` is empty:
```bash
ln -snf ../ans_dev_sandbox_role roles/ans_dev_sandbox_role
```

### Vault Usage

Demo vault password (`password`) stored in `vault-pw.txt` (git-ignored). Decrypt vaulted variables:
```bash
python3 DECRYPT_VAULTED_ITEMS.py --file vars/file.yml --vault-id dev [--decode] [--color]
```

## Integration Points

### External Dependencies

- **Collections**: `ansible.posix`, `community.general` (installed by `RUN_PLAYBOOK.bash`)
- **Container Runtime**: Podman (preferred) or Docker with feature detection
- **Python Packages**: `requirements.txt` includes `molecule`, `molecule-plugins`, `ansible-lint`, `yamllint`, `pygments`, `pytest-testinfra`

### CI/CD Workflows

- `.github/workflows/molecule.yml` - Matrix tests across Molecule scenarios
- `.github/workflows/unit-tests.yml` - Bash + Python unit test execution

## Common Patterns

### Task Cleanup Pattern

Playbooks should clean up temporary resources in `post_tasks`:
```yaml
post_tasks:
  - name: Clean up temporary directory created by ans_dev_sandbox_role
    ansible.builtin.file:
      path: "{{ temp_dir_results.path }}"
      state: absent
    when: temp_dir_results is defined and temp_dir_results.path is defined
    failed_when: false
```

### Inventory Host Variables

Both hosts use `ansible_python_interpreter: auto_silent` to avoid deprecation warnings. Container target requires explicit SSH connection details:
```yaml
ansible_target:
  ansible_host: 127.0.0.1
  ansible_port: 2222
  ansible_user: root
```

### Error Handling in Scripts

Bash scripts use `set -euo pipefail` with trap-based cleanup:
```bash
cleanup() {
    local exit_code=$?
    echo "Cleaning up..."
    "$CONTAINER_RUNTIME" container stop "$CONTAINER_NAME" 2>/dev/null || true
    exit "$exit_code"
}
trap cleanup EXIT
```

## Troubleshooting Context

- **"molecule: command not found"** → Forgot to `source ACTIVATE_SANDBOX_ENV.bash`
- **argparse.ArgumentError with --ansible-inventory** → `pytest-ansible` plugin conflict; activation script auto-removes it
- **Vault decrypt errors** → Verify vault-id matches block header (`vault_id: !vault |`)
- **Container port conflicts** → Default port 2222 may be in use; modify `CONTAINER_HOST_PORT` in `RUN_PLAYBOOK.bash`
- **Python version issues** → Activation script selects 3.10-3.12; install Python 3.12 if needed (3.13+ has pytest plugin conflicts)

## Development Guidelines

1. **Always activate environment first**: `source ACTIVATE_SANDBOX_ENV.bash` before any Ansible commands
2. **Test changes across scenarios**: Run at least `molecule test -s default` before committing
3. **Lint before commit**: Use `yamllint` and `ansible-lint` (not auto-run by Molecule ≥25)
4. **Document vault changes**: Update vault-id references if modifying encrypted variables
5. **Keep role external**: Never inline the role code—it lives in `briankearney/ans_dev_sandbox_role` repo
