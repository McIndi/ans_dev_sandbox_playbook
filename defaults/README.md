# defaults/

Convenience variables for experiments and tutorials. This is not the role’s intrinsic `defaults/`; include it explicitly via `vars_files` when you want its values applied.

## File
- `main.yml` – contains simple variables like `sample_message` used by the sample playbook.

## Quick Start

```bash
python sandbox.py activate
source .venv/bin/activate
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -l localhost
```

## Override Patterns
- Extra vars override everything in this repo context:

```bash
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml \
  -e sample_message="Hello from -e"
```

- Play vars (`vars:` in a play) override this file.
- Role defaults (inside the external role) are overridden by values loaded via `vars_files`.

## Best Practices
- Keep values non-sensitive here; use vaulted host/group vars for secrets.
- Treat this file as a sandbox for trying different values without editing the external role.
- If a variable becomes intrinsic to the role, move it into the role’s `defaults/main.yml` in the role repository.

## Troubleshooting
- If values don’t seem to apply, ensure the play includes `vars_files: ../defaults/main.yml`.
- Use `ansible-inventory --graph -i inventory/main.yml` to confirm hosts and scope, then try `-l localhost` to target the play correctly.
