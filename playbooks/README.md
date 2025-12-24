# playbooks/

Example playbooks that apply the external role across `localhost` and the optional container target.

## File
`sample_playbook.yml` targets `hosts: all`. Limit with `-l` for faster iteration.

## Quick Start
```bash
python sandbox.py activate
source .venv/bin/activate
python sandbox.py run
```

Limit to specific hosts:
```bash
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -l ansible_target
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -l localhost
```

Syntax check:
```bash
ansible-playbook --syntax-check -i inventory/main.yml playbooks/sample_playbook.yml
```

## Variable Precedence (High → Low)
1. Extra vars (`-e`)
2. Play vars (`vars:`)
3. Role vars (`vars/` inside the role)
4. Role defaults (`defaults/` inside the role)
5. External files loaded via `vars_files` (e.g. `../defaults/main.yml` – only when referenced)

Override example:
```bash
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml \
  -e repo_clone_depth=1 -e enable_cleanup=true
```

Vars file example:
```bash
cat > custom_vars.yml <<'EOF'
repo_clone_depth: 1
EOF

ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -e @custom_vars.yml
```

## Vaulted Data
Create an encrypted string, then include it in a vars file:
```bash
ansible-vault encrypt_string 'supersecret' --name 'vault_example_password'
python3 DECRYPT_VAULTED_ITEMS.py --file path/to/vars.yml --vault-id dev
```

## Post Tasks
`post_tasks` in the sample playbook cleans up temporary role output to ensure idempotence. Adjust as the role evolves.

## Troubleshooting
- Role not found: re-run `ansible-galaxy install -r roles/requirements.yml --roles-path roles --force`.
- Overrides ignored: confirm precedence or use `-e` for highest priority.
- Vault errors: ensure the correct `--vault-id` and password file.
- Idempotence changes: use declarative module states or `changed_when` when appropriate.
- Profile tasks deprecation warning: safe to ignore; pin `ansible-core<2.23` if preferred.


