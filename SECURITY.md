# Security Policy

## Reporting a vulnerability

If you discover a security issue, please report it privately rather than opening a public issue.
Email **a.lacava@northeastern.edu** with a description, reproduction steps, and any relevant logs.
We will acknowledge the report and work with you on a fix and coordinated disclosure.

## Scope and operational safety

This server controls real radio transmit/receive hardware and executes UHD/GNU Radio binaries on
the host. Operators should be aware of the following built-in protections and responsibilities:

- **Transmit guardrails.** Signal-generation parameters (gain, frequency, sample rate, duration)
  are bounded by configurable guardrails (`src/uhd_mcp/utils/guardrails.py`) to reduce the risk of
  hardware damage or out-of-band emissions.
- **Sandboxed script execution.** The `execute_uhd_script` tool validates user-supplied Python via
  an AST allowlist (`src/uhd_mcp/utils/script_validator.py`) and runs it under guardrails and a
  bounded timeout (`src/uhd_mcp/utils/script_executor.py`). It is not a substitute for running the
  server in a trusted, network-restricted environment.
- **Command timeouts** prevent hung subprocesses, and running processes are cleaned up on shutdown.
- **File-serving containment.** `download_file` / `list_shared_files` operate only within
  `MCP_SHARED_DATA_DIR` and enforce a `commonpath` containment check to prevent path escape.
- **Network exposure.** The HTTP transport enables permissive CORS (`*`) by default. Restrict it
  with `--cors-origins` and place the server behind authentication when exposing it beyond
  localhost or a trusted network.

## Regulatory compliance

You are responsible for ensuring that any transmission complies with the radio-frequency
regulations applicable in your jurisdiction (frequency allocations, power limits, licensing).
Operate transmitters only in shielded/lab environments or on frequencies you are authorized to use.
