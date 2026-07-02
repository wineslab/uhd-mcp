# USRP MCP Server - Example Commands

## Starting the Server

```bash
# Start with Hatch in HTTP mode (default - binds to all interfaces)
hatch run python -m uhd_mcp

# Start on specific port
hatch run python -m uhd_mcp --port 9090

# Start on localhost only
hatch run python -m uhd_mcp --host 127.0.0.1 --port 8080

# Or enter Hatch shell first
hatch shell
python -m uhd_mcp --port 8080

# Show help and all options
hatch run python -m uhd_mcp --help
```

## Running Tests

```bash
# Unit and integration tests (no hardware needed)
hatch -e dev run test

# Live end-to-end test against a running server
UHD_MCP_LIVE_URL=http://127.0.0.1:8080/mcp hatch -e dev run test tests/usrp_client/

# Or run the live client standalone with custom host/port
hatch run python tests/usrp_client/test_usrp_client.py 192.168.1.100 8080

# Hardware tests against a connected USRP
USRP_HW_TESTS=1 hatch -e dev run test tests/hardware/
```

## Basic Device Discovery

- **uhd_find_devices()** - Find connected USRP devices
- **uhd_usrp_probe()** - Get detailed device information
- **get_uhd_info()** - Get UHD version and config

## Signal Generation Examples

### Generate 2.4 GHz sine wave for 10 seconds

uhd_siggen(freq=2.4e9, duration=10, wave_type="SINE", wave_freq=1000, gain=15)

### Generate continuous FM signal at 100 MHz

uhd_siggen(freq=100e6, wave_type="SINE", wave_freq=1000, gain=10)

### Generate square wave at 900 MHz

uhd_siggen(freq=900e6, wave_type="SQUARE", wave_freq=500, gain=12, duration=30)

## Signal Capture Examples

### Capture 5 seconds at 2.4 GHz

uhd_rx_samples_to_file(freq=2.4e9, duration=5, gain=20, filename="capture_2400.dat")

### High-rate capture at 900 MHz

uhd_rx_samples_to_file(freq=900e6, rate=5e6, duration=2, gain=15, filename="fast_capture.dat")

## Process Management

- **list_processes()** - Show running signal generators
- **stop_process("process_id")** - Stop specific process
- **cleanup_all_processes()** - Stop all running processes

## Safety Notes

- Always use appropriate gain levels (typically 0-30 dB)
- The server includes safety limits for gain and commands
