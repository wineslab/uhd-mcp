#!/usr/bin/env python3
"""Test client for USRP MCP server - Use: hatch run python test_usrp_client.py"""

import asyncio
import json
import sys

async def send_request(reader, writer, request):
    """Send request and get response"""
    request_json = json.dumps(request) + '\n'
    writer.write(request_json.encode())
    await writer.drain()
    
    response_data = await reader.readline()
    return json.loads(response_data.decode().strip())

async def test_usrp_server(host='localhost', port=8080):
    """Test the USRP MCP server"""
    try:
        print(f"Connecting to USRP server at {host}:{port}...")
        reader, writer = await asyncio.open_connection(host, port)
        
        # Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "usrp-test", "version": "1.0.0"}
            }
        }
        
        response = await send_request(reader, writer, init_request)
        print("✓ Connected to USRP MCP Server")
        
        # Get UHD info
        uhd_info_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_uhd_info",
                "arguments": {}
            }
        }
        
        response = await send_request(reader, writer, uhd_info_request)
        print("✓ UHD Info:", response.get("result", {}).get("content", [{}])[0].get("text", ""))
        
        # Find devices
        find_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "uhd_find_devices",
                "arguments": {}
            }
        }
        
        response = await send_request(reader, writer, find_request)
        devices_result = response.get("result", {}).get("content", [{}])[0].get("text", "")
        print("✓ Device search completed")
        print(devices_result)
        
        # Test signal generation (short duration)
        print("\n🔧 Testing signal generation (2.4 GHz, 5 seconds)...")
        siggen_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "uhd_siggen",
                "arguments": {
                    "freq": 2.4e9,
                    "rate": 1e6,
                    "gain": 10,
                    "duration": 5.0,
                    "wave_type": "SINE",
                    "wave_freq": 1000
                }
            }
        }
        
        response = await send_request(reader, writer, siggen_request)
        siggen_result = response.get("result", {}).get("content", [{}])[0].get("text", "")
        print("✓ Signal generation test:")
        print(siggen_result)
        
        writer.close()
        await writer.wait_closed()
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    asyncio.run(test_usrp_server(host, port))
