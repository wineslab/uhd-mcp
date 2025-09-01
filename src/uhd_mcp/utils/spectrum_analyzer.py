#!/usr/bin/env python3
"""
Keysight N9010B EXA Signal Analyzer Remote Control Script
Connects via Ethernet, configures frequency/bandwidth, and saves trace data
"""

import socket
import time
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import csv

class KeysightEXA:
    def __init__(self, ip_address, port=5025, timeout=10):
        """
        Initialize connection to Keysight EXA Signal Analyzer
        
        Args:
            ip_address (str): IP address of the instrument
            port (int): SCPI port (default 5025)
            timeout (int): Socket timeout in seconds
        """
        self.ip_address = ip_address
        self.port = port
        self.timeout = timeout
        self.socket = None
        self.connected = False
        
    def connect(self):
        """Establish connection to the instrument"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.ip_address, self.port))
            self.connected = True
            print(f"Connected to EXA at {self.ip_address}:{self.port}")
            
            # Get instrument identification
            idn = self.query("*IDN?")
            print(f"Instrument: {idn}")
            
        except Exception as e:
            print(f"Connection failed: {e}")
            self.connected = False
            raise
    
    def disconnect(self):
        """Close connection to the instrument"""
        if self.socket:
            self.socket.close()
            self.connected = False
            print("Disconnected from EXA")
    
    def send_command(self, command):
        """Send SCPI command to instrument"""
        if not self.connected:
            raise Exception("Not connected to instrument")
        
        try:
            # Add termination character
            cmd = command + '\n'
            self.socket.send(cmd.encode())
            time.sleep(0.1)  # Small delay for command processing
        except Exception as e:
            print(f"Error sending command '{command}': {e}")
            raise
    
    def query(self, command):
        """Send query and return response"""
        if not self.connected:
            raise Exception("Not connected to instrument")
        
        try:
            # Send query
            cmd = command + '\n'
            self.socket.send(cmd.encode())
            
            # Receive response - increase buffer size for trace data
            response = b""
            while True:
                try:
                    chunk = self.socket.recv(8192)
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
            
            return response.decode().strip()
            
        except Exception as e:
            print(f"Error querying '{command}': {e}")
            raise
    
    def reset(self):
        """Reset instrument to default state"""
        self.send_command("*RST")
        self.send_command("*CLS")  # Clear error queue
        time.sleep(2)  # Wait for reset to complete
        print("Instrument reset")
    
    def set_center_frequency(self, freq_hz):
        """
        Set center frequency
        
        Args:
            freq_hz (float): Center frequency in Hz
        """
        self.send_command(f"FREQ:CENT {freq_hz}")
        actual_freq = float(self.query("FREQ:CENT?"))
        print(f"Center frequency set to: {actual_freq/1e6:.3f} MHz")
        
    def set_span(self, span_hz):
        """
        Set frequency span (bandwidth)
        
        Args:
            span_hz (float): Frequency span in Hz
        """
        self.send_command(f"FREQ:SPAN {span_hz}")
        actual_span = float(self.query("FREQ:SPAN?"))
        print(f"Frequency span set to: {actual_span/1e6:.3f} MHz")
    
    def set_resolution_bandwidth(self, rbw_hz):
        """
        Set resolution bandwidth
        
        Args:
            rbw_hz (float): Resolution bandwidth in Hz
        """
        self.send_command(f"BAND:RES {rbw_hz}")
        actual_rbw = float(self.query("BAND:RES?"))
        print(f"Resolution bandwidth set to: {actual_rbw/1e3:.1f} kHz")
    
    def set_video_bandwidth(self, vbw_hz):
        """
        Set video bandwidth
        
        Args:
            vbw_hz (float): Video bandwidth in Hz
        """
        self.send_command(f"BAND:VID {vbw_hz}")
        actual_vbw = float(self.query("BAND:VID?"))
        print(f"Video bandwidth set to: {actual_vbw/1e3:.1f} kHz")
    
    def set_reference_level(self, ref_level_dbm):
        """
        Set reference level
        
        Args:
            ref_level_dbm (float): Reference level in dBm
        """
        self.send_command(f"DISP:WIND:TRAC:Y:RLEV {ref_level_dbm}")
        actual_ref = float(self.query("DISP:WIND:TRAC:Y:RLEV?"))
        print(f"Reference level set to: {actual_ref:.1f} dBm")
    
    def set_sweep_points(self, points):
        """
        Set number of sweep points
        
        Args:
            points (int): Number of sweep points
        """
        self.send_command(f"SWE:POIN {points}")
        actual_points = int(self.query("SWE:POIN?"))
        print(f"Sweep points set to: {actual_points}")
    
    def trigger_sweep(self):
        """Trigger a single sweep and wait for completion"""
        self.send_command("INIT:CONT OFF")  # Single sweep mode
        self.send_command("INIT:IMM")       # Trigger sweep
        
        # Wait for sweep to complete by checking operation complete
        self.send_command("*OPC?")          # Query operation complete
        opc_response = self.query("*OPC?")  # Wait for response
        
        print("Sweep completed")
    
    def get_trace_data(self, trace=1):
        """
        Get trace data from the analyzer
        
        Args:
            trace (int): Trace number (1-4)
            
        Returns:
            tuple: (frequencies, amplitudes) in Hz and dBm
        """
        # Get current analyzer settings to calculate frequency array
        center_freq = float(self.query("FREQ:CENT?"))
        span = float(self.query("FREQ:SPAN?"))
        num_points = int(self.query("SWE:POIN?"))
        
        # Calculate frequency array
        start_freq = center_freq - span/2
        stop_freq = center_freq + span/2
        frequencies = np.linspace(start_freq, stop_freq, num_points)
        
        # Get amplitude data for specified trace
        # Try different trace data query formats
        try:
            amp_data = self.query(f"TRAC:DATA? TRACE{trace}")
        except:
            try:
                amp_data = self.query(f"TRAC{trace}:DATA?")
            except:
                # Fallback to basic trace query
                amp_data = self.query("TRAC:DATA?")
        
        amplitudes = np.array([float(x) for x in amp_data.split(',')])
        
        # Ensure arrays are same length
        if len(frequencies) != len(amplitudes):
            print(f"Warning: Frequency points ({len(frequencies)}) != Amplitude points ({len(amplitudes)})")
            min_len = min(len(frequencies), len(amplitudes))
            frequencies = frequencies[:min_len]
            amplitudes = amplitudes[:min_len]
        
        return frequencies, amplitudes
    
    def save_trace_csv(self, filename, trace=1):
        """
        Save trace data to CSV file
        
        Args:
            filename (str): Output filename
            trace (int): Trace number to save
        """
        try:
            frequencies, amplitudes = self.get_trace_data(trace)
            
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Frequency (Hz)', 'Amplitude (dBm)'])
                for freq, amp in zip(frequencies, amplitudes):
                    writer.writerow([freq, amp])
            
            print(f"Trace data saved to: {filename}")
            return frequencies, amplitudes
            
        except Exception as e:
            print(f"Error saving trace data: {e}")
            raise
    
    def plot_trace(self, frequencies, amplitudes, title="Spectrum"):
        """
        Plot trace data
        
        Args:
            frequencies (array): Frequency data in Hz
            amplitudes (array): Amplitude data in dBm
            title (str): Plot title
        """
        plt.figure(figsize=(12, 6))
        plt.plot(frequencies/1e6, amplitudes, 'b-', linewidth=1)
        plt.xlabel('Frequency (MHz)')
        plt.ylabel('Amplitude (dBm)')
        plt.title(title)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()

def main():
    """Main function demonstrating EXA control"""
    
    # Configuration
    INSTRUMENT_IP = "10.101.209.51" 
    CENTER_FREQ = 2.4e9              # 2.4 GHz
    SPAN = 100e6                     # 100 MHz
    RBW = 1e6                        # 1 MHz
    VBW = 3e6                        # 3 MHz
    REF_LEVEL = 0                    # 0 dBm
    SWEEP_POINTS = 1001              # Number of points
    
    # Create timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"exa_trace_{timestamp}.csv"
    
    try:
        # Connect to instrument
        exa = KeysightEXA(INSTRUMENT_IP)
        exa.connect()
        
        # Test basic communication
        print("Testing communication...")
        print(f"Instrument ID: {exa.query('*IDN?')}")
        
        # Configure instrument
        print("\nConfiguring instrument...")
        exa.reset()
        
        # Wait after reset
        time.sleep(3)
        
        # Set instrument to spectrum analyzer mode
        exa.send_command("INST:SEL SA")  # Select spectrum analyzer mode
        
        exa.set_center_frequency(CENTER_FREQ)
        exa.set_span(SPAN)
        exa.set_resolution_bandwidth(RBW)
        exa.set_video_bandwidth(VBW)
        exa.set_reference_level(REF_LEVEL)
        exa.set_sweep_points(SWEEP_POINTS)
        
        # Perform measurement
        print("\nPerforming measurement...")
        exa.trigger_sweep()
        
        # Save and plot data
        print("\nSaving trace data...")
        frequencies, amplitudes = exa.save_trace_csv(csv_filename)
        
        # Plot the results
        title = f"EXA Spectrum - {CENTER_FREQ/1e6:.1f} MHz ± {SPAN/2e6:.1f} MHz"
        exa.plot_trace(frequencies, amplitudes, title)
        
        print(f"\nMeasurement complete!")
        print(f"Center: {CENTER_FREQ/1e6:.1f} MHz")
        print(f"Span: {SPAN/1e6:.1f} MHz")
        print(f"Points: {len(frequencies)}")
        print(f"Data saved to: {csv_filename}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Always disconnect
        try:
            exa.disconnect()
        except:
            pass

if __name__ == "__main__":
    main()