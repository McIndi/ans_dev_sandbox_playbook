# Troubleshooting Guide

## Common Issues and Solutions

### `molecule verify` fails with argparse.ArgumentError

**Error Message:**
```
argparse.ArgumentError: argument --inventory/--ansible-inventory: conflicting option string: --ansible-inventory
ERROR    Verifier tests failed
```

**Cause:**
The `pytest-ansible` and `pytest-testinfra` plugins both register the same command-line argument (`--inventory` / `--ansible-inventory`), causing a conflict during pytest initialization. This affects Python 3.12+ due to stricter argparse validation.

**Solution:**
The activation script (`ACTIVATE_SANDBOX_ENV.bash`) automatically uninstalls `pytest-ansible` after installing dependencies. This is the recommended approach since:
- We only need `pytest-testinfra` for Molecule verify steps
- The `pytest-ansible` plugin is not used in our test scenarios
- Removing it has no impact on other Ansible functionality

**Manual Fix:**
If you encounter this error:
```bash
pip uninstall -y pytest-ansible
```

**Prevention:**
Always use `source ACTIVATE_SANDBOX_ENV.bash` to set up your environment. The script handles this automatically.

### Python Version Issues

**Issue:** Virtual environment created with Python 3.13 or higher

**Solution:**
The project requires Python 3.10-3.12 due to the pytest plugin conflict mentioned above. The activation script automatically selects the newest compatible version. If you need to recreate your environment:

```bash
deactivate
rm -rf .venv
source ACTIVATE_SANDBOX_ENV.bash
```

The script will automatically choose the best available Python version (3.10-3.12).

### Container Port Conflicts

**Error:** Port 2222 already in use when running `RUN_PLAYBOOK.bash`

**Solution:**
Edit `RUN_PLAYBOOK.bash` and modify the `CONTAINER_HOST_PORT` variable to use a different port:

```bash
CONTAINER_HOST_PORT=2223  # or any available port
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

These are automatically installed by `RUN_PLAYBOOK.bash` but may be needed for manual playbook runs.

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

1. Check that your environment is activated: `source ACTIVATE_SANDBOX_ENV.bash`
2. Verify Python version: `python --version` (should be 3.10-3.12)
3. Check for conflicting packages: `pip list | grep pytest`
4. Review logs: `cat ansible.log`
5. Run with verbose output: `molecule --debug verify -s default`

For plugin conflicts or package issues, recreate the virtual environment as described above.
