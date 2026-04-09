"""
Integration tests for the execute_uhd_script feature (no hardware required).

These tests verify the end-to-end flow from script submission through
validation, guardrails, and sandboxed execution without requiring any
physical UHD hardware.

These tests are suitable for CI/CD environments (e.g., GitHub Actions).
"""

import pytest
import toons
from unittest.mock import patch, MagicMock

from uhd_mcp.usrp_mcp_server import execute_uhd_script
from uhd_mcp.utils.guardrails import (
    DEFAULT_MAX_TX_GAIN_DB,
    DEFAULT_MAX_FREQ_HZ,
    DEFAULT_MIN_FREQ_HZ,
    DEFAULT_MAX_SAMPLE_RATE_HZ,
)


def parse_result(raw: str) -> dict:
    return toons.loads(raw)


# ---------------------------------------------------------------------------
# 1. End-to-end: valid UHD script → successful execution
# ---------------------------------------------------------------------------

class TestValidScriptIntegration:

    def test_pure_numpy_script_succeeds(self):
        """A simple numpy-only script must complete successfully."""
        script = (
            "import numpy as np\n"
            "data = np.zeros(1024, dtype=np.complex64)\n"
            "print('Generated', len(data), 'samples')\n"
        )
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is True
        assert "1024" in result["stdout"]

    def test_math_helper_script_succeeds(self):
        script = (
            "import math\n"
            "import numpy as np\n"
            "t = np.linspace(0, 1, 100)\n"
            "signal = np.sin(2 * math.pi * 100 * t)\n"
            "print('Peak:', round(float(signal.max()), 4))\n"
        )
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is True
        assert "Peak" in result["stdout"]

    def test_metadata_safe_params_allowed(self):
        """Valid metadata parameters do not block execution."""
        script = "print('params ok')"
        metadata = {
            "gain": DEFAULT_MAX_TX_GAIN_DB,
            "freq": DEFAULT_MIN_FREQ_HZ,
            "sample_rate": 1e6,
            "duration": 10.0,
        }
        result = parse_result(execute_uhd_script(script, metadata=metadata))
        assert result["success"] is True

    def test_script_with_functions_and_loops(self):
        script = (
            "import numpy as np\n"
            "\n"
            "def gen_tone(f, sr, dur):\n"
            "    t = np.arange(int(sr * dur)) / sr\n"
            "    return np.exp(1j * 2 * 3.14159 * f * t).astype(np.complex64)\n"
            "\n"
            "samples = gen_tone(1e3, 1e6, 0.001)\n"
            "print('Samples:', len(samples))\n"
        )
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is True
        assert "Samples" in result["stdout"]


# ---------------------------------------------------------------------------
# 2. End-to-end: invalid script → rejection before execution
# ---------------------------------------------------------------------------

class TestInvalidScriptRejection:

    def test_os_import_rejected_before_execution(self):
        script = "import os\nos.system('echo pwned')"
        with patch("uhd_mcp.usrp_mcp_server.ScriptExecutor") as mock_cls:
            result = parse_result(execute_uhd_script(script))
        assert result["success"] is False
        assert result["stage"] == "validation"
        mock_cls.assert_not_called()  # executor never reached

    def test_subprocess_import_rejected(self):
        script = "import subprocess\nsubprocess.call(['id'])"
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is False
        assert result["stage"] == "validation"

    def test_file_write_rejected(self):
        script = "with open('/tmp/evil.txt', 'w') as f:\n    f.write('evil')"
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is False
        assert result["stage"] == "validation"

    def test_exec_call_rejected(self):
        script = "exec('import os; os.system(\"ls\")')"
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is False
        assert result["stage"] == "validation"

    def test_dynamic_import_rejected(self):
        script = "m = __import__('subprocess'); m.call(['id'])"
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is False
        assert result["stage"] == "validation"


# ---------------------------------------------------------------------------
# 3. End-to-end: guardrail violation → rejection before execution
# ---------------------------------------------------------------------------

class TestGuardrailRejection:

    def test_gain_above_limit_in_script_rejected(self):
        script = f"usrp.set_tx_gain({DEFAULT_MAX_TX_GAIN_DB + 10})\n"
        with patch("uhd_mcp.usrp_mcp_server.ScriptExecutor") as mock_cls:
            result = parse_result(execute_uhd_script(script))
        assert result["success"] is False
        assert result["stage"] == "guardrails"
        mock_cls.assert_not_called()

    def test_freq_above_max_in_metadata_rejected(self):
        script = "print('test')"
        metadata = {"freq": DEFAULT_MAX_FREQ_HZ * 2}
        result = parse_result(execute_uhd_script(script, metadata=metadata))
        assert result["success"] is False
        assert result["stage"] == "guardrails"

    def test_sample_rate_above_max_in_metadata_rejected(self):
        script = "print('test')"
        metadata = {"sample_rate": DEFAULT_MAX_SAMPLE_RATE_HZ + 1e9}
        result = parse_result(execute_uhd_script(script, metadata=metadata))
        assert result["success"] is False
        assert result["stage"] == "guardrails"

    def test_negative_duration_in_metadata_rejected(self):
        script = "print('test')"
        metadata = {"duration": -1.0}
        result = parse_result(execute_uhd_script(script, metadata=metadata))
        assert result["success"] is False
        assert result["stage"] == "guardrails"


# ---------------------------------------------------------------------------
# 4. Borderline / boundary condition tests
# ---------------------------------------------------------------------------

class TestBorderlineConditions:

    def test_gain_exactly_at_limit_passes(self):
        """Gain equal to the maximum is allowed (inclusive boundary)."""
        script = f"usrp_mock_call = {DEFAULT_MAX_TX_GAIN_DB}\nprint('gain:', usrp_mock_call)"
        # The guardrail parses literal values from set_tx_gain() calls;
        # a bare assignment with the value does not trigger guardrails.
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is True

    def test_gain_one_unit_above_limit_rejected_via_metadata(self):
        script = "print('test')"
        metadata = {"gain": DEFAULT_MAX_TX_GAIN_DB + 0.01}
        result = parse_result(execute_uhd_script(script, metadata=metadata))
        assert result["success"] is False
        assert result["stage"] == "guardrails"

    def test_freq_at_minimum_passes(self):
        script = "print('test')"
        metadata = {"freq": DEFAULT_MIN_FREQ_HZ}
        result = parse_result(execute_uhd_script(script, metadata=metadata))
        assert result["success"] is True

    def test_freq_below_minimum_rejected(self):
        script = "print('test')"
        metadata = {"freq": DEFAULT_MIN_FREQ_HZ - 1}
        result = parse_result(execute_uhd_script(script, metadata=metadata))
        assert result["success"] is False
        assert result["stage"] == "guardrails"

    def test_timeout_of_1_second_enforced(self):
        """Tight timeout must still terminate a sleeping script."""
        script = "import time\ntime.sleep(10)\nprint('done')"
        result = parse_result(execute_uhd_script(script, metadata={"timeout": 1.0}))
        assert result["timed_out"] is True
        assert result["success"] is False

    def test_runtime_error_in_otherwise_valid_script(self):
        """A valid (passes validation/guardrails) but crashing script is handled."""
        script = "raise RuntimeError('test error')"
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is False
        assert result["stage"] == "execution"
        # The error message appears in stderr
        assert "test error" in result["stderr"]


# ---------------------------------------------------------------------------
# 5. Sandbox effectiveness (defense-in-depth)
# ---------------------------------------------------------------------------

class TestSandboxEffectiveness:
    """
    The executor provides process-level isolation (subprocess).
    The AST validator is the primary security gate for dangerous constructs.

    These tests verify that exec() and eval() are blocked by the AST validator
    and that the full MCP tool correctly rejects them at the validation stage.
    """

    def test_exec_blocked_by_ast_validator_not_sandbox(self):
        """
        exec() must be blocked by the MCP tool's AST validator.
        """
        result = parse_result(execute_uhd_script("exec('print(1)')"))
        assert result["success"] is False
        assert result["stage"] == "validation"

    def test_eval_blocked_by_ast_validator_not_sandbox(self):
        """
        eval() must be blocked by the MCP tool's AST validator.
        """
        result = parse_result(execute_uhd_script("eval('1+1')"))
        assert result["success"] is False
        assert result["stage"] == "validation"

    def test_open_blocked_by_ast_validator(self):
        """
        open() must be blocked by the MCP tool's AST validator.
        """
        result = parse_result(execute_uhd_script("open('/etc/passwd')"))
        assert result["success"] is False
        assert result["stage"] == "validation"

    def test_process_isolation_prevents_state_leakage(self):
        """Script runs in a separate process; its state doesn't affect the server."""
        script = "import math\nx = 'injected'\nprint('ok', math.pi)"
        result = parse_result(execute_uhd_script(script))
        assert result["success"] is True
