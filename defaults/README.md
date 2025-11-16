# defaults/

This directory holds default variable files for playbooks and roles used in this repository.

File of interest:
- `main.yml` — contains example/default variables consumed by the sample playbook and role.

Usage
- Edit `defaults/main.yml` to change default values used by `playbooks/sample_playbook.yml`.
- Variables defined here follow typical Ansible variable precedence for `defaults`.

Notes
- Keep defaults minimal and non-sensitive. Use group/host vars or vault for secrets.
