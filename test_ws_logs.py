import asyncio
import websockets
import json

async def test_logs():
    uri = "ws://localhost:8000/api/ws/logs"
    headers = {"Origin": "http://localhost:3000"}
    try:
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            print(f"Connected to {uri}")
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                print(f"Received Log: [{data.get('level')}] {data.get('message')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_logs())
