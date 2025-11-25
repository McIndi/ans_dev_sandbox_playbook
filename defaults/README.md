# defaults/

Convenience variable file (not a role `defaults/` directory). Must be explicitly loaded via `vars_files`.

File of interest:
- `main.yml` — defines `sample_message`, matching the override already present in `sample_playbook.yml` (kept simple for illustration).

Usage
- If you want these values applied, include them explicitly:
	```yaml
	# Inside a playbook
	- hosts: local
		vars_files:
			- ../defaults/main.yml
		roles:
			- ans_dev_sandbox_role
	```
- Otherwise rely on the role's own `defaults/` directory for intrinsic defaults.
- Edit `defaults/main.yml` to experiment with different values without modifying the role.

Notes
- Keep values minimal & non-sensitive; put secrets in vaulted host/group vars.
- To promote a variable to the role's intrinsic defaults, move it into the role’s `defaults/main.yml`.
- Precedence: if included via `vars_files`, these values override role defaults but remain below play vars and extra vars.
