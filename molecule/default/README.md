# Molecule Scenario: default

Validate the full playbook workflow end-to-end with idempotence checks and testinfra verification.

## Purpose
- Runs the complete Molecule sequence: dependency → syntax → create → prepare → converge → idempotence → verify → cleanup → destroy
- Ensures tasks are idempotent (second run makes no changes)
- Verifies system state using pytest-testinfra

## Prerequisites
- Use the repo’s managed environment:

```bash
python sandbox.py activate
source .venv/bin/activate
```

## Quick Start

```bash
# Full test sequence (recommended)
molecule test -s default

# Iterate faster: just run converge → verify
molecule converge -s default
molecule verify -s default

# Clean up
molecule destroy -s default
```

## What This Scenario Tests
- Role installation via `roles/requirements.yml`
- Playbook execution against localhost and container target when present
- Variable handling and precedence
- Idempotence: the second run reports `changed=0`
- Verification: Python availability, Ansible connectivity, cleanup behavior

## Expected Outputs
- Converge run completes without failures
- Idempotence step shows no changes
- Verify step passes all pytest-testinfra tests

## Troubleshooting
- Re-activate environment if Molecule/Ansible aren't found:

```bash
python sandbox.py activate
source .venv/bin/activate
```

- Ensure container target is available (if the play references it):

```bash
python sandbox.py run
```

- Run with verbose logs for debugging:

```bash
molecule --debug test -s default
molecule converge -s default -- -vvv
```

## Known Warning
You may see:

> [DEPRECATION WARNING]: The 'ansible.posix.profile_tasks' callback plugin implements the following deprecated method(s): playbook_on_stats. This feature will be removed from the callback plugin API in ansible-core version 2.23.

Cause: `ansible.posix.profile_tasks` retains a legacy `playbook_on_stats` shim for backward compatibility even though it implements v2 hooks.

Action: Safe to ignore while keeping the callback enabled; optionally pin `ansible-core<2.23` until ansible.posix removes the shim.
