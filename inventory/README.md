# inventory/

This directory contains the sample inventory used by the example playbook.

File of interest:
- `main.yml` — a YAML inventory that defines `localhost` and a `local` group.

Usage
- Run the sample playbook with this inventory:

```bash
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml
```

Notes
- The `ansible_connection: local` entry makes the playbook run directly on the control node for quick testing.
