# playbooks/

For playbook structure, usage patterns, and advanced examples, see the [Playbooks](https://github.com/briankearney/ans_dev_sandbox_playbook/wiki/Playbooks) section of the [project wiki](https://github.com/briankearney/ans_dev_sandbox_playbook/wiki).

Example playbook(s) consuming the sandbox role.

## File
`sample_playbook.yml` targets `hosts: all` (both `localhost` and `ansible_target` if container running). Override or limit with `-l` as needed.

## Basic Run
```bash
source ACTIVATE_SANDBOX_ENV.bash
ansible-galaxy install -r roles/requirements.yml --roles-path roles
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml
```
Limit to the container host only:
```bash
ansible-playbook -i inventory/main.yml playbooks/sample_playbook.yml -l ansible_target
```

## Variable Precedence (High → Low, subset)
1. Extra vars (`-e` / `--extra-vars`)
2. Play vars (`vars:` in playbook)
3. Role vars (`vars/` inside role)
4. Role defaults (`defaults/` inside role)
5. External files loaded via `vars_files` (e.g. `../defaults/main.yml`) — only if explicitly referenced

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
Create encrypted string:
```bash
ansible-vault encrypt_string 'supersecret' --name 'vault_example_password'
```
Include block in a vars file; inspect with:
```bash
python3 DECRYPT_VAULTED_ITEMS.py --file path/to/vars.yml --vault-id dev
```
See root `README.md` for the vault utility overview.

## Post Tasks
`post_tasks` cleans up temporary role output for idempotence. Adjust cleanup logic as role evolves.

## Troubleshooting (Quick)
| Issue | Cause | Action |
|-------|-------|--------|
| Role not found | Not installed | Re-run `ansible-galaxy install ...` |
| Override ignored | Precedence confusion | Use `-e` or move var to higher layer |
| Vault failure | Wrong id/password | Check vault label & password file |
| Idempotence change | Task not declarative | Use module state / set `changed_when` |
| [DEPRECATION WARNING]: The 'ansible.posix.profile_tasks' callback plugin implements the following deprecated method(s): playbook_on_stats. This feature will be removed from the callback plugin API in ansible-core version 2.23. Implement the `v2_*` equivalent callback method(s) instead. | `ansible.posix.profile_tasks` keeps a legacy `playbook_on_stats` shim for backward compatibility even though it implements v2 hooks | Safe to ignore while keeping the callback; optionally pin `ansible-core<2.23` until ansible.posix removes the shim and the warning disappears |


