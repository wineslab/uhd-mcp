#!/usr/bin/env python3
"""
FastMCP Server for USRP Control via UHD
"""

from fastmcp import FastMCP
import subprocess
import json
import signal
import os
from typing import Optional, Dict, Any
import threading
import time
import argparse

# Create the MCP server
mcp = FastMCP("USRP Control Server")

# Global variable to track running processes
running_processes = {}

@mcp.tool()
def uhd_find_devices() -> str:
    """Find all connected UHD devices"""
    try:
        result = subprocess.run(
            ["uhd_find_devices"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return json.dumps({
            "command": "uhd_find_devices",
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }, indent=2)
        
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds"
    except FileNotFoundError:
        return "Error: uhd_find_devices not found. Make sure UHD is installed and in PATH."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def uhd_usrp_probe(args: str = "") -> str:
    """Probe USRP device for detailed information"""
    try:
        cmd = ["uhd_usrp_probe"] + args.split() if args else ["uhd_usrp_probe"]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return json.dumps({
            "command": " ".join(cmd),
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }, indent=2)
        
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds"
    except FileNotFoundError:
        return "Error: uhd_usrp_probe not found. Make sure UHD is installed and in PATH."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def uhd_siggen(
    freq: float,
    rate: float = 1e6,
    gain: float = 10,
    wave_type: str = "SINE",
    wave_freq: float = 1000,
    amplitude: float = 0.3,
    duration: Optional[float] = None,
    args: str = ""
) -> str:
    """
    Run uhd_siggen to generate signals on USRP
    
    Args:
        freq: RF center frequency in Hz (e.g., 2.4e9 for 2.4 GHz)
        rate: Sample rate in Hz (default: 1e6)
        gain: TX gain in dB (default: 10)
        wave_type: Waveform type - CONST, SINE, RAMP, SQUARE (default: SINE)
        wave_freq: Waveform frequency in Hz (default: 1000)
        amplitude: Signal amplitude 0-1 (default: 0.3)
        duration: Duration in seconds (None for continuous)
        args: Additional arguments as string
    """
    try:
        cmd = [
            "uhd_siggen", 
            "--freq", str(freq),
            "--rate", str(rate),
            "--gain", str(gain),
            "--wave-type", wave_type,
            "--wave-freq", str(wave_freq),
            "--ampl", str(amplitude)
        ]
        
        # Add additional arguments
        if args:
            cmd.extend(args.split())
            
        # Generate a process ID
        process_id = f"siggen_{int(time.time())}"
        
        if duration:
            # Run for specified duration
            result = subprocess.run(
                cmd + ["--duration", str(duration)],
                capture_output=True,
                text=True,
                timeout=max(60, duration + 10)
            )
            
            return json.dumps({
                "process_id": process_id,
                "command": " ".join(cmd + ["--duration", str(duration)]),
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
                "duration": duration,
                "completed": True
            }, indent=2)
        else:
            # Run continuously in background
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            running_processes[process_id] = {
                "process": process,
                "command": " ".join(cmd),
                "start_time": time.time()
            }
            
            # Give it a moment to start
            time.sleep(1)
            
            if process.poll() is None:
                return json.dumps({
                    "process_id": process_id,
                    "command": " ".join(cmd),
                    "status": "running",
                    "pid": process.pid,
                    "success": True,
                    "message": f"Signal generation started. Use stop_process('{process_id}') to stop."
                }, indent=2)
            else:
                # Process terminated immediately
                stdout, stderr = process.communicate()
                return json.dumps({
                    "process_id": process_id,
                    "command": " ".join(cmd),
                    "return_code": process.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                    "success": False,
                    "message": "Process terminated immediately"
                }, indent=2)
                
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except FileNotFoundError:
        return "Error: uhd_siggen not found. Make sure UHD is installed and in PATH."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def stop_process(process_id: str) -> str:
    """Stop a running UHD process"""
    if process_id not in running_processes:
        return f"Process ID '{process_id}' not found. Use list_processes() to see running processes."
    
    try:
        process_info = running_processes[process_id]
        process = process_info["process"]
        
        if process.poll() is None:
            # Process is still running
            process.terminate()
            
            # Wait a bit for graceful termination
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if needed
                process.kill()
                process.wait()
            
            stdout, stderr = process.communicate()
            runtime = time.time() - process_info["start_time"]
            
            del running_processes[process_id]
            
            return json.dumps({
                "process_id": process_id,
                "command": process_info["command"],
                "status": "stopped",
                "runtime_seconds": round(runtime, 2),
                "stdout": stdout,
                "stderr": stderr,
                "success": True
            }, indent=2)
        else:
            # Process already terminated
            stdout, stderr = process.communicate()
            runtime = time.time() - process_info["start_time"]
            
            del running_processes[process_id]
            
            return json.dumps({
                "process_id": process_id,
                "command": process_info["command"],
                "status": "already_terminated",
                "return_code": process.returncode,
                "runtime_seconds": round(runtime, 2),
                "stdout": stdout,
                "stderr": stderr,
                "success": True
            }, indent=2)
            
    except Exception as e:
        return f"Error stopping process: {str(e)}"

@mcp.tool()
def list_processes() -> str:
    """List all running UHD processes"""
    if not running_processes:
        return "No running processes"
    
    processes_info = []
    current_time = time.time()
    
    for process_id, info in list(running_processes.items()):
        process = info["process"]
        
        if process.poll() is None:
            # Still running
            runtime = current_time - info["start_time"]
            processes_info.append({
                "process_id": process_id,
                "command": info["command"],
                "status": "running",
                "pid": process.pid,
                "runtime_seconds": round(runtime, 2)
            })
        else:
            # Process terminated, clean up
            del running_processes[process_id]
    
    return json.dumps(processes_info, indent=2)

@mcp.tool()
def uhd_rx_samples_to_file(
    freq: float,
    rate: float = 1e6,
    gain: float = 10,
    duration: float = 1.0,
    filename: str = "samples.dat",
    args: str = ""
) -> str:
    """
    Capture samples from USRP to file
    
    Args:
        freq: RF center frequency in Hz
        rate: Sample rate in Hz (default: 1e6)
        gain: RX gain in dB (default: 10)
        duration: Capture duration in seconds (default: 1.0)
        filename: Output filename (default: samples.dat)
        args: Additional arguments
    """
    try:
        cmd = [
            "uhd_rx_samples_to_file",
            "--freq", str(freq),
            "--rate", str(rate),
            "--gain", str(gain),
            "--duration", str(duration),
            "--file", filename
        ]
        
        if args:
            cmd.extend(args.split())
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(60, duration + 30)
        )
        
        # Check if file was created
        file_created = os.path.exists(filename)
        file_size = os.path.getsize(filename) if file_created else 0
        
        return json.dumps({
            "command": " ".join(cmd),
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
            "output_file": filename,
            "file_created": file_created,
            "file_size_bytes": file_size
        }, indent=2)
        
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except FileNotFoundError:
        return "Error: uhd_rx_samples_to_file not found. Make sure UHD is installed."
    except Exception as e:
        return f"Error: {str(e)}"

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
    """Get UHD installation and version information"""
    try:
        # Check UHD version
        result = subprocess.run(
            ["uhd_config_info", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        version_info = result.stdout if result.returncode == 0 else "Version not available"
        
        # Check UHD config
        result2 = subprocess.run(
            ["uhd_config_info"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        config_info = result2.stdout if result2.returncode == 0 else "Config not available"
        
        return json.dumps({
            "uhd_version": version_info.strip(),
            "uhd_config": config_info,
            "uhd_tools_available": True
        }, indent=2)
        
    except FileNotFoundError:
        return json.dumps({
            "error": "UHD tools not found in PATH",
            "uhd_tools_available": False
        }, indent=2)
    except Exception as e:
        return f"Error getting UHD info: {str(e)}"

def cleanup_on_exit():
    """Cleanup function for atexit"""
    if running_processes:
        for process_id in list(running_processes.keys()):
            try:
                stop_process(process_id)
            except:
                pass  # Ignore errors during cleanup

def main():
    """Main entry point for the USRP MCP server"""
    import atexit
    
    parser = argparse.ArgumentParser(
        description="USRP FastMCP Server for Software Defined Radio control",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Start HTTP server on default port 8080
  %(prog)s --port 9090               # Start HTTP server on port 9090
  %(prog)s --host 192.168.1.10       # Start on specific host
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
    
    args = parser.parse_args()
    
    # Cleanup on exit
    atexit.register(cleanup_on_exit)
    
    # Start server with HTTP transport
    print(f"Starting USRP FastMCP server on HTTP {args.host}:{args.port}/mcp")
    print("Available tools: uhd_find_devices, uhd_usrp_probe, uhd_siggen, uhd_rx_samples_to_file")
    print("Press Ctrl+C to stop the server")
    mcp.run(transport="http", host=args.host, port=args.port, path="/mcp")

if __name__ == "__main__":
    main()
