# USRP MCP Server

A Model Context Protocol (MCP) server for controlling USRP software-defined radios using UHD (USRP Hardware Driver).

## Features

- **Device Discovery**: Find and probe connected USRP devices
- **Signal Generation**: Generate various waveforms (sine, square, etc.)
- **Signal Capture**: Record RF samples to files
- **Process Management**: Monitor and control running processes
- **Safety Limits**: Built-in protections for gain levels and command execution

## Prerequisites

- **UHD (USRP Hardware Driver)**: Required for USRP communication ([UHD Installation Guide](https://files.ettus.com/manual/))
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
   hatch run python -m uhd_mcp --port 8080
   ```

3. **Add the following c**:

   ```bash
   "uhd-mcp": {
      url": "https://<url of your MCP server>:<port>/mcp",
      "type": "http"
   }
   ```

   This will use the remote HTTP server, for claude there is an alternative that uses the proxy through the digital extension

## Development with Hatch

This project uses [Hatch](https://hatch.pypa.io/) for dependency management and environment isolation.

### Common Commands

```bash
# Enter development environment
hatch shell

# Run the server
hatch run python -m uhd_mcp --port 8080

# Run tests
hatch run python test_usrp_client.py

# Development environment with extra tools
hatch env create dev
hatch -e dev shell
```

See `docs/hatch_commands.md` for comprehensive Hatch usage.

## Usage Examples

See `docs/example_commands.md` for detailed usage examples.

## Safety

- Gain levels are limited to prevent damage
- Command execution timeouts prevent hanging
- Process cleanup on server shutdown
- Always verify frequency allocations comply with local regulations

## License

2025 Andrea Lacava All rights reserved