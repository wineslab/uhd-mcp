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
hatch run python usrp_mcp_server.py --tcp --port 8080
