FROM ubuntu:18.04

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends openssh-server && \
    rm -rf /var/lib/apt/lists/*

# Generate all required host keys including DSA (required for ssh-dss HostKeyAlgorithms)
RUN ssh-keygen -A && \
    ssh-keygen -t dsa -N "" -f /etc/ssh/ssh_host_dsa_key 2>/dev/null || true

# Inject weak sshd_config
COPY sshd_config /etc/ssh/sshd_config

# Create privilege separation dir
RUN mkdir -p /run/sshd

# Create a test user for SSH connections
RUN useradd -m -s /bin/bash labuser && \
    echo "labuser:labpass" | chpasswd

EXPOSE 22

# Run sshd in foreground with debug output for container logs
CMD ["/usr/sbin/sshd", "-D", "-e"]
