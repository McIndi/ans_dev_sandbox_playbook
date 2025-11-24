#!/bin/bash

# Test harness for RUN_PLAYBOOK.bash
TEST_COUNT=0
FAIL_COUNT=0

assert_equals() {
    local expected="$1"
    local actual="$2"
    local message="${3:-}"
    if [[ "$expected" == "$actual" ]]; then
        echo "PASS: $message"
    else
        echo "FAIL: $message"
        echo "  Expected: '$expected'"
        echo "  Actual:   '$actual'"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    TEST_COUNT=$((TEST_COUNT + 1))
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local message="${3:-}"
    if [[ "$haystack" == *"$needle"* ]]; then
        echo "PASS: $message"
    else
        echo "FAIL: $message"
        echo "  Needle:   '$needle'"
        echo "  Haystack: '$haystack'"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    TEST_COUNT=$((TEST_COUNT + 1))
}

# Setup
TEST_DIR=$(mktemp -d)
SCRIPT_PATH="$(pwd)/RUN_PLAYBOOK.bash"

cleanup() {
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

# Test 1: setup_ssh_keys
echo "Running Test 1: setup_ssh_keys"
(
    cd "$TEST_DIR" || exit 1
    export PLAYBOOK_PATH="$TEST_DIR"
    export UNIT_TESTING=true
    
    # Mock dependencies
    function ansible() { :; }
    function podman() { :; }
    function docker() { :; }
    
    # Mock ssh-keygen to avoid actual key generation but create expected files
    function ssh-keygen() {
        # args: -N '' -f "$SSH_KEY_FILE" -C "ansible@target"
        local key_file=""
        local next_is_file=false
        for arg in "$@"; do
            if [[ "$arg" == "-f" ]]; then
                next_is_file=true
            elif [[ "$next_is_file" == "true" ]]; then
                key_file="$arg"
                next_is_file=false
            fi
        done
        # Create the key file and pub file
        if [[ -n "$key_file" ]]; then
            touch "$key_file"
            touch "$key_file.pub"
        fi
        return 0
    }
    
    export -f ansible podman docker ssh-keygen

    # Source the script
    source "$SCRIPT_PATH"

    # Run the function
    setup_ssh_keys

    # Verify
    if [[ -d "ssh_keys" ]]; then
        echo "PASS: ssh_keys directory created"
    else
        echo "FAIL: ssh_keys directory not created"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    
    if [[ -f "ssh_keys/ansible_target" && -f "ssh_keys/ansible_target.pub" ]]; then
         echo "PASS: key files created"
    else
         echo "FAIL: key files not created"
         FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    
    if [[ -f "ssh_keys/authorized_keys" ]]; then
        echo "PASS: authorized_keys created"
    else
        echo "FAIL: authorized_keys not created"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    
    exit $FAIL_COUNT
)
if [[ $? -ne 0 ]]; then FAIL_COUNT=$((FAIL_COUNT + 1)); fi

# Test 2: setup_container (using podman)
echo "Running Test 2: setup_container (podman)"
(
    cd "$TEST_DIR" || exit 1
    export PLAYBOOK_PATH="$TEST_DIR"
    export UNIT_TESTING=true
    
    # Mock dependencies
    function ansible() { :; }
    function podman() { echo "MOCK_PODMAN $*"; }
    function docker() { :; }
    
    export -f ansible podman docker

    source "$SCRIPT_PATH"
    
    # Verify CONTAINER_RUNTIME detected as podman
    assert_equals "podman" "$CONTAINER_RUNTIME" "Detected podman runtime"
    
    # Run setup_container and capture output
    output=$(setup_container)
    
    assert_contains "$output" "MOCK_PODMAN build --file containerfile" "Container build command correct"
    assert_contains "$output" "MOCK_PODMAN run" "Container run command correct"
    assert_contains "$output" "--name ansible_target" "Container name correct"
    
    exit $FAIL_COUNT
)
if [[ $? -ne 0 ]]; then FAIL_COUNT=$((FAIL_COUNT + 1)); fi

# Test 3: setup_roles (install from requirements)
echo "Running Test 3: setup_roles (requirements.yml)"
(
    cd "$TEST_DIR" || exit 1
    export PLAYBOOK_PATH="$TEST_DIR"
    export UNIT_TESTING=true
    
    # Setup roles dir structure
    mkdir -p roles
    touch roles/requirements.yml
    
    # Mock dependencies
    function ansible() { :; }
    function podman() { :; }
    function ansible-galaxy() { echo "MOCK_GALAXY $*"; }
    
    export -f ansible podman ansible-galaxy

    source "$SCRIPT_PATH"
    
    output=$(setup_roles)
    
    assert_contains "$output" "MOCK_GALAXY install --role-file roles/requirements.yml" "Roles installed from requirements"
    
    exit $FAIL_COUNT
)
if [[ $? -ne 0 ]]; then FAIL_COUNT=$((FAIL_COUNT + 1)); fi

# Test 4: setup_roles (skip if roles exist)
echo "Running Test 4: setup_roles (roles exist)"
(
    cd "$TEST_DIR" || exit 1
    export PLAYBOOK_PATH="$TEST_DIR"
    export UNIT_TESTING=true
    
    # Setup roles dir with a dummy role
    mkdir -p roles/dummy_role
    
    # Mock dependencies
    function ansible() { :; }
    function podman() { :; }
    function ansible-galaxy() { echo "MOCK_GALAXY $*"; }
    
    export -f ansible podman ansible-galaxy

    source "$SCRIPT_PATH"
    
    output=$(setup_roles)
    
    if [[ -z "$output" ]]; then
        echo "PASS: No output when roles exist (skipped)"
    else
        echo "FAIL: Unexpected output when roles exist: $output"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    
    exit $FAIL_COUNT
)
if [[ $? -ne 0 ]]; then FAIL_COUNT=$((FAIL_COUNT + 1)); fi

# Test 5: setup_roles (local role linking)
echo "Running Test 5: setup_roles (local role linking)"
(
    # Create a nested structure to simulate sibling directories
    # TEST_DIR/
    #   ├── workspace/
    #   │   ├── ans_dev_sandbox_playbook/  (PLAYBOOK_PATH)
    #   │   └── ans_dev_sandbox_role/      (Sibling role)
    
    WORKSPACE_DIR="$TEST_DIR/workspace"
    mkdir -p "$WORKSPACE_DIR/ans_dev_sandbox_playbook/roles"
    mkdir -p "$WORKSPACE_DIR/ans_dev_sandbox_role"
    
    cd "$WORKSPACE_DIR/ans_dev_sandbox_playbook" || exit 1
    export PLAYBOOK_PATH="$PWD"
    export UNIT_TESTING=true
    
    # Create requirements.yml to trigger the check
    touch roles/requirements.yml
    
    # Mock dependencies
    function ansible() { :; }
    function podman() { :; }
    function ansible-galaxy() { echo "MOCK_GALAXY $*"; }
    
    export -f ansible podman ansible-galaxy

    source "$SCRIPT_PATH"
    
    output=$(setup_roles)
    
    assert_contains "$output" "No roles found in roles/ — linking to ../ans_dev_sandbox_role/" "Output indicates local linking"
    
    if [[ -L "roles/ans_dev_sandbox_role" ]]; then
        echo "PASS: Symlink created"
        # Verify link target
        target=$(readlink "roles/ans_dev_sandbox_role")
        if [[ "$target" == "../../ans_dev_sandbox_role/" ]]; then
             echo "PASS: Symlink target is correct"
        else
             echo "FAIL: Symlink target incorrect. Got: '$target'"
             FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
    else
        echo "FAIL: Symlink not created"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    
    # Verify ansible-galaxy was NOT called
    if [[ "$output" == *"MOCK_GALAXY"* ]]; then
        echo "FAIL: ansible-galaxy should not be called when linking locally"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    else
        echo "PASS: ansible-galaxy was not called"
    fi
    
    exit $FAIL_COUNT
)
if [[ $? -ne 0 ]]; then FAIL_COUNT=$((FAIL_COUNT + 1)); fi

# Test 6: setup_collections (install if missing)
echo "Running Test 6: setup_collections (install if missing)"
(
    cd "$TEST_DIR" || exit 1
    export PLAYBOOK_PATH="$TEST_DIR"
    export UNIT_TESTING=true
    
    # Mock dependencies
    function ansible() { :; }
    function podman() { :; }
    function ansible-galaxy() {
        if [[ "$1" == "collection" && "$2" == "list" ]]; then
            # Return empty output to simulate missing collection
            echo ""
        elif [[ "$1" == "collection" && "$2" == "install" ]]; then
            echo "MOCK_GALAXY $*"
        fi
    }
    
    export -f ansible podman ansible-galaxy

    source "$SCRIPT_PATH"
    
    output=$(setup_collections)
    
    assert_contains "$output" "Installing ansible.posix collection..." "ansible.posix log message present"
    assert_contains "$output" "MOCK_GALAXY collection install ansible.posix" "ansible.posix install command called"
    assert_contains "$output" "Installing community.general collection..." "community.general log message present"
    assert_contains "$output" "MOCK_GALAXY collection install community.general" "community.general install command called"
    
    exit $FAIL_COUNT
)
if [[ $? -ne 0 ]]; then FAIL_COUNT=$((FAIL_COUNT + 1)); fi

# Test 7: setup_collections (skip if present)
echo "Running Test 7: setup_collections (skip if present)"
(
    cd "$TEST_DIR" || exit 1
    export PLAYBOOK_PATH="$TEST_DIR"
    export UNIT_TESTING=true
    
    # Mock dependencies
    function ansible() { :; }
    function podman() { :; }
    function ansible-galaxy() {
        if [[ "$1" == "collection" && "$2" == "list" ]]; then
            # Return existing collections
            echo "ansible.posix 1.5.4"
            echo "community.general 8.0.0"
        elif [[ "$1" == "collection" && "$2" == "install" ]]; then
            echo "MOCK_GALAXY $*"
        fi
    }
    
    export -f ansible podman ansible-galaxy

    source "$SCRIPT_PATH"
    
    output=$(setup_collections)
    
    if [[ "$output" == *"Installing ansible.posix collection"* ]]; then
        echo "FAIL: Should not attempt to install ansible.posix if collection exists"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    else
        echo "PASS: No ansible.posix install attempted"
    fi
    
    if [[ "$output" == *"Installing community.general collection"* ]]; then
        echo "FAIL: Should not attempt to install community.general if collection exists"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    else
        echo "PASS: No community.general install attempted"
    fi
    
    if [[ "$output" == *"MOCK_GALAXY collection install"* ]]; then
        echo "FAIL: ansible-galaxy install should not be called"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    
    exit $FAIL_COUNT
)
if [[ $? -ne 0 ]]; then FAIL_COUNT=$((FAIL_COUNT + 1)); fi

# Summary
echo "------------------------------------------------"
# Note: TEST_COUNT is not accurate because of subshells, but FAIL_COUNT is accurate for test block failures.
echo "Failures:  $FAIL_COUNT"

if [[ $FAIL_COUNT -eq 0 ]]; then
    echo "ALL TESTS PASSED"
    exit 0
else
    echo "SOME TESTS FAILED"
    exit 1
fi
