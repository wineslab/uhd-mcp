#!/usr/bin/env python3
"""Test client for USRP MCP server - Use: hatch run python test_usrp_client.py"""

import asyncio
import json
import sys
import aiohttp

async def send_request(session, url, request):
    """Send HTTP request and get response"""
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
    }
    async with session.post(url, json=request, headers=headers) as response:
        if response.status != 200:
            print(f"HTTP Error {response.status}: {response.reason}")
            print(f"Response headers: {dict(response.headers)}")
            response_text = await response.text()
            print(f"Response body: {response_text}")
            raise Exception(f"HTTP {response.status}: {response.reason}")
        
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            return await response.json()
        elif 'text/event-stream' in content_type:
            # Handle Server-Sent Events
            response_text = await response.text()
            print(f"SSE Response: {response_text}")
            
            # Parse SSE format - look for data: lines
            lines = response_text.strip().split('\n')
            for line in lines:
                if line.startswith('data: '):
                    try:
                        return json.loads(line[6:])  # Remove 'data: ' prefix
                    except json.JSONDecodeError:
                        continue
            
            # If no valid JSON found, return the raw text
            return {"error": "No valid JSON in SSE response", "raw": response_text}
        else:
            response_text = await response.text()
            return {"error": f"Unexpected content type: {content_type}", "raw": response_text}

async def test_usrp_server(url='https://uhd-mcp.your-domain.example/mcp/'):
    """Test the USRP MCP server"""
    try:
        print(f"Connecting to USRP server at {url}...")
        
        session_id = None
        
        async with aiohttp.ClientSession() as session:
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
            
            # Send initial request and extract session ID
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/event-stream'
            }
            async with session.post(url, json=init_request, headers=headers) as response:
                session_id = response.headers.get('mcp-session-id')
                print(f"Got session ID: {session_id}")
                
                content_type = response.headers.get('Content-Type', '')
                if 'text/event-stream' in content_type:
                    response_text = await response.text()
                    lines = response_text.strip().split('\n')
                    for line in lines:
                        if line.startswith('data: '):
                            init_response = json.loads(line[6:])
                            break
                else:
                    init_response = await response.json()
            
            print("✓ Connected to USRP MCP Server")
            print(f"  Server response: {init_response}")
            print(f"  Server capabilities: {init_response.get('result', {}).get('capabilities', {})}")
            
            # Send initialized notification to complete the handshake
            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/event-stream',
                'mcp-session-id': session_id
            }
            async with session.post(url, json=initialized_notification, headers=headers) as response:
                if response.status == 200:
                    print("✓ Initialization handshake completed")
                else:
                    print(f"Warning: Initialized notification returned {response.status}")
            
            # Helper function for subsequent requests with session ID
            async def send_with_session(request_data):
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json, text/event-stream',
                    'mcp-session-id': session_id
                }
                async with session.post(url, json=request_data, headers=headers) as response:
                    if response.status != 200:
                        print(f"HTTP Error {response.status}: {response.reason}")
                        response_text = await response.text()
                        print(f"Response body: {response_text}")
                        raise Exception(f"HTTP {response.status}: {response.reason}")
                    
                    content_type = response.headers.get('Content-Type', '')
                    if 'text/event-stream' in content_type:
                        response_text = await response.text()
                        lines = response_text.strip().split('\n')
                        for line in lines:
                            if line.startswith('data: '):
                                return json.loads(line[6:])
                    else:
                        return await response.json()
            
            # List available tools
            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
            
            response = await send_with_session(tools_request)
            print(f"  Tools response: {response}")
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
            
            response = await send_with_session(uhd_info_request)
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
            
            response = await send_with_session(find_request)
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
            
            response = await send_with_session(probe_request)
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
                        "samp_rate": 1e6,
                        "gain": 10,
                        "duration": 5.0,
                        "waveform_type": "sine",
                        "waveform_freq": 1000,
                        "amplitude": 0.3
                    }
                }
            }
            
            response = await send_with_session(siggen_request)
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
                        "samp_rate": 1e6,
                        "gain": 5,
                        "waveform_type": "sine",
                        "waveform_freq": 1000,
                        "amplitude": 0.2
                    }
                }
            }
            
            response = await send_with_session(bg_siggen_request)
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
            
            response = await send_with_session(list_request)
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
            
            response = await send_with_session(cleanup_request)
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
            
            response = await send_with_session(rx_request)
            rx_result = response.get("result", {}).get("content", [{}])[0].get("text", "")
            print("✓ RX sample capture test:")
            print(rx_result)
            
            print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else 'https://uhd-mcp.your-domain.example/mcp/'
    asyncio.run(test_usrp_server(url))
