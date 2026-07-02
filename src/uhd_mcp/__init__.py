"""UHD MCP Server Package."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .usrp_mcp_server import main

try:
    __version__ = version("uhd-mcp")
except PackageNotFoundError:
    # Not installed (e.g. running from a plain checkout): fall back to the
    # repo-root VERSION file, the single source of truth for the version.
    _version_file = Path(__file__).resolve().parents[2] / "VERSION"
    __version__ = _version_file.read_text().strip() if _version_file.exists() else "0.0.0"

__all__ = ["main"]
