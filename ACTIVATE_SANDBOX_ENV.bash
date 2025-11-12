#!/usr/bin/bash

deactivate

GET_SCRIPT_DIR()
{
    local SOURCE_PATH="${BASH_SOURCE[0]}"
    local SYMLINK_DIR
    local SCRIPT_DIR
    # Resolve symlinks recursively
    while [ -L "$SOURCE_PATH" ]; do
        # Get symlink directory
        SYMLINK_DIR="$( cd -P "$( dirname "$SOURCE_PATH" )" >/dev/null 2>&1 && pwd )"
        # Resolve symlink target (relative or absolute)
        SOURCE_PATH="$(readlink "$SOURCE_PATH")"
        # Check if candidate path is relative or absolute
        if [[ $SOURCE_PATH != /* ]]; then
            # Candidate path is relative, resolve to full path
            SOURCE_PATH=$SYMLINK_DIR/$SOURCE_PATH
        fi
    done
    # Get final script directory path from fully resolved source path
    SCRIPT_DIR="$(cd -P "$( dirname "$SOURCE_PATH" )" >/dev/null 2>&1 && pwd)"
    echo "$SCRIPT_DIR"
}

export PLAYBOOK_PATH=$(GET_SCRIPT_DIR) &&\
 cd $PLAYBOOK_PATH &&\
 if [ -d .venv ]
  then
   source ./.venv/bin/activate
  else
   python3 -m venv .venv &&\
   source ./.venv/bin/activate
   python -m pip install --upgrade pip &&\
   python -m pip install ansible-dev-tools
 fi
 export ANSIBLE_DISPLAY_ARGS_TO_STDOUT=false &&\
 export ANSIBLE_CALLBACKS_ENABLED='profile_tasks' &&\
 export ANSIBLE_LOAD_CALLBACK_PLUGINS=true &&\
 export ANSIBLE_LOG_PATH=./ansible.log &&\
 export ANSIBLE_ROLES_PATH=roles &&\
 export ANSIBLE_FILTER_PLUGINS=plugins &&\
 export ANSIBLE_LIBRARY=library &&\
 export ANSIBLE_CALLBACK_RESULT_FORMAT=yaml &&\
 export ANSIBLE_VAULT_PASSWORD_FILE=$PLAYBOOK_PATH/vault-pw.txt &&\
 alias avdad='python $PLAYBOOK_PATH/DECRYPT_VAULTED_ITEMS.py'
