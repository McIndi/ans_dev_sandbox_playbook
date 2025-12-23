"""
Python CLI replacement for the bash workflows formerly provided by
ACTIVATE_SANDBOX_ENV.bash and RUN_PLAYBOOK.bash.

Subcommands
-----------
- activate: prepare the environment (.venv, requirements, .env handoff)
- run: execute the playbook workflow (keys, container, roles/collections, playbook)

Notes
-----
- No ansible.cfg is created; configuration stays environment-driven.
- Defaults prefer podman, host port 2222, container name ansible_target.
- CLI overrides beat values from .env; overrides emit warnings to keep behavior explicit.
"""
from __future__ import annotations

import argparse
import glob
import logging
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

# Logging configuration: maps verbosity count to logging level
# 0=CRITICAL, 1=ERROR, 2=WARNING, 3=INFO, 4+=DEBUG
LOG_LEVELS = [logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]

# Exit codes for different failure scenarios
RETURN_CODES = {
    "SUCCESS": 0,                    # Normal completion
    "UNHANDLED_EXCEPTION": 1,        # Unexpected error caught by main()
    "MISSING_DEPENDENCY": 2,         # Required tool not found (e.g., ansible)
    "NO_PYTHON": 3,                  # No suitable Python version found
    "NO_RUNTIME": 4,                 # No container runtime (podman/docker) found
}

# Default paths and names for sandbox components
DEFAULT_ENV_FILE = Path(".env")
DEFAULT_CONTAINER_RUNTIME = "podman"           # Preferred for SELinux compatibility
DEFAULT_CONTAINER_NAME = "ansible_target"      # Name of the test container
DEFAULT_CONTAINER_IMAGE = "ansible_target:latest"
DEFAULT_HOST_PORT = 2222                       # SSH port on host (avoid privileged 22)
DEFAULT_SSH_PORT = 22                          # SSH port inside container
DEFAULT_SSH_DIR = Path("ssh_keys")             # Directory for ephemeral SSH keys
DEFAULT_KEY_BASENAME = "ansible_target"        # Base name for key files
DEFAULT_VAULT_PASSWORD_FILE = Path("vault-pw.txt")  # Demo vault password file
DEFAULT_LOG_FILE = Path("ansible.log")         # Ansible execution log

# Ansible environment configuration (replaces ansible.cfg for enterprise compliance)
# These variables are written to .env during activation
ANSIBLE_ENV_DEFAULTS: Dict[str, str] = {
    "ANSIBLE_DISPLAY_ARGS_TO_STDOUT": "false",
    "ANSIBLE_CALLBACKS_ENABLED": "profile_tasks",    # Show task timing
    "ANSIBLE_LOAD_CALLBACK_PLUGINS": "true",
    "ANSIBLE_LOG_PATH": str(DEFAULT_LOG_FILE),       # Persist execution logs
    "ANSIBLE_ROLES_PATH": "roles",
    "ANSIBLE_FILTER_PLUGINS": "plugins",
    "ANSIBLE_LIBRARY": "library",
    "ANSIBLE_CALLBACK_RESULT_FORMAT": "yaml",
}

# Default playbook and inventory paths
PLAYBOOK_FILE = Path("playbooks/sample_playbook.yml")
INVENTORY_FILE = Path("inventory/main.yml")


# ----------------------------------------------------------------------------
# Logging helpers
# ----------------------------------------------------------------------------

def configure_logging(verbosity: int, log_file: Optional[Path]) -> None:
    """Configure logging with appropriate level and handlers.
    
    Args:
        verbosity: Verbosity level (0=CRITICAL, 1=ERROR, 2=WARNING, 3=INFO, 4+=DEBUG)
        log_file: Optional path to write log output to file
    
    Note:
        Always logs to stderr. If log_file is provided, also writes to that file.
        Verbosity is capped at the maximum available level (DEBUG).
    """
    level_index = min(len(LOG_LEVELS) - 1, verbosity)
    level = LOG_LEVELS[level_index]
    handlers: List[logging.Handler] = [logging.StreamHandler(sys.stderr)]

    if log_file:
        handlers.append(logging.FileHandler(log_file, mode="w"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )


# ----------------------------------------------------------------------------
# .env helpers
# ----------------------------------------------------------------------------

def load_env_file(path: Path) -> Dict[str, str]:
    """Load environment variables from a .env file.
    
    Args:
        path: Path to the .env file
    
    Returns:
        Dictionary of environment variable key-value pairs
    
    Note:
        - Returns empty dict if file doesn't exist
        - Skips blank lines and comments (lines starting with #)
        - Splits on first '=' to allow '=' in values
        - Strips whitespace from keys and values
    """
    logging.debug("Loading environment file from %s", path)
    if not path.exists():
        logging.debug("Environment file %s does not exist", path)
        return {}

    data: Dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    logging.debug("Loaded %d environment variables from %s", len(data), path)
    return data


def write_env_file(path: Path, values: Dict[str, str]) -> None:
    """Write environment variables to a .env file.
    
    Args:
        path: Path to write the .env file
        values: Dictionary of environment variable key-value pairs
    
    Note:
        Keys are sorted alphabetically for consistent output.
        Each line is formatted as KEY=VALUE with a trailing newline.
    """
    lines = [f"{key}={value}" for key, value in sorted(values.items())]
    path.write_text("\n".join(lines) + "\n")
    logging.info("Wrote environment file at %s", path)


def set_env_vars(path: Path) -> None:
    """Load environment variables from .env file and set them in os.environ.
    
    Args:
        path: Path to the .env file to load
    
    Note:
        This modifies the current process environment. Variables set here
        will be available to subprocesses and os.environ lookups.
    """
    logging.debug("Setting environment variables from %s", path)
    env_vars = load_env_file(path)
    for key, value in env_vars.items():
        os.environ[key] = value
        logging.debug("Set environment variable: %s", key)
    logging.info("Set %d environment variables from %s", len(env_vars), path)


# ----------------------------------------------------------------------------
# Python selection helpers
# ----------------------------------------------------------------------------

def _python_version(path: Path) -> Optional[Tuple[int, int, int]]:
    """Query a Python executable for its version.
    
    Args:
        path: Path to the Python executable
    
    Returns:
        Tuple of (major, minor, micro) version numbers, or None if query fails
    
    Note:
        Returns None for non-existent paths or executables that fail to run.
        Uses subprocess to query sys.version_info to ensure accurate version detection.
    """
    try:
        completed = subprocess.run(
            [str(path), "-c", "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}.{v.micro}')"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return None

    text_version = completed.stdout.strip()
    try:
        parts = tuple(int(x) for x in text_version.split(".")[:3])
    except ValueError:
        return None
    return parts  # type: ignore[return-value]


def find_python_candidates() -> List[Tuple[Path, Tuple[int, int, int]]]:
    """Search common locations for Python 3 installations.
    
    Returns:
        List of tuples containing (path, version) for each found Python executable
    
    Search locations:
        - Current Python executable's directory and variants
        - uv-managed Python installations (~/.local/share/uv/python)
        - System locations (/usr/bin, /usr/local/bin, /opt/*/bin)
        - python3 in PATH (if not already found)
    
    Note:
        Only includes executable files starting with 'python3'.
        Filters out non-executable files and symlinks to non-existent targets.
    """
    logging.debug("Searching for Python candidates")
    search_globs = [
        f"{sys.executable}*",
        "~/.local/share/uv/python/*/bin/python3*",
        "/usr/bin/python3*",
        "/usr/local/bin/python3*",
        "/opt/*/bin/python3*",
    ]

    candidates: List[Tuple[Path, Tuple[int, int, int]]] = []
    for pattern in search_globs:
        expanded_pattern = os.path.expanduser(pattern)
        logging.debug("Searching pattern: %s", expanded_pattern)
        for path in glob.glob(expanded_pattern):
            resolved = Path(path)
            if not resolved.is_file() or not os.access(resolved, os.X_OK):
                continue
            if not resolved.name.startswith("python3"):
                continue
            ver = _python_version(resolved)
            if ver:
                logging.debug("Found Python candidate: %s (version %s)", resolved, ".".join(map(str, ver)))
                candidates.append((resolved, ver))

    path_python = shutil.which("python3")
    if path_python:
        resolved = Path(path_python)
        if all(resolved != p for p, _ in candidates):
            ver = _python_version(resolved)
            if ver:
                logging.debug("Found Python from PATH: %s (version %s)", resolved, ".".join(map(str, ver)))
                candidates.append((resolved, ver))

    logging.info("Found %d Python candidate(s)", len(candidates))
    return candidates


def select_python(candidates: Iterable[Tuple[Path, Tuple[int, int, int]]]) -> Optional[Path]:
    """Select the best Python version from a list of candidates.
    
    Args:
        candidates: Iterable of (path, version) tuples
    
    Returns:
        Path to the highest Python version meeting requirements, or None
    
    Requirements:
        - Version must be >= 3.10.0
        - Version must be < 3.15.0
        - Selects highest version meeting these criteria
    
    Note:
        This version range ensures compatibility with Ansible and project dependencies.
    """
    logging.debug("Selecting best Python from candidates")
    best: Optional[Tuple[int, int, int]] = None
    best_path: Optional[Path] = None
    for path, version in candidates:
        if version < (3, 10, 0):
            logging.debug("Skipping %s (version %s < 3.10.0)", path, ".".join(map(str, version)))
            continue
        if version >= (3, 15, 0):
            logging.debug("Skipping %s (version %s >= 3.15.0)", path, ".".join(map(str, version)))
            continue
        if best is None or version > best:
            best = version
            best_path = path
            logging.debug("New best candidate: %s (version %s)", path, ".".join(map(str, version)))
    if best_path:
        logging.info("Selected Python: %s (version %s)", best_path, ".".join(map(str, best)))
    else:
        logging.warning("No suitable Python found in candidates")
    return best_path


# ----------------------------------------------------------------------------
# Activation workflow
# ----------------------------------------------------------------------------

def build_activation_env(playbook_path: Path) -> Dict[str, str]:
    """Build environment variables for Ansible sandbox activation.
    
    Args:
        playbook_path: Root path of the playbook project
    
    Returns:
        Dictionary of environment variables to write to .env file
    
    Note:
        Includes ANSIBLE_* configuration, container settings, and vault config.
        These replace ansible.cfg for enterprise compliance (no .cfg files).
    """
    logging.debug("Building activation environment for playbook path: %s", playbook_path)
    env: Dict[str, str] = {
        "PLAYBOOK_PATH": str(playbook_path),
        **ANSIBLE_ENV_DEFAULTS,
        "ANSIBLE_VAULT_PASSWORD_FILE": str(playbook_path / DEFAULT_VAULT_PASSWORD_FILE),
        "CONTAINER_RUNTIME": DEFAULT_CONTAINER_RUNTIME,
        "CONTAINER_HOST_PORT": str(DEFAULT_HOST_PORT),
        "CONTAINER_NAME": DEFAULT_CONTAINER_NAME,
    }
    logging.debug("Built %d environment variables", len(env))
    return env


def ensure_venv(playbook_path: Path, unit_testing: bool = False) -> Optional[Path]:
    """Ensure a virtual environment exists, creating if necessary.
    
    Args:
        playbook_path: Root path of the playbook project
        unit_testing: If True, skip venv creation (for testing)
    
    Returns:
        Path to the venv's Python executable, or None if creation failed
    
    Note:
        - Returns existing venv if found
        - Searches for Python 3.10-3.14 to create new venv
        - Skips creation when UNIT_TESTING environment variable is set
    """
    venv_dir = playbook_path / ".venv"
    venv_python = venv_dir / "bin" / "python"

    if venv_python.exists():
        logging.info("Using existing virtual environment at %s", venv_dir)
        return venv_python

    if unit_testing:
        logging.info("UNIT_TESTING set; skipping venv creation")
        return None

    logging.info("No .venv found — locating a suitable Python (Python 3.10-3.14) to create one")
    candidates = find_python_candidates()
    if not candidates:
        logging.error("No python3 interpreters found. Please install Python 3.10-3.14.")
        return None

    picked = select_python(candidates)
    if not picked:
        logging.error("No suitable Python Python 3.10-3.14 found. Please install Python 3.10-3.14.")
        return None

    logging.info("Creating virtual environment using %s", picked)
    try:
        subprocess.run([str(picked), "-m", "venv", str(venv_dir)], check=True)
    except subprocess.SubprocessError as exc:
        logging.error("Failed to create virtualenv with %s: %s", picked, exc)
        return None

    return venv_python if venv_python.exists() else None


def _venv_python(playbook_path: Path) -> Optional[Path]:
    """Check if a virtual environment Python executable exists.
    
    Args:
        playbook_path: Root path of the playbook project
    
    Returns:
        Path to venv Python if it exists, None otherwise
    """
    candidate = playbook_path / ".venv" / "bin" / "python"
    return candidate if candidate.exists() else None


def install_requirements(venv_python: Path) -> None:
    """Install Python requirements into the virtual environment.
    
    Args:
        venv_python: Path to the venv's Python executable
    
    Steps:
        1. Upgrade pip to latest version
        2. Install all packages from requirements.txt
        3. Uninstall pytest-ansible to prevent plugin conflicts with pytest-testinfra
    
    Note:
        pytest-ansible removal is necessary to avoid ArgumentError with
        --ansible-inventory flag when using pytest-testinfra.
    """
    logging.info("Installing Python requirements using %s", venv_python)
    logging.debug("Upgrading pip")
    subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    logging.info("Installing packages from requirements.txt")
    subprocess.run([str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    logging.debug("Uninstalling pytest-ansible to avoid conflicts")
    subprocess.run([str(venv_python), "-m", "pip", "uninstall", "-y", "pytest-ansible"], check=False)
    logging.info("Requirements installation complete")


def activate(args: argparse.Namespace) -> int:
    """Activate the Ansible sandbox environment.
    
    Args:
        args: Parsed command-line arguments
    
    Returns:
        Exit code (0 for success)
    
    Workflow:
        1. Ensure virtual environment exists (.venv)
        2. Install Python requirements if venv was just created
        3. Build Ansible environment configuration
        4. Write configuration to .env file
    
    Note:
        - Creates new venv with Python 3.10-3.14 if not present
        - Skips pip install if venv already exists (assumes deps are current)
        - Configuration is session-scoped via .env (no ansible.cfg)
    """
    logging.info("Starting activation workflow")
    playbook_path = Path(args.playbook_path).resolve() if args.playbook_path else Path(__file__).resolve().parent
    logging.debug("Playbook path: %s", playbook_path)
    env_file = Path(args.env_file)
    logging.debug("Environment file: %s", env_file)
    unit_testing = bool(os.environ.get("UNIT_TESTING"))
    if unit_testing:
        logging.debug("Running in unit testing mode")

    venv_python = _venv_python(playbook_path)
    created = False
    if venv_python is None:
        venv_python = ensure_venv(playbook_path, unit_testing=unit_testing)
        created = venv_python is not None

    if venv_python and created:
        install_requirements(venv_python)
    elif venv_python:
        logging.info("Reusing existing virtualenv without reinstalling requirements")

    env_values = load_env_file(env_file)
    env_values.update(build_activation_env(playbook_path))

    if venv_python:
        env_values["VENV_PYTHON"] = str(venv_python)
        logging.debug("Added VENV_PYTHON to environment: %s", venv_python)

    write_env_file(env_file, env_values)
    logging.info("Activation complete")
    return RETURN_CODES["SUCCESS"]


# ----------------------------------------------------------------------------
# Runtime helpers
# ----------------------------------------------------------------------------

def detect_ansible() -> bool:
    """Check if ansible is available in PATH.
    
    Returns:
        True if ansible command is found, False otherwise
    
    Note:
        This should be called after activating the virtual environment.
        Ansible is typically installed via requirements.txt.
    """
    if shutil.which("ansible"):
        logging.info("'ansible' found in PATH")
        return True
    logging.error("'ansible' was not found in PATH")
    return False


def detect_container_runtime(preferred: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """Detect available container runtime (podman or docker).
    
    Args:
        preferred: Optional preferred runtime ('podman' or 'docker')
    
    Returns:
        Tuple of (runtime_name, volume_option_string) or (None, None) if neither found
    
    Volume options:
        - Podman: ':ro,z' (read-only with SELinux relabeling)
        - Docker: ':ro' (read-only)
    
    Note:
        Searches in order: preferred (if given), then podman, then docker.
        Podman is preferred for SELinux compatibility on enterprise systems.
    """
    logging.debug("Detecting container runtime (preferred: %s)", preferred or "none")
    runtime = None
    volume_opt = None

    ordered = []
    if preferred:
        logging.debug("Preferred runtime specified: %s", preferred)
        ordered.append(preferred)
    ordered.extend([r for r in ("podman", "docker") if r not in ordered])
    logging.debug("Runtime search order: %s", ordered)

    for candidate in ordered:
        if shutil.which(candidate):
            logging.info("Found container runtime: %s", candidate)
            runtime = candidate
            break
        else:
            logging.debug("Container runtime %s not found", candidate)

    if not runtime:
        logging.warning("No container runtime found")
        return None, None

    volume_opt = ":ro,z" if runtime == "podman" else ":ro"
    logging.debug("Using volume option: %s", volume_opt)
    return runtime, volume_opt


def _run_subprocess(
    args: List[str],
    *,
    capture: bool = False,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """Run a subprocess command with logging and error checking.
    
    Args:
        args: Command and arguments as a list
        capture: If True, capture stdout/stderr; otherwise stream to console
        env: Optional environment variables (merged with os.environ if provided)
    
    Returns:
        CompletedProcess instance
    
    Raises:
        subprocess.CalledProcessError: If command exits with non-zero status
    
    Note:
        This is the default runner function injected into setup functions.
        Can be overridden for testing with a mock runner.
    """
    logging.debug("Running command: %s", " ".join(shlex.quote(a) for a in args))
    return subprocess.run(args, check=True, capture_output=capture, text=True, env=env)


def setup_ssh_keys(base_dir: Path, key_basename: str, runner=_run_subprocess) -> Tuple[Path, Path]:
    """Generate ephemeral SSH key pair for Ansible target authentication.
    
    Args:
        base_dir: Root directory of the playbook project
        key_basename: Base name for key files (e.g., 'ansible_target')
        runner: Subprocess runner function (injectable for testing)
    
    Returns:
        Tuple of (private_key_path, authorized_keys_path)
    
    Workflow:
        1. Create ssh_keys/ directory with 0700 permissions
        2. Remove any existing keys (ensures clean state)
        3. Generate new ed25519 key pair without passphrase
        4. Copy public key to authorized_keys for container use
    
    Note:
        Keys are ephemeral and regenerated on each run for security.
        The private key is used by Ansible; authorized_keys is mounted in container.
    """
    logging.info("Setting up SSH keys")
    ssh_dir = base_dir / DEFAULT_SSH_DIR
    ssh_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(ssh_dir, 0o700)
    logging.debug("SSH directory: %s", ssh_dir)

    key_path = ssh_dir / key_basename
    pub_path = ssh_dir / f"{key_basename}.pub"
    auth_keys = ssh_dir / "authorized_keys"

    if key_path.exists():
        logging.debug("Removing existing private key: %s", key_path)
        key_path.unlink()
    if pub_path.exists():
        logging.debug("Removing existing public key: %s", pub_path)
        pub_path.unlink()

    logging.debug("Generating new ed25519 SSH key pair")
    runner([
        "ssh-keygen",
        "-q",
        "-t",
        "ed25519",
        "-N",
        "",
        "-C",
        "ansible@target",
        "-f",
        str(key_path),
    ])

    logging.debug("Writing authorized_keys file")
    auth_keys.write_bytes(pub_path.read_bytes())
    logging.info("SSH keys created: %s, %s", key_path, pub_path)
    return key_path, auth_keys


def setup_vault(playbook_path: Path, vault_file: Path = DEFAULT_VAULT_PASSWORD_FILE) -> Path:
    """Ensure Ansible vault password file exists.
    
    Args:
        playbook_path: Root directory of the playbook project
        vault_file: Name of vault password file (default: 'vault-pw.txt')
    
    Returns:
        Path to the vault password file
    
    Note:
        Creates file with demo password 'password' if not present.
        This is for sandbox development only - production uses secure vault IDs.
        The file is git-ignored via .gitignore.
    """
    target = playbook_path / vault_file
    if not target.exists():
        target.write_text("password\n")
        logging.info("Created vault password file at %s", target)
    return target


def setup_roles(playbook_path: Path, runner=_run_subprocess) -> None:
    """Ensure Ansible roles are installed or linked.
    
    Args:
        playbook_path: Root directory of the playbook project
        runner: Subprocess runner function (injectable for testing)
    
    Strategy:
        1. If roles/ contains entries, assume they're ready (skip)
        2. If sibling ../ans_dev_sandbox_role/ exists, symlink it for development
        3. Otherwise, install roles from roles/requirements.yml via ansible-galaxy
    
    Note:
        Development mode uses symlink to external role repo for live editing.
        Production mode pulls role from GitHub via requirements.yml.
        This allows testing role changes without pushing to GitHub.
    """
    logging.info("Setting up Ansible roles")
    roles_dir = playbook_path / "roles"
    if not roles_dir.exists():
        logging.info("roles/ directory not present — skipping role check")
        return

    role_entries = [p for p in roles_dir.iterdir() if p.is_dir() or p.is_symlink()]
    if role_entries:
        logging.info("Roles already present (%d found); skipping install", len(role_entries))
        logging.debug("Existing roles: %s", [p.name for p in role_entries])
        return

    requirements = roles_dir / "requirements.yml"
    if not requirements.exists():
        logging.info("No roles found and roles/requirements.yml missing — skipping role install")
        return

    sibling_role = playbook_path.parent / "ans_dev_sandbox_role"
    if sibling_role.exists():
        logging.info("No roles found — linking to sibling ans_dev_sandbox_role at %s", sibling_role)
        link_path = roles_dir / "ans_dev_sandbox_role"
        if link_path.exists():
            logging.debug("Removing existing link at %s", link_path)
            link_path.unlink()
        relative_target = Path("../..") / "ans_dev_sandbox_role"
        link_path.symlink_to(relative_target)
        logging.info("Created symlink: %s -> %s", link_path, relative_target)
        return

    logging.info("Installing roles from requirements.yml")
    runner(["ansible-galaxy", "install", "--role-file", str(requirements), "--roles-path", str(roles_dir)])
    logging.info("Role installation complete")


def setup_collections(runner=_run_subprocess) -> None:
    """Ensure required Ansible collections are installed.
    
    Args:
        runner: Subprocess runner function (injectable for testing)
    
    Required collections:
        - ansible.posix: POSIX system management (firewall, selinux, etc.)
        - community.general: Community-maintained modules
    
    Note:
        Checks if each collection is already installed before attempting install.
        Collections are installed to the default location (varies by platform).
    """
    logging.info("Setting up Ansible collections")
    def _has_collection(name: str) -> bool:
        """Check if an Ansible collection is installed."""
        logging.debug("Checking if collection %s is installed", name)
        try:
            result = runner(["ansible-galaxy", "collection", "list"], capture=True)
        except subprocess.SubprocessError:
            logging.debug("Failed to list collections")
            return False
        installed = name in result.stdout
        logging.debug("Collection %s is %s", name, "installed" if installed else "not installed")
        return installed

    if not _has_collection("ansible.posix"):
        logging.info("Installing ansible.posix collection")
        runner(["ansible-galaxy", "collection", "install", "ansible.posix"])
        logging.debug("ansible.posix collection installed")
    else:
        logging.debug("ansible.posix collection already installed")

    if not _has_collection("community.general"):
        logging.info("Installing community.general collection")
        runner(["ansible-galaxy", "collection", "install", "community.general"])
        logging.debug("community.general collection installed")
    else:
        logging.debug("community.general collection already installed")


def setup_container(
    runtime: str,
    volume_opt: str,
    playbook_path: Path,
    container_name: str,
    host_port: int,
    ssh_port: int,
    image: str = DEFAULT_CONTAINER_IMAGE,
    runner=_run_subprocess,
) -> None:
    """Build and start the Ansible target container.
    
    Args:
        runtime: Container runtime to use ('podman' or 'docker')
        volume_opt: Volume mount options (':ro,z' for podman, ':ro' for docker)
        playbook_path: Root directory of the playbook project
        container_name: Name for the container
        host_port: Port on host to bind SSH (default: 2222)
        ssh_port: SSH port inside container (default: 22)
        image: Container image tag (default: 'ansible_target:latest')
        runner: Subprocess runner function (injectable for testing)
    
    Workflow:
        1. Build container image from containerfile (Fedora-based)
        2. Stop existing container with same name (if running)
        3. Start new container in detached mode
        4. Mount ssh_keys/ as /root/.ssh (for authorized_keys)
        5. Expose SSH on specified host_port
    
    Note:
        Container runs sshd in foreground and is removed on exit (--rm).
        SSH keys are mounted read-only with SELinux relabeling (podman).
    """
    logging.info("Setting up container %s using %s", container_name, runtime)
    logging.info("Building container image from containerfile")
    runner([runtime, "build", "--file", "containerfile", "--tag", container_name, str(playbook_path)])
    logging.debug("Container image built: %s", container_name)
    
    try:
        logging.debug("Attempting to stop existing container %s", container_name)
        runner([runtime, "container", "stop", container_name], capture=False)
        logging.debug("Existing container %s stopped", container_name)
    except subprocess.SubprocessError:
        logging.debug("Container %s not running before start; stop skipped", container_name)
    
    logging.info("Starting container %s on port %d", container_name, host_port)
    runner(
        [
            runtime,
            "run",
            "--detach",
            "--hostname",
            container_name,
            "--name",
            container_name,
            "--publish",
            f"{host_port}:{ssh_port}",
            "--rm",
            "--volume",
            f"{playbook_path / DEFAULT_SSH_DIR}:/root/.ssh{volume_opt}",
            image,
        ]
    )
    logging.info("Container %s started successfully", container_name)


def run_playbook(
    inventory: Path,
    playbook: Path,
    extra_env: Dict[str, str],
    limit: Optional[str],
    runner=_run_subprocess,
) -> None:
    """Execute an Ansible playbook.
    
    Args:
        inventory: Path to inventory file
        playbook: Path to playbook YAML file
        extra_env: Additional environment variables (SSH key, vault, etc.)
        limit: Optional Ansible --limit expression (host/group pattern)
        runner: Subprocess runner function (injectable for testing)
    
    Note:
        Merges extra_env with current os.environ for subprocess.
        Uses --limit to restrict playbook to specific hosts/groups.
        Common limits: 'localhost', 'ansible_target', or custom patterns.
    """
    env = os.environ.copy()
    env.update(extra_env)

    cmd = ["ansible-playbook", "--inventory", str(inventory), str(playbook)]
    if limit:
        cmd.extend(["-l", limit])

    logging.info("Running playbook %s", playbook)
    runner(cmd, env=env)


def run(args: argparse.Namespace) -> int:
    """Run the complete Ansible playbook workflow.
    
    Args:
        args: Parsed command-line arguments
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    
    Workflow:
        1. Load configuration from .env and environment
        2. Resolve container settings (runtime, name, ports) with CLI override support
        3. Detect and validate container runtime (podman/docker)
        4. Verify ansible is available
        5. Generate ephemeral SSH keys
        6. Build and start container (unless --skip-container)
        7. Ensure roles and collections are installed
        8. Execute playbook against targets
        9. Clean up container on exit
    
    CLI overrides:
        --container-runtime: Override CONTAINER_RUNTIME from .env
        --container-name: Override CONTAINER_NAME from .env
        --container-host-port: Override CONTAINER_HOST_PORT from .env
        --skip-container: Skip container setup (localhost-only mode)
        --limit: Restrict playbook to specific hosts
    
    Note:
        Container auto-cleanup uses try/finally to ensure cleanup even on errors.
        When --skip-container is used, limit defaults to 'localhost' if not specified.
    """
    logging.info("Starting playbook run workflow")
    playbook_path = Path(args.playbook_path).resolve() if args.playbook_path else Path(__file__).resolve().parent
    logging.debug("Playbook path: %s", playbook_path)
    env_file = Path(args.env_file)
    logging.debug("Environment file: %s", env_file)

    settings = load_env_file(env_file)
    set_env_vars(env_file)

    runtime_preference = args.container_runtime or settings.get("CONTAINER_RUNTIME") or DEFAULT_CONTAINER_RUNTIME
    if args.container_runtime and settings.get("CONTAINER_RUNTIME") and args.container_runtime != settings["CONTAINER_RUNTIME"]:
        logging.warning("Overriding CONTAINER_RUNTIME from .env (%s) with CLI value (%s)", settings["CONTAINER_RUNTIME"], args.container_runtime)

    container_name = args.container_name or settings.get("CONTAINER_NAME") or DEFAULT_CONTAINER_NAME
    if args.container_name and settings.get("CONTAINER_NAME") and args.container_name != settings["CONTAINER_NAME"]:
        logging.warning("Overriding CONTAINER_NAME from .env (%s) with CLI value (%s)", settings["CONTAINER_NAME"], args.container_name)

    host_port_str = args.container_host_port or settings.get("CONTAINER_HOST_PORT") or str(DEFAULT_HOST_PORT)
    if args.container_host_port and settings.get("CONTAINER_HOST_PORT") and args.container_host_port != settings["CONTAINER_HOST_PORT"]:
        logging.warning("Overriding CONTAINER_HOST_PORT from .env (%s) with CLI value (%s)", settings["CONTAINER_HOST_PORT"], args.container_host_port)

    try:
        host_port = int(host_port_str)
        logging.debug("Using host port: %d", host_port)
    except ValueError:
        logging.error("Invalid CONTAINER_HOST_PORT value: %s", host_port_str)
        return RETURN_CODES["NO_RUNTIME"]

    runtime, volume_opt = detect_container_runtime(runtime_preference)
    if not runtime:
        logging.error("Neither podman nor docker found; cannot continue")
        return RETURN_CODES["NO_RUNTIME"]
    logging.info("Using container runtime: %s", runtime)

    if not detect_ansible():
        return RETURN_CODES["MISSING_DEPENDENCY"]

    key_path, auth_keys = setup_ssh_keys(playbook_path, DEFAULT_KEY_BASENAME)
    vault_path = setup_vault(playbook_path)

    container_started = False
    try:
        if not args.skip_container:
            setup_container(runtime, volume_opt or ":ro", playbook_path, container_name, host_port, DEFAULT_SSH_PORT)
            container_started = True
            logging.debug("Container setup complete, marking as started")
        else:
            logging.info("Skipping container setup as requested")

        setup_roles(playbook_path)
        setup_collections()

        extra_env = {
            "ANSIBLE_PRIVATE_KEY_FILE": str(key_path),
            "ANSIBLE_HOST_KEY_CHECKING": "False",
            "ANSIBLE_VAULT_PASSWORD_FILE": str(vault_path),
        }

        limit = args.limit
        if args.skip_container and not args.limit:
            logging.info("Container skipped; defaulting limit to localhost")
            limit = "localhost"
        elif args.limit:
            logging.info("Using custom limit: %s", limit)

        run_playbook(playbook_path / INVENTORY_FILE, playbook_path / PLAYBOOK_FILE, extra_env, limit)
        logging.info("Playbook execution complete")
    finally:
        if container_started:
            logging.info("Cleaning up container %s", container_name)
            try:
                _run_subprocess([runtime, "container", "stop", container_name])
                logging.debug("Container %s stopped successfully", container_name)
            except subprocess.SubprocessError:
                logging.warning("Failed to stop container %s during cleanup", container_name)

    logging.info("Run workflow complete")
    return RETURN_CODES["SUCCESS"]


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.
    
    Args:
        argv: Optional argument list (defaults to sys.argv if None)
    
    Returns:
        Parsed arguments namespace
    
    Subcommands:
        activate: Prepare environment (venv, requirements, .env)
        run: Execute playbook workflow (container, roles, playbook)
    
    Global options:
        --env-file: Path to .env file (default: .env)
        -v/--verbose: Increase verbosity (repeatable, max 4)
        --log-file: Write logs to file in addition to stderr
    """
    parser = argparse.ArgumentParser(description="Ansible sandbox helper")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE), help="Path to .env file (default: .env)")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity (repeatable)")
    parser.add_argument("--log-file", type=Path, default=None, help="Optional log file path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    activate_parser = subparsers.add_parser("activate", help="Prepare virtualenv and write .env")
    activate_parser.add_argument("--playbook-path", dest="playbook_path", help=argparse.SUPPRESS)
    activate_parser.set_defaults(func=activate)

    run_parser = subparsers.add_parser("run", help="Run playbook workflow")
    run_parser.add_argument("--container-runtime", choices=["podman", "docker"], help="Container runtime to use")
    run_parser.add_argument("--container-name", help="Container name override")
    run_parser.add_argument("--container-host-port", help="Host port for SSH (default 2222)")
    run_parser.add_argument("--skip-container", action="store_true", help="Skip container build/run (localhost-only)")
    run_parser.add_argument("--limit", help="Ansible --limit expression")
    run_parser.add_argument("--playbook-path", dest="playbook_path", help=argparse.SUPPRESS)
    run_parser.set_defaults(func=run)

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the sandbox CLI.
    
    Args:
        argv: Optional argument list (defaults to sys.argv if None)
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    
    Error handling:
        - SystemExit: Re-raised (normal argparse behavior)
        - All other exceptions: Logged as critical and return code 1
    
    Note:
        Configures logging before executing subcommand.
        Verbosity levels: 0=CRITICAL, 1=ERROR, 2=WARNING, 3=INFO, 4+=DEBUG
    """
    args = parse_args(argv)
    configure_logging(args.verbose, args.log_file)
    logging.debug("Parsed args: %s", args)

    try:
        return args.func(args)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        logging.critical("Unhandled exception: %s", exc)
        return RETURN_CODES["UNHANDLED_EXCEPTION"]


if __name__ == "__main__":
    sys.exit(main())
