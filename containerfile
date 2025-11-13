# we could use an explicit, configurable Fedora version to avoid "latest" surprises but, in this, we prefer the latest image
# ARG FEDORA_VERSION=43
# FROM fedora:${FEDORA_VERSION}
FROM fedora:latest

# Use bash with pipefail for safer RUN chains
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Metadata
LABEL org.opencontainers.image.title="ans_dev_sandbox_ssh_target" \
 org.opencontainers.image.description="Lightweight Fedora image with OpenSSH for Ansible target testing" \
 org.opencontainers.image.licenses="MIT"

# Install OpenSSH and minimal utilities in a single layer to improve cache efficiency
# - disable weak deps and docs to reduce image size
RUN dnf -y update && \
 dnf -y install --setopt=install_weak_deps=False --nodocs \
 openssh-server openssh-clients python3 git procps && \
 ssh-keygen -A && \
 dnf clean all && \
 rm -rf /var/cache/dnf /var/cache/yum /tmp/*

# Expose SSH port
EXPOSE 22

# Optional healthcheck to ensure sshd is running (requires `procps` for `pgrep`)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
 CMD pgrep -x sshd >/dev/null || exit 1

# Run sshd in the foreground (no debug logging by default)
CMD ["/usr/sbin/sshd", "-dD"]
