import asyncio
import websockets

# Sets to keep track of connected clients
tcp_clients = set()
ws_clients = set()

async def handle_tcp(reader, writer):
    """Handles incoming TCP connections from the Android App."""
    client_addr = writer.get_extra_info('peername')
    print(f"[TCP] Android App connected from {client_addr}")
    tcp_clients.add(writer)
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            message = data.decode('ascii', errors='ignore')
            print(f"[APP -> SIM] {message.strip()}")
            
            # Forward the message to all connected WebSocket clients (HTML Simulator)
            for ws in list(ws_clients):
                try:
                    await ws.send(message)
                except websockets.exceptions.ConnectionClosed:
                    pass
    except Exception as e:
        print(f"[TCP] Error: {e}")
    finally:
        print(f"[TCP] Android App disconnected from {client_addr}")
        tcp_clients.remove(writer)
        writer.close()

async def handle_ws(websocket, path):
    """Handles incoming WebSocket connections from the HTML Simulator."""
    print(f"[WS] HTML Simulator connected from {websocket.remote_address}")
    ws_clients.add(websocket)
    try:
        async for message in websocket:
            print(f"[SIM -> APP] {message.strip()}")
            
            # Forward the message to all connected TCP clients (Android App)
            for writer in list(tcp_clients):
                try:
                    writer.write(message.encode('ascii'))
                    await writer.drain()
                except Exception:
                    pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        print(f"[WS] HTML Simulator disconnected from {websocket.remote_address}")
        ws_clients.remove(websocket)

async def main():
    print("Starting Izis Bridge Server...")
    # Start the TCP server for the Android App (Listens on port 5000)
    tcp_server = await asyncio.start_server(handle_tcp, '0.0.0.0', 5000)
    print("TCP Server listening on 0.0.0.0:5000 (For Android App)")
    
    # Start the WebSocket server for the HTML Simulator (Listens on port 8080)
    ws_server = websockets.serve(handle_ws, '127.0.0.1', 8080)
    print("WebSocket Server listening on 127.0.0.1:8080 (For HTML Simulator)")
    
    await asyncio.gather(tcp_server.serve_forever(), ws_server)

if __name__ == "__main__":
    asyncio.run(main())