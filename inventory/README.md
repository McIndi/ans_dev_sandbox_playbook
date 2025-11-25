# inventory/

Sample YAML inventory consumed by the playbook and Molecule scenarios.

## File
`main.yml` (excerpt matches repository):
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

`ansible_target` is created by `RUN_PLAYBOOK.bash` (container with SSH forwarded to host port 2222). Keys are generated dynamically under `ssh_keys/`.

## Usage
```bash
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml        # all hosts
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -l localhost
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -l ansible_target
```

## Extending
Add new hosts under `all.hosts` or group them under additional children. Use `ansible-inventory --graph` to visualize.

## Notes
- `auto_silent` suppresses interpreter warnings.
- Limit scope with `-l` to speed iteration.

## Troubleshooting (Quick)
| Issue | Cause | Action |
|-------|-------|--------|
| Host unreachable | Port / container not running | Re-run `./RUN_PLAYBOOK.bash` or check port 2222 |
| Wrong vars applied | Group precedence confusion | Inspect with `ansible-inventory --host <name>` |
| Python warnings | Missing interpreter hint | Ensure `auto_silent` present |
