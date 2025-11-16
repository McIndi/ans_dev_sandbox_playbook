# ans_dev_sandbox_playbook
Ansible Playbook Sandbox

## Sample: playbook using briankearney/ans_dev_sandbox_role

This repository includes a small sample playbook and inventory that demonstrates how to run the GitHub-hosted role `briankearney/ans_dev_sandbox_role` locally.

Files added:
- `playbooks/sample_playbook.yml` — example play that applies the role to `localhost`.
`inventory/main.yml` — simple inventory with a `local` group.
- `requirements.yml` — used by `ansible-galaxy` to install the role from GitHub.
- `ansible.cfg` — config that sets `roles_path` to `./roles` and points to the sample inventory.

Quick run (from repo root):

```bash
# install the role into ./roles
ansible-galaxy install -r requirements.yml --roles-path ./roles

# run the sample playbook against localhost
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml
# ans_dev_sandbox_playbook

An Ansible playbook sandbox that demonstrates running a GitHub-hosted role locally against `localhost`.

This repository is intentionally small and aims to provide a convenience environment for developing and testing the
`briankearney/ans_dev_sandbox_role` role.

**Quick Overview**
- **Playbook:** `playbooks/sample_playbook.yml`
- **Inventory:** `inventory/main.yml` (defines a `local` group with `localhost`)
- **Role requirements:** `roles/requirements.yml` (used by `ansible-galaxy` to fetch the role into `./roles`)
- **Helper scripts:** `ACTIVATE_SANDBOX_ENV.bash`, `RUN_PLAYBOOK.bash`, `DECRYPT_VAULTED_ITEMS.py`

**Prerequisites**
- Ansible (recommended 2.9+ or a recent 2.14+ depending on your environment)
- Python virtual environment (optional but recommended)

Quickstart (from repository root):

```bash
# Option A: activate provided virtualenv (if present)
source .venv/bin/activate
# or use the helper script
source ACTIVATE_SANDBOX_ENV.bash

# Install the role into ./roles using the requirements file
ansible-galaxy install -r roles/requirements.yml --roles-path ./roles

# Run the sample playbook against the sample inventory
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml
```

Alternate helper (wrapper):

```bash
# Make the wrapper executable then run it
chmod +x RUN_PLAYBOOK.bash
./RUN_PLAYBOOK.bash
```

Notes
- If this repository uses vaulted variables, use `DECRYPT_VAULTED_ITEMS.py` to assist with decryption workflows (see the script for usage).
- You can edit example variables in `defaults/main.yml` or in the `vars:` block of `playbooks/sample_playbook.yml`.

Files and directories
- `defaults/` : playbook default variables
- `inventory/` : sample inventory used by the playbook
- `playbooks/` : sample playbooks that call the role
- `roles/requirements.yml` : role source for `ansible-galaxy`

If you want, I can also add README files inside each subdirectory explaining their purpose and showing examples. 
