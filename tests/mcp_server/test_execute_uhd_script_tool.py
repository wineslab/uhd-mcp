"""
Tests for the execute_uhd_script MCP tool interface.

These tests do NOT require physical UHD hardware and are suitable
for execution in a CI/CD environment (e.g., GitHub Actions).

The MCP tool is tested by calling it directly as a Python function
(bypassing the HTTP/MCP transport layer).
"""

import pytest
import toons
from unittest.mock import patch, MagicMock

from uhd_mcp.usrp_mcp_server import execute_uhd_script
from uhd_mcp.utils.guardrails import DEFAULT_MAX_TX_GAIN_DB, DEFAULT_MAX_FREQ_HZ, DEFAULT_MAX_SAMPLE_RATE_HZ


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def parse_result(raw: str) -> dict:
    """Decode the TOON string returned by execute_uhd_script."""
    return toons.loads(raw)


# ---------------------------------------------------------------------------
# 1. Valid script execution
# ---------------------------------------------------------------------------

class TestValidScriptExecution:

    def test_simple_print_succeeds(self):
        script = "print('hello from UHD script')"
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is True
        assert "hello from UHD script" in result["stdout"]
        assert result["timed_out"] is False

    def test_numpy_computation_succeeds(self):
        script = "import numpy as np\nprint('shape:', np.zeros(10).shape)"
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is True

    def test_returns_stage_execution_on_success(self):
        script = "print('ok')"
        result = parse_result(execute_uhd_script(script))
        assert result.get("stage") == "execution"

    def test_result_has_required_keys(self):
        script = "print('test')"
        result = parse_result(execute_uhd_script(script))
        for key in ("success", "stdout", "stderr", "return_code", "timed_out", "error", "duration_seconds"):
            assert key in result, f"Missing key: {key}"

    def test_metadata_none_accepted(self):
        script = "print('metadata is optional')"
        result = parse_result(execute_uhd_script(script, metadata=None))
        assert result["success"] is True

    def test_empty_metadata_accepted(self):
        script = "print('empty metadata')"
        result = parse_result(execute_uhd_script(script, metadata={}))
        assert result["success"] is True

    def test_valid_metadata_with_safe_params(self):
        script = "print('safe params')"
        metadata = {"gain": 20.0, "freq": 915e6, "sample_rate": 1e6, "duration": 5.0}
        result = parse_result(execute_uhd_script(script, metadata=metadata))
        assert result["success"] is True

    def test_custom_timeout_in_metadata(self):
        script = "print('custom timeout')"
        result = parse_result(execute_uhd_script(script, metadata={"timeout": 5.0}))
        assert result["success"] is True


# ---------------------------------------------------------------------------
# 2. Script validation failures
# ---------------------------------------------------------------------------

class TestScriptValidationFailures:

    def test_forbidden_import_os_rejected(self):
        script = "import os\nos.system('ls')"
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is False
        assert result["stage"] == "validation"
        assert "os" in result["error"].lower() or "forbidden" in result["error"].lower()

    def test_forbidden_import_subprocess_rejected(self):
        script = "import subprocess\nsubprocess.run(['ls'])"
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is False
        assert result["stage"] == "validation"

    def test_eval_call_rejected(self):
        script = "result = eval('2+2')"
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is False
        assert result["stage"] == "validation"

    def test_open_file_rejected(self):
        script = "f = open('/etc/passwd')"
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is False
        assert result["stage"] == "validation"

    def test_dynamic_import_rejected(self):
        script = "mod = __import__('os')"
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is False
        assert result["stage"] == "validation"

    def test_syntax_error_rejected(self):
        script = "def broken("
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is False
        assert result["stage"] == "validation"

    def test_empty_script_rejected(self):
        result = parse_result(execute_uhd_script(""))
        assert result["success"] is False
        assert result["stage"] == "validation"

    def test_validation_failure_does_not_execute(self):
        """When validation fails the executor must not be called."""
        script = "import os\nos.system('touch /tmp/pwned')"
        with patch("uhd_mcp.usrp_mcp_server.ScriptExecutor") as mock_executor_cls:
            parse_result(execute_uhd_script(script))
            mock_executor_cls.assert_not_called()


# ---------------------------------------------------------------------------
# 3. Guardrail failures
# ---------------------------------------------------------------------------

class TestGuardrailFailures:

    def test_excessive_gain_in_script_rejected(self):
        script = f"usrp.set_tx_gain({DEFAULT_MAX_TX_GAIN_DB + 5})\n"
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is False
        assert result["stage"] == "guardrails"

    def test_excessive_gain_in_metadata_rejected(self):
        script = "print('test')"
        metadata = {"gain": DEFAULT_MAX_TX_GAIN_DB + 10}
        result = parse_result(execute_uhd_script(script, metadata=metadata))
        assert result["success"] is False
        assert result["stage"] == "guardrails"

    def test_freq_too_high_in_metadata_rejected(self):
        script = "print('test')"
        metadata = {"freq": DEFAULT_MAX_FREQ_HZ + 1e9}
        result = parse_result(execute_uhd_script(script, metadata=metadata))
        assert result["success"] is False
        assert result["stage"] == "guardrails"

    def test_sample_rate_too_high_in_metadata_rejected(self):
        script = "print('test')"
        metadata = {"sample_rate": DEFAULT_MAX_SAMPLE_RATE_HZ * 10}
        result = parse_result(execute_uhd_script(script, metadata=metadata))
        assert result["success"] is False
        assert result["stage"] == "guardrails"

    def test_duration_zero_in_metadata_rejected(self):
        script = "print('test')"
        metadata = {"duration": 0.0}
        result = parse_result(execute_uhd_script(script, metadata=metadata))
        assert result["success"] is False
        assert result["stage"] == "guardrails"

    def test_guardrail_failure_does_not_execute(self):
        """When a guardrail is violated the executor must not be called."""
        script = f"usrp.set_tx_gain({DEFAULT_MAX_TX_GAIN_DB + 5})\n"
        with patch("uhd_mcp.usrp_mcp_server.ScriptExecutor") as mock_executor_cls:
            parse_result(execute_uhd_script(script))
            mock_executor_cls.assert_not_called()


# ---------------------------------------------------------------------------
# 4. Timeout handling via metadata
# ---------------------------------------------------------------------------

class TestTimeoutHandling:

    def test_timeout_from_metadata_respected(self):
        """A script that sleeps longer than metadata timeout must time out."""
        script = "import time\ntime.sleep(60)\nprint('done')"
        result = parse_result(execute_uhd_script(script, metadata={"timeout": 1.0}))
        assert result["timed_out"] is True
        assert result["success"] is False

    def test_invalid_timeout_falls_back_to_default(self):
        """Non-numeric timeout in metadata should fall back to the default."""
        script = "print('ok')"
        result = parse_result(execute_uhd_script(script, metadata={"timeout": "not_a_number"}))
        assert result["success"] is True  # script should still run with default timeout

    def test_timeout_clamped_to_max(self):
        """Timeout exceeding MAX_TIMEOUT_SECONDS should be clamped, not rejected."""
        from uhd_mcp.utils.script_executor import MAX_TIMEOUT_SECONDS
        script = "print('clamped')"
        # Requesting 10× max – should be clamped and script should succeed
        result = parse_result(execute_uhd_script(script, metadata={"timeout": MAX_TIMEOUT_SECONDS * 10}))
        assert result["success"] is True


# ---------------------------------------------------------------------------
# 5. Error propagation
# ---------------------------------------------------------------------------

class TestErrorPropagation:

    def test_runtime_error_captured(self):
        """A script that raises an exception should fail gracefully."""
        script = "raise RuntimeError('deliberate error')"
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is False
        assert result["stage"] == "execution"
        assert result["return_code"] is not None

    def test_error_field_set_on_failure(self):
        script = "raise ValueError('bad value')"
        result = parse_result(execute_uhd_script(script))
        assert result["error"] is not None

    def test_successful_stdout_returned(self):
        script = "print('output line 1')\nprint('output line 2')"
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is True
        assert "output line 1" in result["stdout"]
        assert "output line 2" in result["stdout"]

    def test_script_stderr_returned(self):
        script = "import sys\nsys.stderr.write('err line\\n')"
        result = parse_result(execute_uhd_script(script))
        assert isinstance(result["stderr"], str)

    def test_return_code_zero_on_success(self):
        result = parse_result(execute_uhd_script("print('ok')"))
        assert result["return_code"] == 0

    def test_return_code_nonzero_on_failure(self):
        result = parse_result(execute_uhd_script("raise SystemExit(2)"))
        assert result["return_code"] != 0
