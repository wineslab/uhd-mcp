# setup_usrp.sh - Setup script for USRP with Hatch
#!/bin/bash
set -x

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

# Set up SUDO variable based on environment for systemd service creation
if [ "$(id -u)" -eq 0 ]; then
    SUDO=""
elif command -v sudo &> /dev/null; then
    SUDO="sudo"
else
    SUDO=""
    echo "⚠️  Warning: Not running as root and sudo not available. Systemd service creation may fail."
fi

# Create systemd service for production deployment
echo "Creating systemd service..."

$SUDO tee /etc/systemd/system/usrp-mcp.service > /dev/null << EOF
[Unit]
Description=USRP MCP Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PWD
ExecStart=$HATCH_SERVICE_CMD run python usrp_mcp_server.py --tcp --port 8080
Restart=always
RestartSec=10
Environment=PATH=/usr/bin:/usr/local/bin

[Install]
WantedBy=multi-user.target
EOF

if [ $? -eq 0 ]; then
    echo "✅ Systemd service created successfully"
else
    echo "⚠️  Failed to create systemd service (insufficient permissions)"
fi

echo "✅ Setup complete!"
echo "Usage examples:"
echo "  hatch run python usrp_mcp_server.py --tcp --port 8080"
echo "  hatch run python usrp_mcp_server.py --tcp --host 192.168.1.10 --port 9090"
echo "  hatch run python usrp_mcp_server.py --help"
echo "To run in shell mode: hatch shell"
echo "To start interactively: ./start.sh"

# Only show systemd instructions if we successfully created the service
if [ -f "/etc/systemd/system/usrp-mcp.service" ]; then
    echo "To enable as service: ${SUDO} systemctl enable usrp-mcp && ${SUDO} systemctl start usrp-mcp"
fi

