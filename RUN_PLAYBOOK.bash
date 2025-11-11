#!/usr/bin/bash

cd $PLAYBOOK_PATH &&\
   podman build --file containerfile --tag ansible_target . &&\
   podman run --detach --hostname ansible_target --name ansible_target --publish 2222:22 --rm --volume ~/.ssh:/root/.ssh:ro,z ansible_target:latest &&\
   echo '' > ansible.log &&\
   clear &&\
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
                  echo "No roles found in roles/ — installing from roles/requirements.yml"
                  ansible-galaxy install -r roles/requirements.yml
               else
                  echo "No roles found and roles/requirements.yml missing — skipping role install"
               fi
            else
               :
         fi
      else
         echo "roles/ directory not present — skipping role check"
   fi
   ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook --inventory inventory/main.yml playbooks/sample_playbook.yml

podman container stop ansible_target

