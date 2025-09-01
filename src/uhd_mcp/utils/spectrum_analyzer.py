#!/usr/bin/env python3
"""
Keysight EXA N9010B Spectrum Analyzer Control Module
Supports waterfall display capture and frequency analysis
"""

import socket
import time
import logging
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass


@dataclass
class SpectrumConfig:
    """Configuration for spectrum analyzer measurements"""
    center_freq: float  # Hz
    span: float  # Hz
    rbw: Optional[float] = None  # Hz, resolution bandwidth
    vbw: Optional[float] = None  # Hz, video bandwidth
    sweep_time: Optional[float] = None  # seconds
    ref_level: Optional[float] = None  # dBm
    attenuation: Optional[float] = None  # dB


class KeysightEXA:
    """Keysight EXA N9010B Spectrum Analyzer Control Class"""
    
    def __init__(self, host: str, port: int = 5025, timeout: float = 10.0):
        """
        Initialize connection to Keysight EXA spectrum analyzer
        
        Args:
            host: IP address or hostname of the spectrum analyzer
            port: SCPI port (default 5025)
            timeout: Socket timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket = None
        self.logger = logging.getLogger(__name__)
        
    def connect(self) -> bool:
        """
        Establish connection to the spectrum analyzer
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            
            # Test connection with IDN query
            idn = self.query("*IDN?")
            self.logger.info(f"Connected to: {idn}")
            return True
            
        except Exception as e:
            self.logger.error(f"Connection failed: {str(e)}")
            return False
    
    def disconnect(self):
        """Close connection to the spectrum analyzer"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def send(self, command: str):
        """
        Send SCPI command to the analyzer
        
        Args:
            command: SCPI command string
        """
        if not self.socket:
            raise RuntimeError("Not connected to spectrum analyzer")
        
        try:
            cmd_bytes = (command + '\n').encode('utf-8')
            self.socket.send(cmd_bytes)
            self.logger.debug(f"Sent: {command}")
        except Exception as e:
            self.logger.error(f"Send error: {str(e)}")
            raise
    
    def receive(self, buffer_size: int = 4096) -> str:
        """
        Receive response from the analyzer
        
        Args:
            buffer_size: Maximum bytes to receive
            
        Returns:
            Response string
        """
        if not self.socket:
            raise RuntimeError("Not connected to spectrum analyzer")
        
        try:
            # For large data transfers, receive in chunks
            response = b""
            while True:
                try:
                    chunk = self.socket.recv(buffer_size)
                    if not chunk:
                        break
                    response += chunk
                    # Check if we have a complete response (ends with newline)
                    if response.endswith(b'\n'):
                        break
                except socket.timeout:
                    if response:  # We got some data
                        break
                    else:
                        raise
            
            decoded_response = response.decode('utf-8').strip()
            self.logger.debug(f"Received: {decoded_response[:100]}...")  # Log first 100 chars
            return decoded_response
        except Exception as e:
            self.logger.error(f"Receive error: {str(e)}")
            raise
    
    def query(self, command: str, buffer_size: int = 8192) -> str:
        """
        Send command and receive response
        
        Args:
            command: SCPI query command
            buffer_size: Maximum bytes to receive
            
        Returns:
            Response string
        """
        self.send(command)
        return self.receive(buffer_size)
    
    def reset(self):
        """Reset the analyzer to default state"""
        self.send("*RST")
        self.send("*CLS")  # Clear status
        time.sleep(2)  # Wait for reset to complete
    
    def configure_spectrum(self, config: SpectrumConfig):
        """
        Configure spectrum analyzer for measurement
        
        Args:
            config: SpectrumConfig object with measurement parameters
        """
        # Set to spectrum analyzer mode
        self.send("INST SA")
        
        # Set center frequency and span
        self.send(f"FREQ:CENT {config.center_freq}")
        self.send(f"FREQ:SPAN {config.span}")
        
        # Set optional parameters if provided
        if config.rbw is not None:
            self.send(f"BAND:RES {config.rbw}")
        
        if config.vbw is not None:
            self.send(f"BAND:VID {config.vbw}")
        
        if config.sweep_time is not None:
            self.send(f"SWE:TIME {config.sweep_time}")
        
        if config.ref_level is not None:
            self.send(f"DISP:WIND:TRAC:Y:RLEV {config.ref_level}")
        
        if config.attenuation is not None:
            self.send(f"SENS:POW:RF:ATT {config.attenuation}")
        
        self.logger.info(f"Configured spectrum analyzer: {config.center_freq/1e6:.3f} MHz ± {config.span/1e6:.3f} MHz")
    
    def get_trace_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get current trace data (frequency and amplitude)
        
        Returns:
            Tuple of (frequencies, amplitudes) arrays
        """
        # Trigger a single sweep
        self.send("INIT:CONT OFF")  # Single sweep mode
        self.send("INIT:IMM")       # Trigger sweep
        self.send("*WAI")           # Wait for sweep to complete
        
        # Get current analyzer settings to calculate frequency array
        center_freq = float(self.query("FREQ:CENT?"))
        span = float(self.query("FREQ:SPAN?"))
        num_points = int(self.query("SWE:POIN?"))
        
        # Calculate frequency array
        start_freq = center_freq - span/2
        stop_freq = center_freq + span/2
        frequencies = np.linspace(start_freq, stop_freq, num_points)
        
        # Get amplitude data - try different query formats
        try:
            amp_data = self.query("TRAC:DATA? TRACE1", buffer_size=65536)
        except:
            try:
                amp_data = self.query("TRAC1:DATA?", buffer_size=65536)
            except:
                amp_data = self.query("TRAC:DATA?", buffer_size=65536)
        
        # Parse amplitude data with error handling for corrupted values
        amp_values = []
        for value_str in amp_data.split(','):
            try:
                # Handle potential missing negative sign in scientific notation
                value_str = value_str.strip()
                if value_str and not value_str.startswith('-') and 'E+' in value_str:
                    # Check if this looks like a corrupted negative value
                    if value_str[0].isdigit():
                        value_str = '-' + value_str
                amp_values.append(float(value_str))
            except ValueError as e:
                self.logger.warning(f"Skipping invalid amplitude value: '{value_str}' - {e}")
                # Use previous value or a default if this is the first value
                if amp_values:
                    amp_values.append(amp_values[-1])
                else:
                    amp_values.append(-100.0)  # Default noise floor value
        
        amplitudes = np.array(amp_values)
        
        # Ensure arrays are same length
        if len(frequencies) != len(amplitudes):
            min_len = min(len(frequencies), len(amplitudes))
            frequencies = frequencies[:min_len]
            amplitudes = amplitudes[:min_len]
        
        return frequencies, amplitudes
    
    def capture_waterfall(self, config: SpectrumConfig, duration: float, 
                         interval: float, save_dir: str, 
                         filename_prefix: str = "waterfall") -> Dict:
        """
        Capture waterfall display over time
        
        Args:
            config: SpectrumConfig for measurement setup
            duration: Total capture duration in seconds
            interval: Time between measurements in seconds
            save_dir: Directory to save waterfall data
            filename_prefix: Prefix for saved files
            
        Returns:
            Dictionary with capture results and file paths
        """
        # Configure the analyzer
        self.configure_spectrum(config)
        
        # Calculate number of measurements
        num_measurements = int(duration / interval)
        
        # Storage for waterfall data
        waterfall_data = []
        timestamps = []
        frequencies = None
        
        self.logger.info(f"Starting waterfall capture: {num_measurements} measurements over {duration}s")
        
        start_time = time.time()
        
        try:
            for i in range(num_measurements):
                measurement_time = datetime.now()
                
                # Get trace data
                freqs, amps = self.get_trace_data()
                
                if frequencies is None:
                    frequencies = freqs
                
                waterfall_data.append(amps)
                timestamps.append(measurement_time)
                
                self.logger.debug(f"Captured measurement {i+1}/{num_measurements}")
                
                # Wait for next measurement (accounting for measurement time)
                elapsed = time.time() - start_time - (i * interval)
                sleep_time = interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            # Convert to numpy arrays
            waterfall_array = np.array(waterfall_data)
            
            # Create output directory
            os.makedirs(save_dir, exist_ok=True)
            
            # Generate timestamp for filenames
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save raw data
            data_filename = f"{filename_prefix}_{timestamp_str}_data.npz"
            data_path = os.path.join(save_dir, data_filename)
            
            np.savez(data_path,
                    frequencies=frequencies,
                    amplitudes=waterfall_array,
                    timestamps=[t.isoformat() for t in timestamps],
                    config=config.__dict__)
            
            # Create waterfall plot
            plot_filename = f"{filename_prefix}_{timestamp_str}_plot.png"
            plot_path = os.path.join(save_dir, plot_filename)
            
            self._create_waterfall_plot(frequencies, waterfall_array, timestamps, 
                                      config, plot_path)
            
            # Create summary statistics
            stats = {
                "center_frequency_mhz": config.center_freq / 1e6,
                "span_mhz": config.span / 1e6,
                "duration_seconds": duration,
                "num_measurements": num_measurements,
                "min_amplitude_dbm": float(np.min(waterfall_array)),
                "max_amplitude_dbm": float(np.max(waterfall_array)),
                "mean_amplitude_dbm": float(np.mean(waterfall_array)),
                "frequency_range_mhz": [float(frequencies[0]/1e6), float(frequencies[-1]/1e6)]
            }
            
            return {
                "success": True,
                "data_file": data_path,
                "plot_file": plot_path,
                "statistics": stats,
                "capture_duration": time.time() - start_time
            }
            
        except Exception as e:
            self.logger.error(f"Waterfall capture failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_waterfall_plot(self, frequencies: np.ndarray, waterfall_data: np.ndarray,
                              timestamps: List[datetime], config: SpectrumConfig, 
                              output_path: str):
        """
        Create and save waterfall plot
        
        Args:
            frequencies: Frequency array
            waterfall_data: 2D array of amplitude data
            timestamps: List of measurement timestamps
            config: SpectrumConfig used for measurement
            output_path: Path to save plot
        """
        plt.figure(figsize=(12, 8))
        
        # Create waterfall plot
        extent = [frequencies[0]/1e6, frequencies[-1]/1e6, 0, len(timestamps)]
        
        plt.imshow(waterfall_data, aspect='auto', origin='lower', 
                  extent=extent, cmap='viridis', interpolation='nearest')
        
        plt.colorbar(label='Amplitude (dBm)')
        plt.xlabel('Frequency (MHz)')
        plt.ylabel('Time (measurement index)')
        plt.title(f'Waterfall Display - {config.center_freq/1e9:.1f} GHz ± {config.span/1e6:.1f} MHz')
        
        # Add timestamp labels on y-axis
        if len(timestamps) <= 20:  # Only add time labels if not too many points
            time_labels = [t.strftime("%H:%M:%S") for t in timestamps[::max(1, len(timestamps)//10)]]
            plt.yticks(range(0, len(timestamps), max(1, len(timestamps)//10)), time_labels)
        
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"Waterfall plot saved to: {output_path}")


def get_analyzer_config() -> Dict[str, str]:
    """
    Get spectrum analyzer connection configuration from environment variables
    
    Returns:
        Dict with host, port, and timeout configuration
    """
    return {
        "host": os.environ.get("SA_HOST", "10.101.209.51"),
        "port": int(os.environ.get("SA_PORT", "5025")),
        "timeout": float(os.environ.get("SA_TIMEOUT", "10.0"))
    }


def capture_spectrum_waterfall(center_freq: float, span: float, duration: float,
                              interval: float, save_dir: str, 
                              filename_prefix: str = "waterfall",
                              rbw: Optional[float] = None,
                              ref_level: Optional[float] = None) -> Dict:
    """
    High-level function to capture spectrum waterfall
    
    Args:
        center_freq: Center frequency in Hz
        span: Frequency span in Hz
        duration: Total capture duration in seconds
        interval: Time between measurements in seconds
        save_dir: Directory to save results
        filename_prefix: Prefix for output files
        rbw: Resolution bandwidth in Hz (optional)
        ref_level: Reference level in dBm (optional)
        
    Returns:
        Dictionary with capture results
    """
    logger = logging.getLogger(__name__)
    
    # Get analyzer configuration
    analyzer_config = get_analyzer_config()
    
    # Create spectrum configuration
    spec_config = SpectrumConfig(
        center_freq=center_freq,
        span=span,
        rbw=rbw,
        ref_level=ref_level
    )
    
    # Initialize analyzer
    analyzer = KeysightEXA(
        host=analyzer_config["host"],
        port=analyzer_config["port"],
        timeout=analyzer_config["timeout"]
    )
    
    try:
        # Connect to analyzer
        if not analyzer.connect():
            return {
                "success": False,
                "error": "Failed to connect to spectrum analyzer"
            }
        
        # Capture waterfall
        result = analyzer.capture_waterfall(
            config=spec_config,
            duration=duration,
            interval=interval,
            save_dir=save_dir,
            filename_prefix=filename_prefix
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Waterfall capture error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
    
    finally:
        analyzer.disconnect()


if __name__ == "__main__":
    print("Use test_spectrum_analyzer.py for testing this module")
    print("Example:")
    print("  hatch run python test_spectrum_analyzer.py")