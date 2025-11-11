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
```

You can tweak variables passed to the role in `playbooks/sample_playbook.yml` under the `vars:` block.
