"""
UHD Device Parser Utilities

This module contains functions for parsing UHD command outputs into structured data.
"""

from typing import Dict, List, Any


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
    devices = []
    current_device = None
    
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
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                
                # Convert boolean strings
                if value.lower() == "false":
                    value = False
                elif value.lower() == "true":
                    value = True
                # Convert numeric strings if they look like numbers
                elif value.isdigit():
                    value = int(value)
                
                current_device["device_address"][key] = value
            except ValueError:
                # Skip lines that don't parse correctly
                continue
    
    # Add the last device
    if current_device is not None:
        devices.append(current_device)
    
    # Calculate summary statistics
    total_devices = len(devices)
    device_types = {}
    products = {}
    
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
