# USRP B210 MCP Server - Hatch Development Guide

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
# Run server directly
hatch run python usrp_mcp_server.py --tcp 8080

# Run with environment variables
hatch run --env PYTHONPATH=/custom/path python usrp_mcp_server.py

# Enter shell for interactive development
hatch shell
```

## Development Commands

```bash
# Install development dependencies (if configured in pyproject.toml)
hatch env create dev

# Run tests (if configured)
hatch run test

# Run linting (if configured)
hatch run lint

# Format code (if configured)
hatch run format
```

## Dependency Management

```bash
# Add runtime dependency
hatch dep add fastmcp

# Add development dependency
hatch dep add --dev pytest

# Show dependencies
hatch dep show
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
