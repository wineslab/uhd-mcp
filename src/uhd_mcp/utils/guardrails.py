"""
Guardrails for UHD Script Execution

Enforces hardware safety constraints on UHD scripts before execution.
Scans scripts for UHD API calls that exceed defined parameter limits.
"""

import ast
from typing import Optional, Dict, Any

# ---------------------------------------------------------------------------
# Default policy limits (can be overridden per deployment)
# ---------------------------------------------------------------------------

# Maximum TX gain in dB
DEFAULT_MAX_TX_GAIN_DB: float = 31.5

# Frequency bounds in Hz
DEFAULT_MIN_FREQ_HZ: float = 1e6        # 1 MHz
DEFAULT_MAX_FREQ_HZ: float = 6e9        # 6 GHz

# Sample rate bounds in Hz
DEFAULT_MIN_SAMPLE_RATE_HZ: float = 1e3    # 1 kHz
DEFAULT_MAX_SAMPLE_RATE_HZ: float = 56e6   # 56 MHz (B200/B210 max)

# Maximum transmission (stream) duration in seconds
DEFAULT_MAX_DURATION_SECONDS: float = 3600.0  # 1 hour

# ---------------------------------------------------------------------------
# Guardrail policy dataclass
# ---------------------------------------------------------------------------

class GuardrailPolicy:
    """
    Configurable policy for UHD parameter guardrails.

    All limits have sensible defaults; override any field for deployment-
    specific constraints.
    """

    def __init__(
        self,
        max_tx_gain_db: float = DEFAULT_MAX_TX_GAIN_DB,
        min_freq_hz: float = DEFAULT_MIN_FREQ_HZ,
        max_freq_hz: float = DEFAULT_MAX_FREQ_HZ,
        min_sample_rate_hz: float = DEFAULT_MIN_SAMPLE_RATE_HZ,
        max_sample_rate_hz: float = DEFAULT_MAX_SAMPLE_RATE_HZ,
        max_duration_seconds: float = DEFAULT_MAX_DURATION_SECONDS,
    ):
        self.max_tx_gain_db = max_tx_gain_db
        self.min_freq_hz = min_freq_hz
        self.max_freq_hz = max_freq_hz
        self.min_sample_rate_hz = min_sample_rate_hz
        self.max_sample_rate_hz = max_sample_rate_hz
        self.max_duration_seconds = max_duration_seconds


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class GuardrailViolation(Exception):
    """Raised when a script or parameter set violates a guardrail policy."""
    pass


# ---------------------------------------------------------------------------
# Keyword mappings: UHD API set_* call → parameter kind
# ---------------------------------------------------------------------------

# Map keyword argument names used in common UHD Python bindings to a
# semantic category that the guardrails know about.
_GAIN_KWARGS = frozenset({"gain"})
_FREQ_KWARGS = frozenset({"freq", "frequency", "center_freq", "tune_request"})
_RATE_KWARGS = frozenset({"rate", "samp_rate", "sample_rate"})
_DURATION_KWARGS = frozenset({"duration", "tx_duration", "recv_timeout"})

# Positional argument index in common UHD call signatures:
#   usrp.set_tx_gain(gain, chan=0)     → arg 0 is gain
#   usrp.set_rx_freq(freq, chan=0)     → arg 0 is freq
#   usrp.set_tx_rate(rate, chan=0)     → arg 0 is rate
_GAIN_METHODS = frozenset({"set_tx_gain", "set_rx_gain"})
_FREQ_METHODS = frozenset({
    "set_tx_freq", "set_rx_freq",
    "set_center_freq",
})
_RATE_METHODS = frozenset({"set_tx_rate", "set_rx_rate"})


# ---------------------------------------------------------------------------
# Helper: extract a numeric literal from an AST node (best-effort)
# ---------------------------------------------------------------------------

def _ast_numeric_value(node: ast.AST) -> Optional[float]:
    """
    Return the numeric value of an AST expression node, or None if it
    cannot be statically determined.

    Handles:
    - Integer and float literals
    - Unary minus applied to a literal
    - Scientific-notation literals that Python already parses as floats
    - Simple constant names like 1e9 (already floats after parsing)
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    # Unary minus:  -31.5
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.USub)
        and isinstance(node.operand, ast.Constant)
        and isinstance(node.operand.value, (int, float))
    ):
        return -float(node.operand.value)
    return None


# ---------------------------------------------------------------------------
# Main guardrails class
# ---------------------------------------------------------------------------

class Guardrails:
    """
    Scans UHD scripts for parameter violations against a policy.

    Works by walking the script's AST and checking arguments passed to
    known UHD API methods (set_tx_gain, set_tx_freq, set_tx_rate, etc.)
    against the configured policy limits.
    """

    def __init__(self, policy: Optional[GuardrailPolicy] = None):
        self.policy = policy or GuardrailPolicy()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_script(self, script: str) -> None:
        """
        Parse *script* and raise GuardrailViolation on the first violation.

        This method is intentionally conservative: if a numeric value
        cannot be determined statically, the call is silently ignored
        (dynamic values are caught at runtime via check_params).
        """
        try:
            tree = ast.parse(script, mode="exec")
        except SyntaxError:
            # Syntax errors are the validator's responsibility; ignore here.
            return

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            method_name = self._extract_method_name(node)
            if method_name is None:
                continue

            # Extract the first positional argument (value argument)
            first_arg_value: Optional[float] = None
            if node.args:
                first_arg_value = _ast_numeric_value(node.args[0])

            if method_name in _GAIN_METHODS:
                # Also check keyword arg "gain="
                gain = first_arg_value or self._kwarg_value(node, _GAIN_KWARGS)
                if gain is not None:
                    self._check_gain(gain, getattr(node, "lineno", "?"))

            elif method_name in _FREQ_METHODS:
                freq = first_arg_value or self._kwarg_value(node, _FREQ_KWARGS)
                if freq is not None:
                    self._check_freq(freq, getattr(node, "lineno", "?"))

            elif method_name in _RATE_METHODS:
                rate = first_arg_value or self._kwarg_value(node, _RATE_KWARGS)
                if rate is not None:
                    self._check_rate(rate, getattr(node, "lineno", "?"))

    def check_params(self, params: Dict[str, Any]) -> None:
        """
        Validate a dictionary of execution parameters (e.g. from metadata).

        Accepted keys (all optional):
            gain          – TX gain in dB
            freq          – center frequency in Hz
            sample_rate   – sample rate in Hz
            duration      – transmission duration in seconds

        Raises GuardrailViolation on the first violation found.
        """
        if "gain" in params and params["gain"] is not None:
            self._check_gain(float(params["gain"]), "metadata")
        if "freq" in params and params["freq"] is not None:
            self._check_freq(float(params["freq"]), "metadata")
        if "sample_rate" in params and params["sample_rate"] is not None:
            self._check_rate(float(params["sample_rate"]), "metadata")
        if "duration" in params and params["duration"] is not None:
            self._check_duration(float(params["duration"]), "metadata")

    # ------------------------------------------------------------------
    # Private checkers
    # ------------------------------------------------------------------

    def _check_gain(self, gain: float, location: Any) -> None:
        if gain > self.policy.max_tx_gain_db:
            raise GuardrailViolation(
                f"[{location}] TX gain {gain} dB exceeds maximum allowed "
                f"{self.policy.max_tx_gain_db} dB."
            )

    def _check_freq(self, freq: float, location: Any) -> None:
        if freq < self.policy.min_freq_hz:
            raise GuardrailViolation(
                f"[{location}] Frequency {freq} Hz is below minimum allowed "
                f"{self.policy.min_freq_hz} Hz."
            )
        if freq > self.policy.max_freq_hz:
            raise GuardrailViolation(
                f"[{location}] Frequency {freq} Hz exceeds maximum allowed "
                f"{self.policy.max_freq_hz} Hz."
            )

    def _check_rate(self, rate: float, location: Any) -> None:
        if rate < self.policy.min_sample_rate_hz:
            raise GuardrailViolation(
                f"[{location}] Sample rate {rate} Hz is below minimum allowed "
                f"{self.policy.min_sample_rate_hz} Hz."
            )
        if rate > self.policy.max_sample_rate_hz:
            raise GuardrailViolation(
                f"[{location}] Sample rate {rate} Hz exceeds maximum allowed "
                f"{self.policy.max_sample_rate_hz} Hz."
            )

    def _check_duration(self, duration: float, location: Any) -> None:
        if duration <= 0:
            raise GuardrailViolation(
                f"[{location}] Duration {duration} seconds must be positive."
            )
        if duration > self.policy.max_duration_seconds:
            raise GuardrailViolation(
                f"[{location}] Duration {duration} seconds exceeds maximum allowed "
                f"{self.policy.max_duration_seconds} seconds."
            )

    # ------------------------------------------------------------------
    # AST helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_method_name(call_node: ast.Call) -> Optional[str]:
        """Return the attribute (method) name of a call node, if any."""
        if isinstance(call_node.func, ast.Attribute):
            return call_node.func.attr
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        return None

    @staticmethod
    def _kwarg_value(call_node: ast.Call, kwarg_names: frozenset) -> Optional[float]:
        """Extract a numeric value from keyword arguments matching kwarg_names."""
        for kw in call_node.keywords:
            if kw.arg in kwarg_names:
                return _ast_numeric_value(kw.value)
        return None


# ---------------------------------------------------------------------------
# Module-level convenience instance
# ---------------------------------------------------------------------------

_default_guardrails = Guardrails()


def check_script_guardrails(script: str) -> None:
    """Check a script against the default guardrails policy."""
    _default_guardrails.check_script(script)


def check_params_guardrails(params: Dict[str, Any]) -> None:
    """Check a parameter dict against the default guardrails policy."""
    _default_guardrails.check_params(params)
