# Tests

Unit tests cover the CLI and utilities; Molecule scenarios use pytest‑testinfra for system‑state verification.

## Quick Start

```bash
python sandbox.py activate
source .venv/bin/activate
python -m unittest -v tests/test_sandbox.py
python -m unittest -v tests/test_DECRYPT_VAULTED_ITEMS.py
molecule test -s default
```

## Test Files
- `tests/test_sandbox.py` – activation `.env`, runtime detection, SSH keys, container setup, role/collection handling, playbook wiring
- `tests/test_DECRYPT_VAULTED_ITEMS.py` – vault helper tests

## Run Unit Tests
```bash
python sandbox.py activate
source .venv/bin/activate
python -m unittest -v tests/test_sandbox.py
python -m unittest -v tests/test_DECRYPT_VAULTED_ITEMS.py
```

## Run Molecule Verification (Testinfra)
```bash
# Default scenario
molecule verify -s default

# Run testinfra directly
pytest molecule/default/test_default.py -v
pytest molecule/localhost-only/test_localhost.py -v
```

## CI/CD
Unit tests run across Python 3.10–3.14; Molecule scenarios run in a separate matrix. See the Actions tab for results.

## Notes
- Tests use temporary directories and mocks to avoid external side effects.
- Container and Ansible commands are mocked in unit tests; real runs happen in Molecule scenarios.
- `.env` and `.venv` are generated assets and not committed.
