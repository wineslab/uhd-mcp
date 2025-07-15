# setup_usrp.sh - Setup script for USRP B210 with Hatch
#!/bin/bash
set -x

echo "Setting up USRP B210 FastMCP Server with Hatch..."

# Set up SUDO variable based on environment
if [ "$(id -u)" -eq 0 ]; then
    # Running as root, no sudo needed
    SUDO=""
elif command -v sudo &> /dev/null; then
    # Not root but sudo is available
    SUDO="sudo"
else
    # No sudo available and not root
    SUDO=""
    echo "⚠️  Warning: Not running as root and sudo not available. Some operations may fail."
fi

# Check if Hatch is installed
echo "Checking Hatch installation..."

# Ensure pipx path is set up and manually add to PATH
pipx ensurepath

# Manually add pipx bin directories to PATH (since we can't restart terminal in Docker)
export PATH="$HOME/.local/bin:/root/.local/bin:$PATH"

# Source shell configuration files if they exist to pick up any PATH changes
[ -f ~/.bashrc ] && source ~/.bashrc 2>/dev/null || true
[ -f ~/.profile ] && source ~/.profile 2>/dev/null || true

if ! command -v hatch &> /dev/null; then
    echo "❌ Hatch not found. Installing Hatch..."
    pipx install hatch
    
    # After installation, update PATH again and try to source shell configs
    export PATH="$HOME/.local/bin:/root/.local/bin:$PATH"
    [ -f ~/.bashrc ] && source ~/.bashrc 2>/dev/null || true
    [ -f ~/.profile ] && source ~/.profile 2>/dev/null || true
fi

# Verify hatch is available
if command -v hatch &> /dev/null; then
    echo "✅ Hatch found at: $(which hatch)"
    hatch --version
elif [ -f "/root/.local/bin/hatch" ]; then
    echo "✅ Hatch found at: /root/.local/bin/hatch"
    export PATH="/root/.local/bin:$PATH"
    /root/.local/bin/hatch --version
else
    echo "❌ Failed to install Hatch. Please install manually: pip install hatch"
    exit 1
fi

# Test UHD installation
echo "Testing UHD installation..."
if command -v uhd_find_devices &> /dev/null; then
    echo "✅ UHD tools found"
else
    echo "❌ UHD tools not found. Please install UHD first."
    exit 1
fi

# Initialize Hatch environment and install dependencies
echo "Setting up Hatch environment..."

# Use full path if hatch is not in PATH
HATCH_CMD="hatch"
if ! command -v hatch &> /dev/null && [ -f "/root/.local/bin/hatch" ]; then
    HATCH_CMD="/root/.local/bin/hatch"
fi

$HATCH_CMD env create

# Get the Hatch Python executable path
HATCH_PYTHON=$($HATCH_CMD env find)
if [ -z "$HATCH_PYTHON" ]; then
    echo "❌ Failed to locate Hatch environment"
    exit 1
fi

# Get the actual Python executable in the environment
PYTHON_EXEC=$($HATCH_CMD run python -c "import sys; print(sys.executable)")
echo "✅ Using Python: $PYTHON_EXEC"

# Create systemd service
echo "Creating systemd service..."

# Determine the correct hatch path for the service
HATCH_SERVICE_CMD="hatch"
if ! command -v hatch &> /dev/null && [ -f "/root/.local/bin/hatch" ]; then
    HATCH_SERVICE_CMD="/root/.local/bin/hatch"
fi

$SUDO tee /etc/systemd/system/usrp-mcp.service > /dev/null << EOF
[Unit]
Description=USRP B210 MCP Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PWD
ExecStart=$HATCH_SERVICE_CMD run python usrp_mcp_server.py --tcp --port 8080
Restart=always
RestartSec=10
Environment=PATH=/usr/bin:/usr/local/bin:/root/.local/bin

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
echo "  $HATCH_CMD run python usrp_mcp_server.py --tcp --port 8080"
echo "  $HATCH_CMD run python usrp_mcp_server.py --tcp --host 192.168.1.10 --port 9090"
echo "  $HATCH_CMD run python usrp_mcp_server.py --help"
echo "To run in shell mode: $HATCH_CMD shell"

# Only show systemd instructions if we successfully created the service
if [ -f "/etc/systemd/system/usrp-mcp.service" ]; then
    echo "To enable as service: ${SUDO} systemctl enable usrp-mcp && ${SUDO} systemctl start usrp-mcp"
fi
