# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A [FastMCP](https://github.com/jlowin/fastmcp) server that exposes USRP software-defined radios (via UHD/GNU Radio command-line tools) as MCP tools. There is no Python wrapper around UHD — every tool shells out to UHD binaries (`uhd_find_devices`, `uhd_usrp_probe`, `uhd_siggen`, `uhd_rx_cfile`, `uhd_config_info`) with `subprocess`, so **the UHD/GNU Radio binaries must be on `PATH` at runtime**. The codebase has no hardware, so most tools cannot be exercised locally without a connected USRP.

## Commands

The project uses [Hatch](https://hatch.pypa.io/) for environments. The `default` env has runtime deps; the `dev` env adds pytest, black, ruff, mypy.

```bash
./setup.sh                                      # install hatch (via pipx) + verify UHD is present
hatch run python -m uhd_mcp --port 8080         # run server, HTTP transport (default)
hatch run python -m uhd_mcp --transport stdio   # run server, stdio transport (local MCP consumers)

hatch -e dev run test                           # run all tests (pytest tests/)
hatch -e dev run test tests/mcp_server/         # run a single test dir/file
hatch -e dev run lint                           # ruff check .
hatch -e dev run format                         # black .
hatch -e dev run type-check                     # mypy src
```

Note: `run_test.sh` and the README reference `test_usrp_client.py` at the repo root, but the actual test client lives at [tests/usrp_client/test_usrp_client.py](tests/usrp_client/test_usrp_client.py). It is a live integration client that POSTs JSON-RPC to a running HTTP server — not a pytest unit test.

## Architecture

### Server core — [src/uhd_mcp/usrp_mcp_server.py](src/uhd_mcp/usrp_mcp_server.py)
A single module defines `mcp = FastMCP(...)` and registers every tool with `@mcp.tool()`. `main()` parses `--transport {http,stdio}`, `--port`, `--host`, `--cors-origins`, `--log-level` and calls `mcp.run(...)`. The HTTP endpoint is always at path `/mcp`.

Key cross-cutting conventions any new tool must follow:
- **Every tool returns a `toons.dumps(...)` string**, not JSON. Output is [TOON](https://toons.readthedocs.io/) (Token-Oriented Object Notation) to cut token usage. Keep this consistent — the DXT proxy and clients expect TOON.
- **Long-running tools (`uhd_siggen`, `uhd_rx_cfile`) are non-blocking.** They `Popen` a process, register it in the module-global `running_processes` dict under a generated `process_id`, then `time.sleep(USRP_INIT_WAIT_SECONDS)` and check `process.poll()` to distinguish "started OK" from "died during hardware init". The caller later calls `stop_process(process_id)` (graceful stop = write `\n` to stdin, then `terminate`, then `kill`) to retrieve stdout/stderr and results. `list_processes`, `cleanup_all_processes`, and an `atexit` `cleanup_on_exit` manage this dict. `stop_process` special-cases `type == "rx_cfile"` entries to attach capture-file stats via `_rx_cfile_capture_info`.
- **`uhd_siggen` "duration" is not a UHD flag** — it is implemented with a daemon timer thread that stops the process after N seconds.

### Output parsing — [src/uhd_mcp/utils/device_parser.py](src/uhd_mcp/utils/device_parser.py)
Parses the human-readable text from `uhd_find_devices` / `uhd_config_info --print-all` into structured dicts. When UHD output format changes, this is what breaks.

### Shared data layer — [src/uhd_mcp/utils/config.py](src/uhd_mcp/utils/config.py)
All captures and downloadable files go to `MCP_SHARED_DATA_DIR` (env var; default `./shared-data-layer`). `list_shared_files` and `download_file` operate only within this dir — `download_file` enforces a `commonpath` containment check to prevent path escape. Preserve that check when touching file-serving code.

### DXT proxy — [src/usrp_proxy_dxt/](src/usrp_proxy_dxt/)
A separate **Node.js** MCP server (Desktop Extension, DXT spec v0.1) that bridges Claude Desktop's stdio to the remote HTTP server. It re-declares the tool schemas in `manifest.json` / `server/index.js`, so **adding or changing a Python tool's signature requires mirroring it here** or Claude Desktop won't see the change. Note that `--transport stdio` on the Python server makes this proxy unnecessary for local use; the proxy exists for talking to a *remote* HTTP deployment.

## Environment variables
- `MCP_SHARED_DATA_DIR` — where captures/downloads live.
- `PAT_TOKEN` — if set, `start.sh` runs `update-repo.sh` to `git pull` latest before launching (optional; only relevant when the container is built by baking in the repo rather than the default local `COPY`).

## Deployment

### Container image — [deploy/Dockerfile](deploy/Dockerfile)
Builds `FROM ubuntu:24.04`, compiles **UHD from source** at a selectable version (`ARG UHD_VERSION`, default `4.7.0.0`) plus GNU Radio + pipx, creates a non-root `mcp` user, `COPY`s the local build context into the image, runs `./setup.sh`, and uses `CMD ["./start.sh"]`. Captures persist via the `/data/shared` volume (`MCP_SHARED_DATA_DIR`). To reach Ethernet USRPs, run with `--network host`; USB USRPs additionally need device passthrough. See [README.md](README.md) for the full `docker build`/`docker run` commands.

### OpenShift/Kubernetes — [deploy/](deploy/)
The manifests in [deploy/](deploy/) are **generic templates** — placeholders (`your-namespace`, `REPLACE_ME/uhd-mcp:latest`, `your-sriov-network`, `uhd-mcp.your-domain.example`) must be replaced for your cluster. Apply order (see [deploy/README.md](deploy/README.md)):
1. **Secret** named `github-pat` (key `token`) — only needed if you use the optional `PAT_TOKEN` auto-update path.
2. `kubectl apply -f deployment.yaml -f service.yaml -f route.yaml`.

Topology:
- **Deployment** runs `./start.sh` (server on container port 8080), mounts a PVC at the shared data dir, and runs locked-down (non-root, all caps dropped, `RuntimeDefault` seccomp). On OpenShift the platform assigns an arbitrary UID, so the app dir is group-writable.
- It can attach an **SR-IOV** NIC (`k8s.v1.cni.cncf.io/networks` annotation + an `openshift.io/sriovnet_*` resource) for a dedicated radio network the USRP is reached over — adjust the network/resource names to your cluster.
- **Service** is `ClusterIP` on 8080; **Route** exposes it externally with edge TLS (HTTPS, HTTP→HTTPS redirect). The public MCP endpoint is the route host + `/mcp`.

The proxy build workflow only packages the DXT extension and cuts a GitHub release; **it does not build or push the container image**.

### Bare-metal / systemd — [install-service.sh](install-service.sh)
For a non-container host: writes a `usrp-mcp.service` unit that runs `hatch run python -m uhd_mcp --port 8080` as the current user with `Restart=always`, then enables it. Requires `./setup.sh` to have run first (needs `hatch` on PATH).

## Versioning gotcha
There are **three** version sources that can drift: `VERSION` (single line, read by hatch via `[tool.hatch.version]`), `src/uhd_mcp/__init__.py` `__version__`, and `src/usrp_proxy_dxt/manifest.json` `version`. The proxy build workflow ([.github/workflows/build-proxy-package.yml](.github/workflows/build-proxy-package.yml)) reads the version from `manifest.json` and publishes a GitHub release on every push to `main`.

## Stdio logging constraint
In stdio transport, stdout carries the MCP protocol, so `main()` routes all logging to **stderr**. Never `print()` to stdout or add stdout logging in tool code paths — it will corrupt the stdio stream.
