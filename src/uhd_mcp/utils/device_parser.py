"""
UHD Device Parser Utilities

This module contains functions for parsing UHD command outputs into structured data.
"""

from typing import Dict, Any


def parse_uhd_find_devices_output(output: str) -> Dict[str, Any]:
    """
    Parse uhd_find_devices output into structured JSON format
    
    Args:
        output: Raw stdout from uhd_find_devices command
        
    Returns:
        Dictionary with parsed device information containing:
        - total_devices: Number of devices found
        - device_types: Count of each device type
        - products: Count of each product type
        - devices: List of parsed device information
    """
    devices: list[Dict[str, Any]] = []
    current_device: Dict[str, Any] | None = None

    lines = output.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Check for device header
        if line.startswith("-- UHD Device"):
            if current_device is not None:
                devices.append(current_device)
            
            # Extract device number
            device_num = line.split("Device")[1].strip().split()[0]
            current_device = {
                "device_number": int(device_num),
                "device_address": {}
            }
            
        elif line.startswith("Device Address:"):
            # Start of device address section
            continue
            
        elif line and current_device is not None and ":" in line and not line.startswith("-"):
            # Parse key-value pairs
            try:
                key, raw_value = line.split(":", 1)
                key = key.strip()
                raw_value = raw_value.strip()

                # Convert boolean strings
                value: Any = raw_value
                if raw_value.lower() == "false":
                    value = False
                elif raw_value.lower() == "true":
                    value = True
                # Convert numeric strings if they look like numbers
                elif raw_value.isdigit():
                    value = int(raw_value)

                current_device["device_address"][key] = value
            except ValueError:
                # Skip lines that don't parse correctly
                continue
    
    # Add the last device
    if current_device is not None:
        devices.append(current_device)
    
    # Calculate summary statistics
    total_devices = len(devices)
    device_types: Dict[str, int] = {}
    products: Dict[str, int] = {}
    
    for device in devices:
        addr = device.get("device_address", {})
        dev_type = addr.get("type", "unknown")
        product = addr.get("product", "unknown")
        
        device_types[dev_type] = device_types.get(dev_type, 0) + 1
        products[product] = products.get(product, 0) + 1
    
    return {
        "total_devices": total_devices,
        "device_types": device_types,
        "products": products,
        "devices": devices
    }


def parse_uhd_config_info_output(output: str) -> Dict[str, Any]:
    """
    Parse uhd_config_info --print-all output into structured JSON format
    
    Args:
        output: Raw stdout from uhd_config_info --print-all command
        
    Returns:
        Dictionary with parsed UHD configuration information
    """
    config: Dict[str, Any] = {}

    lines = output.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if ":" in line:
            # Split on first colon only
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            
            # Convert key to snake_case and remove spaces
            key = key.lower().replace(" ", "_").replace("-", "_")
            
            # Handle specific value conversions
            if key == "uhd" and "." in value:
                # This is the version line like "UHD 4.3.0.0-0-g1f8fd345"
                config["version"] = value
            elif key == "build_date":
                config["build_date"] = value
            elif key == "c_compiler":
                # Extract compiler name and version
                if "GNU" in value:
                    parts = value.split()
                    config["c_compiler"] = {
                        "name": "GNU GCC",
                        "version": parts[-1] if parts else value
                    }
                else:
                    config["c_compiler"] = {"name": value, "version": "unknown"}
            elif key == "c++_compiler" or key == "cxx_compiler":
                # Extract compiler name and version
                if "GNU" in value:
                    parts = value.split()
                    config["cxx_compiler"] = {
                        "name": "GNU G++",
                        "version": parts[-1] if parts else value
                    }
                else:
                    config["cxx_compiler"] = {"name": value, "version": "unknown"}
            elif key == "enabled_components":
                # Split comma-separated components
                components = [comp.strip() for comp in value.split(",")]
                config["enabled_components"] = components
            elif key == "boost_version":
                config["boost_version"] = value
            elif key == "libusb_version":
                config["libusb_version"] = value
            elif key == "library_path":
                config["library_path"] = value
            elif key == "package_path":
                config["package_path"] = value
            elif key == "images_directory":
                config["images_directory"] = value
            elif key == "install_prefix":
                config["install_prefix"] = value
            elif key == "abi_version_string":
                config["abi_version"] = value
            elif "flags" in key:
                # Parse compiler flags into list
                flags = [flag.strip() for flag in value.split() if flag.strip()]
                config[key] = flags
            else:
                # Default: store as-is
                config[key] = value
        else:
            # Handle lines without colons (like the UHD version line)
            if line.startswith("UHD ") and config.get("version") is None:
                config["version"] = line
    
    return config
