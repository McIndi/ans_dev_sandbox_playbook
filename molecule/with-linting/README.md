# Molecule Scenario: with-linting

Demonstrates that linting is performed separately (manual or CI) prior to scenario execution; focuses on playbook converge + verify.

## Purpose
- Reinforces workflow where `yamllint` and `ansible-lint` run outside Molecule (Molecule ≥25 removed built-in lint stage)
- Validates that the playbook continues to converge and verify after linting passes

## Prerequisites
- Activate environment and run linters:

```bash
python sandbox.py activate
source .venv/bin/activate

# Lint separately
yamllint .
ansible-lint playbooks/ molecule/
```

## Quick Start

```bash
molecule test -s with-linting

# Focused iteration
molecule converge -s with-linting
molecule verify -s with-linting
molecule destroy -s with-linting
```

## Troubleshooting
- If linting fails, address issues, then re-run this scenario.
- Use verbose Molecule output for debugging:

```bash
molecule --debug test -s with-linting
molecule converge -s with-linting -- -vvv
```

## Known Warning
You may see:

> [DEPRECATION WARNING]: The 'ansible.posix.profile_tasks' callback plugin implements the following deprecated method(s): playbook_on_stats.

Cause: `ansible.posix.profile_tasks` retains a legacy shim for backward compatibility even though it implements v2 hooks.

Action: Safe to ignore while keeping the callback enabled; optionally pin `ansible-core<2.23` until ansible.posix removes the shim.
