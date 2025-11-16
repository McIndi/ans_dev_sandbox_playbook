# playbooks/

This directory contains example playbooks that consume roles and variables in this repo.

File of interest:
- `sample_playbook.yml` — applies the `ans_dev_sandbox_role` to hosts defined in `inventory/main.yml`.

Usage

```bash
# from repo root
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml
```

Customization
- Edit the `vars:` block in `sample_playbook.yml` to override defaults or provide example inputs to the role.
- The playbook includes a `post_tasks` step to clean up temporary work created by the role.
