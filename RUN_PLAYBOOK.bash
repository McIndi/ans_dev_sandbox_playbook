#!/usr/bin/bash

set -euo pipefail

# Configuration
readonly SSH_DIR="ssh_keys"
readonly SSH_KEY_FILE="$SSH_DIR/ansible_target"
readonly SSH_AUTHORIZED_KEYS="$SSH_DIR/authorized_keys"
readonly VAULT_PASSWORD_FILE="./vault-pw.txt"
readonly ANSIBLE_LOG_FILE="./ansible.log"
readonly CONTAINER_NAME="ansible_target"
readonly CONTAINER_HOST_PORT=2222
readonly CONTAINER_SSH_PORT=22

# Detect ansible runtime
if command -v ansible >/dev/null 2>&1; then
    echo "INFO: 'ansible' was found in PATH" 
else
    echo "Error: 'ansible' was not found in PATH" >&2
    exit 1
fi

# Detect container runtime: prefer podman, fall back to docker
if command -v podman >/dev/null 2>&1; then
    readonly CONTAINER_RUNTIME="podman"
    echo "INFO: 'podman' was found in PATH" 
elif command -v docker >/dev/null 2>&1; then
    readonly CONTAINER_RUNTIME="docker"
    echo "INFO: 'docker' was found in PATH" 
else
    echo "Error: neither 'podman' nor 'docker' was found in PATH" >&2
    exit 1
fi

# Volume mount option differs for podman (SELinux) vs docker
if [[ "$CONTAINER_RUNTIME" == "podman" ]]; then
    readonly VOLUME_OPT=":ro,z"
else
    readonly VOLUME_OPT=":ro"
fi

# Error handler
cleanup() {
    local exit_code=$?
    echo "Cleaning up..."
    "$CONTAINER_RUNTIME" container stop "$CONTAINER_NAME" 2>/dev/null || true
    exit "$exit_code"
}

trap cleanup EXIT

# Ensure we're in the playbook directory
cd "${PLAYBOOK_PATH:-.}" || {
    echo "Error: Could not change to playbook directory" >&2
    exit 1
}

# Create SSH key pair
setup_ssh_keys() {
    mkdir -p "$SSH_DIR"
    chmod 700 "$SSH_DIR"
    echo 'y' | ssh-keygen -N '' -f "$SSH_KEY_FILE" -C "ansible@target"
    cp "$SSH_KEY_FILE.pub" "$SSH_AUTHORIZED_KEYS"
    export ANSIBLE_PRIVATE_KEY_FILE="$PWD/$SSH_KEY_FILE"
}

# Build and run container
setup_container() {
    "$CONTAINER_RUNTIME" build --file containerfile --tag ansible_target . || {
        echo "Error: Failed to build container" >&2
        return 1
    }
    
    "$CONTAINER_RUNTIME" container stop "$CONTAINER_NAME" 2>/dev/null || true
    
    "$CONTAINER_RUNTIME" run \
        --detach \
        --hostname "$CONTAINER_NAME" \
        --name "$CONTAINER_NAME" \
        --publish "$CONTAINER_HOST_PORT:$CONTAINER_SSH_PORT" \
        --rm \
        --volume "$PWD/$SSH_DIR:/root/.ssh${VOLUME_OPT}" \
        "ansible_target:latest" || {
        echo "Error: Failed to start container" >&2
        return 1
    }
}

# Setup vault password file
setup_vault() {
    if [[ ! -f "$VAULT_PASSWORD_FILE" ]]; then
        echo 'password' > "$VAULT_PASSWORD_FILE"
        echo "Created vault password file"
    fi
}

# Install roles if needed
setup_roles() {
    [[ ! -d roles ]] && {
        echo "roles/ directory not present — skipping role check"
        return 0
    }
    
    local role_count
    role_count=$(find roles -mindepth 1 -maxdepth 1 \( -type l -o -type d \) | wc -l)
    
    [[ $role_count -gt 0 ]] && return 0
    
    if [[ -f roles/requirements.yml ]]; then
        if [[ -d ../ans_dev_sandbox_role/ ]]; then
            echo "No roles found in roles/ — linking to ../ans_dev_sandbox_role/"
            ln -s ../../ans_dev_sandbox_role/ roles/ans_dev_sandbox_role
        else
            echo "No roles found in roles/ — installing from roles/requirements.yml"
            ansible-galaxy install --role-file roles/requirements.yml
        fi
    else
        echo "No roles found and roles/requirements.yml missing — skipping role install"
    fi
}

# Install required collections
setup_collections() {
    if ! ansible-galaxy collection list 2>/dev/null | grep -q ansible.posix; then
        echo "Installing ansible.posix collection..."
        ansible-galaxy collection install ansible.posix
    fi
}

# Main execution
main() {
    setup_ssh_keys
    setup_container
    setup_vault
    setup_roles
    setup_collections
    
    # Initialize ansible log
    > "$ANSIBLE_LOG_FILE"
    
    echo "Running playbook..."
    ANSIBLE_HOST_KEY_CHECKING=False \
        ansible-playbook \
            --inventory inventory/main.yml \
            playbooks/sample_playbook.yml
}

main "$@"