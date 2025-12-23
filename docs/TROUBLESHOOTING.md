# Troubleshooting Guide

## Common Issues and Solutions

### Podman Database Configuration Mismatch (Ubuntu + Snap VS Code)

**Symptom:**
```
Error: database configuration mismatch: static directory "/path/A" does not match current configuration "/path/B"
```
or
```
Error: database configuration mismatch: graphroot "/path/A" does not match current configuration "/path/B"
```

**Root Cause:**
This error occurs when Podman's stored database paths don't match the current runtime environment, commonly caused by:
- VS Code installed via Snap creating isolated filesystem namespaces
- Podman storing absolute paths in `~/.local/share/containers/storage/libpod/bolt_state.db`
- Home directory path changes or Snap confinement causing stored paths to become invalid
- User account changes or system migrations that altered the home directory structure

**Solutions (in order of preference):**

#### Solution 1: Reset Podman Storage (Destructive but Fast)

⚠️ **WARNING:** This destroys all containers, images, and volumes.

```bash
podman system reset
```

After reset, verify Podman is working:
```bash
podman info | grep -A5 graphRoot
podman run --rm hello-world
```

#### Solution 2: Manual Configuration Fix (Preserves Data)

This approach keeps your existing containers and images.

```bash
# 1. View the current path mismatch
podman info 2>&1 | grep -A10 "mismatch"

# 2. Check current storage configuration
cat ~/.config/containers/storage.conf

# 3. Edit storage config to match runtime paths shown in the error
vim ~/.config/containers/storage.conf

# Update these fields to match the paths shown in the error message:
# [storage]
# driver = "overlay"
# graphroot = "/home/username/.local/share/containers/storage"  # Update this path
# runroot = "/run/user/1000/containers"                          # Update if needed

# 4. Also check and update static_dir if present
# static_dir = "/home/username/.local/share/containers/storage"  # Update this path
```

After editing, verify the fix:
```bash
podman info | grep -A5 graphRoot
podman ps -a  # Should list containers without errors
```

#### Solution 3: Switch VS Code Installation Method (Root Cause Fix)

Replace Snap-based VS Code with the native .deb package to avoid filesystem namespace issues.

```bash
# Remove Snap version
sudo snap remove code

# Install native .deb package from Microsoft repository
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
sudo install -D -o root -g root -m 644 packages.microsoft.gpg /etc/apt/keyrings/packages.microsoft.gpg
echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" | sudo tee /etc/apt/sources.list.d/vscode.list
sudo apt update && sudo apt install code

# Clean up
rm -f packages.microsoft.gpg
```

After reinstalling VS Code, test Podman:
```bash
podman info | grep -A5 graphRoot
python sandbox.py run  # Test with project
```

#### Solution 4: Alternative - Use Docker Instead

If Podman continues to have issues, the project supports Docker as well:

```bash
# Install Docker (if not already installed)
sudo apt update
sudo apt install docker.io
sudo usermod -aG docker $USER
newgrp docker  # Or log out and back in

# Verify Docker works
docker info
python sandbox.py run  # CLI auto-detects Docker
```

**Verification Steps:**

After applying any solution:

```bash
# 1. Check Podman configuration is consistent
podman info | grep -E "(graphRoot|runRoot|static)"

# 2. Test basic container operations
podman run --rm alpine:latest echo "Podman is working"

# 3. Run the project's container workflow
python sandbox.py run

# 4. Verify container networking
podman ps -a
```

**Prevention Tips:**

- **Use native package managers** (apt, dnf) over Snap for development tools
- **Avoid changing home directory paths** after Podman initialization
- **Document your VS Code installation method** in team onboarding
- **Consider adding `podman system reset`** to onboarding docs if team uses mixed installations
- **Regular backups**: Export important containers with `podman save` before major system changes

**Related Issues:**

- If you see "permission denied" errors after switching VS Code installations, check directory ownership:
  ```bash
  ls -la ~/.local/share/containers/
  # Should be owned by your user, not root
  ```

- If containers exist but are inaccessible, check the database directly:
  ```bash
  file ~/.local/share/containers/storage/libpod/bolt_state.db
  # Should be a Berkeley DB file
  ```

### `molecule verify` fails with argparse.ArgumentError

**Error Message:**
```
argparse.ArgumentError: argument --inventory/--ansible-inventory: conflicting option string: --ansible-inventory
ERROR    Verifier tests failed
```

**Cause:**
The `pytest-ansible` and `pytest-testinfra` plugins both register the same command-line argument (`--inventory` / `--ansible-inventory`), causing a conflict during pytest initialization. This affects Python 3.12+ due to stricter argparse validation.

**Solution:**
`python sandbox.py activate` installs dependencies and then removes `pytest-ansible` to prevent this clash because:
- We only need `pytest-testinfra` for Molecule verify steps
- The `pytest-ansible` plugin is not used in our test scenarios
- Removing it has no impact on other Ansible functionality

**Manual Fix:**
If you encounter this error:
```bash
pip uninstall -y pytest-ansible
```

**Prevention:**
Run `python sandbox.py activate` (and `source .venv/bin/activate` when needed) before Molecule or pytest.

### Python Version Issues

**Issue:** Virtual environment created with Python 3.13 or higher

**Solution:**
The project supports Python >3.9 and <3.15 due to historical pytest plugin conflicts mitigated by our environment setup. `python sandbox.py activate` automatically selects the newest compatible version available on your system. If you need to recreate your environment:

```bash
deactivate
rm -rf .venv
python sandbox.py activate
source .venv/bin/activate
```

The CLI will automatically choose the best available Python version (typically 3.10–3.14).

### Container Port Conflicts

**Error:** Port 2222 already in use when running `python sandbox.py run`

**Solution:**
Override the port when running or adjust `.env`:

```bash
python sandbox.py run --container-host-port 2223  # or any available port
# or edit CONTAINER_HOST_PORT in .env then rerun
```

### Molecule Config Warnings

**Warning:**
```
WARNING  default ➜ config: The scenario config file has been modified since the scenario was created
```

**Solution:**
This warning appears when the molecule.yml file changes after creating a scenario. To clear it:

```bash
molecule destroy -s default  # Clean up scenario
# or
molecule reset -s default    # Reset configuration without destroying instances
```

### Vault Decryption Failures

**Issue:** Cannot decrypt vaulted variables

**Checklist:**
1. Verify vault password file exists: `ls -la vault-pw.txt`
2. Check vault-id matches in the vaulted block (e.g., `vault_id: !vault |`)
3. Ensure `ANSIBLE_VAULT_PASSWORD_FILE` is set (automatically done by activation script)
4. Use the decrypt utility: `python DECRYPT_VAULTED_ITEMS.py --file vars/file.yml --vault-id dev`

### Missing Collections

**Error:** Collection not found during playbook execution

**Solution:**
Install required collections:
```bash
ansible-galaxy collection install -r requirements.txt  # If collections are in requirements.txt
# or
ansible-galaxy collection install ansible.posix community.general
```

These are automatically installed by `python sandbox.py run` but may be needed for manual playbook runs.

### Role Not Found

**Error:** Role 'ans_dev_sandbox_role' not found

**Solution:**
Install the external role:
```bash
ansible-galaxy install -r roles/requirements.yml --roles-path roles
```

During development, if you have the role locally, create a symlink:
```bash
ln -snf ../ans_dev_sandbox_role roles/ans_dev_sandbox_role
```

## Getting Help

If you encounter an issue not covered here:

1. Check that your environment is activated: `python sandbox.py activate` then `source .venv/bin/activate`
2. Verify Python version: `python --version` (should be within >3.9 and <3.15)
3. Check for conflicting packages: `pip list | grep pytest`
4. Review logs: `cat ansible.log`
5. Run with verbose output: `molecule --debug verify -s default`

For plugin conflicts or package issues, recreate the virtual environment as described above.
