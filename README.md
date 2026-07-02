# USRP MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://github.com/wineslab/uhd-mcp/actions/workflows/tests-on-pr.yml/badge.svg)](https://github.com/wineslab/uhd-mcp/actions/workflows/tests-on-pr.yml)

A Model Context Protocol (MCP) server for controlling USRP software-defined radios using UHD (USRP Hardware Driver).

## Features

- **Device Discovery**: Find and probe connected USRP devices
- **Signal Generation**: Generate various waveforms (sine, square, etc.)
- **Signal Capture**: Record RF samples to files
- **Process Management**: Monitor and control running processes
- **Safety Limits**: Built-in protections for gain levels and command execution
- **TOON Output**: All tool responses use [TOON (Token-Oriented Object Notation)](https://toons.readthedocs.io/en/stable/) — a compact, LLM-friendly format that reduces token usage compared to JSON

## Prerequisites

- **UHD (USRP Hardware Driver)**: Required for USRP communication ([UHD Installation Guide](https://files.ettus.com/manual/))
- **Python 3.10+**: For running the server
- **Hatch**: Modern Python project management (installed automatically by setup script)

## Quick Setup

1. **Run the setup script**:

   ```bash
   ./setup.sh
   ```

2. **Start the server**:

   ```bash
   ./start.sh
   ```

   Or manually (HTTP mode, default):

   ```bash
   hatch run python -m uhd_mcp --port 8080
   ```

   Or in **local stdio mode** (for Claude Desktop, VS Code, OpenWebUI, etc.):

   ```bash
   hatch run python -m uhd_mcp --transport stdio
   ```

## Transport Modes

The server supports two transport modes selected with `--transport`:

| Mode | Flag | Use case |
|------|------|----------|
| HTTP | `--transport http` (default) | Remote / Kubernetes deployments; any HTTP-capable MCP consumer |
| stdio | `--transport stdio` | Local execution on the same machine as the MCP consumer |

### HTTP mode — remote server

```json
"uhd-mcp": {
  "url": "https://<url of your MCP server>:<port>/mcp",
  "type": "http"
}
```

For Claude Desktop there is also the DXT proxy extension in `src/usrp_proxy_dxt/` which wraps the HTTP server behind a stdio interface.

### stdio mode — local (Claude Desktop / VS Code / OpenWebUI)

No proxy is needed when `--transport stdio` is used.  The server process is started directly by the MCP consumer.

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "uhd-mcp": {
      "command": "python",
      "args": ["-m", "uhd_mcp", "--transport", "stdio"],
      "env": {
        "MCP_SHARED_DATA_DIR": "/path/to/shared-data"
      }
    }
  }
}
```

**VS Code** (`.vscode/mcp.json` or user settings):

```json
{
  "servers": {
    "uhd-mcp": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "uhd_mcp", "--transport", "stdio"],
      "env": {
        "MCP_SHARED_DATA_DIR": "/path/to/shared-data"
      }
    }
  }
}
```

**OpenWebUI** — connect via **Admin Panel → Settings → Tools → Add MCP Server**:

| Field | Value |
|-------|-------|
| URL | `http://<host>:<port>` |
| OpenAPI Spec URL | `/mcp` |
| Auth | None |

> **Note**: the server exposes its MCP endpoint at `/mcp`. In OpenWebUI, set **URL** to the server root (e.g. `http://192.168.1.10:8080`) and **OpenAPI Spec URL** to `/mcp`. Set Auth to **None** unless the server sits behind an authenticating reverse proxy. CORS is enabled for all origins by default (`*`); use `--cors-origins` to restrict access in production (e.g. `--cors-origins https://my-openwebui.example.com`).

## TOON Output Format

All MCP tool responses are serialised using **TOON (Token-Oriented Object Notation)**, a compact human-readable format optimised for LLM contexts.  TOON uses significantly fewer tokens than JSON for the same data.

Example — `uhd_find_devices` response in TOON:

```
command: uhd_find_devices
return_code: 0
success: true
parsed_output:
  total_devices: 2
  devices[2]{device_number,type,addr}:
    0,b200,192.168.1.10
    1,x310,192.168.1.11
```

The same data in JSON would be approximately 3× larger.  See the [TOON documentation](https://toons.readthedocs.io/en/stable/) for the full specification.

## Development with Hatch

This project uses [Hatch](https://hatch.pypa.io/) for dependency management and environment isolation.

### Common Commands

```bash
# Enter development environment
hatch shell

# Run the server (HTTP)
hatch run python -m uhd_mcp --port 8080

# Run the server locally (stdio)
hatch run python -m uhd_mcp --transport stdio

# Run tests (hardware and live e2e tests are skipped unless opted in)
hatch -e dev run test

# Live e2e test against a running server
UHD_MCP_LIVE_URL=http://127.0.0.1:8080/mcp hatch -e dev run test tests/usrp_client/

# Hardware tests against a connected USRP
USRP_HW_TESTS=1 hatch -e dev run test tests/hardware/

# Lint / format / type-check
hatch -e dev run lint
hatch -e dev run format
hatch -e dev run type-check

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

See [SECURITY.md](SECURITY.md) for the full safety/security posture and how to report issues.

## Container / Docker

Released versions are published as container images:

```bash
docker pull ghcr.io/wineslab/uhd-mcp:latest   # or a specific version, e.g. :0.1.0
```

The [deploy/Dockerfile](deploy/Dockerfile) is a multi-stage build with a selectable UHD source:

- **prebuilt** (default): builds on the org UHD base image `ghcr.io/wineslab/uhd` and adds a
  `deps` layer (GNU Radio, pipx, FPGA images) plus the app. Requires `docker login ghcr.io`
  while those base images are private.
- **source**: fully self-contained — compiles **UHD from source** at a version you choose
  (default `4.7.0.0`, tested up to `4.8.0.0`) on public `ubuntu:24.04`. No registry access needed.

```bash
# Build on the org UHD base (default)
docker build -f deploy/Dockerfile -t uhd-mcp .

# Fast build reusing the published deps image (what release CI does)
docker build -f deploy/Dockerfile --build-arg DEPS_IMAGE=ghcr.io/wineslab/uhd-mcp-deps:uhd4.7 -t uhd-mcp .

# Fully self-contained build (pick the UHD version you need)
docker build -f deploy/Dockerfile --build-arg UHD_FLAVOR=source --build-arg UHD_VERSION=4.7.0.0 -t uhd-mcp .

# Run against real USRPs and persist IQ captures
mkdir -p shared-data   # pre-create so it isn't root-owned (container runs as UID 1000)
docker run --rm --network host \
  -v "$PWD/shared-data:/data/shared" \
  uhd-mcp
```

Add `--build-arg DOWNLOAD_UHD_IMAGES=false` for a much smaller image without the bundled
FPGA images (needed only for flashing networked USRPs).

- `--network host` lets `uhd_find_devices` reach Ethernet USRPs (X3x0/N3xx) on the host's radio network.
- The bind mount persists captures written by `uhd_rx_cfile` to `MCP_SHARED_DATA_DIR` (`/data/shared` in the image).
- **USB USRPs (B2xx)** additionally need device access: add `--privileged` or `-v /dev/bus/usb:/dev/bus/usb`.
- On OpenShift/Kubernetes the SR-IOV NIC defined in [deploy/](deploy/) provides the radio network instead of `--network host`.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). By participating you agree to
the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

Licensed under the MIT License — see [LICENSE](LICENSE). Copyright (c) 2025 Andrea Lacava.
