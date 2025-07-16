#!/usr/bin/env python3
"""Test client for USRP MCP server - Use: hatch run python test_usrp_client.py"""

import asyncio
import json
import sys
import time

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
        print(f"  Server capabilities: {response.get('result', {}).get('capabilities', {})}")
        
        # List available tools
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        response = await send_request(reader, writer, tools_request)
        tools = response.get("result", {}).get("tools", [])
        print(f"✓ Available tools: {[tool['name'] for tool in tools]}")
        
        # Get UHD info
        uhd_info_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_uhd_info",
                "arguments": {}
            }
        }
        
        response = await send_request(reader, writer, uhd_info_request)
        uhd_info = response.get("result", {}).get("content", [{}])[0].get("text", "")
        print("✓ UHD Info:")
        print(uhd_info)
        
        # Find devices
        find_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "uhd_find_devices",
                "arguments": {}
            }
        }
        
        response = await send_request(reader, writer, find_request)
        devices_result = response.get("result", {}).get("content", [{}])[0].get("text", "")
        print("✓ Device search completed:")
        print(devices_result)
        
        # Test device probe (if devices found)
        probe_request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "uhd_usrp_probe",
                "arguments": {
                    "args": "--tree"
                }
            }
        }
        
        response = await send_request(reader, writer, probe_request)
        probe_result = response.get("result", {}).get("content", [{}])[0].get("text", "")
        print("✓ Device probe completed:")
        print(probe_result[:500] + "..." if len(probe_result) > 500 else probe_result)
        
        # Test signal generation (short duration)
        print("\n🔧 Testing signal generation (2.4 GHz, 5 seconds)...")
        siggen_request = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "uhd_siggen",
                "arguments": {
                    "freq": 2.4e9,
                    "rate": 1e6,
                    "gain": 10,
                    "duration": 5.0,
                    "wave_type": "SINE",
                    "wave_freq": 1000,
                    "amplitude": 0.3
                }
            }
        }
        
        response = await send_request(reader, writer, siggen_request)
        siggen_result = response.get("result", {}).get("content", [{}])[0].get("text", "")
        print("✓ Signal generation test:")
        print(siggen_result)
        
        # Test background signal generation
        print("\n🔧 Testing background signal generation...")
        bg_siggen_request = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "uhd_siggen",
                "arguments": {
                    "freq": 2.45e9,
                    "rate": 1e6,
                    "gain": 5,
                    "wave_type": "SINE",
                    "wave_freq": 1000,
                    "amplitude": 0.2
                }
            }
        }
        
        response = await send_request(reader, writer, bg_siggen_request)
        bg_result = response.get("result", {}).get("content", [{}])[0].get("text", "")
        print("✓ Background signal generation started:")
        print(bg_result)
        
        # List running processes
        print("\n🔧 Checking running processes...")
        list_request = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "list_processes",
                "arguments": {}
            }
        }
        
        response = await send_request(reader, writer, list_request)
        processes_result = response.get("result", {}).get("content", [{}])[0].get("text", "")
        print("✓ Running processes:")
        print(processes_result)
        
        # Wait a bit then stop all processes
        print("\n⏳ Waiting 3 seconds...")
        await asyncio.sleep(3)
        
        cleanup_request = {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "cleanup_all_processes",
                "arguments": {}
            }
        }
        
        response = await send_request(reader, writer, cleanup_request)
        cleanup_result = response.get("result", {}).get("content", [{}])[0].get("text", "")
        print("✓ Cleanup completed:")
        print(cleanup_result)
        
        # Test RX capture (small file)
        print("\n🔧 Testing RX sample capture...")
        rx_request = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "uhd_rx_samples_to_file",
                "arguments": {
                    "freq": 2.4e9,
                    "rate": 1e6,
                    "gain": 10,
                    "duration": 1.0,
                    "filename": "test_samples.dat"
                }
            }
        }
        
        response = await send_request(reader, writer, rx_request)
        rx_result = response.get("result", {}).get("content", [{}])[0].get("text", "")
        print("✓ RX sample capture test:")
        print(rx_result)
        
        writer.close()
        await writer.wait_closed()
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    asyncio.run(test_usrp_server(host, port))
