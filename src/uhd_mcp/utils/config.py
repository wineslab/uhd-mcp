"""
Configuration utilities for UHD MCP Server
"""

import os

# Default configuration. Override with the MCP_SHARED_DATA_DIR environment variable.
DEFAULT_SHARED_DATA_DIR = os.path.join(os.getcwd(), "shared-data-layer")


def get_shared_data_dir():
    """
    Get the shared data directory path from environment or default
    
    Returns:
        str: Path to the shared data directory
    """
    return os.environ.get("MCP_SHARED_DATA_DIR", DEFAULT_SHARED_DATA_DIR)


def get_config_info():
    """
    Get comprehensive configuration information
    
    Returns:
        dict: Configuration details including paths, environment variables, etc.
    """
    shared_data_dir = get_shared_data_dir()
    
    return {
        "shared_data_dir": shared_data_dir,
        "shared_data_dir_exists": os.path.exists(shared_data_dir),
        "shared_data_dir_writable": os.access(shared_data_dir, os.W_OK) if os.path.exists(shared_data_dir) else False,
        "environment_variables": {
            "MCP_SHARED_DATA_DIR": os.environ.get("MCP_SHARED_DATA_DIR", "not set")
        },
        "default_shared_data_dir": DEFAULT_SHARED_DATA_DIR
    }
