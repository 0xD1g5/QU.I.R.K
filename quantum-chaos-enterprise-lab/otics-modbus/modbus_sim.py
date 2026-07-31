"""Fragile Modbus/TCP simulator — chaos-lab `otics` profile (Phase 141, OTICS-04).

Simulates a Schneider Electric M221 PLC answering FC 43/14 Read Device
Identification (Basic category) on the real standard Modbus/TCP port (502).

Behaviorally enforces fragility per 141-CONTEXT.md D-10 so
`expected_results_otics.md` can assert that the scanner's D-05 one-strike
circuit-breaker / OTICS-03 single-in-flight guarantee is what keeps this
simulator "healthy" — not just documented as a rule:

  - Single in-flight connection only. A second concurrent TCP connection
    while one is already being served is immediately reset (closed with no
    response) rather than queued or accepted.
  - Malformed-input reset. Any inbound byte stream that does not look like a
    well-formed Modbus/TCP MBAP header (protocol identifier != 0x0000, or an
    implausible length field) is reset immediately instead of forwarded.

Architecture: a lightweight asyncio "gatekeeper" listens on the real
0.0.0.0:502 and enforces the two fragility rules above, splicing
well-formed traffic through to a real `pymodbus` TCP server bound to an
internal-only loopback port. The actual Modbus/TCP protocol framing,
FC 43/14 decode/encode, and device-identification response are all handled
by `pymodbus` itself (never hand-rolled) — only the fragility policy at the
raw-socket admission layer is custom.
"""
from __future__ import annotations

import asyncio
import logging
import warnings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
_LOG = logging.getLogger("otics-modbus-sim")

# Suppress pymodbus 3.x deprecation warnings for the legacy datastore/context
# API — the exact pin (<4) this container uses still ships it fully
# functional; the replacement SimData/SimDevice API is a v4 migration
# concern, not relevant to a pinned-below-4 chaos-lab simulator.
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pymodbus")

_PUBLIC_HOST = "0.0.0.0"
_PUBLIC_PORT = 502
_INTERNAL_HOST = "127.0.0.1"
_INTERNAL_PORT = 15020

# Simulated device identity — Schneider Electric M221 PLC (D-11 discretion).
# Maps directly onto pymodbus's Basic-category Read Device Identification
# object IDs that quirk/scanner/modbus_scanner.py reads back:
#   object 0 (VendorName)        -> modbus_vendor
#   object 1 (ProductCode)       -> modbus_model
#   object 2 (MajorMinorRevision)-> modbus_firmware
_DEVICE_IDENTITY = {
    "VendorName": "Schneider Electric",
    "ProductCode": "M221",
    "MajorMinorRevision": "1.6.2.0",
}

# One connection in flight at a time (D-10 single-in-flight fragility).
_busy = False


async def _run_internal_pymodbus_server() -> None:
    """Start the real pymodbus TCP server on an internal-only loopback port."""
    from pymodbus.datastore import (
        ModbusDeviceContext,
        ModbusSequentialDataBlock,
        ModbusServerContext,
    )
    from pymodbus.pdu.device import ModbusDeviceIdentification
    from pymodbus.server import ModbusTcpServer

    block = ModbusSequentialDataBlock(1, [0] * 100)
    device_ctx = ModbusDeviceContext(di=block, co=block, hr=block, ir=block)
    context = ModbusServerContext(devices=device_ctx, single=True)
    identity = ModbusDeviceIdentification(info_name=_DEVICE_IDENTITY)

    server = ModbusTcpServer(
        context, identity=identity, address=(_INTERNAL_HOST, _INTERNAL_PORT)
    )
    _LOG.info(
        "internal pymodbus server listening on %s:%d (vendor=%s model=%s firmware=%s)",
        _INTERNAL_HOST,
        _INTERNAL_PORT,
        _DEVICE_IDENTITY["VendorName"],
        _DEVICE_IDENTITY["ProductCode"],
        _DEVICE_IDENTITY["MajorMinorRevision"],
    )
    await server.serve_forever()


def _looks_like_valid_mbap(head: bytes) -> bool:
    """Sanity-check the first bytes of a Modbus/TCP MBAP header.

    MBAP header layout: transaction_id(2) + protocol_id(2) + length(2) +
    unit_id(1) = 7 bytes. protocol_id MUST be 0x0000 for Modbus. length is
    unit_id + PDU length and must be in [2, 253] for any real request.
    Anything else is treated as malformed input (D-10 reset-on-malformed).
    """
    if len(head) < 7:
        return False
    protocol_id = int.from_bytes(head[2:4], "big")
    length = int.from_bytes(head[4:6], "big")
    return protocol_id == 0x0000 and 2 <= length <= 253


async def _splice(
    reader_a: asyncio.StreamReader,
    writer_b: asyncio.StreamWriter,
) -> None:
    try:
        while True:
            chunk = await reader_a.read(4096)
            if not chunk:
                break
            writer_b.write(chunk)
            await writer_b.drain()
    except (ConnectionResetError, OSError):
        pass
    finally:
        try:
            writer_b.close()
        except Exception:
            pass


async def _handle_gatekeeper_connection(
    client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter
) -> None:
    global _busy
    peer = client_writer.get_extra_info("peername")

    if _busy:
        # D-10: a second concurrent connection is reset immediately — the
        # simulator never queues or serves more than one in-flight probe.
        _LOG.warning("rejecting concurrent connection from %s (single-in-flight)", peer)
        client_writer.close()
        try:
            await client_writer.wait_closed()
        except Exception:
            pass
        return

    _busy = True
    _LOG.info("accepted connection from %s", peer)
    internal_writer = None
    try:
        # Peek the first chunk before committing to forward anything, so a
        # malformed opening frame never reaches the internal pymodbus server.
        try:
            head = await asyncio.wait_for(client_reader.read(4096), timeout=5)
        except asyncio.TimeoutError:
            _LOG.warning("no data from %s within timeout — resetting", peer)
            return

        if not head:
            return

        if not _looks_like_valid_mbap(head):
            _LOG.warning("malformed MBAP header from %s — resetting connection", peer)
            return

        internal_reader, internal_writer = await asyncio.open_connection(
            _INTERNAL_HOST, _INTERNAL_PORT
        )
        internal_writer.write(head)
        await internal_writer.drain()

        await asyncio.gather(
            _splice(client_reader, internal_writer),
            _splice(internal_reader, client_writer),
        )
    except (ConnectionResetError, OSError) as exc:
        _LOG.debug("connection from %s ended abnormally: %s", peer, exc)
    finally:
        _busy = False
        try:
            client_writer.close()
        except Exception:
            pass
        if internal_writer is not None:
            try:
                internal_writer.close()
            except Exception:
                pass
        _LOG.info("connection from %s closed", peer)


async def _run_gatekeeper() -> None:
    server = await asyncio.start_server(
        _handle_gatekeeper_connection, _PUBLIC_HOST, _PUBLIC_PORT
    )
    _LOG.info("fragile gatekeeper listening on %s:%d", _PUBLIC_HOST, _PUBLIC_PORT)
    async with server:
        await server.serve_forever()


async def main() -> None:
    await asyncio.gather(_run_internal_pymodbus_server(), _run_gatekeeper())


if __name__ == "__main__":
    asyncio.run(main())
