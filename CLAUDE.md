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

Two test suites are gated behind env vars and skip in default runs:
- [tests/usrp_client/test_usrp_client.py](tests/usrp_client/test_usrp_client.py) — live e2e over HTTP JSON-RPC; runs only when `UHD_MCP_LIVE_URL` points at a running server's `/mcp` endpoint. Also runnable standalone: `hatch run python tests/usrp_client/test_usrp_client.py <host> <port>` (or `./run_test.sh`).
- [tests/hardware/](tests/hardware/) — requires `USRP_HW_TESTS=1` *and* a reachable USRP (auto-detected via `uhd_find_devices`); optional `USRP_ADDR` pins a specific device. The `execute_uhd_script` tests need the UHD Python bindings importable from the sandbox: if UHD was built from source, set `PYTHONPATH=/usr/local/lib/python3.X/site-packages` (the sandbox whitelists `PYTHONPATH`; the container image sets it already).

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
A **multi-stage** build with a selectable UHD source (all recipes documented in the Dockerfile header and [README.md](README.md)):
- `uhd-source` — compiles UHD from source (`ARG UHD_VERSION`, default `4.7.0.0`) on `ubuntu:24.04`; the self-contained path (`--build-arg UHD_FLAVOR=source`), works without registry access, any arch.
- `uhd-prebuilt` — `FROM ${UHD_BASE_IMAGE}` (default `ghcr.io/wineslab/uhd:4.7`, amd64-only, currently private → needs `docker login ghcr.io`). This is the default flavor.
- `deps` — adds what the UHD base lacks: GNU Radio (`uhd_siggen`/`uhd_rx_cfile`), pipx, network tooling, and FPGA images (`ARG DOWNLOAD_UHD_IMAGES=true`). Published as `ghcr.io/wineslab/uhd-mcp-deps:uhd4.7`; pass `--build-arg DEPS_IMAGE=<ref>` to reuse it and skip this stage.
- `mcp` (final) — `COPY`s the app, creates the non-root `mcp` user (uid 1000, gid 0, group-writable for OpenShift), runs `./setup.sh`, `CMD ["./start.sh"]`.

Captures persist via the `/data/shared` volume (`MCP_SHARED_DATA_DIR`). To reach Ethernet USRPs, run with `--network host`; USB USRPs additionally need device passthrough.

### OpenShift/Kubernetes — [deploy/](deploy/)
The manifests in [deploy/](deploy/) are **generic templates** — placeholders (`your-namespace`, `REPLACE_ME/uhd-mcp:latest`, `your-sriov-network`, `uhd-mcp.your-domain.example`) must be replaced for your cluster. Apply order (see [deploy/README.md](deploy/README.md)):
1. **Secret** named `github-pat` (key `token`) — only needed if you use the optional `PAT_TOKEN` auto-update path.
2. `kubectl apply -f deployment.yaml -f service.yaml -f route.yaml`.

Topology:
- **Deployment** runs `./start.sh` (server on container port 8080), mounts a PVC at the shared data dir, and runs locked-down (non-root, all caps dropped, `RuntimeDefault` seccomp). On OpenShift the platform assigns an arbitrary UID, so the app dir is group-writable.
- It can attach an **SR-IOV** NIC (`k8s.v1.cni.cncf.io/networks` annotation + an `openshift.io/sriovnet_*` resource) for a dedicated radio network the USRP is reached over — adjust the network/resource names to your cluster.
- **Service** is `ClusterIP` on 8080; **Route** exposes it externally with edge TLS (HTTPS, HTTP→HTTPS redirect). The public MCP endpoint is the route host + `/mcp`.

### CI/release workflows — [.github/workflows/](.github/workflows/)
- [tests-on-pr.yml](.github/workflows/tests-on-pr.yml) — runs the non-hardware pytest whitelist on PRs.
- [build-proxy-package.yml](.github/workflows/build-proxy-package.yml) — on a release tag: stamps `manifest.json` from `VERSION`, packs the DXT, creates the GitHub release.
- [build-deps-image.yml](.github/workflows/build-deps-image.yml) — builds/pushes `ghcr.io/wineslab/uhd-mcp-deps:uhd4.7`; runs on `workflow_dispatch` or when `deploy/Dockerfile` changes on `main`.
- [build-mcp-image.yml](.github/workflows/build-mcp-image.yml) — on a release tag: builds `ghcr.io/wineslab/uhd-mcp` from the published deps image and pushes `X.Y.Z`, `X.Y`, `latest`, `sha-*` tags. `workflow_dispatch` gives a build-only dry run.

Releases are **tag-driven**: push a git tag equal to `VERSION` (plain `X.Y.Z`, no `v` prefix). Both release workflows guard `tag == VERSION`. CI image pulls require the repo to have read access to the `wineslab/uhd` ghcr package.

### Bare-metal / systemd — [install-service.sh](install-service.sh)
For a non-container host: writes a `usrp-mcp.service` unit that runs `hatch run python -m uhd_mcp --port 8080` as the current user with `Restart=always`, then enables it. Requires `./setup.sh` to have run first (needs `hatch` on PATH).

## Versioning
`VERSION` (single line, read by hatch via `[tool.hatch.version]`) is the **only** hand-edited version source. `src/uhd_mcp/__init__.py` derives `__version__` from installed package metadata (falling back to the `VERSION` file), and the proxy workflow stamps `src/usrp_proxy_dxt/manifest.json` and `package.json` from `VERSION` at build time. To release: bump `VERSION`, then push a matching `X.Y.Z` tag.

## Stdio logging constraint
In stdio transport, stdout carries the MCP protocol, so `main()` routes all logging to **stderr**. Never `print()` to stdout or add stdout logging in tool code paths — it will corrupt the stdio stream.
