# Molecule Scenario: localhost-only

Validate playbook behavior and configuration when targeting only `localhost` (connection: local).

## Purpose
- Ensures `ansible_connection: local` and `ansible_python_interpreter: auto_silent` are correct
- Proves playbook can run without the container target
- Faster feedback for iterative development

## Prerequisites
- Activate the managed environment:

```bash
python sandbox.py activate
source .venv/bin/activate
```

## Quick Start

```bash
# Full test sequence for this scenario
molecule test -s localhost-only

# Or iterate quickly
molecule converge -s localhost-only
molecule verify -s localhost-only

# Cleanup
molecule destroy -s localhost-only
```

## What This Scenario Tests
- Localhost-only execution path
- Python interpreter auto-detection on localhost
- Ansible connectivity and essential tooling availability

## Tips
- Use `python sandbox.py run --skip-container --limit localhost` to replicate this scenario outside Molecule.
- Prefer this scenario for fast iteration when container networking or ports are constrained.

## Known Warning
You may see:

> [DEPRECATION WARNING]: The 'ansible.posix.profile_tasks' callback plugin implements the following deprecated method(s): playbook_on_stats.

Cause: `ansible.posix.profile_tasks` retains a legacy shim for backward compatibility even though it implements v2 hooks.

Action: Safe to ignore while keeping the callback enabled; optionally pin `ansible-core<2.23` until ansible.posix removes the shim.
