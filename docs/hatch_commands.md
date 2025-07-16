# USRP MCP Server - Hatch Development Guide

## Environment Management

```bash
# Create/recreate environment
hatch env create

# Remove environment
hatch env remove

# Show environment info
hatch env show

# List all environments
hatch env show --all

# Find environment path
hatch env find
```

## Running the Server

```bash
# Run server in HTTP mode (default - binds to all interfaces)
hatch run python -m uhd_mcp

# Run on specific port
hatch run python -m uhd_mcp --port 9090

# Run on localhost only
hatch run python -m uhd_mcp --host 127.0.0.1 --port 8080

# Show all command-line options
hatch run python -m uhd_mcp --help

# Run with environment variables
hatch run --env PYTHONPATH=/custom/path python -m uhd_mcp --tcp

# Enter shell for interactive development
hatch shell
```

## Development Commands

```bash
# Install development dependencies (if configured in pyproject.toml)
hatch env create dev

# Run tests (if configured)
hatch run test
```

## Building and Publishing

```bash
# Build the project
hatch build

# Clean build artifacts
hatch clean

# Publish to PyPI (if configured)
hatch publish
```

## Troubleshooting

```bash
# Check environment status
hatch env show

# Recreate environment if corrupted
hatch env remove && hatch env create

# Check Python executable being used
hatch run python -c "import sys; print(sys.executable)"

# Debug environment variables
hatch run python -c "import os; print(dict(os.environ))"
```
