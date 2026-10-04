import asyncio
import sys
import websockets

# Sets to keep track of connected clients
tcp_clients = set()
ws_clients = set()

def extract_packets(buffer: str):
    """Unpacks complete ~...# packets and returns (extracted_packets, remaining_buffer)."""
    packets = []
    while True:
        start = buffer.find('~')
        if start == -1:
            # No start delimiter, flush noise
            buffer = ""
            break

        end = buffer.find('#', start)
        if end == -1:
            # Check if a second '~' arrived before '#', indicating a dropped fragment
            next_start = buffer.find('~', start + 1)
            if next_start != -1:
                buffer = buffer[next_start:]
                continue
            # Incomplete packet, wait for next chunk
            buffer = buffer[start:]
            break

        packet = buffer[start:end + 1]
        packets.append(packet)
        buffer = buffer[end + 1:]

    return packets, buffer


async def handle_tcp(reader, writer):
    """Handles incoming TCP connections from the Android App or test driver."""
    client_addr = writer.get_extra_info('peername')
    print(f"[TCP] Client connected from {client_addr}")
    tcp_clients.add(writer)
    tcp_buffer = ""

    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break

            tcp_buffer += data.decode('ascii', errors='ignore')
            packets, tcp_buffer = extract_packets(tcp_buffer)

            for packet in packets:
                print(f"[APP -> SIM] {packet}")
                # Forward each discrete packet to all connected Izis simulators
                for ws in list(ws_clients):
                    try:
                        await ws.send(packet)
                    except websockets.exceptions.ConnectionClosed:
                        pass
    except Exception as e:
        print(f"[TCP] Error with {client_addr}: {e}")
    finally:
        print(f"[TCP] Client disconnected from {client_addr}")
        tcp_clients.discard(writer)
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def handle_ws(websocket, *args):
    """Handles incoming WebSocket connections from the Izis Simulator.

    Compatible with both websockets <10 (with 'path' argument) and >=10.
    """
    remote = getattr(websocket, 'remote_address', 'Izis Simulator')
    print(f"[WS] Izis Simulator connected from {remote}")
    ws_clients.add(websocket)

    try:
        async for message in websocket:
            clean_msg = message.strip()
            print(f"[SIM -> APP] {clean_msg}")

            # Forward hardware events/responses to all active TCP clients
            data = clean_msg.encode('ascii')
            for writer in list(tcp_clients):
                try:
                    writer.write(data)
                    await writer.drain()
                except Exception:
                    tcp_clients.discard(writer)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        print(f"[WS] Izis Simulator disconnected from {remote}")
        ws_clients.discard(websocket)


async def main():
    print("Starting Izis Simulator Bridge Server...")

    # Start the TCP server for App (Port 5000)
    tcp_server = await asyncio.start_server(handle_tcp, '0.0.0.0', 5000)
    print("TCP Server listening on 0.0.0.0:5000 (For App)")

    # Start WebSocket server for Izis Simulator (Port 8080)
    async with websockets.serve(handle_ws, '127.0.0.1', 8080):
        print(
            "WebSocket Server listening on 127.0.0.1:8080 (For Izis Simulator)"
        )
        print("Ready for connections. Press Ctrl+C to stop.\n")
        try:
            await tcp_server.serve_forever()
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nIzis Simulator Bridge Server stopped.")
        sys.exit(0)