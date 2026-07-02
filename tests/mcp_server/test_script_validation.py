"""
Tests for the script validator module.

These tests do NOT require physical UHD hardware and are suitable
for execution in a CI/CD environment (e.g., GitHub Actions).
"""

import pytest
from uhd_mcp.utils.script_validator import (
    ScriptValidator,
    ValidationError,
    validate_script,
    is_valid_script,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def validator():
    return ScriptValidator()


# ---------------------------------------------------------------------------
# 1. Positive tests – valid scripts should pass validation
# ---------------------------------------------------------------------------

class TestValidScripts:
    """Scripts that should pass validation without errors."""

    def test_empty_body_raises(self, validator):
        """Empty scripts are rejected with a clear message."""
        with pytest.raises(ValidationError, match="empty"):
            validator.validate("")

    def test_valid_numpy_script(self, validator):
        script = "import numpy as np\ndata = np.zeros(1024)\nprint(data.shape)"
        validator.validate(script)  # must not raise

    def test_valid_numpy_alias(self, validator):
        script = "import numpy as np\nx = np.array([1, 2, 3])"
        validator.validate(script)  # must not raise

    def test_valid_math_import(self, validator):
        script = "import math\nprint(math.pi)"
        validator.validate(script)  # must not raise

    def test_valid_typing_import(self, validator):
        script = "from typing import List\ndef foo(x: List[int]) -> int:\n    return sum(x)"
        validator.validate(script)  # must not raise

    def test_valid_time_import(self, validator):
        script = "import time\ntime.sleep(0.001)"
        validator.validate(script)  # must not raise

    def test_valid_collections_import(self, validator):
        script = "from collections import defaultdict\nd = defaultdict(list)"
        validator.validate(script)  # must not raise

    def test_valid_script_with_loops(self, validator):
        script = (
            "import numpy as np\n"
            "total = 0\n"
            "for i in range(10):\n"
            "    total += i\n"
            "print(total)\n"
        )
        validator.validate(script)  # must not raise

    def test_valid_script_with_functions(self, validator):
        script = (
            "import numpy as np\n"
            "\n"
            "def process(data):\n"
            "    return np.abs(data)\n"
            "\n"
            "result = process(np.ones(10))\n"
            "print(result)\n"
        )
        validator.validate(script)  # must not raise

    def test_valid_script_with_comprehensions(self, validator):
        script = (
            "import numpy as np\n"
            "data = [np.random.random() for _ in range(10)]\n"
            "print(data)\n"
        )
        validator.validate(script)  # must not raise

    def test_valid_from_numpy_import(self, validator):
        script = "from numpy import zeros, ones\nx = zeros(10) + ones(10)"
        validator.validate(script)  # must not raise

    def test_is_valid_returns_true_for_valid(self, validator):
        script = "import numpy as np\nprint(np.pi)"
        assert validator.is_valid(script) is True

    def test_module_level_convenience_valid(self):
        """is_valid_script and validate_script module helpers work."""
        script = "import math\nprint(math.e)"
        assert is_valid_script(script) is True
        validate_script(script)  # should not raise


# ---------------------------------------------------------------------------
# 2. Negative tests – forbidden imports
# ---------------------------------------------------------------------------

class TestForbiddenImports:
    """Scripts importing forbidden modules must be rejected."""

    @pytest.mark.parametrize("module", [
        "os",
        "subprocess",
        "socket",
        "sys",
        "shutil",
        "pathlib",
        "tempfile",
        "io",
        "ctypes",
        "threading",
        "multiprocessing",
        "importlib",
        "pickle",
        "urllib",
        "http",
    ])
    def test_import_forbidden_module(self, validator, module):
        script = f"import {module}\nprint('hello')"
        with pytest.raises(ValidationError, match=module):
            validator.validate(script)

    def test_from_import_forbidden_module(self, validator):
        script = "from os import path\nprint(path.sep)"
        with pytest.raises(ValidationError, match="os"):
            validator.validate(script)

    def test_import_os_path(self, validator):
        script = "import os.path\nprint(os.path.sep)"
        with pytest.raises(ValidationError, match="os"):
            validator.validate(script)

    def test_import_subprocess_run(self, validator):
        script = "from subprocess import run\nrun(['ls'])"
        with pytest.raises(ValidationError, match="subprocess"):
            validator.validate(script)

    def test_import_unknown_module(self, validator):
        """Modules not in allowed_imports are also rejected."""
        script = "import requests\nprint('ok')"
        with pytest.raises(ValidationError, match="requests"):
            validator.validate(script)

    def test_is_valid_returns_false_for_forbidden(self, validator):
        script = "import os\nos.system('echo hello')"
        assert validator.is_valid(script) is False

    def test_module_level_convenience_forbidden(self):
        script = "import subprocess\nsubprocess.run(['ls'])"
        assert is_valid_script(script) is False
        with pytest.raises(ValidationError):
            validate_script(script)


# ---------------------------------------------------------------------------
# 3. Negative tests – forbidden built-ins
# ---------------------------------------------------------------------------

class TestForbiddenBuiltins:
    """Scripts calling forbidden built-ins must be rejected."""

    def test_exec_call_rejected(self, validator):
        script = "exec('print(1)')"
        with pytest.raises(ValidationError, match="exec"):
            validator.validate(script)

    def test_eval_call_rejected(self, validator):
        script = "result = eval('1 + 1')"
        with pytest.raises(ValidationError, match="eval"):
            validator.validate(script)

    def test_compile_call_rejected(self, validator):
        script = "code = compile('1+1', '<string>', 'eval')"
        with pytest.raises(ValidationError, match="compile"):
            validator.validate(script)

    def test_breakpoint_rejected(self, validator):
        script = "breakpoint()"
        with pytest.raises(ValidationError, match="breakpoint"):
            validator.validate(script)


# ---------------------------------------------------------------------------
# 4. Negative tests – file I/O
# ---------------------------------------------------------------------------

class TestFileIO:
    """Scripts that attempt file I/O must be rejected."""

    def test_open_call_rejected(self, validator):
        script = "f = open('/etc/passwd', 'r')\nprint(f.read())"
        with pytest.raises(ValidationError, match="open"):
            validator.validate(script)

    def test_open_write_rejected(self, validator):
        script = "with open('/tmp/pwned.txt', 'w') as f:\n    f.write('pwned')"
        with pytest.raises(ValidationError, match="open"):
            validator.validate(script)

    def test_context_manager_open_rejected(self, validator):
        script = "with open('data.txt') as fh:\n    data = fh.read()"
        with pytest.raises(ValidationError, match="open"):
            validator.validate(script)


# ---------------------------------------------------------------------------
# 5. Negative tests – dynamic imports
# ---------------------------------------------------------------------------

class TestDynamicImports:
    """Scripts that use dynamic import mechanisms must be rejected."""

    def test_dunder_import_rejected(self, validator):
        script = "mod = __import__('os')\nmod.system('ls')"
        with pytest.raises(ValidationError, match="__import__"):
            validator.validate(script)

    def test_importlib_import_module_rejected(self, validator):
        script = "import importlib\nmod = importlib.import_module('os')"
        with pytest.raises(ValidationError, match="importlib"):
            validator.validate(script)


# ---------------------------------------------------------------------------
# 6. Negative tests – forbidden attribute chains
# ---------------------------------------------------------------------------

class TestForbiddenAttributes:
    """Scripts accessing dangerous attribute chains must be rejected."""

    def test_os_system_rejected(self, validator):
        # os not imported, but attribute access should still be caught
        script = "os.system('rm -rf /')"
        with pytest.raises(ValidationError, match="os.system"):
            validator.validate(script)

    def test_os_environ_rejected(self, validator):
        script = "val = os.environ['HOME']"
        with pytest.raises(ValidationError, match="os.environ"):
            validator.validate(script)

    def test_subprocess_popen_rejected(self, validator):
        script = "proc = subprocess.Popen(['ls'])"
        with pytest.raises(ValidationError, match="subprocess.Popen"):
            validator.validate(script)

    def test_subprocess_run_attr_rejected(self, validator):
        script = "subprocess.run(['ls'])"
        with pytest.raises(ValidationError, match="subprocess.run"):
            validator.validate(script)


# ---------------------------------------------------------------------------
# 7. Syntax errors
# ---------------------------------------------------------------------------

class TestSyntaxErrors:
    """Malformed scripts must produce a clear ValidationError."""

    def test_syntax_error_caught(self, validator):
        script = "def foo(\n    # missing closing paren and body"
        with pytest.raises(ValidationError, match="syntax"):
            validator.validate(script)

    def test_non_string_input(self, validator):
        with pytest.raises(ValidationError, match="string"):
            validator.validate(42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 8. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge-case scripts."""

    def test_whitespace_only_script(self, validator):
        with pytest.raises(ValidationError, match="empty"):
            validator.validate("   \n\t\n   ")

    def test_comment_only_script_accepted(self, validator):
        # A comment-only script is syntactically valid and has no dangerous nodes
        validator.validate("# This is a safe UHD comment script\n")

    def test_multiline_valid_script(self, validator):
        script = (
            "import numpy as np\n"
            "import math\n"
            "\n"
            "def generate_sine(freq, samp_rate, duration):\n"
            "    t = np.arange(0, duration, 1.0 / samp_rate)\n"
            "    return np.exp(1j * 2 * math.pi * freq * t).astype(np.complex64)\n"
            "\n"
            "samples = generate_sine(1e3, 1e6, 0.01)\n"
            "print('Generated', len(samples), 'samples')\n"
        )
        validator.validate(script)  # must not raise
