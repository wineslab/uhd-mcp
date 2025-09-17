# Spectrum Analyzer Control Documentation

## Overview

The UHD MCP server now includes comprehensive support for controlling the Keysight EXA N9010B Spectrum Analyzer. This functionality enables waterfall display capture and frequency analysis over time.

## Features

- **SCPI Communication**: Direct TCP/IP communication with the analyzer
- **Waterfall Capture**: Time-based spectrum analysis with automatic plotting
- **Configurable Parameters**: Frequency, span, resolution bandwidth, reference level
- **Data Export**: Raw data saved as NumPy files, plots as PNG images
- **Environment Configuration**: Flexible analyzer connection settings

## Quick Start

### 1. Environment Setup

Set environment variables for your spectrum analyzer:

```bash
export SA_HOST="127.0.0.1"  # Your analyzer IP address
export SA_PORT="5025"           # SCPI port (default: 5025)
export SA_TIMEOUT="15.0"        # Connection timeout in seconds
```

### 2. Basic Usage

```python
from src.uhd_mcp.utils.spectrum_analyzer import capture_spectrum_waterfall

# Capture 2.4 GHz ISM band waterfall for 60 seconds
result = capture_spectrum_waterfall(
    center_freq=2.4e9,    # 2.4 GHz center frequency
    span=100e6,           # 100 MHz span
    duration=60,          # 60 seconds total capture
    interval=1.0,         # 1 second between measurements
    save_dir="/tmp/spectrum_data",
    filename_prefix="ism_band",
    rbw=1e6,             # 1 MHz resolution bandwidth
    ref_level=-30        # -30 dBm reference level
)

if result["success"]:
    print(f"Data saved to: {result['data_file']}")
    print(f"Plot saved to: {result['plot_file']}")
    print(f"Statistics: {result['statistics']}")
```

### 3. Running the Test Script

```bash
cd /home/user/uhd-mcp
hatch run python test_spectrum_analyzer.py
```

## API Reference

### Class: `KeysightEXA`

Main class for controlling the Keysight EXA spectrum analyzer.

#### Constructor

```python
KeysightEXA(host: str, port: int = 5025, timeout: float = 10.0)
```

- `host`: IP address or hostname of the analyzer
- `port`: SCPI port (default: 5025)
- `timeout`: Socket timeout in seconds

#### Methods

- `connect() -> bool`: Establish connection to analyzer
- `disconnect()`: Close connection
- `query(command: str) -> str`: Send SCPI query and get response
- `send(command: str)`: Send SCPI command
- `configure_spectrum(config: SpectrumConfig)`: Configure analyzer settings
- `get_trace_data() -> Tuple[np.ndarray, np.ndarray]`: Get frequency and amplitude data
- `capture_waterfall(...)`: Capture waterfall display over time

### Class: `SpectrumConfig`

Configuration dataclass for spectrum analyzer measurements.

```python
@dataclass
class SpectrumConfig:
    center_freq: float              # Center frequency in Hz
    span: float                     # Frequency span in Hz
    rbw: Optional[float] = None     # Resolution bandwidth in Hz
    vbw: Optional[float] = None     # Video bandwidth in Hz
    sweep_time: Optional[float] = None  # Sweep time in seconds
    ref_level: Optional[float] = None   # Reference level in dBm
    attenuation: Optional[float] = None # Attenuation in dB
```

### Function: `capture_spectrum_waterfall`

High-level function for waterfall capture.

```python
capture_spectrum_waterfall(
    center_freq: float,
    span: float,
    duration: float,
    interval: float,
    save_dir: str,
    filename_prefix: str = "waterfall",
    rbw: Optional[float] = None,
    ref_level: Optional[float] = None
) -> Dict
```

#### Parameters

- `center_freq`: Center frequency in Hz
- `span`: Frequency span in Hz
- `duration`: Total capture duration in seconds
- `interval`: Time between measurements in seconds
- `save_dir`: Directory to save results
- `filename_prefix`: Prefix for output files
- `rbw`: Resolution bandwidth in Hz (optional)
- `ref_level`: Reference level in dBm (optional)

#### Returns

Dictionary with results:
```python
{
    "success": bool,
    "data_file": str,      # Path to .npz data file
    "plot_file": str,      # Path to .png plot file
    "statistics": dict,    # Summary statistics
    "capture_duration": float  # Actual capture time
}
```

## SCPI Commands Used

The implementation uses standard SCPI commands compatible with the Keysight EXA:

### Configuration Commands
- `INST SA` - Set to spectrum analyzer mode
- `FREQ:CENT <freq>` - Set center frequency
- `FREQ:SPAN <span>` - Set frequency span
- `BAND:RES <rbw>` - Set resolution bandwidth
- `BAND:VID <vbw>` - Set video bandwidth
- `DISP:WIND:TRAC:Y:RLEV <level>` - Set reference level
- `SENS:POW:RF:ATT <atten>` - Set input attenuation

### Measurement Commands
- `INIT:CONT OFF` - Single sweep mode
- `INIT:IMM` - Trigger immediate sweep
- `*WAI` - Wait for operation complete
- `TRAC:DATA? TRACE1` - Get trace data
- `FREQ:CENT?` - Query center frequency
- `FREQ:SPAN?` - Query frequency span
- `SWE:POIN?` - Query sweep points

## File Outputs

### Data File (.npz)
Contains raw measurement data in NumPy format:
- `frequencies`: Frequency array in Hz
- `amplitudes`: 2D array of amplitude measurements in dBm
- `timestamps`: ISO format timestamps for each measurement
- `config`: Configuration dictionary used for measurement

### Plot File (.png)
Waterfall display showing:
- X-axis: Frequency in MHz
- Y-axis: Time (measurement index)
- Color scale: Amplitude in dBm
- Title with center frequency and span information

## Example Use Cases

### 1. WiFi Band Monitoring
Monitor the 2.4 GHz WiFi band for interference:

```python
result = capture_spectrum_waterfall(
    center_freq=2.442e9,   # WiFi center (channel 7)
    span=84e6,             # Full WiFi band
    duration=300,          # 5 minutes
    interval=0.5,          # 0.5 second updates
    save_dir="/data/wifi_monitoring",
    rbw=1e6,
    ref_level=-40
)
```

### 2. LTE Band Analysis
Analyze LTE band 7 (2.6 GHz):

```python
result = capture_spectrum_waterfall(
    center_freq=2.655e9,   # LTE band 7 center
    span=70e6,             # Band 7 bandwidth
    duration=600,          # 10 minutes
    interval=1.0,          # 1 second intervals
    save_dir="/data/lte_analysis",
    rbw=100e3,             # 100 kHz RBW
    ref_level=-20
)
```

### 3. Custom Frequency Sweep
Monitor a specific frequency range:

```python
result = capture_spectrum_waterfall(
    center_freq=915e6,     # 915 MHz ISM band
    span=50e6,             # 50 MHz span
    duration=120,          # 2 minutes
    interval=2.0,          # 2 second intervals
    save_dir="/data/custom_sweep",
    rbw=1e6,
    ref_level=-50
)
```

## Error Handling

The module includes comprehensive error handling:

- **Connection Errors**: Timeout, network issues, wrong IP
- **SCPI Errors**: Invalid commands, instrument errors
- **Data Errors**: Malformed responses, missing data
- **File Errors**: Permission issues, disk space

All errors are logged and returned in the result dictionary.

## Troubleshooting

### Common Issues

1. **Connection Timeout**
   - Check analyzer IP address and network connectivity
   - Verify SCPI port (usually 5025)
   - Increase timeout value

2. **Invalid Frequency Range**
   - Check analyzer specifications (10 Hz to 44 GHz for N9010B)
   - Ensure span doesn't exceed maximum

3. **SCPI Command Errors**
   - Verify analyzer is in spectrum analyzer mode
   - Check command syntax in analyzer manual

4. **Data Size Issues**
   - Large waterfall captures use significant memory
   - Consider reducing duration or increasing interval

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show all SCPI commands and responses.

## Dependencies

Required Python packages:
- `numpy`: Numerical arrays and calculations
- `matplotlib`: Plotting and visualization
- `socket`: TCP/IP communication (built-in)
- `time`, `datetime`: Timing and timestamps (built-in)
- `logging`: Debug and error logging (built-in)

Install with:
```bash
hatch run pip install numpy matplotlib
```

## Integration with UHD MCP Server

The spectrum analyzer functionality is designed to integrate with the UHD MCP server for comprehensive RF measurement capabilities. Future versions may include:

- MCP tools for spectrum analysis
- Integration with USRP signal generation
- Automated measurement sequences
- Real-time spectrum monitoring via web interface


# References

## Direct Product Pages

- Main Product Page: https://www.keysight.com/us/en/product/N9010B/exa-signal-analyzer-multi-touch-10-hz-44-ghz.html
- Technical Support Page: https://www.keysight.com/us/en/support/N9010B/exa-signal-analyzer-multi-touch-10-hz-44-ghz.html

## Technical Documentation (PDFs):

- X-Series Programming Conversion Guide: https://www.keysight.com/us/en/assets/9018-02282/user-manuals/9018-02282.pdf
- N9010B Data Sheet: https://www.keysight.com/us/en/assets/7018-05049/data-sheets/5992-1256.pdf
- Configuration Guide: https://www.keysight.com/us/en/assets/7018-05046/configuration-guides/5992-1253.pdf
- N9010B Specifications Guide: https://www.keysight.com/us/en/assets/9018-70012/technical-specifications/9018-70012.pdf
- SCPI Language Compatibility Reference: https://literature.cdn.keysight.com/litweb/pdf/N9062-90002.pdf

## Remote Control Software:

- Web Remote Control Software: https://www.keysight.com/us/en/assets/7018-01779/technical-overviews/5989-8185.pdf
- Instrument Firmware Page: https://www.keysight.com/us/en/lib/software-detail/instrument-firmware-software/n9010b-exa-signal-analyzer-instrument-software-2674915.html
- SCPI Community Discussion: https://community.keysight.com/thread/21176

The X-Series Programming Conversion Guide and SCPI Language Compatibility Reference would be particularly useful for API programming details.