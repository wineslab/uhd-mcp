#!/bin/bash

echo "🚀 USRP Quick Start (Hatch Environment)"
echo "============================================="

# Step 1: Update repository if PAT_TOKEN is provided
if [ -n "$PAT_TOKEN" ]; then
    echo "🔄 Updating repository with latest changes..."
    ./update-repo.sh
    if [ $? -ne 0 ]; then
        echo "❌ Repository update failed, but continuing with startup..."
        echo "   Check PAT_TOKEN and network connectivity"
    fi
    echo
else
    echo "⚠️  PAT_TOKEN not provided, skipping repository update"
    echo
fi

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
    if echo "$UHD_OUTPUT" | grep -q "Device Address"; then
        echo "✅ USRP detected!"
    else
        echo "⚠️  No USRP found. Starting server anyway (hardware may be connected later)."
    fi
else
    echo "⚠️  UHD tools not found, skipping hardware check."
fi

# Start the server using Hatch
echo "Starting USRP MCP Server on HTTP 0.0.0.0:8080/mcp..."
echo "Press Ctrl+C to stop the server"
$HATCH_CMD run python -m uhd_mcp --port 8080
