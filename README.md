# USRP B210 MCP Server

A Model Context Protocol (MCP) server for controlling USRP B210 software-defined radios using UHD (USRP Hardware Driver).

## Features

- **Device Discovery**: Find and probe connected USRP devices
- **Signal Generation**: Generate various waveforms (sine, square, etc.)
- **Signal Capture**: Record RF samples to files
- **Process Management**: Monitor and control running processes
- **Safety Limits**: Built-in protections for gain levels and command execution

## Prerequisites

- **UHD (USRP Hardware Driver)**: Required for USRP communication
  - Ubuntu/Debian: `sudo apt install uhd-host`
  - Other systems: [UHD Installation Guide](https://files.ettus.com/manual/)
- **Python 3.8+**: For running the server
- **Hatch**: Modern Python project management (installed automatically by setup script)

## Quick Setup

1. **Run the setup script**:
   ```bash
   ./setup_usrp.sh
   ```

2. **Start the server**:
   ```bash
   ./quick_start.sh
   ```

   Or manually:
   ```bash
   hatch run python usrp_mcp_server.py --tcp 8080
   ```

## Development with Hatch

This project uses [Hatch](https://hatch.pypa.io/) for dependency management and environment isolation.

### Common Commands

```bash
# Enter development environment
hatch shell

# Run the server
hatch run python usrp_mcp_server.py --tcp 8080

# Run tests
hatch run python test_usrp_client.py

# Development environment with extra tools
hatch env create dev
hatch -e dev shell
```

See `hatch_commands.md` for comprehensive Hatch usage.

## Available Tools

- `uhd_find_devices()` - Find connected USRP devices
- `uhd_usrp_probe()` - Get detailed device information
- `uhd_siggen()` - Generate RF signals
- `uhd_rx_samples_to_file()` - Capture RF samples
- `get_uhd_info()` - Get UHD version information
- `list_processes()` - Show running processes
- `stop_process()` - Stop specific processes
- `cleanup_all_processes()` - Stop all processes

## Usage Examples

See `example_commands.md` for detailed usage examples.

## Safety

- Gain levels are limited to prevent damage
- Command execution timeouts prevent hanging
- Process cleanup on server shutdown
- Always verify frequency allocations comply with local regulations

## Files

- `usrp_mcp_server.py` - Main MCP server
- `test_usrp_client.py` - Test client for verification
- `setup_usrp.sh` - Initial setup script
- `quick_start.sh` - Quick server startup
- `pyproject.toml` - Hatch project configuration
- `example_commands.md` - Usage examples
- `hatch_commands.md` - Hatch development guide
- `claude_config.json` - Claude Desktop configuration example

## License

MIT
