# Contributing to USRP MCP Server

Thanks for your interest in contributing! This project exposes USRP software-defined radios as
[MCP](https://modelcontextprotocol.io/) tools by shelling out to the UHD/GNU Radio command-line
binaries. Because of that, most tools can only be exercised end-to-end with a connected USRP — but
the parsing, validation, guardrail, and server logic is unit-tested and can be developed without
hardware.

## Development setup

The project uses [Hatch](https://hatch.pypa.io/) for environment management.

```bash
./setup.sh            # installs Hatch (via pipx) and verifies UHD is on PATH
hatch run python -m uhd_mcp --transport stdio   # run locally (stdio)
hatch run python -m uhd_mcp --port 8080         # run locally (HTTP, default)
```

UHD/GNU Radio binaries (`uhd_find_devices`, `uhd_usrp_probe`, `uhd_siggen`, `uhd_rx_cfile`,
`uhd_config_info`) must be on `PATH` at runtime. See the [UHD install guide](https://files.ettus.com/manual/)
or use the container in [deploy/Dockerfile](deploy/Dockerfile).

## Checks to run before opening a PR

```bash
hatch -e dev run test          # pytest
hatch -e dev run lint          # ruff check .
hatch -e dev run format        # black .  (or format-check to verify without writing)
hatch -e dev run type-check    # mypy src
```

Please keep new tools consistent with the existing conventions documented in
[CLAUDE.md](CLAUDE.md):

- Every MCP tool returns a `toons.dumps(...)` string (TOON), not JSON.
- Long-running tools are non-blocking and registered in the `running_processes` registry.
- In stdio transport, never `print()` to stdout — it corrupts the MCP stream; log to stderr.

## Mirroring tool changes into the DXT proxy

The Node.js Desktop Extension in [src/usrp_proxy_dxt/](src/usrp_proxy_dxt/) re-declares each tool's
schema in `manifest.json` and `server/index.js`. **If you add or change a Python tool's signature,
mirror it there** or Claude Desktop won't see the change.

## Versioning

Three version sources must stay in sync when you cut a release:

- `VERSION` (read by Hatch)
- `src/uhd_mcp/__init__.py` `__version__`
- `src/usrp_proxy_dxt/manifest.json` `version`

## Pull request workflow

1. Fork and branch off `main`.
2. Make focused changes with clear commit messages.
3. Run the checks above; add/adjust tests under `tests/` where practical.
4. Open a PR describing what changed, how you tested it, and whether hardware was involved.

By contributing you agree your contributions are licensed under the project's
[MIT License](LICENSE) and that you will follow the [Code of Conduct](CODE_OF_CONDUCT.md).
