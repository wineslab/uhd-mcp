#!/bin/bash

# USRP MCP Proxy DXT - Development & Testing Script

set -e

echo "🚀 USRP MCP Proxy Desktop Extension - Development Setup"
echo "========================================================"

# Check Node.js version
echo "📋 Checking Node.js version..."
node_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$node_version" -lt "16" ]; then
    echo "❌ Node.js version 16 or higher is required. Current: $(node --version)"
    exit 1
fi
echo "✅ Node.js version: $(node --version)"

# Install dependencies
echo "📦 Installing dependencies..."
npm install --cache=/tmp/.npm

# Validate manifest
echo "🔍 Validating manifest.json..."
if ! node -e "JSON.parse(require('fs').readFileSync('manifest.json', 'utf8'))" > /dev/null 2>&1; then
    echo "❌ Invalid manifest.json"
    exit 1
fi
echo "✅ Manifest is valid"

# Test server startup
echo "🧪 Testing server startup..."
if timeout 3 node server/index.js 2>&1 | grep -q "USRP Proxy MCP server started successfully"; then
    echo "✅ Server starts successfully"
else
    echo "❌ Server failed to start"
    exit 1
fi

echo ""
echo "🎉 Development setup complete!"
echo ""
echo "Available commands:"
echo "  npm start        - Start the proxy server"
echo "  npm test         - Run test suite (if you add tests)"
echo "  node test.js     - Run comprehensive MCP tests"
echo ""
echo "Configuration:"
echo "  Set USRP_SERVER_URL environment variable to your server URL"
echo "  Set DEBUG_MODE=true for verbose logging"
echo "  Set REQUEST_TIMEOUT for custom timeout (seconds)"
echo ""
echo "Example usage:"
echo "  USRP_SERVER_URL='https://your-server.com/mcp/' DEBUG_MODE=true node server/index.js"
