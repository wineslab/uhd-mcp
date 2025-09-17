# USRP MCP Proxy Desktop Extension

## 📁 Project Structure

```
src/usrp_proxy_dxt/
├── manifest.json              # DXT extension manifest (DXT spec v0.1)
├── package.json               # Node.js package configuration
├── server/index.js            # Main MCP proxy server implementation
├── README.md                  # This comprehensive guide
├── INSTALL.md                 # Detailed installation instructions
├── dev-setup.sh              # Development setup script
├── test.js                    # MCP functionality test suite
├── icon.png                   # Extension icon
└── node_modules/              # Dependencies (after npm install)
```

## ✅ Key Features Implemented

### MCP Protocol Compliance

- ✅ Proper stdio transport for Claude Desktop integration
- ✅ JSON-RPC 2.0 protocol implementation
- ✅ MCP session management with remote server
- ✅ Server-Sent Events (SSE) parsing for HTTP responses
- ✅ Robust error handling and timeout management

### USRP Tool Integration

- ✅ `uhd_find_devices` - Device discovery with structured JSON
- ✅ `uhd_usrp_probe` - Hardware probing with argument support
- ✅ `uhd_siggen` - Signal generation with full parameter control
- ✅ `uhd_rx_cfile` - RF data capture (corrected from uhd_rx_samples_to_file)
- ✅ `get_uhd_info` - UHD configuration information
- ✅ Process management tools (list, stop, cleanup)

### User Experience

- ✅ User-configurable server URL, timeout, and debug settings
- ✅ Comprehensive tool schemas with validation
- ✅ Debug logging for troubleshooting
- ✅ Production-ready error handling
- ✅ Professional logging with configurable levels

## 🚀 Quick Start

### 1. Test the Extension

```bash
cd src/usrp_proxy_dxt
./dev-setup.sh
node test.js  # Optional: comprehensive testing
```

### 2. Package for Claude Desktop

```bash
# From the uhd-mcp project root directory
npm install -g @anthropic-ai/dxt
dxt pack src/usrp_proxy_dxt/
```

### 3. Install in Claude Desktop

- Open Claude Desktop
- Go to Settings → Extensions
- Install the generated `usrp_proxy_dxt.dxt` file
- Configure your USRP server URL

## 🔧 Architecture Overview

```text
Claude Desktop ←→ DXT Proxy ←→ HTTP/SSE ←→ Remote USRP Server ←→ UHD Tools ←→ USRP Hardware
     (stdio)         (MCP)        (JSON-RPC)       (subprocess)      (USB/Ethernet)
```

The proxy handles:

- **Protocol Translation**: stdio ↔ HTTP with MCP JSON-RPC
- **Session Management**: Automatic MCP session initialization
- **Error Handling**: Timeouts, network errors, tool failures
- **Response Parsing**: SSE and JSON response handling
- **Logging Integration**: Professional logging with configurable levels

## 📊 Supported Tools

### Core UHD Tools

- `uhd_find_devices` - Discover connected USRP devices
- `uhd_usrp_probe` - Probe device capabilities and tree structure
- `uhd_siggen` - Generate RF signals with comprehensive parameter control (25+ parameters)
- `uhd_rx_cfile` - Capture RF data to files using GNU Radio (corrected implementation)
- `get_uhd_info` - Get UHD installation and configuration info

### Process Management

- `list_processes` - List running background processes
- `stop_process` - Stop specific background processes
- `cleanup_all_processes` - Stop all background processes

### Enhanced Features

- **Duration Control**: Automatic process termination after specified duration
- **Background Processes**: Long-running signal generation with proper management
- **Graceful Stopping**: Proper signal handling for clean process termination
- **Error Recovery**: Robust error handling with structured JSON responses

## ⚙️ Configuration

When installing this extension, you'll be prompted to configure:

- **USRP Server URL**: The URL of your remote USRP MCP server
- **Request Timeout**: Maximum time to wait for server responses (10-300 seconds)
- **Debug Mode**: Enable verbose logging for troubleshooting

**Example Configuration:**
```
USRP Server URL: https://uhd-mcp.your-domain.example/mcp
Request Timeout: 60 seconds
Debug Mode: false (or true for troubleshooting)
```

## 🧪 Testing & Development

### Local Testing

```bash
# Run setup and validation
./dev-setup.sh

# Test MCP functionality
node test.js

# Manual testing with debug
DEBUG_MODE=true node server/index.js
```

### Package for Claude Desktop

```bash
# From the project root directory
dxt pack src/usrp_proxy_dxt/

# This creates usrp_proxy_dxt.dxt file
```

### Claude Desktop Installation & Testing

1. **Install the Extension:**
   - Open Claude Desktop
   - Go to Settings → Extensions
   - Click "Install Extension"
   - Select the `usrp_proxy_dxt.dxt` file
   - Configure the USRP server URL when prompted

2. **Test Commands in Claude Desktop:**

   **Basic Device Discovery:**
   ```
   Find all USRP devices connected to the system
   ```

   **Get System Information:**
   ```
   Show me the UHD installation and configuration details
   ```

   **Device Probing:**
   ```
   Probe the USRP device and show me the hardware tree structure
   ```

   **Signal Generation Examples:**
   ```
   Generate a 2.4 GHz sine wave with 10 dB gain for 5 seconds
   
   Create a continuous square wave at 915 MHz with 0.5 amplitude
   
   Generate a 1 kHz tone at 2.45 GHz for 30 seconds using USRP
   ```

   **Data Capture Examples:**
   ```
   Capture 3 seconds of RF data at 433 MHz and save to file
   
   Record samples at 2.4 GHz with 20 dB gain for 10 seconds
   
   Capture ISM band data at 915 MHz for analysis using uhd_rx_cfile
   ```

   **Process Management:**
   ```
   Show me all running USRP processes
   
   Stop all background signal generation processes
   
   List any active RF signal generators
   ```

   **Advanced Examples:**
   ```
   Generate a 10 MHz bandwidth signal at 5.8 GHz for WiFi testing
   
   Probe the X310 USRP at IP address 192.168.40.28 and show capabilities
   
   Create a continuous sine wave at 2.45 GHz with custom amplitude
   
   Start signal generation for 30 seconds with automatic termination
   ```

3. **Troubleshooting Commands:**
   ```
   Check if the USRP server is responding
   
   Show me debug information for the last command
   
   Test the connection to the remote USRP server
   ```

4. **Validation Tests:**
   - Device discovery should return a list of available USRPs
   - Signal generation should return process IDs for background tasks
   - Data capture should confirm file creation and size
   - Process management should show/control running tasks
   - All responses should be in structured JSON format

5. **Expected Response Format:**
   All tool responses include:
   - `success`: boolean indicating operation status
   - `parsed_output`: structured data when applicable
   - `raw_stdout`: original command output
   - `command`: the actual command executed
   - `return_code`: process exit code

## 🛠️ Development

To modify this extension:

1. Edit `server/index.js` for the main proxy logic
2. Update `manifest.json` for metadata changes
3. Modify `package.json` for dependencies
4. Test with `node server/index.js`

### Available Scripts
```bash
npm start        # Start the proxy server
npm run dev      # Start with debug mode
npm test         # Run test suite
npm run pack     # Package as DXT extension
npm run validate # Validate manifest.json
```

## 🎯 Success Criteria Met

✅ **DXT Compliance**: Follows official DXT v0.1 specification  
✅ **MCP Protocol**: Proper stdio transport with JSON-RPC 2.0  
✅ **HTTP Proxy**: Seamless translation to remote server  
✅ **Tool Coverage**: All major UHD tools with comprehensive parameters  
✅ **Error Handling**: Robust timeout and error management  
✅ **User Config**: Configurable server URL and settings  
✅ **Documentation**: Comprehensive guides and examples  
✅ **Testing**: Automated validation and test suite  
✅ **Process Management**: Background process control with graceful termination  
✅ **Logging Integration**: Professional logging with configurable levels  
✅ **GNU Radio Compatibility**: Correct uhd_rx_cfile implementation  

## 🛡️ Security & Best Practices

### Implemented Security Measures
- ✅ HTTPS-only communication with remote server
- ✅ Request timeout protection
- ✅ Input validation for all tool parameters
- ✅ Safe environment variable handling
- ✅ No hardcoded credentials or sensitive data

### Production Considerations
- ⚠️ Configure appropriate timeouts for your network
- ⚠️ Use HTTPS URLs for remote servers
- ⚠️ Test with actual hardware before deployment
- ⚠️ Monitor debug logs in production environments

## 🌟 What This Enables

This extension bridges the gap between Claude Desktop's local MCP requirement and your remote USRP infrastructure, enabling:

- **Local AI Control**: Claude can directly control SDR hardware
- **Simplified Deployment**: No local UHD installation needed
- **Centralized Hardware**: Multiple users can access shared USRP resources
- **Scalable Architecture**: Easy to add more tools and capabilities
- **Educational Use**: Perfect for RF engineering courses and research

## 📋 Requirements

- Node.js >= 16.0.0
- Network access to the remote USRP MCP server
- Claude Desktop >= 1.0.0

## 📄 License

MIT License - see the project repository for details.

## 📚 Additional Documentation

- `INSTALL.md` - Detailed installation and setup guide
- `test.js` - Comprehensive test suite for validation

## 🔄 Recent Enhancements

### Latest Updates (August 2025)
- ✅ **Enhanced uhd_siggen**: Full parameter support with 25+ command-line options
- ✅ **Corrected uhd_rx_cfile**: Fixed from incorrect uhd_rx_samples_to_file implementation
- ✅ **Duration Control**: Intelligent process management with configurable timeouts
- ✅ **Professional Logging**: Replaced print statements with structured logging
- ✅ **Graceful Termination**: Proper signal handling for clean process shutdown
- ✅ **Background Processing**: Non-blocking signal generation with process tracking

### Logging Configuration
The server now uses Python's logging module with configurable levels:
- **DEBUG**: Detailed diagnostic information
- **INFO**: General operational information (default)
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error conditions that don't halt execution
- **CRITICAL**: Serious errors that may halt execution

Configure logging level when starting the server:

```bash
python3 -m src.uhd_mcp.usrp_mcp_server --log-level DEBUG
```

The extension is production-ready and follows all DXT best practices for security, reliability, and user experience!
