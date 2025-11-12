#!/bin/bash -x

set -euo pipefail

# Deactivate any existing virtual environment
deactivate 2>/dev/null || true

# Get the directory of this script, resolving symlinks
get_script_dir() {
    local source_path="${BASH_SOURCE[0]}"
    while [[ -L "$source_path" ]]; do
        source_path="$(readlink -f "$source_path")"
    done
    cd -P "$(dirname "$source_path")" >/dev/null && pwd
}

export PLAYBOOK_PATH="$(get_script_dir)"
cd "$PLAYBOOK_PATH" || return 1

# Activate existing venv or create a new one
if [[ -d .venv ]]; then
    # shellcheck disable=SC1091
    source ./.venv/bin/activate
    return 0
fi

# Find suitable Python interpreter
find_python() {
    # Use a newline-separated string for portability when sourcing the script
    local candidates="" p ver

    # Search common locations
    for p in /usr/bin/python3* /usr/local/bin/python3* /opt/*/bin/python3*; do
        [[ -x "$p" ]] || continue
        [[ "$(basename "$p")" =~ ^python3([.0-9]+)?$ ]] || continue

        ver=$("$p" -c 'import sys; v=sys.version_info; print("%d.%d.%d"%(v.major,v.minor,v.micro))' 2>/dev/null) || continue
        if [[ -z "$candidates" ]]; then
            candidates="$p:$ver"
        else
            candidates="$candidates
$p:$ver"
        fi
    done

    # Add python3 from PATH if not already present
    if command -v python3 >/dev/null 2>&1; then
        p="$(command -v python3)"
        if [[ -x "$p" ]]; then
            local already_added=false
            # iterate over newline-separated entries
            while IFS= read -r c; do
                [[ -z "$c" ]] && continue
                [[ "$c" == "$p:"* ]] && already_added=true && break
            done <<< "$candidates"

            if [[ "$already_added" == false ]]; then
                ver=$("$p" -c 'import sys; v=sys.version_info; print("%d.%d.%d"%(v.major,v.minor,v.micro))' 2>/dev/null) || true
                if [[ -n "$ver" ]]; then
                    if [[ -z "$candidates" ]]; then
                        candidates="$p:$ver"
                    else
                        candidates="$candidates
$p:$ver"
                    fi
                fi
            fi
        fi
    fi

    [[ -z "$candidates" ]] && return 1
    printf '%s\n' "$candidates"
}

# Select best Python version (newest < 3.14)
select_python() {
    # Read candidate lines from stdin in the Python program invoked with -c so
    # the piped input becomes python's sys.stdin (using a here-doc would steal
    # stdin and ignore the piped candidates).
    python3 -c 'import sys

best = None
best_path = None

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        path, ver = line.split(":", 1)
        parts = tuple(int(x) for x in ver.split(".")[:3])
        if parts < (3, 14, 0) and (best is None or parts > best):
            best = parts
            best_path = path
    except (ValueError, IndexError):
        continue

if best_path:
    print(best_path)
    sys.exit(0)
sys.exit(2)
'
}

echo "No .venv found — locating a suitable Python (newest < 3.14) to create one..."

candidates=$(find_python) || {
    echo "No python3 interpreters found on the system. Please install Python 3.13 or older." >&2
    return 1
}

picked=$(echo "$candidates" | select_python) || {
    echo "No suitable Python < 3.14 found. Please install Python 3.13 or older." >&2
    return 1
}

echo "Creating virtualenv using: $picked"
"$picked" -m venv .venv || {
    echo "Failed to create venv with $picked" >&2
    return 1
}

# Activate the newly-created venv
# shellcheck disable=SC1091
: "${PROMPT_START:=}"
: "${PROMPT_END:=}"
: "${PROMPT_CONTAINER:=}"
source ./.venv/bin/activate

# Upgrade pip and install tools using the venv's python
VENV_PY="$(pwd)/.venv/bin/python"
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install ansible-dev-tools


# Configure Ansible environment
export ANSIBLE_DISPLAY_ARGS_TO_STDOUT=false
export ANSIBLE_CALLBACKS_ENABLED='profile_tasks'
export ANSIBLE_LOAD_CALLBACK_PLUGINS=true
export ANSIBLE_LOG_PATH=./ansible.log
export ANSIBLE_ROLES_PATH=roles
export ANSIBLE_FILTER_PLUGINS=plugins
export ANSIBLE_LIBRARY=library
export ANSIBLE_CALLBACK_RESULT_FORMAT=yaml
export ANSIBLE_VAULT_PASSWORD_FILE="$PLAYBOOK_PATH/vault-pw.txt"

# Convenient alias for decrypting vaulted items
alias avdad='python "$PLAYBOOK_PATH/DECRYPT_VAULTED_ITEMS.py"'