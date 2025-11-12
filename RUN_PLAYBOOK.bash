#!/usr/bin/bash

cd $PLAYBOOK_PATH &&\
   mkdir ssh_keys &&\
   chmod 700 ssh_keys &&\
   ssh-keygen -N '' -f ssh_keys/ansible_target &&\
   cp ssh_keys/ansible_target.pub ssh_keys/authorized_keys
   export ANSIBLE_PRIVATE_KEY_FILE=$PWD/ssh_keys/ansible_target &&\
   podman build --file containerfile --tag ansible_target . &&\
   podman run --detach --hostname ansible_target --name ansible_target --publish 2222:22 --rm --volume $PWD/ssh_keys:/root/.ssh:ro,z ansible_target:latest &&\
   echo '' > ansible.log &&\
   if [ -f ./vault-pw.txt ]
      then
         :
      else
         echo 'password' > ./vault-pw.txt
   fi
   if [ -d roles ]
      then
         role_count=$(find roles -mindepth 1 -maxdepth 1 \( -type l -o -type d \) | wc -l)
         if [ "${role_count}" -eq 0 ]
            then
               if [ -f roles/requirements.yml ]; then
                  if [ -d ../ans_dev_sandbox_role/ ]
                     then
                        echo "No roles found in roles/ — linking to ../ans_dev_sandbox_role/"
                        ln -s ../../ans_dev_sandbox_role/ roles/ans_dev_sandbox_role
                     else
                        echo "No roles found in roles/ — installing from roles/requirements.yml"
                        ansible-galaxy install --role-file roles/requirements.yml
                  fi
               else
                  echo "No roles found and roles/requirements.yml missing — skipping role install"
               fi
            else
               :
         fi
      else
         echo "roles/ directory not present — skipping role check"
   fi
   if [ $(ansible-galaxy collection list | grep -q ansible\.posix) ]
      then
         :
      else
         ansible-galaxy collection install ansible.posix
   fi
   ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook --inventory inventory/main.yml playbooks/sample_playbook.yml

podman container stop ansible_target

