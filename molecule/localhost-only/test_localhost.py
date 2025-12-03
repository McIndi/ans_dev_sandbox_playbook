"""
Testinfra tests for localhost-only Molecule scenario.

These tests verify localhost connection configuration and
Python interpreter detection work correctly.
"""

import pytest


# Use local backend for testinfra
@pytest.fixture
def host(request):
    """Return a testinfra host using local backend."""
    import testinfra
    return testinfra.get_host("local://")


def test_localhost_connection_is_local(host):
    """Verify we're running on localhost with local connection."""
    # Test that localhost resolves to loopback
    localhost_check = host.run("ping -c 1 localhost")
    assert localhost_check.rc == 0, "Should be able to ping localhost"


def test_python_interpreter_detection(host):
    """Verify Python interpreter is correctly detected."""
    # Test that Python is available and can import sys
    python_version = host.run("python3 -c 'import sys; print(sys.version)'")
    assert python_version.rc == 0, "Python should be available"
    assert "Python 3." in python_version.stdout or python_version.stdout.startswith("3."), \
        "Should be Python 3.x"
    
    # Verify we can get executable path
    python_executable = host.run("python3 -c 'import sys; print(sys.executable)'")
    assert python_executable.rc == 0, "Should be able to get Python executable path"
    assert "/python" in python_executable.stdout, "Executable path should contain 'python'"


def test_fact_gathering_capabilities(host):
    """Verify we can gather system facts on localhost."""
    # Test hostname
    hostname = host.run("hostname")
    assert hostname.rc == 0, "Should be able to gather hostname"
    assert len(hostname.stdout.strip()) > 0, "Hostname should not be empty"
    
    # Test OS family detection
    os_family = host.run("uname -s")
    assert os_family.rc == 0, "Should be able to detect OS family"
    assert os_family.stdout.strip() in ["Linux", "Darwin"], "OS should be Linux or Darwin"
    
    # Test we can get current user
    current_user = host.run("whoami")
    assert current_user.rc == 0, "Should be able to get current user"
    assert len(current_user.stdout.strip()) > 0, "Username should not be empty"


def test_ansible_localhost_connectivity(host):
    """Verify Ansible can connect to localhost."""
    # Test Ansible ping module with local connection
    ping_result = host.run("ansible localhost -m ping -c local")
    assert ping_result.rc == 0, "Ansible should be able to ping localhost"
    assert "pong" in ping_result.stdout.lower() or "success" in ping_result.stdout.lower(), \
        "Ping should return success"


def test_required_tools_available(host):
    """Verify required tools are available for playbook execution."""
    required_commands = [
        ("python3", "Python 3."),
        ("git", "git version"),
        ("ansible", "ansible"),
    ]
    
    for cmd, expected_output in required_commands:
        result = host.run(f"{cmd} --version")
        assert result.rc == 0, f"{cmd} should be available"
        assert expected_output in result.stdout, \
            f"{cmd} version output should contain '{expected_output}'"


@pytest.mark.parametrize("env_var", ["HOME", "USER", "PATH"])
def test_environment_variables_set(host, env_var):
    """Verify essential environment variables are set."""
    env_check = host.run(f"echo ${env_var}")
    assert env_check.rc == 0, f"Should be able to access ${env_var}"
    assert len(env_check.stdout.strip()) > 0, f"${env_var} should be set"
