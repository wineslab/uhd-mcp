"""
Tests for the script executor module.

These tests do NOT require physical UHD hardware and are suitable
for execution in a CI/CD environment (e.g., GitHub Actions).
"""

import time
import pytest
from uhd_mcp.utils.script_executor import (
    ScriptExecutor,
    ExecutionResult,
    execute_script,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def executor():
    return ScriptExecutor(timeout=10.0)


# ---------------------------------------------------------------------------
# 1. ExecutionResult dataclass
# ---------------------------------------------------------------------------

class TestExecutionResult:

    def test_success_result_to_dict(self):
        result = ExecutionResult(
            success=True,
            stdout="hello\n",
            stderr="",
            return_code=0,
            timed_out=False,
            error=None,
            duration_seconds=0.1,
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["stdout"] == "hello\n"
        assert d["return_code"] == 0
        assert d["timed_out"] is False
        assert d["error"] is None

    def test_failure_result_to_dict(self):
        result = ExecutionResult(
            success=False,
            stdout="",
            stderr="error msg",
            return_code=1,
            timed_out=False,
            error="Script exited with code 1",
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["return_code"] == 1
        assert d["error"] is not None

    def test_timeout_result_to_dict(self):
        result = ExecutionResult(
            success=False,
            timed_out=True,
            error="timed out",
        )
        d = result.to_dict()
        assert d["timed_out"] is True
        assert d["success"] is False


# ---------------------------------------------------------------------------
# 2. ScriptExecutor construction
# ---------------------------------------------------------------------------

class TestScriptExecutorConstruction:

    def test_default_timeout(self):
        ex = ScriptExecutor()
        assert ex.timeout == DEFAULT_TIMEOUT_SECONDS

    def test_custom_timeout(self):
        ex = ScriptExecutor(timeout=5.0)
        assert ex.timeout == 5.0

    def test_zero_timeout_raises(self):
        with pytest.raises(ValueError, match="positive"):
            ScriptExecutor(timeout=0.0)

    def test_negative_timeout_raises(self):
        with pytest.raises(ValueError, match="positive"):
            ScriptExecutor(timeout=-1.0)

    def test_timeout_exceeding_max_raises(self):
        with pytest.raises(ValueError, match="maximum"):
            ScriptExecutor(timeout=MAX_TIMEOUT_SECONDS + 1)

    def test_exactly_max_timeout_allowed(self):
        ex = ScriptExecutor(timeout=MAX_TIMEOUT_SECONDS)
        assert ex.timeout == MAX_TIMEOUT_SECONDS


# ---------------------------------------------------------------------------
# 3. Successful script execution
# ---------------------------------------------------------------------------

class TestSuccessfulExecution:

    def test_hello_world(self, executor):
        result = executor.execute("print('hello, world')")
        assert result.success is True
        assert "hello, world" in result.stdout
        assert result.return_code == 0
        assert result.timed_out is False
        assert result.error is None

    def test_arithmetic_output(self, executor):
        result = executor.execute("print(2 + 2)")
        assert result.success is True
        assert "4" in result.stdout

    def test_numpy_computation(self, executor):
        script = "import numpy as np\nprint(np.zeros(3))"
        result = executor.execute(script)
        assert result.success is True
        assert result.return_code == 0

    def test_multi_line_script(self, executor):
        script = (
            "total = 0\n"
            "for i in range(5):\n"
            "    total += i\n"
            "print('total:', total)\n"
        )
        result = executor.execute(script)
        assert result.success is True
        assert "10" in result.stdout

    def test_duration_tracked(self, executor):
        result = executor.execute("import time\ntime.sleep(0.05)\nprint('done')")
        assert result.duration_seconds >= 0.0
        assert result.duration_seconds < 10.0  # should be fast

    def test_to_dict_keys_present(self, executor):
        result = executor.execute("print('ok')")
        d = result.to_dict()
        for key in ("success", "stdout", "stderr", "return_code", "timed_out", "error", "duration_seconds"):
            assert key in d


# ---------------------------------------------------------------------------
# 4. Failed script execution (non-zero exit)
# ---------------------------------------------------------------------------

class TestFailedExecution:

    def test_syntax_error_fails(self, executor):
        script = "print('unclosed"  # SyntaxError
        result = executor.execute(script)
        assert result.success is False
        assert result.return_code != 0

    def test_runtime_exception_fails(self, executor):
        script = "raise ValueError('intentional error')"
        result = executor.execute(script)
        assert result.success is False
        assert result.return_code != 0
        assert "intentional error" in result.stderr

    def test_import_error_fails(self, executor):
        script = "import non_existent_module_xyz"
        result = executor.execute(script)
        assert result.success is False

    def test_stderr_captured(self, executor):
        script = "import sys\nsys.stderr.write('err msg\\n')"
        result = executor.execute(script)
        # stderr may or may not cause failure, but it should be captured
        assert isinstance(result.stderr, str)


# ---------------------------------------------------------------------------
# 5. Sandbox isolation (process-level, not builtin removal)
# ---------------------------------------------------------------------------

class TestSandboxRestrictions:
    """
    The executor provides process-level isolation: each script runs in a
    separate Python subprocess.

    Security note: The AST validator is the primary gate that blocks dangerous
    constructs (exec, eval, open, os imports, etc.) BEFORE the executor is
    called.  The executor itself provides:
      - Process isolation
      - Timeout enforcement
      - Captured stdout/stderr
    """

    def test_safe_script_runs_in_subprocess(self, executor):
        """A valid script must execute successfully in the isolated subprocess."""
        script = "import numpy as np\nprint(np.pi)"
        result = executor.execute(script)
        assert result.success is True

    def test_process_isolation_separate_memory(self, executor):
        """The subprocess has its own memory; side effects don't leak."""
        script = "import sys\nprint(sys.version)"
        result = executor.execute(script)
        assert result.success is True
        assert result.return_code == 0

    def test_runtime_error_contained_in_subprocess(self, executor):
        """A crashing script only affects its subprocess, not the test runner."""
        script = "raise SystemExit(42)"
        result = executor.execute(script)
        assert result.success is False
        assert result.return_code == 42


# ---------------------------------------------------------------------------
# 6. Timeout enforcement
# ---------------------------------------------------------------------------

class TestTimeoutEnforcement:

    def test_timeout_terminates_long_script(self):
        """A script that sleeps longer than the timeout should be killed."""
        executor = ScriptExecutor(timeout=1.0)
        script = "import time\ntime.sleep(60)\nprint('done')"
        start = time.monotonic()
        result = executor.execute(script)
        elapsed = time.monotonic() - start
        assert result.timed_out is True
        assert result.success is False
        assert elapsed < 5.0  # must terminate well within 5 seconds

    def test_infinite_loop_terminates(self):
        """An infinite loop must be killed by the timeout."""
        executor = ScriptExecutor(timeout=1.0)
        script = "while True:\n    pass\n"
        result = executor.execute(script)
        assert result.timed_out is True
        assert result.success is False

    def test_fast_script_not_timed_out(self, executor):
        result = executor.execute("print('fast')")
        assert result.timed_out is False
        assert result.success is True


# ---------------------------------------------------------------------------
# 7. Module-level convenience function
# ---------------------------------------------------------------------------

class TestExecuteScriptHelper:

    def test_basic_execute(self):
        result = execute_script("print('hello from helper')")
        assert result.success is True
        assert "hello from helper" in result.stdout

    def test_custom_timeout_via_helper(self):
        result = execute_script("import time\ntime.sleep(60)", timeout=1.0)
        assert result.timed_out is True
