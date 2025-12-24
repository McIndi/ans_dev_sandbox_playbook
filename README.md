# ans_dev_sandbox_playbook

[![Molecule Tests](https://github.com/briankearney/ans_dev_sandbox_playbook/actions/workflows/molecule.yml/badge.svg)](https://github.com/briankearney/ans_dev_sandbox_playbook/actions/workflows/molecule.yml)
[![Unit Tests](https://github.com/briankearney/ans_dev_sandbox_playbook/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/briankearney/ans_dev_sandbox_playbook/actions/workflows/unit-tests.yml)

Lightweight Ansible playbook sandbox for developing and validating the GitHub-hosted role `briankearney/ans_dev_sandbox_role` using environment‑based configuration, Molecule scenarios, and unit tests.

## Table of Contents

- [Documentation & Wiki](#documentation--wiki)
- [Quick Map](#quick-map)
- [Quick Start](#quick-start)
- [Design Philosophy](#design-philosophy-condensed)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Tutorial: Getting Started](#tutorial-getting-started)
- [Usage Patterns](#usage-patterns)
- [Container Workflow](#container-workflow-brief)
- [Testing & Linting](#testing--linting)
- [Vault Decryption Utility](#vault-decryption-utility)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting-selected)
- [Security & Compliance](#security--compliance)
- [Contributing](#contributing-short)

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

## Quick Start

```bash
git clone https://github.com/briankearney/ans_dev_sandbox_playbook.git
cd ans_dev_sandbox_playbook
python sandbox.py activate
source .venv/bin/activate
python sandbox.py run
```

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

## Installation & Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/briankearney/ans_dev_sandbox_playbook.git
cd ans_dev_sandbox_playbook
```

### Step 2: Activate the Environment

The `sandbox.py activate` command performs several critical setup tasks:
- Automatically selects the best available Python version (>3.9, <3.15)
- Creates a virtual environment (`.venv`)
- Installs all required dependencies from `requirements.txt`
- Generates a `.env` file with ANSIBLE_* environment variables
- Removes conflicting packages (e.g., `pytest-ansible`)

```bash
python sandbox.py activate
```

**Expected output:**
```
✓ Python 3.12.x selected
✓ Virtual environment created at .venv
✓ Dependencies installed
✓ Environment file written to .env
✓ Setup complete
```

### Step 3: Activate the Virtual Environment

```bash
source .venv/bin/activate
```

Your prompt should now show `(.venv)` prefix, indicating the virtual environment is active.

### Step 4: Verify Installation

```bash
# Check Ansible version
ansible --version

# Check Molecule version
molecule --version

# Verify environment variables
cat .env
```

## Tutorial: Getting Started

This tutorial walks you through the complete workflow from initial setup to running your first playbook.

### Tutorial Part 1: Understanding the Environment

The project uses **environment variables** instead of `ansible.cfg` for configuration. This approach:
- Ensures enterprise compliance (many organizations disallow `ansible.cfg`)
- Provides session-scoped, auditable configuration
- Allows easy per-run customization

After running `python sandbox.py activate`, inspect the `.env` file:

```bash
cat .env
```

Key variables you'll see:
```bash
export ANSIBLE_ROLES_PATH=roles
export ANSIBLE_VAULT_PASSWORD_FILE="$PLAYBOOK_PATH/vault-pw.txt"
export ANSIBLE_CALLBACKS_ENABLED='profile_tasks'
export ANSIBLE_LOG_PATH=./ansible.log
export ANSIBLE_HOST_KEY_CHECKING=False
```

### Tutorial Part 2: Running Your First Playbook (Localhost Only)

Start with the simplest workflow—running against localhost only:

```bash
# Ensure the environment is activated
source .venv/bin/activate

# Run against localhost only (no container)
python sandbox.py run --skip-container --limit localhost
```

**What happens:**
1. Installs the `ans_dev_sandbox_role` from GitHub (or uses symlinked local version)
2. Installs required Ansible collections (`ansible.posix`, `community.general`)
3. Executes `playbooks/sample_playbook.yml` against localhost
4. Applies the role and runs post-tasks cleanup

**Expected output:**
```
PLAY [Apply ans_dev_sandbox_role to localhost] ********************************

TASK [ans_dev_sandbox_role : Create temporary directory] **********************
ok: [localhost]

TASK [ans_dev_sandbox_role : Display message] *********************************
ok: [localhost] => {
    "msg": "Hello from sample playbook"
}

PLAY RECAP *********************************************************************
localhost                  : ok=2    changed=0    unreachable=0    failed=0
```

### Tutorial Part 3: Running with Container Target

Now let's run the full workflow with both localhost and a containerized SSH target:

```bash
python sandbox.py run
```

**What happens:**
1. **Generates SSH keys**: Creates ephemeral ed25519 key pair in `ssh_keys/`
2. **Builds container**: Builds Fedora-based image from `containerfile`
3. **Starts container**: Runs `ansible_target` container with SSH on host port 2222
4. **Installs collections**: Ensures `ansible.posix` and `community.general` are available
5. **Installs role**: Installs `ans_dev_sandbox_role` from GitHub or symlinks local version
6. **Runs playbook**: Executes against both `localhost` and `ansible_target`
7. **Cleanup**: Automatically stops and removes container on exit

**Container details:**
- **Name**: `ansible_target`
- **Host port**: `2222` (maps to container port 22)
- **User**: `root`
- **SSH**: Passwordless (uses generated keys)
- **Runtime**: Podman (preferred) or Docker

### Tutorial Part 4: Testing Specific Hosts

You can target specific hosts using the `--limit` flag:

```bash
# Target only the container
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -l ansible_target

# Target only localhost
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -l localhost

# Target a specific group
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -l local
```

### Tutorial Part 5: Overriding Variables

Variables can be overridden at multiple levels:

```bash
# Using extra vars (highest precedence)
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml \
  -e sample_message="Custom message"

# Using a vars file
cat > custom_vars.yml <<'EOF'
sample_message: "Message from vars file"
EOF

ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml \
  -e @custom_vars.yml
```

### Tutorial Part 6: Running Molecule Tests

Molecule provides comprehensive testing of your playbook:

```bash
# Run the default scenario (full test sequence with idempotence)
molecule test -s default

# Run just the converge step (apply the playbook)
molecule converge -s default

# Run verification tests
molecule verify -s default

# Clean up
molecule destroy -s default
```

**Test scenarios available:**
- `default`: Full test with idempotence checking
- `localhost-only`: Tests localhost connection configuration
- `with-linting`: Assumes linting done separately (manual or CI)

### Tutorial Part 7: Working with Vault

Create and use encrypted variables:

```bash
# Create an encrypted string
ansible-vault encrypt_string 'my_secret_value' --name 'my_secret_var'

# Decrypt vaulted items for inspection
python3 DECRYPT_VAULTED_ITEMS.py --file vars/file.yml --vault-id dev

# Decrypt and base64-decode
python3 DECRYPT_VAULTED_ITEMS.py --file vars/file.yml --vault-id dev --decode
```

## Usage Patterns

### Pattern 1: Quick Localhost Testing

```bash
python sandbox.py activate
source .venv/bin/activate
python sandbox.py run --skip-container --limit localhost
```

### Pattern 2: Full Integration Testing

```bash
python sandbox.py activate
source .venv/bin/activate
python sandbox.py run
```

### Pattern 3: Iterative Development

```bash
# Make changes to the role (in sibling directory or via git)

# Test changes quickly (localhost only)
python sandbox.py run --skip-container --limit localhost

# Full test with container when ready
python sandbox.py run

# Run Molecule tests before committing
molecule test -s default
```

### Pattern 4: Custom Container Port

```bash
# Override default port 2222
python sandbox.py run --container-host-port 2223
```

### Pattern 5: Manual Role Installation

```bash
# Install role manually from GitHub
ansible-galaxy install -r roles/requirements.yml --roles-path roles --force

# Or symlink a local development version
ln -snf ../ans_dev_sandbox_role roles/ans_dev_sandbox_role
```

## Container Workflow (Brief)
`python sandbox.py run` builds an image via `containerfile`, starts `ansible_target` (SSH exposed on host port 2222), generates ephemeral `ssh_keys/`, installs required collections (`ansible.posix`, `community.general`), and runs the playbook across `localhost` + `ansible_target` (unless limited). These artifacts are transient.

### Container Lifecycle Details

**Build Phase:**
- Uses `containerfile` (Fedora-based)
- Installs OpenSSH server, Python 3, and basic utilities
- Configures SSH to allow root login with key authentication
- Sets up proper permissions for SSH directories

**Runtime Phase:**
- Container name: `ansible_target`
- Host port mapping: `2222:22` (customizable via `--container-host-port`)
- SSH keys: Generated in `ssh_keys/` (ephemeral, git-ignored)
- Auto-cleanup: Container removed on script exit (via trap)

**Runtime Selection:**
- **Preferred**: Podman (SELinux-friendly mounts)
- **Fallback**: Docker (if Podman unavailable)
- Detection automatic, no configuration needed

**SELinux Considerations:**
When using Podman on SELinux-enabled systems, the script automatically uses `:Z` mount labels for proper container access to host directories.

## Project Structure

```
ans_dev_sandbox_playbook/
├── .github/
│   └── workflows/              # CI/CD workflows (Molecule tests, unit tests)
├── defaults/
│   ├── main.yml                # Convenience variables (loaded via vars_files)
│   └── README.md               # Variable management guide
├── docs/
│   └── TROUBLESHOOTING.md      # Detailed troubleshooting guide
├── inventory/
│   ├── main.yml                # Inventory with localhost + ansible_target
│   └── README.md               # Inventory management guide
├── molecule/
│   ├── default/                # Full test scenario with idempotence
│   ├── localhost-only/         # Localhost connection tests
│   ├── with-linting/           # Linting-focused scenario
│   └── README.md               # Comprehensive testing guide
├── playbooks/
│   ├── sample_playbook.yml     # Example playbook using the role
│   └── README.md               # Playbook usage guide
├── roles/
│   └── requirements.yml        # Role dependencies (GitHub-hosted role)
├── ssh_keys/                   # Generated SSH keys (git-ignored)
├── tests/
│   ├── test_sandbox.py         # Unit tests for sandbox.py
│   ├── test_DECRYPT_VAULTED_ITEMS.py  # Unit tests for vault utility
│   └── README.md               # Testing documentation
├── .ansible-lint               # Ansible lint configuration
├── .env                        # Generated environment variables (git-ignored)
├── .gitignore                  # Excludes .env, .venv, ssh_keys/, etc.
├── .yamllint                   # YAML lint configuration
├── containerfile               # Fedora-based SSH target for testing
├── constraints.txt             # Python package version constraints
├── DECRYPT_VAULTED_ITEMS.py    # Vault decryption utility
├── pytest.ini                  # Pytest configuration
├── README.md                   # This file
├── requirements.txt            # Python dependencies
├── sandbox.py                  # Main CLI (activate/run subcommands)
└── vault-pw.txt                # Demo vault password (git-ignored)
```

### Key File Purposes

| File/Directory | Purpose | Committed to Git |
|----------------|---------|------------------|
| `sandbox.py` | Main CLI for environment setup and playbook execution | Yes |
| `containerfile` | Defines the Fedora-based SSH target container | Yes |
| `DECRYPT_VAULTED_ITEMS.py` | Utility for inspecting encrypted Ansible vault blocks | Yes |
| `.env` | ANSIBLE_* environment variables (session-scoped) | No (generated) |
| `.venv/` | Python virtual environment | No (generated) |
| `ssh_keys/` | Ephemeral SSH keys for container access | No (generated) |
| `vault-pw.txt` | Demo vault password file | No (generated) |
| `inventory/main.yml` | Defines localhost and ansible_target hosts | Yes |
| `playbooks/sample_playbook.yml` | Example playbook applying the role | Yes |
| `roles/requirements.yml` | External role dependency specification | Yes |
| `molecule/` | Test scenarios for validation | Yes |
| `.ansible-lint` | Linting rules and configuration | Yes |
| `.yamllint` | YAML formatting rules | Yes |

## Testing & Linting

### Running Python Unit Tests

Test the CLI and utilities:
```bash
python -m unittest -v tests/test_sandbox.py
python -m unittest -v test_DECRYPT_VAULTED_ITEMS.py
```

**What's tested:**
- Environment activation and `.env` generation
- Python version selection logic
- SSH key generation
- Container runtime detection (Podman/Docker)
- Role and collection installation
- Vault decryption with various options

### Running Molecule Tests

Molecule provides end-to-end playbook testing:

```bash
# Ensure environment is activated first
python sandbox.py activate
source .venv/bin/activate

# Run default scenario (full test with idempotence)
molecule test -s default

# Run specific scenarios
molecule test -s localhost-only
molecule test -s with-linting

# Step-by-step testing (for debugging)
molecule create          # Set up test environment
molecule prepare         # Install dependencies
molecule converge        # Run the playbook
molecule idempotence     # Verify no changes on second run (default only)
molecule verify          # Run verification tests
molecule destroy         # Clean up
```

**Scenario comparison:**

| Scenario | Idempotence Test | Verification Method | Purpose |
|----------|------------------|---------------------|---------|
| `default` | Yes | pytest-testinfra | Complete validation with idempotence |
| `localhost-only` | No | pytest-testinfra | Localhost connection testing |
| `with-linting` | No | Ansible-based | Assumes linting done separately |

### Running Linters

**Note**: Molecule ≥25 removed the built-in `lint` command. Run linters separately:

```bash
# YAML linting
yamllint .

# Ansible linting
ansible-lint playbooks/ molecule/

# Run both together
yamllint . && ansible-lint playbooks/ molecule/
```

**Lint configuration:**
- **ansible-lint**: Production profile, line length 160, excludes external roles
- **yamllint**: 2-space indentation, line length 160, document-start required

### CI/CD Integration

GitHub Actions automatically runs:
- **Molecule tests**: All scenarios across Python 3.10-3.14
- **Unit tests**: Python unit tests across supported versions
- **Linting**: Separate lint job validates YAML and Ansible syntax

View results at: [Actions Tab](https://github.com/briankearney/ans_dev_sandbox_playbook/actions)

## Vault Decryption Utility

The `DECRYPT_VAULTED_ITEMS.py` utility helps inspect and debug encrypted Ansible vault variables.

### Basic Usage

```bash
# Decrypt variables in a file
python3 DECRYPT_VAULTED_ITEMS.py --file path/to/vars.yml --vault-id dev

# Decrypt and base64-decode the result
python3 DECRYPT_VAULTED_ITEMS.py --file path/to/vars.yml --vault-id dev --decode

# Disable colorized output
python3 DECRYPT_VAULTED_ITEMS.py --file path/to/vars.yml --vault-id dev --no-color
```

### Features

- **Multiple vault-id support**: Specify which vault identity to use
- **Base64 decoding**: Optionally decode base64-encoded secrets
- **Colorized output**: Highlights decrypted values (disable with `--no-color`)
- **Graceful error handling**: Clear messages for missing files or wrong passwords
- **Multiple variable detection**: Processes all vaulted blocks in a file

### Example Workflow

**1. Create a vaulted variable:**
```bash
ansible-vault encrypt_string 'my_secret_password' --name 'db_password' > vars/secrets.yml
```

**2. Inspect the encrypted value:**
```bash
python3 DECRYPT_VAULTED_ITEMS.py --file vars/secrets.yml --vault-id dev
```

**Output:**
```
Decrypted variables from vars/secrets.yml:
  db_password: my_secret_password
```

**3. For base64-encoded secrets:**
```bash
# Create base64-encoded secret
echo -n "my_secret" | base64  # => bXlfc2VjcmV0
ansible-vault encrypt_string 'bXlfc2VjcmV0' --name 'encoded_secret' > vars/encoded.yml

# Decrypt and decode
python3 DECRYPT_VAULTED_ITEMS.py --file vars/encoded.yml --vault-id dev --decode
```

### Vault Password Management

By default, the utility looks for `vault-pw.txt` in the current directory (demo password: `password`).

For production use:
```bash
# Use a different password file
export ANSIBLE_VAULT_PASSWORD_FILE=/secure/path/to/vault-pass.txt
python3 DECRYPT_VAULTED_ITEMS.py --file vars/secrets.yml --vault-id production
```

## Inventory Notes
`inventory/main.yml` includes both `localhost` (connection local) and `ansible_target` (container host with forwarded SSH on port 2222). Use `-l` to scope runs.

## Dynamic / Demo Artefacts
- `ssh_keys/` created only by `python sandbox.py run` (excluded from repo)
- `vault-pw.txt` demo password file—replace or manage securely in production
- Temporary virtualenv `.venv` created automatically, removable at will

## Troubleshooting (Selected)

For comprehensive troubleshooting, see [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

### Common Issues

| Symptom | Cause | Resolution |
|---------|-------|-----------|
| `molecule: command not found` | Virtual environment not activated | Run `python sandbox.py activate` then `source .venv/bin/activate` |
| `ansible-galaxy: command not found` | Dependencies not installed | Run `python sandbox.py activate` to install all dependencies |
| Container port conflict (address already in use) | Port 2222 occupied | Use `python sandbox.py run --container-host-port 2223` or stop conflicting service |
| Role not found | Role not installed | Run `ansible-galaxy install -r roles/requirements.yml --roles-path roles --force` |
| Idempotence test fails | Task not idempotent | Review task for `changed_when` conditions or use proper module state |
| Vault decrypt error | Wrong vault ID or password | Verify vault block header matches `--vault-id` and check `vault-pw.txt` |
| Python version unexpected | Wrong interpreter selected | Install Python 3.10-3.14, then run `python sandbox.py activate` again |
| SSH connection refused to container | Container not running | Verify container with `podman ps` or `docker ps`, restart with `python sandbox.py run` |
| SELinux denials on container mounts | Incorrect mount labels | Use Podman (auto-handles `:Z` labels) or adjust SELinux policy |
| `pytest-ansible` conflict | Plugin incompatibility | Run `python sandbox.py activate` (auto-removes pytest-ansible) |

### Profile Tasks Deprecation Warning

**Warning message:**
```
[DEPRECATION WARNING]: The 'ansible.posix.profile_tasks' callback plugin implements 
the following deprecated method(s): playbook_on_stats. This feature will be removed 
from the callback plugin API in ansible-core version 2.23.
```

**Explanation:**
The `ansible.posix.profile_tasks` callback plugin maintains a legacy `playbook_on_stats` method for backward compatibility, even though it implements the newer `v2_*` callback hooks.

**Action:**
- **Safe to ignore** while keeping the callback enabled
- **Optional**: Pin `ansible-core<2.23` in `requirements.txt` until ansible.posix removes the shim
- Does not affect functionality or test results

### Debug Commands

```bash
# Check Python version being used
which python3
python3 --version

# Verify Ansible installation
ansible --version
ansible-galaxy collection list

# Check container runtime
podman --version   # or docker --version

# Verify role installation
ls -la roles/

# Check environment variables
cat .env

# View Ansible logs
tail -f ansible.log

# Test container connectivity
ssh -p 2222 -i ssh_keys/ansible_target_key root@127.0.0.1

# Verify inventory
ansible-inventory -i inventory/main.yml --graph
ansible-inventory -i inventory/main.yml --list

# Test playbook syntax
ansible-playbook --syntax-check -i inventory/main.yml playbooks/sample_playbook.yml
```

### Getting Help

1. Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for detailed solutions
2. Review GitHub Actions workflow runs for CI/CD issues
3. Examine `ansible.log` for detailed execution logs
4. Run with increased verbosity: `ansible-playbook ... -vvv`
5. Check Molecule logs in `molecule/<scenario>/` directories

## Security & Compliance

### No Persistent Configuration Files

This project deliberately **avoids using `ansible.cfg`** to comply with enterprise security policies:
- `ansible.cfg` is explicitly blocked in `.gitignore`
- All configuration uses environment variables in `.env`
- Configuration is session-scoped and fully auditable
- Each activation generates fresh configuration

### Demo Credentials

** Security Notice**: This project includes demo credentials for development only:
- Vault password: `password` (stored in `vault-pw.txt`)
- SSH keys: Ephemeral, generated per run
- Container access: Local-only, not exposed to network

**For production use:**
1. Replace demo vault password with secure credential
2. Use proper secret management (HashiCorp Vault, AWS Secrets Manager, etc.)
3. Implement proper SSH key management
4. Follow your organization's security policies

### Environment Variable Security

The `.env` file contains sensitive paths and configuration:
```bash
export ANSIBLE_VAULT_PASSWORD_FILE="$PLAYBOOK_PATH/vault-pw.txt"
export ANSIBLE_HOST_KEY_CHECKING=False
```

**Best practices:**
- Never commit `.env` to version control (enforced by `.gitignore`)
- Regenerate `.env` for each development session
- Review environment variables before sharing terminal output
- Use separate vault passwords for different environments (dev/staging/prod)

### Container Security

**Development containers:**
- Root user access (for testing only)
- Host key checking disabled (development convenience)
- SSH port exposed only to localhost
- Auto-cleanup on exit (ephemeral containers)

**Production recommendations:**
- Use non-root users in containers
- Enable host key checking
- Implement proper SSH hardening
- Use secrets management for SSH keys
- Enable SELinux/AppArmor policies

## Contributing (Short)

### Contribution Workflow

1. **Fork and branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes** following project conventions:
   - Use 2-space indentation for YAML
   - Document start (`---`) required, no document end
   - Line length: 160 characters
   - Follow ansible-lint production profile

3. **Test your changes:**
   ```bash
   # Unit tests
   python -m unittest -v tests/test_sandbox.py
   
   # Linting
   yamllint .
   ansible-lint playbooks/ molecule/
   
   # Molecule tests
   molecule test -s default
   molecule test -s localhost-only
   ```

4. **Commit with clear messages:**
   ```bash
   git commit -m "feat: add new feature description"
   git commit -m "fix: resolve issue with specific component"
   git commit -m "docs: update README with new section"
   ```

5. **Open Pull Request:**
   - Provide clear description of changes
   - Reference related issues
   - Include test results
   - Update documentation as needed

### Development Guidelines

**Code Standards:**
- Follow existing code style and patterns
- Add tests for new functionality
- Update documentation for user-facing changes
- Keep commits atomic and well-described

**Testing Requirements:**
- All unit tests must pass
- Molecule tests must pass for all scenarios
- Linting must pass (yamllint and ansible-lint)
- Idempotence test must pass for playbook changes

**Documentation:**
- Update README.md for significant changes
- Add inline comments for complex logic
- Update troubleshooting section for common issues
- Keep wiki documentation in sync

### Reporting Issues

When reporting bugs or issues:
1. Check existing issues first
2. Provide clear reproduction steps
3. Include environment details (OS, Python version, Ansible version)
4. Attach relevant logs (`ansible.log`, Molecule output)
5. Describe expected vs actual behavior

---

## Additional Resources

- [Ansible Documentation](https://docs.ansible.com/)
- [Molecule Documentation](https://ansible.readthedocs.io/projects/molecule/)
- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html)
- [YAML Specification](https://yaml.org/spec/1.2/spec.html)
- [Project Wiki](https://github.com/briankearney/ans_dev_sandbox_playbook/wiki)

## License

See [LICENSE](LICENSE) file for details.
