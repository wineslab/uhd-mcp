#!/bin/bash
# Script to run the USRP MCP client test
# Usage: ./run_test.sh

set -e  # Exit on any error

echo "Running USRP MCP client test..."
echo "================================"

# Check if hatch is available
if ! command -v hatch &> /dev/null; then
    echo "Error: hatch is not installed or not in PATH"
    echo "Please install hatch first: pip install hatch"
    exit 1
fi

# Run the test using hatch
hatch run python test_usrp_client.py "$@"

echo "Test completed."
