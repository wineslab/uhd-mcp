"""
Tests for the guardrails module.

These tests do NOT require physical UHD hardware and are suitable
for execution in a CI/CD environment (e.g., GitHub Actions).
"""

import pytest
from uhd_mcp.utils.guardrails import (
    Guardrails,
    GuardrailPolicy,
    GuardrailViolation,
    check_script_guardrails,
    check_params_guardrails,
    DEFAULT_MAX_TX_GAIN_DB,
    DEFAULT_MIN_FREQ_HZ,
    DEFAULT_MAX_FREQ_HZ,
    DEFAULT_MIN_SAMPLE_RATE_HZ,
    DEFAULT_MAX_SAMPLE_RATE_HZ,
    DEFAULT_MAX_DURATION_SECONDS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def guardrails():
    return Guardrails()


@pytest.fixture
def strict_policy():
    """A very strict policy for boundary testing."""
    return GuardrailPolicy(
        max_tx_gain_db=20.0,
        min_freq_hz=100e6,
        max_freq_hz=3e9,
        min_sample_rate_hz=1e4,
        max_sample_rate_hz=10e6,
        max_duration_seconds=60.0,
    )


@pytest.fixture
def strict_guardrails(strict_policy):
    return Guardrails(policy=strict_policy)


# ---------------------------------------------------------------------------
# 1. Default policy constant sanity checks
# ---------------------------------------------------------------------------

class TestDefaultPolicyConstants:

    def test_max_tx_gain_db_positive(self):
        assert DEFAULT_MAX_TX_GAIN_DB > 0

    def test_freq_bounds_sensible(self):
        assert DEFAULT_MIN_FREQ_HZ < DEFAULT_MAX_FREQ_HZ
        assert DEFAULT_MIN_FREQ_HZ >= 1e3   # at least 1 kHz
        assert DEFAULT_MAX_FREQ_HZ <= 100e9  # at most 100 GHz

    def test_sample_rate_bounds_sensible(self):
        assert DEFAULT_MIN_SAMPLE_RATE_HZ < DEFAULT_MAX_SAMPLE_RATE_HZ

    def test_max_duration_positive(self):
        assert DEFAULT_MAX_DURATION_SECONDS > 0


# ---------------------------------------------------------------------------
# 2. check_params – gain limits
# ---------------------------------------------------------------------------

class TestGainLimits:

    def test_gain_within_limit_passes(self, guardrails):
        guardrails.check_params({"gain": DEFAULT_MAX_TX_GAIN_DB})  # exact boundary – allowed

    def test_gain_below_limit_passes(self, guardrails):
        guardrails.check_params({"gain": 0.0})

    def test_gain_negative_passes(self, guardrails):
        guardrails.check_params({"gain": -10.0})

    def test_gain_exceeds_limit_raises(self, guardrails):
        with pytest.raises(GuardrailViolation, match="gain"):
            guardrails.check_params({"gain": DEFAULT_MAX_TX_GAIN_DB + 0.1})

    def test_gain_far_above_limit_raises(self, guardrails):
        with pytest.raises(GuardrailViolation, match="gain"):
            guardrails.check_params({"gain": 100.0})

    def test_strict_gain_at_boundary_passes(self, strict_guardrails):
        strict_guardrails.check_params({"gain": 20.0})  # exactly at limit

    def test_strict_gain_above_boundary_raises(self, strict_guardrails):
        with pytest.raises(GuardrailViolation):
            strict_guardrails.check_params({"gain": 20.1})


# ---------------------------------------------------------------------------
# 3. check_params – frequency bounds
# ---------------------------------------------------------------------------

class TestFrequencyBounds:

    def test_valid_frequency_passes(self, guardrails):
        guardrails.check_params({"freq": 2.4e9})

    def test_min_frequency_boundary_passes(self, guardrails):
        guardrails.check_params({"freq": DEFAULT_MIN_FREQ_HZ})

    def test_max_frequency_boundary_passes(self, guardrails):
        guardrails.check_params({"freq": DEFAULT_MAX_FREQ_HZ})

    def test_frequency_below_min_raises(self, guardrails):
        with pytest.raises(GuardrailViolation, match="[Ff]requency|freq"):
            guardrails.check_params({"freq": DEFAULT_MIN_FREQ_HZ - 1})

    def test_frequency_above_max_raises(self, guardrails):
        with pytest.raises(GuardrailViolation, match="[Ff]requency|freq"):
            guardrails.check_params({"freq": DEFAULT_MAX_FREQ_HZ + 1})

    def test_zero_frequency_raises(self, guardrails):
        with pytest.raises(GuardrailViolation):
            guardrails.check_params({"freq": 0.0})

    def test_negative_frequency_raises(self, guardrails):
        with pytest.raises(GuardrailViolation):
            guardrails.check_params({"freq": -1e9})


# ---------------------------------------------------------------------------
# 4. check_params – sample rate
# ---------------------------------------------------------------------------

class TestSampleRateLimits:

    def test_valid_sample_rate_passes(self, guardrails):
        guardrails.check_params({"sample_rate": 1e6})

    def test_min_sample_rate_boundary_passes(self, guardrails):
        guardrails.check_params({"sample_rate": DEFAULT_MIN_SAMPLE_RATE_HZ})

    def test_max_sample_rate_boundary_passes(self, guardrails):
        guardrails.check_params({"sample_rate": DEFAULT_MAX_SAMPLE_RATE_HZ})

    def test_sample_rate_below_min_raises(self, guardrails):
        with pytest.raises(GuardrailViolation, match="[Ss]ample rate|rate"):
            guardrails.check_params({"sample_rate": DEFAULT_MIN_SAMPLE_RATE_HZ - 1})

    def test_sample_rate_above_max_raises(self, guardrails):
        with pytest.raises(GuardrailViolation, match="[Ss]ample rate|rate"):
            guardrails.check_params({"sample_rate": DEFAULT_MAX_SAMPLE_RATE_HZ + 1})


# ---------------------------------------------------------------------------
# 5. check_params – duration limits
# ---------------------------------------------------------------------------

class TestDurationLimits:

    def test_valid_duration_passes(self, guardrails):
        guardrails.check_params({"duration": 10.0})

    def test_max_duration_boundary_passes(self, guardrails):
        guardrails.check_params({"duration": DEFAULT_MAX_DURATION_SECONDS})

    def test_duration_above_max_raises(self, guardrails):
        with pytest.raises(GuardrailViolation, match="[Dd]uration"):
            guardrails.check_params({"duration": DEFAULT_MAX_DURATION_SECONDS + 1})

    def test_zero_duration_raises(self, guardrails):
        with pytest.raises(GuardrailViolation, match="[Dd]uration"):
            guardrails.check_params({"duration": 0.0})

    def test_negative_duration_raises(self, guardrails):
        with pytest.raises(GuardrailViolation, match="[Dd]uration"):
            guardrails.check_params({"duration": -5.0})


# ---------------------------------------------------------------------------
# 6. check_params – mixed parameter dicts
# ---------------------------------------------------------------------------

class TestMixedParams:

    def test_empty_params_passes(self, guardrails):
        guardrails.check_params({})  # no constraints to violate

    def test_none_values_ignored(self, guardrails):
        guardrails.check_params({"gain": None, "freq": None, "sample_rate": None, "duration": None})

    def test_all_valid_params_passes(self, guardrails):
        guardrails.check_params({
            "gain": 20.0,
            "freq": 915e6,
            "sample_rate": 1e6,
            "duration": 5.0,
        })

    def test_first_violation_raises(self, guardrails):
        """Only one violation is needed to reject."""
        with pytest.raises(GuardrailViolation):
            guardrails.check_params({
                "gain": 999.0,  # violates gain
                "freq": 915e6,
                "sample_rate": 1e6,
            })


# ---------------------------------------------------------------------------
# 7. check_script – AST scanning of UHD calls
# ---------------------------------------------------------------------------

class TestScriptGuardrails:

    def test_safe_script_passes(self, guardrails):
        script = (
            "import numpy as np\n"
            "usrp = None  # mock\n"
            "data = np.zeros(1024, dtype=np.complex64)\n"
        )
        guardrails.check_script(script)  # must not raise

    def test_script_with_safe_gain_passes(self, guardrails):
        script = (
            "usrp.set_tx_gain(20.0)\n"
        )
        guardrails.check_script(script)  # must not raise

    def test_script_with_excessive_gain_raises(self, guardrails):
        script = f"usrp.set_tx_gain({DEFAULT_MAX_TX_GAIN_DB + 1})\n"
        with pytest.raises(GuardrailViolation, match="[Gg]ain"):
            guardrails.check_script(script)

    def test_script_with_valid_freq_passes(self, guardrails):
        script = "usrp.set_tx_freq(2.4e9)\n"
        guardrails.check_script(script)  # must not raise

    def test_script_with_freq_too_high_raises(self, guardrails):
        script = f"usrp.set_tx_freq({DEFAULT_MAX_FREQ_HZ + 1e6})\n"
        with pytest.raises(GuardrailViolation, match="[Ff]requency|freq"):
            guardrails.check_script(script)

    def test_script_with_freq_too_low_raises(self, guardrails):
        # Negative frequency
        script = "usrp.set_tx_freq(-1e6)\n"
        with pytest.raises(GuardrailViolation):
            guardrails.check_script(script)

    def test_script_with_valid_sample_rate_passes(self, guardrails):
        script = "usrp.set_tx_rate(1e6)\n"
        guardrails.check_script(script)  # must not raise

    def test_script_with_excessive_sample_rate_raises(self, guardrails):
        script = f"usrp.set_tx_rate({DEFAULT_MAX_SAMPLE_RATE_HZ + 1e6})\n"
        with pytest.raises(GuardrailViolation, match="[Ss]ample rate|rate"):
            guardrails.check_script(script)

    def test_script_rx_gain_excessive_raises(self, guardrails):
        script = f"usrp.set_rx_gain({DEFAULT_MAX_TX_GAIN_DB + 5.0})\n"
        with pytest.raises(GuardrailViolation, match="[Gg]ain"):
            guardrails.check_script(script)

    def test_script_rx_gain_safe_passes(self, guardrails):
        script = "usrp.set_rx_gain(10.0)\n"
        guardrails.check_script(script)  # must not raise

    def test_script_set_rx_rate_excessive_raises(self, guardrails):
        script = f"usrp.set_rx_rate({DEFAULT_MAX_SAMPLE_RATE_HZ * 2})\n"
        with pytest.raises(GuardrailViolation):
            guardrails.check_script(script)

    def test_syntax_error_in_script_does_not_raise_guardrail(self, guardrails):
        """Syntax errors are the validator's job; guardrails should silently skip."""
        script = "def broken("  # syntax error
        guardrails.check_script(script)  # must not raise GuardrailViolation

    def test_dynamic_value_not_caught_by_ast(self, guardrails):
        """Dynamic values cannot be determined statically – that is acceptable."""
        script = "gain_value = some_function()\nusrp.set_tx_gain(gain_value)\n"
        # No violation because the value is not a literal
        guardrails.check_script(script)  # must not raise

    def test_kwarg_gain_excessive_raises(self, guardrails):
        script = f"usrp.set_tx_gain(gain={DEFAULT_MAX_TX_GAIN_DB + 1})\n"
        with pytest.raises(GuardrailViolation, match="[Gg]ain"):
            guardrails.check_script(script)


# ---------------------------------------------------------------------------
# 8. Module-level convenience functions
# ---------------------------------------------------------------------------

class TestModuleLevelHelpers:

    def test_check_params_guardrails_passes(self):
        check_params_guardrails({"gain": 10.0, "freq": 915e6})  # must not raise

    def test_check_params_guardrails_raises(self):
        with pytest.raises(GuardrailViolation):
            check_params_guardrails({"gain": 999.0})

    def test_check_script_guardrails_passes(self):
        check_script_guardrails("import numpy as np\nprint('ok')")  # must not raise

    def test_check_script_guardrails_raises(self):
        with pytest.raises(GuardrailViolation):
            check_script_guardrails(f"usrp.set_tx_gain({DEFAULT_MAX_TX_GAIN_DB + 5})\n")
