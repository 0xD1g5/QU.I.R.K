"""Fragile BACnet/IP simulator — chaos-lab `otics` profile (Phase 141, OTICS-04).

Simulates a Johnson Controls FX16 field controller answering directed-unicast
Who-Is with I-Am, plus ReadProperty(model-name, firmware-revision) on the
Device object, over the real standard BACnet/IP UDP port (47808).

Behaviorally enforces fragility per 141-CONTEXT.md D-10 so
`expected_results_otics.md` can assert that the scanner's D-05 one-strike
circuit-breaker / OTICS-03 single-in-flight guarantee is what keeps this
simulator "healthy" — not just documented as a rule:

  - Single in-flight request only. A second Who-Is/ReadProperty arriving
    while one is already being processed is silently dropped (no response)
    rather than queued or answered — the UDP analog of "reset" for a
    connectionless protocol (there is no TCP connection to reset).
  - Malformed-input drop. Any inbound datagram that does not carry a valid
    BACnet/IP BVLC header (type byte 0x81) is dropped before it ever reaches
    the real `bacpypes3` Application's protocol stack.

Architecture: a lightweight asyncio UDP "gatekeeper" listens on the real
0.0.0.0:47808 and enforces the two fragility rules above, forwarding
well-formed datagrams to a real `bacpypes3` Application bound to an
internal-only loopback port and returning its responses to the original
client address. The actual BACnet/IP BVLC/NPDU/APDU framing, Who-Is/I-Am,
and ReadProperty handling are all done by `bacpypes3` itself (never
hand-rolled) — only the fragility policy at the raw-datagram admission layer
is custom.
"""
from __future__ import annotations

import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
_LOG = logging.getLogger("otics-bacnet-sim")

_PUBLIC_HOST = "0.0.0.0"
_PUBLIC_PORT = 47808
_INTERNAL_HOST = "127.0.0.1"
_INTERNAL_PORT = 47850

# Simulated device identity — Johnson Controls FX16 field controller
# (D-11 discretion; a recognizable BAS/HVAC controller model).
_DEVICE_NAME = "JCI-FX16-Sim"
_DEVICE_INSTANCE = 4001
_VENDOR_NAME = "Johnson Controls"
_VENDOR_IDENTIFIER = 5  # Johnson Controls' registered BACnet vendor ID
_MODEL_NAME = "FX16"
_FIRMWARE_REVISION = "9.0.1"

# One request in flight at a time (D-10 single-in-flight fragility).
_busy = False


def _looks_like_valid_bvlc(datagram: bytes) -> bool:
    """Sanity-check the BACnet/IP BVLC header.

    BVLC header layout: type(1, always 0x81 for BACnet/IP) + function(1) +
    length(2). Anything else is treated as malformed input (D-10
    drop-on-malformed — the UDP analog of a TCP reset).
    """
    if len(datagram) < 4:
        return False
    return datagram[0] == 0x81


class _GatekeeperProtocol(asyncio.DatagramProtocol):
    """Public-facing UDP gatekeeper enforcing D-10 fragility before forwarding
    well-formed traffic to the internal bacpypes3 Application."""

    def __init__(self) -> None:
        self.transport: asyncio.DatagramTransport | None = None
        self._internal_transport: asyncio.DatagramTransport | None = None
        self._client_addr: tuple[str, int] | None = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:  # type: ignore[override]
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:  # type: ignore[override]
        global _busy

        if not _looks_like_valid_bvlc(data):
            _LOG.warning("malformed BVLC datagram from %s — dropping", addr)
            return

        if _busy:
            _LOG.warning("dropping concurrent request from %s (single-in-flight)", addr)
            return

        _busy = True
        self._client_addr = addr
        asyncio.ensure_future(self._forward(data, addr))

    async def _forward(self, data: bytes, addr: tuple[str, int]) -> None:
        global _busy
        loop = asyncio.get_event_loop()
        try:
            transport, _protocol = await loop.create_datagram_endpoint(
                lambda: _InternalReplyProtocol(self),
                remote_addr=(_INTERNAL_HOST, _INTERNAL_PORT),
            )
            self._internal_transport = transport
            transport.sendto(data)
            # Bound how long a single in-flight slot can be held — protects
            # the simulator from a permanently wedged _busy flag if the
            # internal Application never replies.
            await asyncio.sleep(2.5)
        finally:
            if self._internal_transport is not None:
                self._internal_transport.close()
                self._internal_transport = None
            _busy = False

    def relay_reply(self, data: bytes) -> None:
        if self.transport is not None and self._client_addr is not None:
            self.transport.sendto(data, self._client_addr)


class _InternalReplyProtocol(asyncio.DatagramProtocol):
    """Relays the internal bacpypes3 Application's reply back to the
    original public client via the gatekeeper."""

    def __init__(self, gatekeeper: _GatekeeperProtocol) -> None:
        self._gatekeeper = gatekeeper

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:  # type: ignore[override]
        self._gatekeeper.relay_reply(data)


async def _run_internal_bacpypes3_application() -> None:
    """Start the real bacpypes3 Application on an internal-only loopback port."""
    from bacpypes3.app import Application
    from bacpypes3.local.device import DeviceObject
    from bacpypes3.local.networkport import NetworkPortObject

    device_object = DeviceObject(
        objectIdentifier=("device", _DEVICE_INSTANCE),
        objectName=_DEVICE_NAME,
        vendorName=_VENDOR_NAME,
        vendorIdentifier=_VENDOR_IDENTIFIER,
        modelName=_MODEL_NAME,
        firmwareRevision=_FIRMWARE_REVISION,
        applicationSoftwareVersion=_FIRMWARE_REVISION,
    )
    network_port_object = NetworkPortObject(
        f"{_INTERNAL_HOST}/32:{_INTERNAL_PORT}",
        objectIdentifier=("network-port", 1),
        objectName="NetworkPort-1",
        networkNumber=0,
        networkNumberQuality="unknown",
    )
    app = Application.from_object_list([device_object, network_port_object])
    _LOG.info(
        "internal bacpypes3 Application listening on %s:%d "
        "(vendor=%s model=%s firmware=%s)",
        _INTERNAL_HOST,
        _INTERNAL_PORT,
        _VENDOR_NAME,
        _MODEL_NAME,
        _FIRMWARE_REVISION,
    )
    # Application binds its own UDP socket on construction; keep the task
    # alive for the lifetime of the container.
    try:
        await asyncio.Event().wait()
    finally:
        app.close()


async def _run_gatekeeper() -> None:
    loop = asyncio.get_event_loop()
    transport, _protocol = await loop.create_datagram_endpoint(
        _GatekeeperProtocol, local_addr=(_PUBLIC_HOST, _PUBLIC_PORT)
    )
    _LOG.info("fragile gatekeeper listening on %s:%d/udp", _PUBLIC_HOST, _PUBLIC_PORT)
    try:
        await asyncio.Event().wait()
    finally:
        transport.close()


async def main() -> None:
    await asyncio.gather(_run_internal_bacpypes3_application(), _run_gatekeeper())


if __name__ == "__main__":
    asyncio.run(main())
