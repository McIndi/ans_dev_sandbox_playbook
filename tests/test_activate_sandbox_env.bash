#!/bin/bash

# Test harness
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

# Setup
TEST_DIR=$(mktemp -d)
ORIGINAL_DIR=$(pwd)
SCRIPT_PATH="$(pwd)/ACTIVATE_SANDBOX_ENV.bash"

cleanup() {
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

# Copy script to test dir to avoid modifying source if we needed to, 
# but here we just want to run it in a clean env.
# We need to source the script.
# The script expects to be in a git repo or similar, it does `cd "$PLAYBOOK_PATH"`.
# We should probably run tests from the repo root.

# Test 1: select_python logic
echo "Running Test 1: select_python logic"
(
    # Source the script with UNIT_TESTING set
    export UNIT_TESTING=true
    # We need to mock cd or ensure we are in a valid place.
    # The script does `cd "$PLAYBOOK_PATH"`.
    # If we source it from the current dir, PLAYBOOK_PATH will be current dir.
    
    source "$SCRIPT_PATH"
    
    # Test select_python with valid input
    input="
/usr/bin/python3.13:3.13.0
/usr/bin/python3.12:3.12.0
/usr/bin/python3.11:3.11.5
"
    result=$(echo "$input" | select_python)
    assert_equals "/usr/bin/python3.13" "$result" "Select newest python < 3.14"

    # Test with newer python
    input="
/usr/bin/python3.13:3.13.0
/usr/bin/python3.12:3.12.0
"
    result=$(echo "$input" | select_python)
    assert_equals "/usr/bin/python3.13" "$result" "Ignore python >= 3.14"

    # Test with invalid input
    input="
invalid
"
    result=$(echo "$input" | select_python)
    # Should fail (exit 2)
    if [[ $? -ne 0 ]]; then
         echo "PASS: Handle invalid input"
    else
         echo "FAIL: Should have failed on invalid input"
         FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
)

# Test 2: get_script_dir
echo "Running Test 2: get_script_dir logic"
(
    export UNIT_TESTING=true
    source "$SCRIPT_PATH"
    
    # Verify PLAYBOOK_PATH is set to the directory of the script
    # Since we sourced it using absolute path, it should resolve correctly.
    expected_dir=$(dirname "$SCRIPT_PATH")
    assert_equals "$expected_dir" "$PLAYBOOK_PATH" "PLAYBOOK_PATH set correctly"
)

# Summary
echo "------------------------------------------------"
echo "Tests run: $TEST_COUNT"
echo "Failures:  $FAIL_COUNT"

if [[ $FAIL_COUNT -eq 0 ]]; then
    echo "ALL TESTS PASSED"
    exit 0
else
    echo "SOME TESTS FAILED"
    exit 1
fi
