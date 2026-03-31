#!/usr/bin/env python3
"""
FastMCP Server for USRP Control via UHD and GNU Radio
"""

from fastmcp import FastMCP
from fastmcp.utilities.types import File, Image
import subprocess
import os
import logging
from typing import Optional, Dict, Any
import threading
import time
import argparse

import toons

from .utils import (
    parse_uhd_find_devices_output, 
    parse_uhd_config_info_output,
    get_shared_data_dir,
    capture_spectrum_waterfall as _capture_spectrum_waterfall
)


def format_output(data) -> str:
    """
    Serialize tool output using TOON (Token-Oriented Object Notation) — a compact,
    human-readable format optimised for LLM contexts. See https://toons.readthedocs.io
    """
    return toons.dumps(data)

# Create the MCP server
mcp = FastMCP("USRP Control Server")

# Global variable to track running processes
running_processes = {}

@mcp.tool()
def uhd_find_devices() -> str:
    """Find all connected UHD devices"""
    logger = logging.getLogger(__name__)
    try:
        logger.debug("Running uhd_find_devices")
        result = subprocess.run(
            ["uhd_find_devices"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Parse the output into structured format
        if result.returncode == 0 and result.stdout:
            parsed_devices = parse_uhd_find_devices_output(result.stdout)
            logger.info(f"Found {len(parsed_devices) if parsed_devices else 0} UHD devices")
            
            return format_output({
                "command": "uhd_find_devices",
                "return_code": result.returncode,
                "success": True,
                "parsed_output": parsed_devices,
                "raw_stdout": result.stdout,
                "stderr": result.stderr
            })
        else:
            logger.warning("uhd_find_devices failed or returned no output")
            return format_output({
                "command": "uhd_find_devices",
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
                "error": "No devices found or command failed"
            })
        
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds"
    except FileNotFoundError:
        return "Error: uhd_find_devices not found. Make sure UHD is installed and in PATH."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def uhd_usrp_probe(args: str = "") -> str:
    """Probe USRP device for detailed information"""
    logger = logging.getLogger(__name__)
    try:
        logger.debug(f"Running uhd_usrp_probe with args: {args}")
        cmd = ["uhd_usrp_probe"]
        
        # Parse arguments to handle command flags vs device args correctly
        if args:
            arg_parts = args.split()
            command_flags = []
            device_args = []
            
            # Separate command flags from device arguments
            i = 0
            while i < len(arg_parts):
                if arg_parts[i].startswith("--") and arg_parts[i] != "--args":
                    # This is a command flag (like --tree)
                    command_flags.append(arg_parts[i])
                elif arg_parts[i] == "--args":
                    # Everything after --args should be device arguments
                    i += 1
                    if i < len(arg_parts):
                        device_args.extend(arg_parts[i:])
                    break
                else:
                    # If we encounter a non-flag argument, treat it as device args
                    device_args.extend(arg_parts[i:])
                    break
                i += 1
            
            # Add command flags first
            cmd.extend(command_flags)
            
            # Add device arguments with --args if there are any
            if device_args:
                cmd.append("--args")
                cmd.append(" ".join(device_args))
        
        logging.debug(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # Increased timeout for probe operations
        )
        
        return format_output({
            "command": " ".join(cmd),
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        })
        
    except subprocess.TimeoutExpired:
        return "Command timed out after 60 seconds"
    except FileNotFoundError:
        return "Error: uhd_usrp_probe not found. Make sure UHD is installed and in PATH."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def uhd_siggen(
    freq: float,
    # USRP Arguments
    device_args: Optional[str] = None,
    spec: Optional[str] = None,
    antenna: Optional[str] = None,
    samp_rate: Optional[float] = None,
    gain: Optional[float] = None,
    power: Optional[float] = None,
    lo_offset: Optional[float] = None,
    channels: Optional[str] = None,
    lo_export: Optional[str] = None,
    lo_source: Optional[str] = None,
    otw_format: Optional[str] = None,
    stream_args: Optional[str] = None,
    verbose: bool = False,
    show_async_msg: bool = False,
    sync: Optional[str] = None,
    clock_source: Optional[str] = None,
    time_source: Optional[str] = None,
    # Siggen Arguments
    amplitude: Optional[float] = None,
    waveform_freq: Optional[float] = None,
    waveform2_freq: Optional[float] = None,
    waveform_type: str = "sine",  # sine, const, gaussian, uniform, 2tone, sweep
    offset: Optional[float] = None,
    # Control arguments
    duration: Optional[float] = 10.0,  # Default 10 seconds
    additional_args: Optional[str] = None
) -> str:
    """
    Run uhd_siggen to generate signals on USRP
    
    USRP Arguments:
        freq: RF center frequency in Hz (required, e.g., 2.4e9 for 2.4 GHz)
        device_args: UHD device address args
        spec: Subdevice(s) specification
        antenna: Select Tx antenna(s)
        samp_rate: Sample rate in Hz
        gain: TX gain in dB (conflicts with power)
        power: Reference power level in dBm (conflicts with gain)
        lo_offset: Daughterboard LO offset
        channels: Select Tx channels
        lo_export: TwinRX LO export settings
        lo_source: TwinRX LO source settings
        otw_format: Over-the-wire data format (sc16, sc12, sc8)
        stream_args: Additional stream arguments
        verbose: Use verbose console output
        show_async_msg: Show asynchronous message notifications
        sync: Synchronization mode (default, pps, auto)
        clock_source: Clock source (internal, external, gpsdo)
        time_source: Time source
    
    Siggen Arguments:
        amplitude: Output amplitude 0.0-1.0
        waveform_freq: Baseband waveform frequency in Hz
        waveform2_freq: Second waveform frequency in Hz (for 2tone)
        waveform_type: Waveform type (sine, const, gaussian, uniform, 2tone, sweep)
        offset: Waveform phase offset
    
    Control:
        duration: Duration in seconds (default: 10.0, set to None for continuous) - implemented by running process for specified time
        additional_args: Any additional command-line arguments as string
    
    Note: uhd_siggen runs continuously by default. Duration is implemented by starting the process
    and terminating it after the specified time, not via a UHD parameter.
    """
    try:
        logger = logging.getLogger(__name__)
        cmd = ["uhd_siggen"]
        
        # Required frequency argument
        cmd.extend(["--freq", str(freq)])
        
        # USRP Arguments
        if device_args:
            cmd.extend(["--args", device_args])
        if spec:
            cmd.extend(["--spec", spec])
        if antenna:
            cmd.extend(["--antenna", antenna])
        if samp_rate is not None:
            cmd.extend(["--samp-rate", str(samp_rate)])
        if gain is not None:
            cmd.extend(["--gain", str(gain)])
        if power is not None:
            cmd.extend(["--power", str(power)])
        if lo_offset is not None:
            cmd.extend(["--lo-offset", str(lo_offset)])
        if channels:
            cmd.extend(["--channels", channels])
        if lo_export:
            cmd.extend(["--lo-export", lo_export])
        if lo_source:
            cmd.extend(["--lo-source", lo_source])
        if otw_format:
            cmd.extend(["--otw-format", otw_format])
        if stream_args:
            cmd.extend(["--stream-args", stream_args])
        if verbose:
            cmd.append("--verbose")
        if show_async_msg:
            cmd.append("--show-async-msg")
        if sync:
            cmd.extend(["--sync", sync])
        if clock_source:
            cmd.extend(["--clock-source", clock_source])
        if time_source:
            cmd.extend(["--time-source", time_source])
            
        # Siggen Arguments
        if amplitude is not None:
            cmd.extend(["--amplitude", str(amplitude)])
        if waveform_freq is not None:
            cmd.extend(["--waveform-freq", str(waveform_freq)])
        if waveform2_freq is not None:
            cmd.extend(["--waveform2-freq", str(waveform2_freq)])
        if offset is not None:
            cmd.extend(["--offset", str(offset)])
            
        # Waveform type selection (mutually exclusive)
        if waveform_type.lower() == "sine":
            cmd.append("--sine")
        elif waveform_type.lower() == "const":
            cmd.append("--const")
        elif waveform_type.lower() == "gaussian":
            cmd.append("--gaussian")
        elif waveform_type.lower() == "uniform":
            cmd.append("--uniform")
        elif waveform_type.lower() == "2tone":
            cmd.append("--2tone")
        elif waveform_type.lower() == "sweep":
            cmd.append("--sweep")
        else:
            return format_output({
                "error": f"Invalid waveform_type '{waveform_type}'. Must be one of: sine, const, gaussian, uniform, 2tone, sweep",
                "success": False
            })
        
        # Add any additional arguments
        if additional_args:
            cmd.extend(additional_args.split())
            
        # Generate a process ID
        process_id = f"siggen_{int(time.time())}"
        
        logger.info(f"Starting uhd_siggen process {process_id} with command: {' '.join(cmd)}")
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True
        )
        
        # Store in running processes for management
        running_processes[process_id] = {
            "process": process,
            "command": " ".join(cmd),
            "start_time": time.time(),
            "duration": duration
        }
        
        # Set up automatic stopping for timed execution
        if duration is not None:
            def stop_after_duration():
                time.sleep(duration)
                if process_id in running_processes and process.poll() is None:
                    # Send newline to stop uhd_siggen gracefully
                    try:
                        process.stdin.write('\n')
                        process.stdin.flush()
                    except Exception as e:
                        logger.error(f"Failed to write to process stdin for {process_id}: {e}")
                        # If stdin fails, terminate normally
                        process.terminate()
            
            # Start timer thread
            timer_thread = threading.Thread(target=stop_after_duration, daemon=True)
            timer_thread.start()
        
        # Always return immediately with appropriate message
        time.sleep(0.5)  # Brief pause to check if process started successfully
        
        if process.poll() is None:
            # Process is running
            if duration is None:
                message = f"Signal generation started continuously. Use stop_process('{process_id}') to stop."
                logger.info(f"Process {process_id} started continuously")
            else:
                message = f"Signal generation started for {duration} seconds. Will stop automatically or use stop_process('{process_id}') to stop early."
                logger.info(f"Process {process_id} started for {duration} seconds")
            
            return format_output({
                "process_id": process_id,
                "command": " ".join(cmd),
                "status": "running",
                "pid": process.pid,
                "success": True,
                "duration": duration,
                "message": message
            })
        else:
            # Process terminated immediately
            logger.warning(f"Process {process_id} terminated immediately")
            stdout, stderr = process.communicate()
            if process_id in running_processes:
                del running_processes[process_id]
            
            return format_output({
                "process_id": process_id,
                "command": " ".join(cmd),
                "return_code": process.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "success": False,
                "duration": duration,
                "message": f"Process terminated immediately (intended duration: {duration} seconds)"
            })
                
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except FileNotFoundError:
        return "Error: uhd_siggen not found. Make sure UHD is installed and in PATH."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def stop_process(process_id: str) -> str:
    """Stop a running UHD process"""
    logger = logging.getLogger(__name__)
    
    if process_id not in running_processes:
        logger.warning(f"Attempt to stop unknown process: {process_id}")
        return f"Process ID '{process_id}' not found. Use list_processes() to see running processes."
    
    try:
        process_info = running_processes[process_id]
        process = process_info["process"]
        
        if process.poll() is None:
            # Process is still running - try graceful stop first (press enter)
            logger.info(f"Stopping running process {process_id} gracefully")
            try:
                process.stdin.write('\n')
                process.stdin.flush()
                process.wait(timeout=3)  # Wait up to 3 seconds for graceful stop
            except:
                # If stdin fails or timeout, use terminate
                logger.warning(f"Graceful stop failed for {process_id}, using terminate")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if needed
                    logger.warning(f"Process {process_id} required force kill")
                    process.kill()
                    process.wait()
            
            stdout, stderr = process.communicate()
            runtime = time.time() - process_info["start_time"]
            duration = process_info.get("duration", "continuous")
            
            del running_processes[process_id]
            
            logger.info(f"Process {process_id} stopped successfully after {round(runtime, 2)} seconds")
            
            return format_output({
                "process_id": process_id,
                "command": process_info["command"],
                "status": "stopped",
                "runtime_seconds": round(runtime, 2),
                "duration": duration,
                "stdout": stdout,
                "stderr": stderr,
                "success": True
            })
        else:
            # Process already terminated
            logger.info(f"Process {process_id} was already terminated")
            stdout, stderr = process.communicate()
            runtime = time.time() - process_info["start_time"]
            duration = process_info.get("duration", "continuous")
            
            del running_processes[process_id]
            
            return format_output({
                "process_id": process_id,
                "command": process_info["command"],
                "status": "already_terminated",
                "return_code": process.returncode,
                "runtime_seconds": round(runtime, 2),
                "duration": duration,
                "stdout": stdout,
                "stderr": stderr,
                "success": True
            })
            
    except Exception as e:
        return f"Error stopping process: {str(e)}"

@mcp.tool()
def list_processes() -> str:
    """List all running UHD processes"""
    if not running_processes:
        return "No running processes"
    
    processes_info = []
    current_time = time.time()
    terminated_ids = []
    
    for process_id, info in list(running_processes.items()):
        process = info["process"]
        
        if process.poll() is None:
            # Still running
            runtime = current_time - info["start_time"]
            duration = info.get("duration", "continuous")
            processes_info.append({
                "process_id": process_id,
                "command": info["command"],
                "status": "running",
                "pid": process.pid,
                "runtime_seconds": round(runtime, 2),
                "duration": duration
            })
        else:
            # Process terminated, add to clean up list
            terminated_ids.append(process_id)
    
    for process_id in terminated_ids:
        del running_processes[process_id]    

    return format_output(processes_info)

@mcp.tool()
def uhd_rx_cfile(
    freq: float,
    # Core UHD parameters from manpage
    args: Optional[str] = None,  # UHD device address args
    spec: Optional[str] = None,  # Subdevice specification  
    antenna: Optional[str] = None,  # Select Rx antenna
    samp_rate: float = 1e6,  # Sample rate (bandwidth)
    gain: Optional[float] = None,  # Gain in dB (default: midpoint)
    lo_offset: Optional[float] = None,  # Daughterboard LO offset
    # Output options
    output_shorts: bool = False,  # Output 16-bit shorts instead of floats
    nsamples: Optional[float] = None,  # Number of samples to collect
    verbose: bool = False,  # Verbose output
    additional_args: Optional[str] = None
) -> str:
    """
    Capture I/Q samples from USRP to complex file using GNU Radio uhd_rx_cfile
    
    Based on official manpage parameters:
        freq: RF center frequency in Hz (required)
        args: UHD device address args (e.g., "addr=192.168.10.2")
        spec: Subdevice of UHD device where appropriate
        antenna: Select Rx antenna where appropriate
        samp_rate: Sample rate (bandwidth) in Hz (default: 1e6)
        gain: Gain in dB (default: midpoint if not specified)
        lo_offset: Daughterboard LO offset (default: hw default)
        output_shorts: Output 16-bit interleaved shorts instead of complex floats
        nsamples: Number of samples to collect (default: infinite)
        verbose: Verbose output
        additional_args: Additional command-line arguments
        
    Returns filename of captured data file.
    """
    try:
        logger = logging.getLogger(__name__)
        
        # Get the shared data layer directory
        shared_data_dir = get_shared_data_dir()
        
        # Ensure the directory exists (create if needed)
        os.makedirs(shared_data_dir, exist_ok=True)
        
        # Generate unique filename with timestamp
        timestamp = int(time.time())
        extension = ".cfile" if not output_shorts else ".sfile"
        filename_base = f"uhd_rx_{timestamp}_{int(freq/1e6)}MHz{extension}"
        filename = os.path.join(shared_data_dir, filename_base)
        
        cmd = ["uhd_rx_cfile"]
        
        # Required frequency argument
        cmd.extend(["-f", str(freq)])
        
        # UHD device arguments
        if args:
            cmd.extend(["-a", args])
        
        # Subdevice specification
        if spec:
            cmd.extend(["--spec", spec])
        
        # Antenna selection
        if antenna:
            cmd.extend(["-A", antenna])
        
        # Sample rate
        cmd.extend(["--samp-rate", str(samp_rate)])
        
        # Gain settings
        if gain is not None:
            cmd.extend(["-g", str(gain)])
        
        # LO offset
        if lo_offset is not None:
            cmd.extend(["--lo-offset", str(lo_offset)])
        
        # Output format
        if output_shorts:
            cmd.append("-s")
        
        # Number of samples
        if nsamples is not None:
            cmd.extend(["-N", str(nsamples)])
        
        # Verbose output
        if verbose:
            cmd.append("-v")
        
        # Additional arguments
        if additional_args:
            cmd.extend(additional_args.split())
        
        # Output filename (must be last)
        cmd.append(filename)
        
        # Calculate expected duration for timeout
        if nsamples is not None:
            duration = nsamples / samp_rate
            timeout = max(60, duration + 30)
            logger.info(f"Starting uhd_rx_cfile: {nsamples} samples at {freq} Hz (estimated {duration:.2f}s) -> {filename}")
        else:
            # For infinite capture, use a reasonable timeout
            timeout = 300  # 5 minutes max
            logger.info(f"Starting uhd_rx_cfile: infinite capture at {freq} Hz (max {timeout}s timeout) -> {filename}")
        
        logger.debug(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        # Check if file was created and get its size
        file_created = os.path.exists(filename)
        file_size = os.path.getsize(filename) if file_created else 0
        
        # Calculate number of samples captured based on file size
        if file_created:
            if output_shorts:
                # 16-bit complex shorts (4 bytes per sample: 2 bytes I + 2 bytes Q)
                samples_captured = file_size // 4
            else:
                # 32-bit complex floats (8 bytes per sample: 4 bytes I + 4 bytes Q)
                samples_captured = file_size // 8
            
            logger.info(f"Capture completed: {samples_captured} samples captured, file size: {file_size} bytes, saved to: {filename}")
        else:
            samples_captured = 0
            logger.warning("No output file created during capture")
        
        return format_output({
            "command": " ".join(cmd),
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
            "capture_info": {
                "freq": freq,
                "samp_rate": samp_rate,
                "gain": gain,
                "samples_requested": nsamples,
                "samples_captured": samples_captured,
                "duration_seconds": samples_captured / samp_rate if samples_captured > 0 else 0,
                "output_format": "16-bit complex shorts" if output_shorts else "32-bit complex floats"
            },
            "output_file": filename,
            "file_created": file_created,
            "file_size_bytes": file_size
        })
        
    except subprocess.TimeoutExpired:
        return format_output({
            "success": False,
            "error": "Command timed out",
            "message": f"uhd_rx_cfile timed out after {timeout} seconds"
        })
    except FileNotFoundError:
        return format_output({
            "success": False,
            "error": "uhd_rx_cfile not found. Make sure GNU Radio and UHD are installed.",
            "command": "uhd_rx_cfile"
        })
    except Exception as e:
        return format_output({
            "success": False,
            "error": str(e),
            "command": "uhd_rx_cfile"
        })

@mcp.tool()
def list_shared_files(file_type: str = "all") -> str:
    """
    List all files in the shared data directory with optional filtering
    
    Args:
        file_type (str): Filter by file type:
                        "all" - all files (default)
                        "images" - PNG/JPG files (screenshots)
                        "captures" - DAT/complex files (RF captures)
    
    Returns:
        JSON with list of files and their information
    """
    try:
        logger = logging.getLogger(__name__)
        
        # Get the shared data layer directory
        shared_data_dir = get_shared_data_dir()
        
        # Check if directory exists
        if not os.path.exists(shared_data_dir):
            return format_output({
                "success": False,
                "error": f"Shared data directory {shared_data_dir} does not exist",
                "files": []
            })
        
        # Define file extensions for different types
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp'}
        capture_extensions = {'.dat', '.bin', '.complex', '.iq', '.cfile'}
        
        # List files based on filter
        files_info = []
        try:
            for filename in os.listdir(shared_data_dir):
                file_path = os.path.join(shared_data_dir, filename)
                
                # Skip directories
                if not os.path.isfile(file_path):
                    continue
                
                # Get file extension
                _, ext = os.path.splitext(filename.lower())
                
                # Apply filter
                if file_type == "images" and ext not in image_extensions:
                    continue
                elif file_type == "captures" and ext not in capture_extensions:
                    continue
                # For "all", include everything
                
                file_size = os.path.getsize(file_path)
                file_size_mb = file_size / (1024 * 1024)
                
                # Get file modification time
                mod_time = os.path.getmtime(file_path)
                
                # Determine file category
                if ext in image_extensions:
                    category = "image"
                elif ext in capture_extensions:
                    category = "capture"
                else:
                    category = "other"
                
                files_info.append({
                    "filename": filename,
                    "file_path": file_path,
                    "file_size_bytes": file_size,
                    "file_size_mb": round(file_size_mb, 2),
                    "modified_timestamp": mod_time,
                    "modified_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mod_time)),
                    "category": category,
                    "extension": ext
                })
        
        except PermissionError:
            return format_output({
                "success": False,
                "error": f"Permission denied accessing {shared_data_dir}",
                "files": []
            })
        
        # Sort by modification time (newest first)
        files_info.sort(key=lambda x: x["modified_timestamp"], reverse=True)
        
        logger.info(f"Listed {len(files_info)} files in shared data layer (filter: {file_type})")
        
        return format_output({
            "success": True,
            "shared_data_dir": shared_data_dir,
            "filter_applied": file_type,
            "total_files": len(files_info),
            "files": files_info
        })
        
    except Exception as e:
        logger.error(f"Error listing shared files: {str(e)}")
        return format_output({
            "success": False,
            "error": str(e),
            "files": []
        })

@mcp.tool()
def cleanup_all_processes() -> str:
    """Stop all running UHD processes"""
    if not running_processes:
        return "No processes to clean up"
    
    stopped_processes = []
    
    for process_id in list(running_processes.keys()):
        result = stop_process(process_id)
        stopped_processes.append(f"Stopped {process_id}")
    
    return f"Cleaned up {len(stopped_processes)} processes:\n" + "\n".join(stopped_processes)

@mcp.tool()
def get_uhd_info() -> str:
    """Get UHD installation and configuration information"""
    try:
        # Get comprehensive UHD config info with --print-all
        result = subprocess.run(
            ["uhd_config_info", "--print-all"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Build base response structure
        response = {
            "command": "uhd_config_info --print-all",
            "return_code": result.returncode,
            "success": result.returncode == 0,
            "raw_stdout": result.stdout,
            "stderr": result.stderr
        }
        
        # Add parsed output if successful and has output
        if result.returncode == 0 and result.stdout:
            response["parsed_output"] = parse_uhd_config_info_output(result.stdout)
        else:
            response["error"] = "Failed to get UHD configuration information"
        
        return format_output(response)
        
    except FileNotFoundError:
        return format_output({
            "error": "UHD tools not found in PATH",
            "uhd_tools_available": False
        })
    except subprocess.TimeoutExpired:
        return "Command timed out after 10 seconds"
    except Exception as e:
        return f"Error getting UHD info: {str(e)}"

@mcp.tool()
def capture_spectrum_waterfall(
    center_freq: float,
    span: float, 
    duration: float,
    filename_prefix: str = "waterfall",
    rbw: Optional[float] = None,
    ref_level: Optional[float] = None
) -> str:
    """
    Capture spectrum waterfall from Keysight EXA spectrum analyzer using continuous capture
    
    Args:
        center_freq: Center frequency in Hz (e.g., 2.4e9 for 2.4 GHz)
        span: Frequency span in Hz (e.g., 100e6 for 100 MHz)
        duration: Total capture duration in seconds
        filename_prefix: Prefix for output files (default: "waterfall")
        rbw: Resolution bandwidth in Hz (optional)
        ref_level: Reference level in dBm (optional)
        
    Returns:
        JSON with capture results, file paths, and statistics
    """
    try:
        logger = logging.getLogger(__name__)
        
        # Get the shared data layer directory  
        shared_data_dir = get_shared_data_dir()
        
        # Capture spectrum waterfall
        result = _capture_spectrum_waterfall(
            center_freq=center_freq,
            span=span,
            duration=duration,
            save_dir=shared_data_dir,
            filename_prefix=filename_prefix,
            rbw=rbw,
            ref_level=ref_level
        )
        
        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Spectrum waterfall capture failed: {error_msg}")
            return format_output({
                "success": False,
                "error": error_msg
            })
        
        # Get file sizes
        data_file = result.get("data_file", "")
        plot_file = result.get("plot_file", "")
        data_size = os.path.getsize(data_file) if os.path.exists(data_file) else 0
        plot_size = os.path.getsize(plot_file) if os.path.exists(plot_file) else 0
        
        logger.info(f"Spectrum waterfall captured: {data_file} ({data_size} bytes), {plot_file} ({plot_size} bytes)")
        
        return format_output({
            "success": True,
            "data_file": data_file,
            "plot_file": plot_file,
            "data_filename": os.path.basename(data_file) if data_file else "",
            "plot_filename": os.path.basename(plot_file) if plot_file else "",
            "data_size_bytes": data_size,
            "plot_size_bytes": plot_size,
            "statistics": result.get("statistics", {}),
            "capture_duration": result.get("capture_duration", 0)
        })
        
    except Exception as e:
        logger.error(f"Spectrum waterfall capture error: {str(e)}")
        return format_output({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def download_file(filename: str) -> File | Image:
    """
    Download a file from the shared data layer
    
    Args:
        filename: Name of the file to download from the shared data directory
        
    Returns:
        File or Image object with the file content, automatically handled by fastmcp
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Get the shared data directory
        shared_data_dir = get_shared_data_dir()
        file_path = os.path.join(shared_data_dir, filename)
        
        # Security check: ensure the file is within the shared data directory
        if not os.path.commonpath([shared_data_dir, file_path]) == shared_data_dir:
            raise ValueError("Access denied: file outside shared data directory")
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {filename}")
        
        # Check if it's actually a file (not a directory)
        if not os.path.isfile(file_path):
            raise ValueError(f"Path is not a file: {filename}")
        
        # Get file extension to determine if it's an image
        file_ext = os.path.splitext(filename)[1].lower()
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.svg'}
        
        logger.info(f"Downloading file: {filename} ({os.path.getsize(file_path)} bytes)")
        
        # Return appropriate type based on file extension
        if file_ext in image_extensions:
            return Image(path=file_path)
        else:
            return File(path=file_path, name=filename)
        
    except Exception as e:
        logger.error(f"File download error: {str(e)}")
        raise

def cleanup_on_exit():
    """Cleanup function for atexit"""
    logger = logging.getLogger(__name__)
    if running_processes:
        logger.info(f"Cleaning up {len(running_processes)} running processes on exit")
        for process_id in list(running_processes.keys()):
            try:
                stop_process(process_id)
                logger.debug(f"Cleaned up process {process_id}")
            except:
                logger.error(f"Failed to cleanup process {process_id}")
                pass  # Ignore errors during cleanup
    else:
        logger.debug("No processes to cleanup on exit")

def main():
    """Main entry point for the USRP MCP server"""
    import atexit
    import sys
    
    parser = argparse.ArgumentParser(
        description="USRP FastMCP Server for Software Defined Radio control",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Start HTTP server on default port 8080
  %(prog)s --port 9090               # Start HTTP server on port 9090
  %(prog)s --host 192.168.1.10       # Start on specific host
  %(prog)s --transport stdio         # Run locally over stdio (Claude Desktop, VS Code, etc.)
  %(prog)s --help                    # Show this help
"""
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to run the HTTP server on (default: 8080)"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--transport",
        type=str,
        default="http",
        choices=["http", "stdio"],
        help="Transport to use: 'http' for network access (default), 'stdio' for local MCP consumers such as Claude Desktop or VS Code"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # When running over stdio the MCP protocol uses stdout, so all logging
    # must be directed to stderr to avoid corrupting the data stream.
    log_stream = sys.stderr if args.transport == "stdio" else sys.stdout
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=log_stream
    )
    
    logger = logging.getLogger(__name__)
    
    # Cleanup on exit
    atexit.register(cleanup_on_exit)
    
    try:
        if args.transport == "stdio":
            logger.info("Starting USRP FastMCP server over stdio")
            logger.info(f"Shared data directory: {get_shared_data_dir()}")
            mcp.run(transport="stdio")
        else:
            # Start server with HTTP transport
            logger.info(f"Starting USRP FastMCP server on HTTP {args.host}:{args.port}/mcp")
            logger.info(f"Shared data directory: {get_shared_data_dir()}")
            logger.info("Press Ctrl+C to stop the server")
            mcp.run(transport="http", host=args.host, port=args.port, path="/mcp")
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise

if __name__ == "__main__":
    main()
