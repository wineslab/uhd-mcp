#!/usr/bin/env python3
"""
Test script for MCP spectrum analyzer tool
"""

import requests
import json
import time

def test_spectrum_analyzer_mcp_tool():
    """Test the spectrum analyzer tool via MCP server HTTP interface"""
    
    # Start MCP server first (assumes it's running on port 8001)
    server_url = "http://localhost:8001/mcp"
    
    print("Testing MCP Spectrum Analyzer Tool")
    print("=" * 50)
    
    # Test parameters for a quick capture
    test_params = {
        "center_freq": 2.4e9,  # 2.4 GHz
        "span": 100e6,         # 100 MHz
        "duration": 10,        # 10 seconds  
        "interval": 2.5,       # ~4 measurements
        "filename_prefix": "mcp_test"
    }
    
    print(f"Test parameters:")
    print(f"  Center Frequency: {test_params['center_freq']/1e9:.1f} GHz")
    print(f"  Span: {test_params['span']/1e6:.0f} MHz") 
    print(f"  Duration: {test_params['duration']} seconds")
    print(f"  Measurements: ~{int(test_params['duration']/test_params['interval'])}")
    print()
    
    try:
        # Call the MCP tool via HTTP
        payload = {
            "method": "tools/call",
            "params": {
                "name": "capture_spectrum_waterfall",
                "arguments": test_params
            }
        }
        
        print("Sending request to MCP server...")
        response = requests.post(server_url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ MCP tool call successful!")
            
            # Parse the result (it should be JSON string in result.content)
            if 'result' in result and 'content' in result['result']:
                content = json.loads(result['result']['content'])
                
                if content.get('success', False):
                    print("✅ Spectrum waterfall capture successful!")
                    print(f"  Data file: {content.get('data_filename', 'N/A')}")
                    print(f"  Plot file: {content.get('plot_filename', 'N/A')}")
                    print(f"  Capture duration: {content.get('capture_duration', 0):.1f}s")
                    
                    stats = content.get('statistics', {})
                    if stats:
                        print(f"  Measurements: {stats.get('num_measurements', 'N/A')}")
                        print(f"  Frequency range: {stats.get('frequency_range_mhz', ['N/A', 'N/A'])[0]:.0f}-{stats.get('frequency_range_mhz', ['N/A', 'N/A'])[1]:.0f} MHz")
                        print(f"  Amplitude range: {stats.get('min_amplitude_dbm', 'N/A'):.1f} to {stats.get('max_amplitude_dbm', 'N/A'):.1f} dBm")
                else:
                    print(f"❌ Capture failed: {content.get('error', 'Unknown error')}")
            else:
                print("❌ Unexpected response format")
                print(result)
        else:
            print(f"❌ HTTP error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        print("\nMake sure the MCP server is running:")
        print("  hatch run python -m uhd_mcp --port 8001")

if __name__ == "__main__":
    test_spectrum_analyzer_mcp_tool()
