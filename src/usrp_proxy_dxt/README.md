# USRP MCP Proxy Desktop Extension

This Desktop Extension (DXT) provides a local MCP proxy for remote USRP MCP servers, enabling Claude Desktop to control software-defined radio equipment via UHD (USRP Hardware Driver) tools.

## Features

- **Device Discovery**: Find and enumerate connected USRP devices
- **Device Probing**: Get detailed hardware information and capabilities
- **Signal Generation**: Generate various waveforms with configurable parameters
- **Data Capture**: Capture RF samples to files
- **Process Management**: Control background signal generation processes
- **Session Management**: Automatic MCP session handling with the remote server
- **Error Handling**: Robust error handling with timeout management
- **Debug Logging**: Optional verbose logging for troubleshooting

## Supported Tools

### Core UHD Tools
- `uhd_find_devices` - Discover connected USRP devices
- `uhd_usrp_probe` - Probe device capabilities and tree structure
- `uhd_siggen` - Generate RF signals with configurable parameters
- `uhd_rx_samples_to_file` - Capture RF data to files
- `get_uhd_info` - Get UHD installation and configuration info

### Process Management
- `list_processes` - List running background processes
- `stop_process` - Stop specific background processes
- `cleanup_all_processes` - Stop all background processes

## Configuration

When installing this extension, you'll be prompted to configure:

- **USRP Server URL**: The URL of your remote USRP MCP server
- **Request Timeout**: Maximum time to wait for server responses (10-300 seconds)
- **Debug Mode**: Enable verbose logging for troubleshooting

## Requirements

- Node.js >= 16.0.0
- Network access to the remote USRP MCP server
- Claude Desktop >= 1.0.0

## Usage Examples

### Find Connected Devices
```
Use the uhd_find_devices tool to discover USRP devices
```

### Generate a Signal
```
Use uhd_siggen with parameters:
- freq: 2.4e9 (2.4 GHz)
- rate: 1e6 (1 MHz)
- gain: 10 (dB)
- duration: 10 (seconds)
```

### Capture RF Data
```
Use uhd_rx_samples_to_file with:
- freq: 915e6 (915 MHz)
- duration: 2.0 (seconds)
- filename: "capture.dat"
```

## Architecture

This extension acts as a proxy between Claude Desktop (MCP client) and a remote USRP MCP server:

```
Claude Desktop → DXT Proxy → HTTP/SSE → Remote USRP Server → UHD Tools → USRP Hardware
```

The proxy handles:
- MCP protocol translation between stdio and HTTP
- Session management with the remote server
- Server-Sent Events (SSE) parsing
- Error handling and timeouts
- Tool schema validation

## Development

To modify this extension:

1. Edit `server/index.js` for the main proxy logic
2. Update `manifest.json` for metadata changes
3. Modify `package.json` for dependencies
4. Test with `node server/index.js`

## Security Considerations

- The extension connects to external servers over HTTPS
- Sensitive configuration is handled via user configuration
- All network requests include timeout protection
- Debug logging can be disabled in production

## License

MIT License - see the project repository for details.
