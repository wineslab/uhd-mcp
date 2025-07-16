# setup_usrp.sh - Setup script for USRP with Hatch
#!/bin/bash
# set -x

echo "Setting up USRP FastMCP Server with Hatch..."

# Check if Hatch is installed
echo "Checking Hatch installation..."

# Ensure pipx path is set up permanently
pipx ensurepath

# Install Hatch if not available
if ! command -v hatch &> /dev/null; then
    echo "❌ Hatch not found. Installing Hatch..."
    pipx install hatch
fi

echo "✅ Hatch found at: $(which hatch)"
HATCH_SERVICE_CMD="hatch"

# Test UHD installation
echo "Testing UHD installation..."
if command -v uhd_find_devices &> /dev/null; then
    echo "✅ UHD tools found"
else
    echo "❌ UHD tools not found. Please install UHD first."
    exit 1
fi

echo "✅ Setup complete!"
echo "Usage examples:"
echo "  hatch run python -m uhd_mcp.usrp_mcp_server                    # Default HTTP on 127.0.0.1:8080"
echo "  hatch run python -m uhd_mcp.usrp_mcp_server --port 9090        # HTTP on port 9090"
echo "  hatch run python -m uhd_mcp.usrp_mcp_server --host 0.0.0.0     # HTTP on all interfaces"
echo "  hatch run python -m uhd_mcp.usrp_mcp_server --help             # Show all options"
echo "  hatch run usrp-mcp-server --port 8080                          # Using console script"
echo "To run in shell mode: hatch shell"
echo "To start interactively: ./start.sh"
echo "To install as system service: ./install-service.sh"

