#!/bin/bash

echo "🚀 USRP B210 Quick Start (Hatch Environment)"
echo "============================================="

# Ensure PATH includes pipx/hatch directories
export PATH="$HOME/.local/bin:/root/.local/bin:$PATH"

# Determine which hatch command to use
HATCH_CMD="hatch"
if ! command -v hatch &> /dev/null && [ -f "/root/.local/bin/hatch" ]; then
    HATCH_CMD="/root/.local/bin/hatch"
fi

# Check if Hatch is available
if ! command -v $HATCH_CMD &> /dev/null; then
    echo "❌ Hatch not found. Please run setup.sh first."
    exit 1
fi

# Ensure Hatch environment is created and dependencies are installed
echo "Setting up Hatch environment and installing dependencies..."
$HATCH_CMD env create

# Verify the environment and dependencies
echo "Verifying Python environment..."
PYTHON_EXEC=$($HATCH_CMD run python -c "import sys; print(sys.executable)")
echo "✅ Using Python: $PYTHON_EXEC"

# Check if USRP is connected (optional check - may not have hardware in container)
echo "Checking for USRP devices..."
if command -v uhd_find_devices &> /dev/null; then
    UHD_OUTPUT=$(uhd_find_devices 2>/dev/null)
    if echo "$UHD_OUTPUT" | grep -q "type: b200"; then
        echo "✅ USRP B210 detected!"
    else
        echo "⚠️  No USRP B210 found. Starting server anyway (hardware may be connected later)."
    fi
else
    echo "⚠️  UHD tools not found, skipping hardware check."
fi

# Start the server using Hatch
echo "Starting USRP MCP Server on port 8080..."
echo "Press Ctrl+C to stop the server"
$HATCH_CMD run python usrp_mcp_server.py --tcp --port 8080
