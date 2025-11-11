#!/usr/bin/bash

# rm -fr /tmp/ansible.*

cd $PLAYBOOK_PATH &&\
 podman build --file containerfile --tag ansible_target . &&\
 podman run --detach --hostname ansible_target --name ansible_target --publish 2222:22 --rm --volume ~/.ssh:/root/.ssh:ro,z ansible_target:latest &&\
 echo '' > ansible.log &&\
 clear &&\
 ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook --inventory inventory/main.yml playbooks/sample_playbook.yml

podman container stop ansible_target

