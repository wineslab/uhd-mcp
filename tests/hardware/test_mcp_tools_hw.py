"""
Hardware integration tests for the MCP tools themselves (uhd_find_devices,
uhd_usrp_probe, uhd_siggen, uhd_rx_cfile and the process-management tools).

⚠️  THESE TESTS REQUIRE PHYSICAL UHD HARDWARE ⚠️

They are SKIPPED automatically unless:
- USRP_HW_TESTS=1 is set in the environment
- AND at least one UHD device is reachable (uhd_find_devices)

Optionally set USRP_ADDR to the IP of a specific device (e.g. 192.168.40.34);
otherwise the first discovered device is used.

Usage with hardware:
    USRP_HW_TESTS=1 pytest tests/hardware/test_mcp_tools_hw.py -v
"""

import os
import subprocess
import time

import pytest
import toons

# ---------------------------------------------------------------------------
# Skip markers – same gating pattern as test_hardware_integration.py
# ---------------------------------------------------------------------------

HW_TESTS_ENABLED = os.environ.get("USRP_HW_TESTS", "0") == "1"

pytestmark = pytest.mark.skipif(
    not HW_TESTS_ENABLED,
    reason="Hardware tests disabled. Set USRP_HW_TESTS=1 to enable.",
)


def _usrp_available() -> bool:
    """Return True if at least one UHD device can be found."""
    try:
        result = subprocess.run(
            ["uhd_find_devices"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0 and "UHD Device" in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# Only shell out to uhd_find_devices when the suite is enabled at all.
requires_usrp = pytest.mark.skipif(
    not (HW_TESTS_ENABLED and _usrp_available()),
    reason="No UHD device found. Skipping hardware test.",
)

# Safe RF parameters: inside the tuning range of the common X3x0/B2xx
# daughterboards, low gain, low amplitude.
TEST_FREQ_HZ = 2.4e9
TEST_SAMP_RATE = 1e6
TEST_TX_GAIN_DB = 5.0
TEST_RX_GAIN_DB = 10.0

USRP_ADDR = os.environ.get("USRP_ADDR", "")


def parse_result(raw: str) -> dict:
    return toons.loads(raw)


def _tools():
    """Lazy import so collection never fails when hardware tests are skipped."""
    from uhd_mcp import usrp_mcp_server
    return usrp_mcp_server


@requires_usrp
class TestDeviceDiscoveryTools:

    def test_find_devices_tool(self):
        server = _tools()
        result = parse_result(server.uhd_find_devices())
        assert result["success"] is True, f"stderr: {result.get('stderr')}"
        parsed = result["parsed_output"]
        assert parsed["total_devices"] >= 1
        assert parsed["devices"], "device list is empty despite total_devices >= 1"
        assert "addr" in parsed["devices"][0]["device_address"]

    def test_probe_tool(self):
        server = _tools()
        args = f"--args addr={USRP_ADDR}" if USRP_ADDR else ""
        result = parse_result(server.uhd_usrp_probe(args))
        assert result["success"] is True, f"stderr: {result.get('stderr')}"
        assert "Device:" in result["stdout"] or "Mboard" in result["stdout"]


@requires_usrp
class TestSiggenLifecycle:

    def test_siggen_start_list_stop(self):
        """Background siggen shows up in list_processes and stops cleanly."""
        server = _tools()
        started = parse_result(server.uhd_siggen(
            freq=TEST_FREQ_HZ,
            samp_rate=TEST_SAMP_RATE,
            gain=TEST_TX_GAIN_DB,
            amplitude=0.2,
            waveform_freq=1000,
            waveform_type="sine",
            device_args=f"addr={USRP_ADDR}" if USRP_ADDR else None,
            duration=30.0,  # safety net; we stop it manually well before
        ))
        assert started["success"] is True, f"siggen failed to start: {started}"
        process_id = started["process_id"]

        listed = server.list_processes()
        assert process_id in listed, f"{process_id} not in list_processes: {listed}"

        stopped = parse_result(server.stop_process(process_id))
        assert stopped["success"] is True, f"stop_process failed: {stopped}"

        # The registry must be empty again.
        assert server.list_processes() == "No running processes"


@requires_usrp
class TestRxCapture:

    def test_rx_cfile_capture(self, tmp_path, monkeypatch):
        """Short capture produces a file with samples in the shared data dir."""
        monkeypatch.setenv("MCP_SHARED_DATA_DIR", str(tmp_path))
        server = _tools()
        started = parse_result(server.uhd_rx_cfile(
            freq=TEST_FREQ_HZ,
            samp_rate=TEST_SAMP_RATE,
            gain=TEST_RX_GAIN_DB,
            args=f"addr={USRP_ADDR}" if USRP_ADDR else None,
            nsamples=TEST_SAMP_RATE,  # ~1 second of samples
        ))
        assert started["success"] is True, f"rx_cfile failed to start: {started}"
        process_id = started["process_id"]

        # Give the capture time to stream the requested samples.
        time.sleep(5)

        stopped = parse_result(server.stop_process(process_id))
        assert stopped["success"] is True, f"stop_process failed: {stopped}"
        assert stopped["file_created"] is True, f"no capture file: {stopped}"
        assert stopped["capture_info"]["samples_captured"] > 0
        assert os.path.dirname(stopped["output_file"]) == str(tmp_path)

    def test_cleanup_all_processes(self):
        server = _tools()
        result = server.cleanup_all_processes()
        assert "No processes" in result or "Cleaned up" in result
