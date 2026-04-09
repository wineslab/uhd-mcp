#!/usr/bin/env node

/**
 * USRP MCP Proxy Server - Desktop Extension
 * 
 * This extension acts as a local MCP proxy for a remote USRP MCP server,
 * enabling Claude Desktop to control software-defined radio equipment
 * via UHD tools through HTTP requests.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListPromptsRequestSchema,
  ListResourcesRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import fetch from "node-fetch";
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { encode as toonEncode } from '@toon-format/toon';

// Read version from manifest.json
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const manifestPath = path.join(__dirname, '../manifest.json');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const VERSION = manifest.version;

class USRPProxyServer {
  constructor() {
    this.server = new Server(
      {
        name: "usrp-proxy",
        version: VERSION,
      },
      {
        capabilities: {
          tools: {},
          prompts: {},
          resources: {},
        },
      }
    );

    // Configuration from environment variables
    this.serverUrl = process.env.USRP_SERVER_URL || "https://uhd-mcp.your-domain.example/mcp";
    this.requestTimeout = parseInt(process.env.REQUEST_TIMEOUT || "60") * 1000; // Convert to milliseconds
    this.debugMode = process.env.DEBUG_MODE === "true"; // Disable debug by default in production
    this.sessionId = null;

    this.setupHandlers();
    this.logDebug("USRP Proxy server initialized");
    this.logDebug(`Server URL: ${this.serverUrl}`);
    this.logDebug(`Request timeout: ${this.requestTimeout}ms`);
    this.logDebug(`Version: ${VERSION}`);
  }

  logDebug(message) {
    if (this.debugMode) {
      console.error(`[DEBUG] ${new Date().toISOString()} - ${message}`);
    }
  }

  logError(message, error = null) {
    console.error(`[ERROR] ${new Date().toISOString()} - ${message}`);
    if (error && this.debugMode) {
      console.error(error);
    }
  }

  /**
   * Send HTTP request to remote MCP server with proper session management
   */
  async sendMCPRequest(request) {
    try {
      const headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
      };

      // Add session ID if we have one
      if (this.sessionId) {
        headers["mcp-session-id"] = this.sessionId;
      }

      this.logDebug(`Sending request: ${JSON.stringify(request)}`);

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.requestTimeout);

      const response = await fetch(this.serverUrl, {
        method: "POST",
        headers,
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Extract session ID from response headers if present
      const newSessionId = response.headers.get("mcp-session-id");
      if (newSessionId && !this.sessionId) {
        this.sessionId = newSessionId;
        this.logDebug(`Acquired session ID: ${this.sessionId}`);
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const contentType = response.headers.get("content-type");
      
      if (contentType && contentType.includes("text/event-stream")) {
        // Handle Server-Sent Events
        const responseText = await response.text();
        this.logDebug(`SSE Response: ${responseText}`);

        // Parse SSE format - look for data: lines
        const lines = responseText.trim().split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const jsonData = JSON.parse(line.substring(6)); // Remove 'data: ' prefix
              this.logDebug(`Parsed SSE data: ${JSON.stringify(jsonData)}`);
              return jsonData;
            } catch (parseError) {
              this.logError("Failed to parse SSE JSON", parseError);
              continue;
            }
          }
        }

        throw new Error("No valid JSON found in SSE response");
      } else {
        // Handle regular JSON response
        const jsonResponse = await response.json();
        this.logDebug(`JSON Response: ${JSON.stringify(jsonResponse)}`);
        return jsonResponse;
      }
    } catch (error) {
      if (error.name === "AbortError") {
        throw new Error(`Request timeout after ${this.requestTimeout}ms`);
      }
      this.logError("HTTP request failed", error);
      throw error;
    }
  }

  /**
   * Initialize MCP session with remote server
   */
  async initializeSession() {
    try {
      this.logDebug("Initializing MCP session...");
      this.logDebug(`Target server URL: ${this.serverUrl}`);

      // Send initialize request
      const initRequest = {
        jsonrpc: "2.0",
        id: 1,
        method: "initialize",
        params: {
          protocolVersion: "2024-11-05",
          capabilities: {},
          clientInfo: { name: "usrp-proxy-dxt", version: VERSION },
        },
      };

      this.logDebug(`Sending init request: ${JSON.stringify(initRequest)}`);
      const initResponse = await this.sendMCPRequest(initRequest);
      this.logDebug(`Init response: ${JSON.stringify(initResponse)}`);

      if (initResponse.error) {
        throw new Error(`Initialize failed: ${JSON.stringify(initResponse.error)}`);
      }

      // Send initialized notification
      const initializedNotification = {
        jsonrpc: "2.0",
        method: "notifications/initialized",
      };

      this.logDebug(`Sending initialized notification: ${JSON.stringify(initializedNotification)}`);
      
      // The initialized notification doesn't expect a response, so we handle it differently
      try {
        const response = await fetch(this.serverUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "mcp-session-id": this.sessionId,
          },
          body: JSON.stringify(initializedNotification),
        });

        // For notifications, we don't need to parse the response
        if (response.ok) {
          this.logDebug("Initialized notification sent successfully");
        } else {
          this.logDebug(`Initialized notification response: ${response.status} ${response.statusText}`);
        }
      } catch (error) {
        this.logDebug(`Initialized notification error (non-fatal): ${error.message}`);
        // Don't throw here - notifications are fire-and-forget
      }
      
      this.logDebug("MCP session initialized successfully");
      
      console.error("✅ Successfully connected to remote USRP server");
    } catch (error) {
      this.logError("Failed to initialize MCP session", error);
      console.error("❌ Failed to connect to remote USRP server:", error.message);
      throw error;
    }
  }

  /**
   * Forward tool call to remote server
   */
  async callRemoteTool(toolName, args = {}) {
    try {
      // Ensure session is initialized
      if (!this.sessionId) {
        this.logDebug("Session not initialized, attempting to initialize...");
        await this.initializeSession();
      }

      const toolRequest = {
        jsonrpc: "2.0",
        id: Date.now(),
        method: "tools/call",
        params: {
          name: toolName,
          arguments: args,
        },
      };

      this.logDebug(`Calling remote tool: ${toolName} with args: ${JSON.stringify(args)}`);

      const response = await this.sendMCPRequest(toolRequest);

      if (response.error) {
        throw new Error(`Tool call failed: ${response.error.message}`);
      }

      // Extract the content from the MCP response
      const result = response.result;
      if (result && result.content && Array.isArray(result.content)) {
        // Return the text content from the first content item
        return result.content[0]?.text || JSON.stringify(result);
      }

      return JSON.stringify(result || response);
    } catch (error) {
      this.logError(`Remote tool call failed for ${toolName}`, error);
      
      // Return a structured error response instead of throwing
      return toonEncode({
        success: false,
        error: error.message,
        tool: toolName,
        server_url: this.serverUrl,
        timestamp: new Date().toISOString(),
        debug_info: {
          session_id: this.sessionId,
          error_type: error.constructor.name
        }
      });
    }
  }

  setupHandlers() {
    // Handle tool listing
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      this.logDebug("Listing available tools");
      
      return {
        tools: [
          {
            name: "uhd_find_devices",
            description: "Find all connected UHD devices with structured JSON output",
            inputSchema: {
              type: "object",
              properties: {},
            },
          },
          {
            name: "uhd_usrp_probe",
            description: "Probe USRP device for detailed hardware information",
            inputSchema: {
              type: "object",
              properties: {
                args: {
                  type: "string",
                  description: "Arguments for uhd_usrp_probe (e.g., '--tree --args addr=192.168.40.28')",
                  default: "",
                },
              },
            },
          },
          {
            name: "uhd_siggen",
            description: "Generate signals on USRP with full parameter support - all UHD siggen capabilities",
            inputSchema: {
              type: "object",
              properties: {
                // Required
                freq: {
                  type: "number",
                  description: "RF center frequency in Hz (required, e.g., 2.4e9 for 2.4 GHz)",
                },
                // USRP Arguments
                device_args: {
                  type: "string",
                  description: "UHD device address args",
                },
                spec: {
                  type: "string",
                  description: "Subdevice(s) specification",
                },
                antenna: {
                  type: "string",
                  description: "Select Tx antenna(s)",
                },
                samp_rate: {
                  type: "number",
                  description: "Sample rate in Hz",
                },
                gain: {
                  type: "number",
                  description: "TX gain in dB (conflicts with power)",
                },
                power: {
                  type: "number",
                  description: "Reference power level in dBm (conflicts with gain)",
                },
                lo_offset: {
                  type: "number",
                  description: "Daughterboard LO offset",
                },
                channels: {
                  type: "string",
                  description: "Select Tx channels",
                },
                lo_export: {
                  type: "string",
                  description: "TwinRX LO export settings",
                },
                lo_source: {
                  type: "string",
                  description: "TwinRX LO source settings",
                },
                otw_format: {
                  type: "string",
                  description: "Over-the-wire data format",
                  enum: ["sc16", "sc12", "sc8"],
                },
                stream_args: {
                  type: "string",
                  description: "Additional stream arguments",
                },
                verbose: {
                  type: "boolean",
                  description: "Use verbose console output",
                  default: false,
                },
                show_async_msg: {
                  type: "boolean",
                  description: "Show asynchronous message notifications",
                  default: false,
                },
                sync: {
                  type: "string",
                  description: "Synchronization mode",
                  enum: ["default", "pps", "auto"],
                },
                clock_source: {
                  type: "string",
                  description: "Clock source (internal, external, gpsdo)",
                },
                time_source: {
                  type: "string",
                  description: "Time source",
                },
                // Siggen Arguments
                amplitude: {
                  type: "number",
                  description: "Output amplitude 0.0-1.0",
                },
                waveform_freq: {
                  type: "number",
                  description: "Baseband waveform frequency in Hz",
                },
                waveform2_freq: {
                  type: "number",
                  description: "Second waveform frequency in Hz (for 2tone)",
                },
                waveform_type: {
                  type: "string",
                  description: "Waveform type",
                  enum: ["sine", "const", "gaussian", "uniform", "2tone", "sweep"],
                  default: "sine",
                },
                offset: {
                  type: "number",
                  description: "Waveform phase offset",
                },
                // Control
                duration: {
                  type: "number",
                  description: "Duration in seconds (default: 10.0, set to null for continuous)",
                },
                additional_args: {
                  type: "string",
                  description: "Any additional command-line arguments",
                },
              },
              required: ["freq"],
            },
          },
          {
            name: "uhd_rx_cfile",
            description: "Capture I/Q samples from USRP to complex file using GNU Radio uhd_rx_cfile. Files are saved to shared data layer.",
            inputSchema: {
              type: "object",
              properties: {
                freq: {
                  type: "number",
                  description: "RF center frequency in Hz (required)",
                },
                // Core UHD parameters from manpage
                args: {
                  type: "string",
                  description: "UHD device address args (e.g., 'addr=192.168.10.2')",
                },
                spec: {
                  type: "string",
                  description: "Subdevice of UHD device where appropriate",
                },
                antenna: {
                  type: "string",
                  description: "Select Rx antenna where appropriate",
                },
                samp_rate: {
                  type: "number",
                  description: "Sample rate (bandwidth) in Hz",
                  default: 1e6,
                },
                gain: {
                  type: "number",
                  description: "Gain in dB (default: midpoint if not specified)",
                },
                lo_offset: {
                  type: "number",
                  description: "Daughterboard LO offset (default: hw default)",
                },
                // Output options
                output_shorts: {
                  type: "boolean",
                  description: "Output 16-bit interleaved shorts instead of complex floats",
                  default: false,
                },
                nsamples: {
                  type: "number",
                  description: "Number of samples to collect (omit for infinite)",
                },
                verbose: {
                  type: "boolean",
                  description: "Verbose output",
                  default: false,
                },
                additional_args: {
                  type: "string",
                  description: "Additional command-line arguments",
                },
              },
              required: ["freq"],
            },
          },
          {
            name: "list_shared_files",
            description: "List all files in the shared data directory (captures, screenshots, etc.)",
            inputSchema: {
              type: "object",
              properties: {
                file_type: {
                  type: "string",
                  description: "Filter by file type (optional): 'images' for PNG/JPG, 'captures' for DAT/complex files, 'all' for everything",
                  enum: ["all", "images", "captures"],
                  default: "all"
                },
              },
            },
          },
          {
            name: "get_uhd_info",
            description: "Get UHD installation and configuration information",
            inputSchema: {
              type: "object",
              properties: {},
            },
          },
          {
            name: "stop_process",
            description: "Stop a running UHD background process",
            inputSchema: {
              type: "object",
              properties: {
                process_id: {
                  type: "string",
                  description: "ID of the process to stop",
                },
              },
              required: ["process_id"],
            },
          },
          {
            name: "list_processes",
            description: "List all running UHD background processes",
            inputSchema: {
              type: "object",
              properties: {},
            },
          },
          {
            name: "cleanup_all_processes",
            description: "Stop all running UHD background processes",
            inputSchema: {
              type: "object",
              properties: {},
            },
          },
          {
            name: "capture_spectrum_waterfall",
            description: "Capture spectrum waterfall from Keysight EXA spectrum analyzer using continuous capture. Saves data/plot files in the shared data directory.",
            inputSchema: {
              type: "object",
              properties: {
                center_freq: {
                  type: "number",
                  description: "Center frequency in Hz (e.g., 2.4e9 for 2.4 GHz)",
                },
                span: {
                  type: "number", 
                  description: "Frequency span in Hz (e.g., 100e6 for 100 MHz)",
                },
                duration: {
                  type: "number",
                  description: "Total capture duration in seconds",
                },
                filename_prefix: {
                  type: "string",
                  description: "Prefix for output files (default: 'waterfall')",
                },
                rbw: {
                  type: "number",
                  description: "Resolution bandwidth in Hz (optional)",
                },
                ref_level: {
                  type: "number", 
                  description: "Reference level in dBm (optional)",
                },
              },
              required: ["center_freq", "span", "duration"],
            },
          },
          {
            name: "download_file",
            description: "Download a file from the shared data layer. Returns the actual file content (images as ImageContent, other files as EmbeddedResource with proper MIME types)",
            inputSchema: {
              type: "object",
              properties: {
                filename: {
                  type: "string",
                  description: "Name of the file to download from the shared data directory",
                },
              },
              required: ["filename"],
            },
          },
        ],
      };
    });

    // Handle prompts listing
    this.server.setRequestHandler(ListPromptsRequestSchema, async () => {
      this.logDebug("Listing available prompts");
      
      return {
        prompts: [], // No prompts supported by this proxy
      };
    });

    // Handle resources listing
    this.server.setRequestHandler(ListResourcesRequestSchema, async () => {
      this.logDebug("Listing available resources");
      
      return {
        resources: [], // No resources supported by this proxy
      };
    });

    // Handle tool execution
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        this.logDebug(`Executing tool: ${name}`);

        // Forward the tool call to the remote server
        const result = await this.callRemoteTool(name, args);

        return {
          content: [
            {
              type: "text",
              text: result,
            },
          ],
        };
      } catch (error) {
        this.logError(`Tool execution failed: ${name}`, error);

        return {
          content: [
            {
              type: "text",
              text: toonEncode({
                success: false,
                error: error.message,
                tool: name,
                timestamp: new Date().toISOString(),
              }),
            },
          ],
          isError: true,
        };
      }
    });
  }

  async run() {
    try {
      this.logDebug("Starting USRP Proxy MCP server...");

      const transport = new StdioServerTransport();
      await this.server.connect(transport);

      this.logDebug("USRP Proxy MCP server running on stdio");
      console.error("USRP Proxy MCP server started successfully");
      
      // Pre-initialize the session to test connectivity
      try {
        this.logDebug("Testing connection to remote server...");
        await this.initializeSession();
        this.logDebug("Successfully connected to remote server");
      } catch (error) {
        this.logError("Failed to connect to remote server during startup - will retry on first tool call", error);
        // Don't exit, just log the error and continue
        this.sessionId = null;
      }
    } catch (error) {
      this.logError("Failed to start USRP Proxy MCP server", error);
      console.error("STACK TRACE:", error.stack);
      process.exit(1);
    }
  }
}

// Start the proxy server
console.error("🚀 Starting USRP MCP Proxy...");
console.error(`📡 Target server: ${process.env.USRP_SERVER_URL || "https://uhd-mcp.your-domain.example/mcp"}`);
console.error(`🐛 Debug mode: ${process.env.DEBUG_MODE === "true" ? "ON" : "OFF"}`);

// Add process event handlers for better debugging
process.on('uncaughtException', (error) => {
  console.error('💥 Uncaught Exception:', error.message);
  console.error('Stack trace:', error.stack);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('💥 Unhandled Rejection at:', promise);
  console.error('Reason:', reason);
  process.exit(1);
});

const proxyServer = new USRPProxyServer();
proxyServer.run().catch((error) => {
  console.error("💥 Fatal error during startup:", error.message);
  console.error("Stack trace:", error.stack);
  process.exit(1);
});
