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
