# setup_usrp.sh - Setup script for USRP B210 with Hatch
#!/bin/bash

echo "Setting up USRP B210 FastMCP Server with Hatch..."

# Check if Hatch is installed
echo "Checking Hatch installation..."
if ! command -v hatch &> /dev/null; then
    echo "❌ Hatch not found. Installing Hatch..."
    if command -v pipx &> /dev/null; then
        pipx install hatch
    else
        echo "Installing pipx first..."
        python3 -m pip install --user pipx
        python3 -m pipx ensurepath
        export PATH="$HOME/.local/bin:$PATH"
        pipx install hatch
    fi
    
    # Source bashrc to update PATH
    if [ -f ~/.bashrc ]; then
        source ~/.bashrc
    fi
fi

if command -v hatch &> /dev/null; then
    echo "✓ Hatch found"
    hatch --version
else
    echo "❌ Failed to install Hatch. Please install manually: pip install hatch"
    exit 1
fi

# Test UHD installation
echo "Testing UHD installation..."
if command -v uhd_find_devices &> /dev/null; then
    echo "✓ UHD tools found"
    uhd_find_devices
else
    echo "❌ UHD tools not found. Please install UHD first."
    echo "On Ubuntu/Debian: sudo apt install uhd-host"
    echo "On other systems, see: https://files.ettus.com/manual/"
    exit 1
fi

# Initialize Hatch environment and install dependencies
echo "Setting up Hatch environment..."
hatch env create

# Get the Hatch Python executable path
HATCH_PYTHON=$(hatch env find)
if [ -z "$HATCH_PYTHON" ]; then
    echo "❌ Failed to locate Hatch environment"
    exit 1
fi

# Get the actual Python executable in the environment
PYTHON_EXEC=$(hatch run python -c "import sys; print(sys.executable)")
echo "✓ Using Python: $PYTHON_EXEC"

# Create systemd service
echo "Creating systemd service..."
sudo tee /etc/systemd/system/usrp-mcp.service > /dev/null << EOF
[Unit]
Description=USRP B210 MCP Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PWD
ExecStart=hatch run python usrp_mcp_server.py --tcp 8080
Restart=always
RestartSec=10
Environment=PATH=/usr/bin:/usr/local/bin

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Setup complete!"
echo "To start the server: hatch run python usrp_mcp_server.py --tcp 8080"
echo "To run in shell mode: hatch shell"
echo "To enable as service: sudo systemctl enable usrp-mcp && sudo systemctl start usrp-mcp"

# test_usrp_client.py - Test client for USRP server (run with Hatch)
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

# example_commands.md - Example usage with Hatch
# USRP B210 MCP Server - Example Commands

## Starting the Server
```bash
# Start with Hatch (recommended)
hatch run python usrp_mcp_server.py --tcp 8080

# Or enter Hatch shell first
hatch shell
python usrp_mcp_server.py --tcp 8080
```

## Running Tests
```bash
# Run test client
hatch run python test_usrp_client.py

# Run with custom host/port
hatch run python test_usrp_client.py 192.168.1.100 8080
```

## Basic Device Discovery
- **uhd_find_devices()** - Find connected USRP devices
- **uhd_usrp_probe()** - Get detailed device information
- **get_uhd_info()** - Get UHD version and config

## Signal Generation Examples

### Generate 2.4 GHz sine wave for 10 seconds
uhd_siggen(freq=2.4e9, duration=10, wave_type="SINE", wave_freq=1000, gain=15)

### Generate continuous FM signal at 100 MHz
uhd_siggen(freq=100e6, wave_type="SINE", wave_freq=1000, gain=10)

### Generate square wave at 900 MHz
uhd_siggen(freq=900e6, wave_type="SQUARE", wave_freq=500, gain=12, duration=30)

## Signal Capture Examples

### Capture 5 seconds at 2.4 GHz
uhd_rx_samples_to_file(freq=2.4e9, duration=5, gain=20, filename="capture_2400.dat")

### High-rate capture at 900 MHz
uhd_rx_samples_to_file(freq=900e6, rate=5e6, duration=2, gain=15, filename="fast_capture.dat")

## Process Management
- **list_processes()** - Show running signal generators
- **stop_process("process_id")** - Stop specific process
- **cleanup_all_processes()** - Stop all running processes

## Safety Notes
- Always use appropriate gain levels (typically 0-30 dB)
- Be mindful of local RF regulations
- Use short durations for testing
- The server includes safety limits for gain and commands

# quick_start.sh - Quick start script with Hatch
#!/bin/bash

echo "🚀 USRP B210 Quick Start (Hatch Environment)"
echo "============================================="

# Check if Hatch is available
if ! command -v hatch &> /dev/null; then
    echo "❌ Hatch not found. Please run setup script first."
    exit 1
fi

# Check if USRP is connected
echo "Checking for USRP devices..."
if uhd_find_devices | grep -q "type: b200"; then
    echo "✓ USRP B210 detected!"
else
    echo "❌ No USRP B210 found. Check USB connection."
    exit 1
fi

# Start the server using Hatch
echo "Starting USRP MCP Server on port 8080 using Hatch..."
hatch run python usrp_mcp_server.py --tcp 8080

# claude_config.json - Example Claude Desktop config with Hatch
{
  "mcpServers": {
    "usrp-b210": {
      "command": "ssh",
      "args": [
        "username@your-laptop-ip",
        "cd /home/username/uhd-mcp && hatch run python usrp_mcp_server.py"
      ]
    }
  }
}

# hatch_commands.md - Hatch Development Commands
# USRP B210 MCP Server - Hatch Development Guide

## Environment Management
```bash
# Create/recreate environment
hatch env create

# Remove environment
hatch env remove

# Show environment info
hatch env show

# List all environments
hatch env show --all

# Find environment path
hatch env find
```

## Running the Server
```bash
# Run server directly
hatch run python usrp_mcp_server.py --tcp 8080

# Run with environment variables
hatch run --env PYTHONPATH=/custom/path python usrp_mcp_server.py

# Enter shell for interactive development
hatch shell
```

## Development Commands
```bash
# Install development dependencies (if configured in pyproject.toml)
hatch env create dev

# Run tests (if configured)
hatch run test

# Run linting (if configured)
hatch run lint

# Format code (if configured)
hatch run format
```

## Dependency Management
```bash
# Add runtime dependency
hatch dep add fastmcp

# Add development dependency
hatch dep add --dev pytest

# Show dependencies
hatch dep show
```

## Building and Publishing
```bash
# Build the project
hatch build

# Clean build artifacts
hatch clean

# Publish to PyPI (if configured)
hatch publish
```

## Troubleshooting
```bash
# Check environment status
hatch env show

# Recreate environment if corrupted
hatch env remove && hatch env create

# Check Python executable being used
hatch run python -c "import sys; print(sys.executable)"

# Debug environment variables
hatch run python -c "import os; print(dict(os.environ))"
```
