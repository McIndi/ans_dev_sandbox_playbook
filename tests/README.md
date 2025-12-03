# Tests

For test strategies, validation workflows, and CI/CD integration, see the [Testing and Validation](https://github.com/briankearney/ans_dev_sandbox_playbook/wiki/Testing-and-Validation) section of the [project wiki](https://github.com/briankearney/ans_dev_sandbox_playbook/wiki).

Unit tests for helper scripts and Python utility. The project uses **pytest-testinfra** for Molecule scenario verification, providing robust Python-based system state testing with better assertion capabilities compared to Ansible-based verification.

## Test Overview

### Bash Script Tests
- **`test_activate_sandbox_env.bash`** - Tests for `ACTIVATE_SANDBOX_ENV.bash`
- **`test_run_playbook.bash`** - Tests for `RUN_PLAYBOOK.bash`

### Python Unit Tests
- **`test_DECRYPT_VAULTED_ITEMS.py`** - Unit tests for `DECRYPT_VAULTED_ITEMS.py`

## Running Tests

### Bash Script Tests

Run from the repository root:

```bash
# Test the environment activation script
bash tests/test_activate_sandbox_env.bash

# Test the playbook runner script
bash tests/test_run_playbook.bash
```

### Python Unit Tests

Run from the repository root:

```bash
# Run all Python unit tests
python3 -m unittest test_DECRYPT_VAULTED_ITEMS.py

# Run with verbose output
python3 -m unittest -v test_DECRYPT_VAULTED_ITEMS.py

# Run specific test class
python3 -m unittest test_DECRYPT_VAULTED_ITEMS.TestDecryptVaultedItems

# Run specific test method
python3 -m unittest test_DECRYPT_VAULTED_ITEMS.TestDecryptVaultedItems.test_extract_vault_content_success
```

### Run Everything (Convenience)

From repository root after activation:
```bash
source ACTIVATE_SANDBOX_ENV.bash
bash tests/test_activate_sandbox_env.bash && \
	bash tests/test_run_playbook.bash && \
	python3 -m unittest -v test_DECRYPT_VAULTED_ITEMS.py
```

## CI/CD Integration

All unit tests run automatically via GitHub Actions (push/PR to `main` & `develop`). Matrix covers Python 3.10–3.12.

**Molecule Testing**: The project now uses pytest-testinfra for Molecule scenario verification. See `molecule/default/test_default.py` and `molecule/localhost-only/test_localhost.py` for Python-based system state assertions that complement the unit tests for helper scripts.

### GitHub Actions Workflow

**File**: [`.github/workflows/unit-tests.yml`](../.github/workflows/unit-tests.yml)

**Triggers**:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Manual workflow dispatch

**Matrix Testing**: Python 3.10, 3.11, 3.12

**Jobs**:
1. **bash-tests**: Runs both Bash script tests (`test_activate_sandbox_env.bash`, `test_run_playbook.bash`)
2. **python-tests**: Runs Python unit tests (`test_DECRYPT_VAULTED_ITEMS.py`) with verbose output
3. **test-summary**: Aggregates results from both jobs

**Artifacts**: Failure logs retained briefly (7 days) for debugging.

**Viewing Results**:
- Check the [Actions tab](https://github.com/briankearney/ans_dev_sandbox_playbook/actions) in the repository
- View the status badges in the main [README.md](../README.md)
- Review workflow runs for detailed test output and logs


## Test Details

### `test_activate_sandbox_env.bash`

Tests the Python virtual environment activation script.

**What it tests:**
- **Python Version Selection**: Verifies the script correctly identifies and selects the newest Python version < 3.14
- **Directory Resolution**: Ensures `get_script_dir` correctly resolves the script's location even when sourced from different directories

**Framework:** Custom Bash-based assertion functions (`assert_equals`); no external harness (e.g. `bats`) to keep dependencies minimal.

**Notes:**
- Uses `UNIT_TESTING` environment variable to source the script without executing side effects
- Output shows "ALL TESTS PASSED" on success

### `test_run_playbook.bash`

Tests the Ansible playbook runner wrapper script.

**What it tests:**
- **Argument Parsing**: Verifies correct handling of command-line arguments
- **Playbook Execution**: Tests the playbook running logic
- **Error Handling**: Ensures proper error messages and exit codes

**Framework:** Custom Bash-based testing harness

### `test_DECRYPT_VAULTED_ITEMS.py`

Comprehensive unit tests for the vault decryption utility (`DECRYPT_VAULTED_ITEMS.py`) using `unittest`.

**Test Coverage (10 test cases):**

#### `extract_vault_content` Function
1. **`test_extract_vault_content_success`** - Verifies successful extraction of vault content from YAML files with proper indentation handling
2. **`test_extract_vault_content_id_not_found`** - Ensures `ValueError` is raised when vault ID is not found
3. **`test_extract_vault_content_file_not_found`** - Ensures `FileNotFoundError` is raised for missing files

#### `decrypt_vault` Function
4. **`test_decrypt_vault_success`** - Mocks `subprocess.run` to test successful ansible-vault decryption
5. **`test_decrypt_vault_failure`** - Tests error handling when decryption fails

#### `attempt_base64_decode` Function
6. **`test_attempt_base64_decode_valid`** - Tests decoding valid base64 encoded data
7. **`test_attempt_base64_decode_invalid`** - Tests handling of non-base64 data
8. **`test_attempt_base64_decode_bytes`** - Tests handling of bytes input

#### `format_output` Function
9. **`test_format_output_no_color`** - Tests YAML output without syntax highlighting
10. **`test_format_output_color`** - Tests YAML output with pygments syntax highlighting

**Key Features:**
- **Mocking Strategy**: Uses `unittest.mock` to mock external dependencies (`subprocess.run`, `pygments`)
- **Dependency Handling**: Automatically mocks `pygments` if not installed
- **Temporary Files**: Uses `tempfile` for creating test YAML files
- **Comprehensive Coverage**: Tests both success and failure scenarios

**Prerequisites:** Python 3.x, `PyYAML`; `pygments` optional (mocked if absent).

### Sample Successful Output (Bash)

```text
Running test_activate_sandbox_env.bash...
TEST: python version selection ... OK
TEST: get_script_dir resolution ... OK
ALL TESTS PASSED
```

### Sample Failure (Illustrative)

```text
TEST: python version selection ... FAIL (expected 3.12, got 3.8)
```

## Framework Notes
| Type | Framework | Key Traits |
|------|-----------|-----------|
| Bash | Custom assertions | No external deps, environment isolation |
| Python | `unittest` + mocks | Temp dirs, broad success/failure coverage |

## Extending
Add new Bash tests (`test_<script>.bash`) or Python modules (`test_<module>.py`). For system-level assertions (filesystem state, services), use pytest-testinfra in Molecule scenarios (see `molecule/default/test_default.py` and `molecule/localhost-only/test_localhost.py` for examples).

## Prerequisites

### For Bash Tests
- Bash (standard on most Linux/macOS systems)
- Python 3 (for testing Python selection logic)

### For Python Tests
- Python 3.x
- Standard library modules: `unittest`, `tempfile`, `base64`, `subprocess`
- Project dependencies: `PyYAML`
- Optional: `pygments` (will be mocked if unavailable)

## Notes

- All tests are designed to run without modifying the system or creating persistent side effects
- Bash tests use `UNIT_TESTING` environment variable to prevent side effects during sourcing.
- Python tests automatically clean up temporary files and directories.
- Tests can be run individually or as a complete suite
- Exit codes: 0 = success, non-zero = failure
