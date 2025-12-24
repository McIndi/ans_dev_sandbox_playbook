# inventory/

Inventory groups both `localhost` (connection: local) and an optional container target (`ansible_target`) for dual‑target testing.

## File
`main.yml` defines hosts and the `local` group:

```yaml
---
all:
  hosts:
    localhost:
      ansible_connection: local
      ansible_python_interpreter: auto_silent
    ansible_target:
      ansible_host: 127.0.0.1
      ansible_port: 2222
      ansible_python_interpreter: auto_silent
      ansible_user: root
  children:
    local:
      hosts:
        localhost: {}
        ansible_target: {}
```

`ansible_target` is created by `python sandbox.py run` and exposes SSH on host port 2222. Ephemeral keys are generated in `ssh_keys/`.

## Quick Start

```bash
# Run against all hosts
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml

# Limit to localhost
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -l localhost

# Limit to container target
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -l ansible_target

# Visualize inventory
ansible-inventory -i inventory/main.yml --graph
ansible-inventory -i inventory/main.yml --list
```

## Extending
Add hosts under `all.hosts` or new children groups. Keep `auto_silent` for Python interpreter detection to avoid warnings.

## Troubleshooting
- Host unreachable: verify container is running or re-run `python sandbox.py run`.
- Wrong variables applied: inspect precedence with `ansible-inventory --host <name>`.
- Python interpreter warnings: ensure `ansible_python_interpreter: auto_silent` is set.
- Profile tasks deprecation warning: safe to ignore; pin `ansible-core<2.23` if you prefer to suppress it.
