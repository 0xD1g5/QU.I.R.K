#!/bin/sh
# QU.I.R.K. — segmented-network chaos lab gateway entrypoint.
#
# Phase 152 / DISC-09/DISC-10. This container is attached to two Docker
# bridge networks (segnet-live, segnet-dead) and acts as the routing point
# between them. Enabling IP forwarding + FORWARD-chain REJECT rules here
# scopes the REJECT policy to THIS container's own network namespace/routing
# table — NOT the Docker host's iptables tables — which is the correct scope
# for a container with two attached NICs (see RESEARCH.md Pitfall 1).
#
# Effect: any packet destined for the dead subnet (segnet-dead, injected via
# SEGNET_DEAD_CIDR) that reaches this container's FORWARD chain is REJECTed
# with a TCP RST (for TCP traffic) or ICMP host-unreachable (all other
# traffic) instead of being silently dropped or forwarded. This produces
# genuine "unreachable host" network behavior for scanner verification.
set -e

SEGNET_DEAD_CIDR="${SEGNET_DEAD_CIDR:-10.71.0.0/24}"

# IP forwarding is set via compose's `sysctls: [net.ipv4.ip_forward=1]`
# (Docker applies this at container-creation time). /proc/sys is read-only
# from inside a non-host-network bridge container even with NET_ADMIN, so
# this in-container attempt is a defense-in-depth no-op on Docker
# Desktop/Engine — failures here are tolerated (|| true) rather than fatal.
echo "[segnet-gateway] enabling IP forwarding"
sysctl -w net.ipv4.ip_forward=1 || echo "[segnet-gateway] in-container sysctl -w failed (expected — relying on compose sysctls:)"
if [ "$(cat /proc/sys/net/ipv4/ip_forward 2>/dev/null)" != "1" ]; then
  echo "[segnet-gateway] FATAL: net.ipv4.ip_forward is not 1 — compose sysctls: entry did not apply" >&2
  exit 1
fi

echo "[segnet-gateway] installing FORWARD-chain REJECT rules for ${SEGNET_DEAD_CIDR}"
# TCP traffic to the dead subnet gets a real RST — fast "closed" response.
iptables -A FORWARD -d "${SEGNET_DEAD_CIDR}" -p tcp -j REJECT --reject-with tcp-reset
# Everything else (including the ICMP probes nmap -Pn skips, but kept for
# completeness/non-TCP protocols) gets ICMP host-unreachable.
iptables -A FORWARD -d "${SEGNET_DEAD_CIDR}" -j REJECT --reject-with icmp-host-unreachable

echo "[segnet-gateway] rules installed, idling"
tail -f /dev/null
