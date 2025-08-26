"""
VNC screenshot utility for UHD MCP Server
"""
import os
import time
import logging
from PIL import Image
from io import BytesIO

try:
    from vncdotool import api
except ImportError:
    api = None


def get_vnc_config():
    """
    Get VNC connection configuration from environment variables
    Returns:
        dict: VNC host, port, password
    """
    return {
        "host": os.environ.get("VNC_HOST", "vnc://10.101.209.51"),
        "port": int(os.environ.get("VNC_PORT", "5900")),
        "password": os.environ.get("VNC_PASSWORD", "1234"),
    }


def take_vnc_screenshot(save_dir, filename=None):
    """
    Connect to VNC server and take a screenshot, saving to save_dir
    Args:
        save_dir (str): Directory to save screenshot
        filename (str): Optional filename (default: vncshot_TIMESTAMP.png)
    Returns:
        str: Full path to saved screenshot, or error message
    """
    logger = logging.getLogger(__name__)
    config = get_vnc_config()
    if api is None:
        return None, "vncdotool not installed"
    try:
        os.makedirs(save_dir, exist_ok=True)
        if not filename:
            timestamp = int(time.time())
            filename = f"vncshot_{timestamp}.png"
        filepath = os.path.join(save_dir, filename)
        client = api.connect(f"{config['host']}::{config['port']}", password=config['password'])
        image_bytes = client.screen()
        image = Image.open(BytesIO(image_bytes))
        image.save(filepath)
        logger.info(f"VNC screenshot saved to {filepath}")
        return filepath, None
    except Exception as e:
        logger.error(f"VNC screenshot error: {str(e)}")
        return None, str(e)
