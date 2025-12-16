# Molecule Testing for ans_dev_sandbox_playbook

For detailed testing, validation, and CI/CD guidance, see the [Testing and Validation](https://github.com/briankearney/ans_dev_sandbox_playbook/wiki/Testing-and-Validation) section of the [project wiki](https://github.com/briankearney/ans_dev_sandbox_playbook/wiki).

Comprehensive testing infrastructure using [Molecule](https://ansible.readthedocs.io/projects/molecule/) for the `ans_dev_sandbox_playbook` Ansible playbook.

## Overview

This repository includes three Molecule test scenarios to validate the playbook and the `ans_dev_sandbox_role` it uses:

1. **default** - Full test sequence with idempotence checking
2. **localhost-only** - Tests specifically for localhost connection configuration
3. **with-linting** - Scenario name retained; linting is now run externally (Molecule ≥25 removed built‑in lint command)

All scenarios use the **delegated** driver, which runs tests directly on the local machine without requiring containers or VMs.

## Prerequisites

- Python >3.9 and <3.15
- Ansible 2.9 or higher
- Molecule 6.0 or higher
- ansible-lint 6.0 or higher
- yamllint

These are already installed in the `.venv` virtual environment.

## Quick Start

### Activate Virtual Environment

```bash
source ACTIVATE_SANDBOX_ENV.bash
```

### Run All Tests

```bash
# Run default scenario (recommended for first-time testing)
molecule test

# Run specific scenario
molecule test -s localhost-only
molecule test -s with-linting
```

### Step-by-Step Testing (for debugging)

```bash
# Run tests step by step
molecule create          # Create test environment
molecule prepare         # Install role dependencies
molecule converge        # Run the playbook
molecule idempotence     # Verify idempotence (default scenario only)
molecule verify          # Run verification tests
molecule destroy         # Clean up

# Or run individual steps
molecule converge        # Just run the playbook
molecule verify          # Just run verification
```

## Test Scenarios

### Default Scenario

**Location**: `molecule/default/`

**Purpose**: Comprehensive testing with full test sequence

**Test Sequence**:
1. `dependency` - Install role dependencies via ansible-galaxy
2. `syntax` - Validate playbook syntax
3. `create` - Create test environment
4. `prepare` - Set up test prerequisites
5. `converge` - Execute the playbook
6. `idempotence` - Verify playbook is idempotent (no changes on second run)
7. `verify` - Run verification tasks
8. `cleanup` - Clean up test artifacts
9. `destroy` - Destroy test environment

**What it tests**:
- Role installation from GitHub
- Playbook execution
- Variable handling
- Idempotence (critical for Ansible best practices)
- Cleanup tasks
- System state validation

### Localhost-Only Scenario

**Location**: `molecule/localhost-only/`

**Purpose**: Validate localhost connection configuration

**Test Sequence**: dependency → syntax → create → prepare → converge → verify → cleanup → destroy

**What it tests**:
- `ansible_connection: local` configuration
- `ansible_python_interpreter: auto_silent` detection
- Fact gathering on localhost
- Python interpreter availability
- Connection type validation

### With-Linting Scenario

**Location**: `molecule/with-linting/`

**Purpose**: Emphasize that linting should be performed separately prior to convergence.

**Test Sequence**: dependency → syntax → create → prepare → converge → verify → cleanup → destroy

**What it tests**:
- Assumes lint was run manually or via CI before scenario execution
- Playbook execution & verification tasks
- System state validation

**Recommended linting workflow (manual or CI)**:
- `yamllint .`
- `ansible-lint playbooks/ molecule/`

## Verification Tests

This project uses **pytest-testinfra** for verification, providing robust Python-based system state testing. Testinfra offers better assertion capabilities, clearer test output, and more maintainable test code compared to Ansible-based verification.

### Testinfra Integration

**Default Scenario** (`molecule/default/test_default.py`):
- Python interpreter availability and functionality
- Ansible operational verification (ping test)
- Role execution artifact validation
- System fact gathering capabilities
- Git command availability
- Temporary directory cleanup verification
- Python YAML module availability

**Localhost-Only Scenario** (`molecule/localhost-only/test_localhost.py`):
- Localhost connection type verification
- Python interpreter detection and path resolution
- Fact gathering capabilities (hostname, OS family, user)
- Ansible localhost connectivity
- Required tool availability (python3, git, ansible)
- Environment variable configuration

**With-Linting Scenario**:
- Uses Ansible-based verification (legacy `verify.yml`)
- Focuses on linting validation

### Running Testinfra Tests

```bash
# Run verification as part of full test sequence
molecule test -s default

# Run only the verify step
molecule verify -s default

# Run testinfra tests directly with pytest
pytest molecule/default/test_default.py -v
pytest molecule/localhost-only/test_localhost.py -v

# Run with additional pytest options
pytest molecule/default/test_default.py -v --tb=short
pytest molecule/default/test_default.py -v -k "test_python"
```

### Legacy Ansible Verification

For reference, the original Ansible-based verification playbooks are preserved as:
- `molecule/default/verify_legacy.yml`
- `molecule/localhost-only/verify_legacy.yml`

These can be used as fallback or reference implementations.

## Linting Configuration

### ansible-lint (`../.ansible-lint`)

- **Profile**: production
- **Excludes**: External roles, virtual environments, cache directories
- **Skip rules**: External role naming, Galaxy changelogs
- **Custom rules**: Line length (160), variable naming, command usage

### yamllint (`../.yamllint`)

- **Line length**: 160 characters (warning level)
- **Indentation**: 2 spaces
- **Document markers**: Start required, end optional
- **Truthy values**: Allows yes/no, true/false, on/off

## Running Linting Separately

```bash
# Run yamllint
yamllint .

# Run ansible-lint
ansible-lint playbooks/ molecule/

# Run both (as done in with-linting scenario)
yamllint . && ansible-lint
```

## CI/CD Integration

### GitHub Actions Workflow

**File**: `.github/workflows/molecule.yml`

**Triggers**:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Manual workflow dispatch

**Matrix Testing**:
- Python versions: 3.10, 3.11, 3.12, 3.13, 3.14
- All three scenarios: default, localhost-only, with-linting
- Total: 9 test combinations

**Jobs**:
1. **molecule** - Runs all scenarios across Python versions
2. **lint-only** - Separate linting validation
3. **test-summary** - Aggregates results

**Artifacts**: Test logs uploaded on failure (retained for 7 days)

## Troubleshooting

### Common Issues

#### Role Not Found
```bash
# Manually install the role
ansible-galaxy install -r roles/requirements.yml --roles-path ./roles --force
```

#### Molecule Command Not Found
```bash
# Ensure sandbox environment is activated
source ACTIVATE_SANDBOX_ENV.bash

# Verify installation
molecule --version
```

#### Linting Failures
```bash
# Run linting separately to see detailed errors
yamllint .
ansible-lint playbooks/ molecule/

# Check configuration files
cat .yamllint
cat .ansible-lint
```

#### Idempotence Test Fails
This means the playbook makes changes on the second run. Check:
- Are tasks using `changed_when` appropriately?
- Are tasks truly idempotent?
- Review the converge output for unexpected changes

#### Profile tasks deprecation warning
Warning observed during runs:

> [DEPRECATION WARNING]: The 'ansible.posix.profile_tasks' callback plugin implements the following deprecated method(s): playbook_on_stats. This feature will be removed from the callback plugin API in ansible-core version 2.23. Implement the `v2_*` equivalent callback method(s) instead.

Cause: `ansible.posix.profile_tasks` retains a legacy `playbook_on_stats` shim for backward compatibility even though it implements v2 hooks. Action: Safe to ignore while keeping the callback enabled; optionally pin `ansible-core<2.23` until ansible.posix removes the shim and the warning disappears.

### Debug Mode

```bash
# Run with verbose output
molecule --debug test

# Run specific step with verbosity
molecule converge -- -vvv
```

### Clean Start

```bash
# Destroy and start fresh
molecule destroy
molecule test
```

## Creating New Scenarios

To create a new test scenario:

```bash
# Create new scenario
molecule init scenario <scenario-name>

# Copy and modify from existing scenario
cp -r molecule/default molecule/my-scenario
# Edit molecule/my-scenario/molecule.yml to change scenario name
```

## Best Practices

1. **Always run idempotence tests** - Use the default scenario to ensure playbooks are idempotent
2. **Test before committing** - Run `molecule test -s default` locally before pushing
3. **Use linting** - Run the with-linting scenario to catch issues early
4. **Check CI/CD** - Monitor GitHub Actions for test results
5. **Keep scenarios focused** - Each scenario should test a specific aspect (connection logic, idempotence, lint pre-checks, etc.)
6. **Update verify tasks** - Add verification for new functionality

## File Structure

```
molecule/
├── default/
│   ├── molecule.yml      # Scenario configuration
│   ├── prepare.yml       # Setup tasks
│   ├── converge.yml      # Main playbook to test
│   └── verify.yml        # Verification tasks
├── localhost-only/
│   ├── molecule.yml
│   ├── prepare.yml
│   ├── converge.yml
│   └── verify.yml
└── with-linting/
    ├── molecule.yml
    ├── prepare.yml
    ├── converge.yml
    └── verify.yml
```

## Additional Resources

- [Molecule Documentation](https://ansible.readthedocs.io/projects/molecule/)
- [Ansible Lint Documentation](https://ansible.readthedocs.io/projects/lint/)
- [YAML Lint Documentation](https://yamllint.readthedocs.io/)
- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Molecule logs in `molecule/<scenario>/`
3. Check GitHub Actions workflow runs
4. Review ansible.log for detailed execution logs
