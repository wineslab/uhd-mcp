"""
Hardware integration tests for the execute_uhd_script feature.

⚠️  THESE TESTS REQUIRE PHYSICAL UHD HARDWARE ⚠️

These tests will be SKIPPED automatically if:
- The environment variable USRP_HW_TESTS is not set to "1"
- OR no UHD device is reachable (uhd_find_devices returns no devices)

Do NOT include these tests in standard CI runs against GitHub Actions runners
that do not have USRP hardware attached.

Usage with hardware:
    USRP_HW_TESTS=1 pytest tests/hardware/test_hardware_integration.py -v
"""

import os
import toons
import time
import pytest
import subprocess


# ---------------------------------------------------------------------------
# Skip marker – guard ALL tests in this file
# ---------------------------------------------------------------------------

HW_TESTS_ENABLED = os.environ.get("USRP_HW_TESTS", "0") == "1"

pytestmark = pytest.mark.skipif(
    not HW_TESTS_ENABLED,
    reason="Hardware tests disabled. Set USRP_HW_TESTS=1 to enable.",
)


# ---------------------------------------------------------------------------
# Additional runtime check: is a USRP actually reachable?
# ---------------------------------------------------------------------------

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


requires_usrp = pytest.mark.skipif(
    not _usrp_available(),
    reason="No UHD device found. Skipping hardware test.",
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def parse_result(raw: str) -> dict:
    return toons.loads(raw)


# ---------------------------------------------------------------------------
# Import tool here (lazy so that missing imports don't break the rest of
# the test suite when hardware tests are skipped at collection time).
# ---------------------------------------------------------------------------

def _get_tool():
    from uhd_mcp.usrp_mcp_server import execute_uhd_script
    return execute_uhd_script


# ---------------------------------------------------------------------------
# 1. Device discovery via script
# ---------------------------------------------------------------------------

@requires_usrp
class TestHardwareDeviceDiscovery:

    def test_find_devices_via_script(self):
        """A script that prints UHD device info should succeed."""
        execute_uhd_script = _get_tool()
        script = (
            "import uhd\n"
            "devices = uhd.find('', find_all=True)\n"
            "print('Found devices:', len(devices))\n"
            "for dev in devices:\n"
            "    print(' -', dev)\n"
        )
        result = parse_result(execute_uhd_script(script, metadata={"timeout": 30}))
        assert result["success"] is True, f"stderr: {result.get('stderr')}"
        assert "Found devices" in result["stdout"]


# ---------------------------------------------------------------------------
# 2. Basic RX operation
# ---------------------------------------------------------------------------

@requires_usrp
class TestHardwareRxOperation:

    def test_rx_samples_script(self):
        """Receive a small number of samples and print the count."""
        execute_uhd_script = _get_tool()
        script = (
            "import uhd\n"
            "import numpy as np\n"
            "\n"
            "NUM_SAMPS = 1024\n"
            "FREQ      = 915e6\n"
            "RATE      = 1e6\n"
            "GAIN      = 10.0\n"
            "\n"
            "usrp = uhd.usrp.MultiUSRP()\n"
            "usrp.set_rx_rate(RATE, 0)\n"
            "usrp.set_rx_freq(uhd.libpyuhd.types.tune_request(FREQ), 0)\n"
            "usrp.set_rx_gain(GAIN, 0)\n"
            "\n"
            "st_args = uhd.usrp.StreamArgs('fc32', 'sc16')\n"
            "st_args.channels = [0]\n"
            "metadata = uhd.types.RXMetadata()\n"
            "streamer = usrp.get_rx_stream(st_args)\n"
            "recv_buffer = np.zeros((1, NUM_SAMPS), dtype=np.complex64)\n"
            "\n"
            "stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.num_done)\n"
            "stream_cmd.num_samps = NUM_SAMPS\n"
            "stream_cmd.stream_now = True\n"
            "streamer.issue_stream_cmd(stream_cmd)\n"
            "\n"
            "num_rx_samps = streamer.recv(recv_buffer, metadata, 3.0)\n"
            "print('Received samples:', num_rx_samps)\n"
        )
        result = parse_result(execute_uhd_script(script, metadata={"timeout": 30}))
        assert result["success"] is True, f"stderr: {result.get('stderr')}"
        assert "Received samples: 1024" in result["stdout"]


# ---------------------------------------------------------------------------
# 3. Hardware guardrail enforcement (safe values)
# ---------------------------------------------------------------------------

@requires_usrp
class TestHardwareGuardrailSafe:

    def test_safe_gain_accepted_and_applied(self):
        """A script with a safe gain value should execute on real hardware."""
        execute_uhd_script = _get_tool()
        script = (
            "import uhd\n"
            "usrp = uhd.usrp.MultiUSRP()\n"
            "usrp.set_rx_gain(10.0, 0)\n"
            "actual = usrp.get_rx_gain(0)\n"
            "print('Applied gain:', actual)\n"
        )
        result = parse_result(execute_uhd_script(script, metadata={"timeout": 20}))
        assert result["success"] is True, f"stderr: {result.get('stderr')}"

    def test_safe_frequency_accepted(self):
        execute_uhd_script = _get_tool()
        script = (
            "import uhd\n"
            "usrp = uhd.usrp.MultiUSRP()\n"
            "usrp.set_rx_freq(uhd.libpyuhd.types.tune_request(915e6), 0)\n"
            "actual = usrp.get_rx_freq(0)\n"
            "print('Tuned to:', actual)\n"
        )
        result = parse_result(execute_uhd_script(script, metadata={"timeout": 20}))
        assert result["success"] is True, f"stderr: {result.get('stderr')}"


# ---------------------------------------------------------------------------
# 4. Hardware guardrail enforcement (unsafe values should be rejected)
# ---------------------------------------------------------------------------

class TestHardwareGuardrailUnsafe:
    """
    These tests verify that unsafe parameter values are caught by guardrails
    BEFORE the script reaches the hardware. No actual hardware call is made.
    They do NOT require physical hardware, but are grouped here to document
    the hardware-safety intent.
    """

    def test_excessive_tx_gain_rejected_before_hw(self):
        from uhd_mcp.usrp_mcp_server import execute_uhd_script
        from uhd_mcp.utils.guardrails import DEFAULT_MAX_TX_GAIN_DB
        script = f"usrp.set_tx_gain({DEFAULT_MAX_TX_GAIN_DB + 20})\n"
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is False
        assert result["stage"] == "guardrails"

    def test_excessive_freq_rejected_before_hw(self):
        from uhd_mcp.usrp_mcp_server import execute_uhd_script
        from uhd_mcp.utils.guardrails import DEFAULT_MAX_FREQ_HZ
        script = "print('test')"
        metadata = {"freq": DEFAULT_MAX_FREQ_HZ * 10}
        result = parse_result(execute_uhd_script(script, metadata=metadata))
        assert result["success"] is False
        assert result["stage"] == "guardrails"


# ---------------------------------------------------------------------------
# 5. End-to-end: forbidden script must not reach hardware
# ---------------------------------------------------------------------------

class TestForbiddenScriptDoesNotReachHardware:
    """
    Verifies that scripts rejected at the validation/guardrails stage do NOT
    reach the hardware executor. This is important for hardware safety.
    These tests do not require physical hardware.
    """

    def test_os_import_rejected_before_execution(self):
        from uhd_mcp.usrp_mcp_server import execute_uhd_script
        script = "import os\nos.system('echo hello')"
        result = parse_result(execute_uhd_script(script))
        assert result["stage"] == "validation"
        assert result["success"] is False

    def test_subprocess_rejected_before_execution(self):
        from uhd_mcp.usrp_mcp_server import execute_uhd_script
        script = "import subprocess\nsubprocess.call(['id'])"
        result = parse_result(execute_uhd_script(script))
        assert result["stage"] == "validation"
        assert result["success"] is False
