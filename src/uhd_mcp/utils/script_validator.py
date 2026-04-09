"""
Script Validator for UHD MCP Server

Provides AST-based validation of agent-generated Python scripts before execution.
Ensures scripts only use allowed libraries and safe constructs.
"""

import ast
from typing import List, Tuple

# Modules that are explicitly allowed in UHD scripts
ALLOWED_IMPORTS: frozenset = frozenset({
    "uhd",
    "numpy",
    "np",       # common numpy alias
    "math",
    "time",
    "sys",      # only sys.argv / sys.exit are used but we block at call level
    "collections",
    "functools",
    "itertools",
    "typing",
    "dataclasses",
    "enum",
    "struct",
    "logging",
})

# Module names that must never be imported (blocked explicitly)
FORBIDDEN_IMPORTS: frozenset = frozenset({
    "os",
    "subprocess",
    "socket",
    "sys",          # sys is in allowed *and* forbidden – forbidden wins
    "shutil",
    "pathlib",
    "tempfile",
    "io",
    "builtins",
    "ctypes",
    "gc",
    "signal",
    "threading",
    "multiprocessing",
    "concurrent",
    "asyncio",
    "importlib",
    "pkgutil",
    "zipimport",
    "runpy",
    "code",
    "codeop",
    "pty",
    "tty",
    "termios",
    "fcntl",
    "mmap",
    "resource",
    "urllib",
    "http",
    "ftplib",
    "telnetlib",
    "smtplib",
    "xmlrpc",
    "pickle",
    "shelve",
    "dbm",
    "sqlite3",
    "csv",         # file I/O wrapper
    "configparser",
    "netrc",
    "pdb",
    "dis",
    "inspect",
    "traceback",
    "warnings",    # could be used to suppress safety warnings
    "platform",
    "pwd",
    "grp",
})

# Built-in names that must not be called in the script
FORBIDDEN_BUILTINS: frozenset = frozenset({
    "exec",
    "eval",
    "compile",
    "open",
    "__import__",
    "input",
    "print",   # allow; see _is_print_call below — actually we allow print
    "globals",
    "locals",
    "vars",
    "dir",
    "delattr",
    "setattr",
    "getattr",
    "hasattr",
    "breakpoint",
    "memoryview",
    "bytearray",
})

# Actually we allow print; remove it from the set
FORBIDDEN_BUILTINS = FORBIDDEN_BUILTINS - {"print"}

# Attributes that signal unsafe access patterns
FORBIDDEN_ATTRIBUTE_CHAINS: List[Tuple[str, str]] = [
    # (object_name, attribute_name)
    ("os", "system"),
    ("os", "popen"),
    ("os", "exec"),
    ("os", "execl"),
    ("os", "execle"),
    ("os", "execlp"),
    ("os", "execv"),
    ("os", "execve"),
    ("os", "execvp"),
    ("os", "execvpe"),
    ("os", "fork"),
    ("os", "spawn"),
    ("os", "kill"),
    ("os", "remove"),
    ("os", "unlink"),
    ("os", "rmdir"),
    ("os", "mkdir"),
    ("os", "makedirs"),
    ("os", "rename"),
    ("os", "environ"),
    ("subprocess", "run"),
    ("subprocess", "call"),
    ("subprocess", "Popen"),
    ("subprocess", "check_call"),
    ("subprocess", "check_output"),
]


class ValidationError(Exception):
    """Raised when a script fails validation."""
    pass


class ScriptValidator:
    """
    Validates Python scripts intended for UHD device control.

    Uses AST analysis to enforce:
    - Allowed import whitelist
    - Forbidden import blacklist
    - No dangerous built-in calls
    - No file I/O
    - No dynamic imports
    """

    def __init__(
        self,
        allowed_imports: frozenset = ALLOWED_IMPORTS,
        forbidden_imports: frozenset = FORBIDDEN_IMPORTS,
        forbidden_builtins: frozenset = FORBIDDEN_BUILTINS,
    ):
        self.allowed_imports = allowed_imports
        self.forbidden_imports = forbidden_imports
        self.forbidden_builtins = forbidden_builtins

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, script: str) -> None:
        """
        Validate a script string.

        Raises ValidationError with a descriptive message on the first
        violation found. Returns None on success.
        """
        if not isinstance(script, str):
            raise ValidationError("Script must be a string.")

        if not script.strip():
            raise ValidationError("Script is empty.")

        try:
            tree = ast.parse(script, mode="exec")
        except SyntaxError as exc:
            raise ValidationError(f"Script has syntax errors: {exc}") from exc

        self._check_imports(tree)
        self._check_forbidden_builtins(tree)
        self._check_file_io(tree)
        self._check_dynamic_imports(tree)
        self._check_forbidden_attribute_access(tree)

    def is_valid(self, script: str) -> bool:
        """Return True if the script passes validation, False otherwise."""
        try:
            self.validate(script)
            return True
        except ValidationError:
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_import_name(self, node: ast.AST) -> str:
        """Extract the top-level module name from an import node."""
        if isinstance(node, ast.Import):
            # e.g.  import os.path  →  "os"
            return node.names[0].name.split(".")[0]
        if isinstance(node, ast.ImportFrom):
            # e.g.  from os.path import join  →  "os"
            if node.module:
                return node.module.split(".")[0]
        return ""

    def _check_imports(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue

            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    self._assert_import_allowed(top, node)
            elif isinstance(node, ast.ImportFrom):
                top = node.module.split(".")[0] if node.module else ""
                if top:
                    self._assert_import_allowed(top, node)

    def _assert_import_allowed(self, module_name: str, node: ast.AST) -> None:
        line = getattr(node, "lineno", "?")
        if module_name in self.forbidden_imports:
            raise ValidationError(
                f"Line {line}: Import of forbidden module '{module_name}' is not allowed."
            )
        if module_name not in self.allowed_imports:
            raise ValidationError(
                f"Line {line}: Import of module '{module_name}' is not in the allowed list."
            )

    def _check_forbidden_builtins(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            # Direct calls like eval(...) or exec(...)
            if isinstance(func, ast.Name) and func.id in self.forbidden_builtins:
                line = getattr(node, "lineno", "?")
                raise ValidationError(
                    f"Line {line}: Call to forbidden built-in '{func.id}' is not allowed."
                )

    def _check_file_io(self, tree: ast.AST) -> None:
        """Reject any call to open() and any 'with open(...)' construct."""
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id == "open":
                line = getattr(node, "lineno", "?")
                raise ValidationError(
                    f"Line {line}: File I/O via open() is not allowed."
                )
            # Attribute access: e.g. builtins.open(...)
            if isinstance(func, ast.Attribute) and func.attr == "open":
                line = getattr(node, "lineno", "?")
                raise ValidationError(
                    f"Line {line}: File I/O via .open() is not allowed."
                )

    def _check_dynamic_imports(self, tree: ast.AST) -> None:
        """Reject __import__(...) and importlib.import_module(...)."""
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            # __import__(...)
            if isinstance(func, ast.Name) and func.id == "__import__":
                line = getattr(node, "lineno", "?")
                raise ValidationError(
                    f"Line {line}: Dynamic import via __import__() is not allowed."
                )
            # importlib.import_module(...)
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "import_module"
                and isinstance(func.value, ast.Name)
                and func.value.id == "importlib"
            ):
                line = getattr(node, "lineno", "?")
                raise ValidationError(
                    f"Line {line}: Dynamic import via importlib.import_module() is not allowed."
                )

    def _check_forbidden_attribute_access(self, tree: ast.AST) -> None:
        """Reject known-dangerous attribute chains like os.system, subprocess.Popen, etc."""
        forbidden_set = {(obj, attr) for obj, attr in FORBIDDEN_ATTRIBUTE_CHAINS}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute):
                continue
            if isinstance(node.value, ast.Name):
                pair = (node.value.id, node.attr)
                if pair in forbidden_set:
                    line = getattr(node, "lineno", "?")
                    raise ValidationError(
                        f"Line {line}: Access to '{node.value.id}.{node.attr}' is not allowed."
                    )


# Module-level convenience instance
_default_validator = ScriptValidator()


def validate_script(script: str) -> None:
    """Validate a script using the default validator. Raises ValidationError on failure."""
    _default_validator.validate(script)


def is_valid_script(script: str) -> bool:
    """Return True if the script passes validation with the default validator."""
    return _default_validator.is_valid(script)
