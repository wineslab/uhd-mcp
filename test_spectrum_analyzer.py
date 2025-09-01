#!/usr/bin/env python3
"""
Test script for spectrum analyzer waterfall capture
"""

import os
import logging
from src.uhd_mcp.utils.spectrum_analyzer import capture_spectrum_waterfall, get_analyzer_config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_waterfall_capture():
    """Test the waterfall capture functionality"""
    
    # Set environment variables for testing (you can modify these)
    os.environ["SA_HOST"] = "10.101.209.51"  # Replace with your analyzer IP
    os.environ["SA_PORT"] = "5025"
    os.environ["SA_TIMEOUT"] = "15.0"
    
    print("Testing Spectrum Analyzer Waterfall Capture")
    print("=" * 50)
    
    # Get current configuration
    config = get_analyzer_config()
    print(f"Analyzer Configuration:")
    print(f"  Host: {config['host']}")
    print(f"  Port: {config['port']}")
    print(f"  Timeout: {config['timeout']}s")
    print()
    
    # Test parameters
    test_params = {
        "center_freq": 2.4e9,      # 2.4 GHz (WiFi/ISM band)
        "span": 100e6,             # 100 MHz span
        "duration": 30,            # 30 seconds capture
        "interval": 2.0,           # 2 seconds between measurements
        "save_dir": "/tmp/test_spectrum",
        "filename_prefix": "test_waterfall",
        "rbw": 1e6,               # 1 MHz resolution bandwidth
        "ref_level": -30           # -30 dBm reference level
    }
    
    print("Test Parameters:")
    print(f"  Center Frequency: {test_params['center_freq']/1e6:.1f} MHz")
    print(f"  Span: {test_params['span']/1e6:.1f} MHz")
    print(f"  Duration: {test_params['duration']} seconds")
    print(f"  Interval: {test_params['interval']} seconds")
    print(f"  RBW: {test_params['rbw']/1e6:.1f} MHz")
    print(f"  Reference Level: {test_params['ref_level']} dBm")
    print(f"  Save Directory: {test_params['save_dir']}")
    print()
    
    # Perform waterfall capture
    print("Starting waterfall capture...")
    try:
        result = capture_spectrum_waterfall(**test_params)
        
        if result["success"]:
            print("\n✅ Waterfall capture completed successfully!")
            print("\nResults:")
            print(f"  Data file: {result['data_file']}")
            print(f"  Plot file: {result['plot_file']}")
            print(f"  Capture duration: {result['capture_duration']:.2f} seconds")
            
            print("\nStatistics:")
            stats = result['statistics']
            print(f"  Center frequency: {stats['center_frequency_mhz']:.1f} MHz")
            print(f"  Span: {stats['span_mhz']:.1f} MHz")
            print(f"  Measurements: {stats['num_measurements']}")
            print(f"  Min amplitude: {stats['min_amplitude_dbm']:.1f} dBm")
            print(f"  Max amplitude: {stats['max_amplitude_dbm']:.1f} dBm")
            print(f"  Mean amplitude: {stats['mean_amplitude_dbm']:.1f} dBm")
            print(f"  Frequency range: {stats['frequency_range_mhz'][0]:.1f} - {stats['frequency_range_mhz'][1]:.1f} MHz")
            
            return True
            
        else:
            print(f"\n❌ Waterfall capture failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_connection():
    """Test simple connection to the spectrum analyzer"""
    from src.uhd_mcp.utils.spectrum_analyzer import KeysightEXA, get_analyzer_config
    
    print("Testing simple connection to spectrum analyzer...")
    
    config = get_analyzer_config()
    analyzer = KeysightEXA(
        host=config["host"],
        port=config["port"],
        timeout=config["timeout"]
    )
    
    try:
        if analyzer.connect():
            print("✅ Connection successful!")
            
            # Try a simple query
            idn = analyzer.query("*IDN?")
            print(f"Instrument ID: {idn}")
            
            analyzer.disconnect()
            return True
        else:
            print("❌ Connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("Spectrum Analyzer Waterfall Test Suite")
    print("=" * 50)
    
    # Test 1: Simple connection
    print("\nTest 1: Simple Connection")
    print("-" * 30)
    connection_ok = test_simple_connection()
    
    if connection_ok:
        # Test 2: Waterfall capture
        print("\nTest 2: Waterfall Capture")
        print("-" * 30)
        waterfall_ok = test_waterfall_capture()
        
        if waterfall_ok:
            print("\n🎉 All tests passed!")
        else:
            print("\n⚠️  Waterfall test failed, but connection works")
    else:
        print("\n⚠️  Connection test failed - check analyzer IP and network")
        print("You can modify the SA_HOST environment variable to point to your analyzer")
