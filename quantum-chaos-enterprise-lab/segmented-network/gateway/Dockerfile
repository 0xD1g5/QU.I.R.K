# QU.I.R.K. — segmented-network chaos lab gateway container.
#
# Phase 152 / DISC-09/DISC-10: this container sits between the "live" and
# "dead" bridge networks (segnet-live / segnet-dead) and REJECTs all forward
# traffic destined for the dead subnet, producing genuine RST (TCP) /
# ICMP-host-unreachable behavior instead of the unassigned-loopback-alias
# silence every other chaos lab profile uses.
#
# Base image: alpine:3.20 (patch-pinned per CHAOS-05 policy — reuses the
# exact tag already pinned elsewhere in docker-compose.yml, e.g. tls-modern's
# nginx sibling services and otics-modbus's base image family).
#
# Capability: this container requires cap_add: [NET_ADMIN] (granted at the
# compose level, NOT via --privileged) so entrypoint.sh can flip
# net.ipv4.ip_forward and install iptables FORWARD-chain rules inside its own
# network namespace. Scope is limited to this single gateway container — no
# other service in this profile (or the wider lab) needs NET_ADMIN. This is
# the same "minimal explicit capability, never --privileged" posture as
# sensor.Dockerfile's cap_add: [NET_RAW] for raw-socket nmap scanning.
FROM alpine:3.20

RUN apk add --no-cache iptables

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
