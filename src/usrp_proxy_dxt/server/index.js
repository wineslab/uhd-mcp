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
} from "@modelcontextprotocol/sdk/types.js";
import fetch from "node-fetch";

class USRPProxyServer {
  constructor() {
    this.server = new Server(
      {
        name: "usrp-proxy",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    // Configuration from environment variables
    this.serverUrl = process.env.USRP_SERVER_URL || "https://uhd-mcp-route-mcp-services.apps.tenoran.automation.otic.open6g.net/mcp/";
    this.requestTimeout = parseInt(process.env.REQUEST_TIMEOUT || "60") * 1000; // Convert to milliseconds
    this.debugMode = process.env.DEBUG_MODE === "true";
    this.sessionId = null;

    this.setupHandlers();
    this.logDebug("USRP Proxy server initialized");
    this.logDebug(`Server URL: ${this.serverUrl}`);
    this.logDebug(`Request timeout: ${this.requestTimeout}ms`);
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

      // Send initialize request
      const initRequest = {
        jsonrpc: "2.0",
        id: 1,
        method: "initialize",
        params: {
          protocolVersion: "2024-11-05",
          capabilities: {},
          clientInfo: { name: "usrp-proxy-dxt", version: "1.0.0" },
        },
      };

      const initResponse = await this.sendMCPRequest(initRequest);

      if (initResponse.error) {
        throw new Error(`Initialize failed: ${initResponse.error.message}`);
      }

      // Send initialized notification
      const initializedNotification = {
        jsonrpc: "2.0",
        method: "notifications/initialized",
      };

      await this.sendMCPRequest(initializedNotification);
      this.logDebug("MCP session initialized successfully");
    } catch (error) {
      this.logError("Failed to initialize MCP session", error);
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
      throw error;
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
            description: "Generate signals on USRP with configurable parameters",
            inputSchema: {
              type: "object",
              properties: {
                freq: {
                  type: "number",
                  description: "RF center frequency in Hz (e.g., 2.4e9 for 2.4 GHz)",
                },
                rate: {
                  type: "number",
                  description: "Sample rate in Hz",
                  default: 1e6,
                },
                gain: {
                  type: "number",
                  description: "TX gain in dB",
                  default: 10,
                },
                wave_type: {
                  type: "string",
                  description: "Waveform type",
                  enum: ["CONST", "SINE", "RAMP", "SQUARE"],
                  default: "SINE",
                },
                wave_freq: {
                  type: "number",
                  description: "Waveform frequency in Hz",
                  default: 1000,
                },
                amplitude: {
                  type: "number",
                  description: "Signal amplitude 0-1",
                  default: 0.3,
                },
                duration: {
                  type: "number",
                  description: "Duration in seconds (omit for continuous)",
                },
                args: {
                  type: "string",
                  description: "Additional arguments as string",
                  default: "",
                },
              },
              required: ["freq"],
            },
          },
          {
            name: "uhd_rx_samples_to_file",
            description: "Capture RF samples from USRP to file",
            inputSchema: {
              type: "object",
              properties: {
                freq: {
                  type: "number",
                  description: "RF center frequency in Hz",
                },
                rate: {
                  type: "number",
                  description: "Sample rate in Hz",
                  default: 1e6,
                },
                gain: {
                  type: "number",
                  description: "RX gain in dB",
                  default: 10,
                },
                duration: {
                  type: "number",
                  description: "Capture duration in seconds",
                  default: 1.0,
                },
                filename: {
                  type: "string",
                  description: "Output filename",
                  default: "samples.dat",
                },
                args: {
                  type: "string",
                  description: "Additional arguments",
                  default: "",
                },
              },
              required: ["freq"],
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
        ],
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
              text: JSON.stringify({
                success: false,
                error: error.message,
                tool: name,
                timestamp: new Date().toISOString(),
              }, null, 2),
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
    } catch (error) {
      this.logError("Failed to start USRP Proxy MCP server", error);
      process.exit(1);
    }
  }
}

// Start the proxy server
const proxyServer = new USRPProxyServer();
proxyServer.run().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
