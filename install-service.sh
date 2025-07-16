#!/bin/bash

echo "🔧 Installing USRP MCP Server as systemd service"
echo "================================================"

# Check if running as root or if sudo is available
if [ "$(id -u)" -eq 0 ]; then
    SUDO=""
    echo "✅ Running as root"
elif command -v sudo &> /dev/null; then
    SUDO="sudo"
    echo "✅ Using sudo for installation"
else
    echo "❌ Error: This script requires root access or sudo"
    echo "   Please run as root or install sudo first"
    exit 1
fi

# Check if hatch is available
if ! command -v hatch &> /dev/null; then
    echo "❌ Error: Hatch not found. Please run ./setup.sh first"
    exit 1
fi

# Get the current working directory for the service
WORK_DIR="$(pwd)"
HATCH_PATH="$(which hatch)"

echo "Creating systemd service..."

$SUDO tee /etc/systemd/system/usrp-mcp.service > /dev/null << EOF
[Unit]
Description=USRP MCP Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$WORK_DIR
ExecStart=$HATCH_PATH run python -m uhd_mcp.usrp_mcp_server --tcp --port 8080
Restart=always
RestartSec=10
Environment=PATH=/usr/bin:/usr/local/bin:$HOME/.local/bin

[Install]
WantedBy=multi-user.target
EOF

if [ $? -eq 0 ]; then
    echo "✅ Systemd service created successfully"
    
    # Reload systemd and enable the service
    echo "Enabling and starting service..."
    $SUDO systemctl daemon-reload
    $SUDO systemctl enable usrp-mcp
    
    echo "✅ Service installed and enabled"
    echo ""
    echo "Service management commands:"
    echo "  Start:   ${SUDO} systemctl start usrp-mcp"
    echo "  Stop:    ${SUDO} systemctl stop usrp-mcp"
    echo "  Status:  ${SUDO} systemctl status usrp-mcp"
    echo "  Logs:    ${SUDO} journalctl -u usrp-mcp -f"
    echo ""
    echo "To start the service now: ${SUDO} systemctl start usrp-mcp"
else
    echo "❌ Failed to create systemd service"
    exit 1
fi
