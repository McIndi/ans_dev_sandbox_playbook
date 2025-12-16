# Molecule Scenario: with-linting

## Known Warning
[DEPRECATION WARNING]: The 'ansible.posix.profile_tasks' callback plugin implements the following deprecated method(s): playbook_on_stats. This feature will be removed from the callback plugin API in ansible-core version 2.23. Implement the `v2_*` equivalent callback method(s) instead.

Cause: `ansible.posix.profile_tasks` retains a legacy `playbook_on_stats` shim for backward compatibility even though it implements v2 hooks. Action: Safe to ignore while keeping the callback enabled; optionally pin `ansible-core<2.23` until ansible.posix removes the shim and the warning disappears.
