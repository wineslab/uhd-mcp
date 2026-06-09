"""
Script Executor for UHD MCP Server

Provides a sandboxed execution environment for agent-generated UHD scripts.
Scripts are executed in a subprocess with:
 - A timeout-based kill switch
 - Process-level isolation (separate Python process)
 - Captured stdout/stderr
 - A structured result object

Security note: The primary safety gate is the AST-based validator in
script_validator.py.  The executor provides process isolation and timeout
enforcement. It does NOT attempt to modify Python's builtins because doing
so would break standard library packages (e.g., numpy depends on open()).
"""

import subprocess
import sys
import os
import tempfile
import time
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default execution timeout in seconds
DEFAULT_TIMEOUT_SECONDS: float = 30.0

# Maximum allowed timeout that callers may request
MAX_TIMEOUT_SECONDS: float = 300.0  # 5 minutes

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


class ExecutionResult:
    """Structured result returned by ScriptExecutor.execute()."""

    def __init__(
        self,
        success: bool,
        stdout: str = "",
        stderr: str = "",
        return_code: Optional[int] = None,
        timed_out: bool = False,
        error: Optional[str] = None,
        duration_seconds: float = 0.0,
    ):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code
        self.timed_out = timed_out
        self.error = error
        self.duration_seconds = duration_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_code": self.return_code,
            "timed_out": self.timed_out,
            "error": self.error,
            "duration_seconds": round(self.duration_seconds, 4),
        }


# ---------------------------------------------------------------------------
# Sandboxed execution wrapper (injected at the top of every script)
# ---------------------------------------------------------------------------

# This wrapper is prepended to the user script to restrict the built-in
# namespace before the user code runs.
_SANDBOX_PREAMBLE = ""


# ---------------------------------------------------------------------------
# ScriptExecutor
# ---------------------------------------------------------------------------


class ScriptExecutor:
    """
    Executes a validated UHD script in a sandboxed subprocess.

    Isolation mechanism:
    - Runs the script as a separate Python process (subprocess.run).
    - The subprocess gets a clean environment with only PATH / HOME kept,
      unless *full_env* is True (used by the unsafe execution path).
    - The subprocess is killed after *timeout* seconds.

    Note: This class does NOT re-validate the script. Call the validator and
    guardrails checks *before* calling execute().
    """

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        extra_env: Optional[Dict[str, str]] = None,
        full_env: bool = False,
    ):
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if timeout > MAX_TIMEOUT_SECONDS:
            raise ValueError(
                f"timeout {timeout}s exceeds maximum allowed {MAX_TIMEOUT_SECONDS}s"
            )
        self.timeout = timeout
        self.extra_env = extra_env or {}
        # When True, the subprocess inherits the full parent environment instead
        # of the minimal restricted one. Only used by the unsafe execution path.
        self.full_env = full_env

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, script: str) -> ExecutionResult:
        """
        Execute *script* in an isolated subprocess.

        Returns an ExecutionResult with stdout, stderr, return_code, and
        whether execution timed out.
        """
        # Write to a temp file so we don't pass arbitrary code via shell args
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".py",
                delete=False,
                encoding="utf-8",
            ) as tmp:
                tmp.write(script)
                tmp_path = tmp.name

            env = self._build_env()
            start = time.monotonic()

            try:
                result = subprocess.run(
                    [sys.executable, tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    env=env,
                )
                elapsed = time.monotonic() - start

                success = result.returncode == 0
                return ExecutionResult(
                    success=success,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    return_code=result.returncode,
                    timed_out=False,
                    error=None if success else f"Script exited with code {result.returncode}",
                    duration_seconds=elapsed,
                )

            except subprocess.TimeoutExpired:
                elapsed = time.monotonic() - start
                logger.warning("Script execution timed out after %.1fs", self.timeout)
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr="",
                    return_code=None,
                    timed_out=True,
                    error=f"Script execution timed out after {self.timeout} seconds",
                    duration_seconds=elapsed,
                )

        except Exception as exc:  # pragma: no cover
            logger.exception("Unexpected error during script execution")
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                return_code=None,
                timed_out=False,
                error=str(exc),
                duration_seconds=0.0,
            )
        finally:
            if tmp is not None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_env(self) -> Dict[str, str]:
        """Build the environment for the subprocess.

        In the default (restricted) mode only a minimal whitelist is kept. When
        *full_env* is set the subprocess inherits the complete parent
        environment (unsafe mode), lifting the I/O environment restriction.
        """
        if self.full_env:
            env = os.environ.copy()
            env.update(self.extra_env)
            return env
        clean_env: Dict[str, str] = {}
        # Keep only PATH and HOME so standard Python can find itself
        for key in ("PATH", "HOME", "PYTHONPATH", "VIRTUAL_ENV"):
            if key in os.environ:
                clean_env[key] = os.environ[key]
        clean_env.update(self.extra_env)
        return clean_env


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------


def execute_script(
    script: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    full_env: bool = False,
) -> ExecutionResult:
    """Execute *script* with the given timeout using a default ScriptExecutor."""
    executor = ScriptExecutor(timeout=timeout, full_env=full_env)
    return executor.execute(script)
