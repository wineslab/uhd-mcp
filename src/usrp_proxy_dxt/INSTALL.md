# USRP MCP Proxy DXT - Installation Guide

## Quick Start

### 1. Install the DXT CLI Tool (if not already installed)
```bash
npm install -g @anthropic-ai/dxt
```

### 2. Build the Extension
From the project root:
```bash
cd src/usrp_proxy_dxt
chmod +x dev-setup.sh
./dev-setup.sh
```

### 3. Package the Extension
```bash
dxt pack .
```
This creates a `.dxt` file that can be installed in Claude Desktop.

### 4. Install in Claude Desktop
- Open Claude Desktop
- Go to Settings → Extensions
- Click "Install Extension"
- Select the generated `.dxt` file
- Configure the USRP server URL when prompted

## Manual Development Setup

### Prerequisites
- Node.js >= 16.0.0
- npm (included with Node.js)
- Access to a remote USRP MCP server

### Installation Steps

1. **Navigate to the extension directory:**
   ```bash
   cd src/usrp_proxy_dxt
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Test the extension locally:**
   ```bash
   # Basic test
   node server/index.js
   
   # With debug mode
   DEBUG_MODE=true node server/index.js
   
   # With custom server URL
   USRP_SERVER_URL="https://your-server.com/mcp/" node server/index.js
   ```

4. **Run comprehensive tests:**
   ```bash
   node test.js
   ```

## Configuration

When installing the extension in Claude Desktop, you'll be prompted to configure:

### Required Settings
- **USRP Server URL**: The full URL to your USRP MCP server endpoint
  - Example: `https://your-server.com/mcp/`
  - Default: `https://uhd-mcp-route-mcp-services.apps.tenoran.automation.otic.open6g.net/mcp/`

### Optional Settings
- **Request Timeout**: Maximum time to wait for server responses (10-300 seconds)
  - Default: 60 seconds
- **Debug Mode**: Enable verbose logging for troubleshooting
  - Default: false

## Testing the Extension

### Local Testing
```bash
# Run the development setup script
./dev-setup.sh

# Run comprehensive tests
node test.js
```

### Claude Desktop Testing
1. Install the extension in Claude Desktop
2. Start a conversation
3. Try using USRP-related commands:
   - "Find USRP devices"
   - "Get UHD configuration info"
   - "Generate a signal at 2.4 GHz"

## Directory Structure

```
usrp_proxy_dxt/
├── manifest.json          # DXT extension manifest
├── package.json           # Node.js package configuration
├── README.md              # Extension documentation
├── INSTALL.md             # This installation guide
├── dev-setup.sh           # Development setup script
├── test.js                # Comprehensive test suite
├── server/
│   └── index.js           # Main MCP proxy server
└── node_modules/          # Dependencies (after npm install)
```

## Troubleshooting

### Common Issues

**1. "Module not found" errors**
```bash
cd src/usrp_proxy_dxt
npm install
```

**2. "Permission denied" when running scripts**
```bash
chmod +x dev-setup.sh
chmod +x test.js
```

**3. "Request timeout" errors**
- Check network connectivity to the USRP server
- Increase the request timeout in configuration
- Enable debug mode to see detailed logs

**4. "Invalid manifest" error**
```bash
# Validate manifest syntax
node -e "console.log(JSON.parse(require('fs').readFileSync('manifest.json', 'utf8')))"
```

### Debug Logging

Enable debug mode for detailed logs:
```bash
DEBUG_MODE=true node server/index.js
```

In Claude Desktop, enable debug mode through the extension configuration.

### Network Issues

Test server connectivity:
```bash
curl -X POST https://your-server.com/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}'
```

## Production Deployment

### For End Users
1. Package the extension: `dxt pack .`
2. Distribute the `.dxt` file
3. Provide installation instructions for Claude Desktop

### For Developers
1. Set up proper error handling for production environments
2. Configure appropriate timeout values
3. Ensure server URLs use HTTPS
4. Test with various network conditions

## Support

- Check the main project repository for issues
- Enable debug logging for detailed error information
- Test connectivity to the remote server
- Verify Claude Desktop version compatibility
