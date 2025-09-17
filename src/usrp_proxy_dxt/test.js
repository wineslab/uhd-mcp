#!/usr/bin/env node

/**
 * Test script for USRP MCP Proxy Desktop Extension
 * 
 * This script tests the proxy server functionality by sending MCP requests
 * via stdio and validating the responses.
 */

import { spawn } from "child_process";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

class MCPProxyTester {
  constructor() {
    this.requestId = 1;
    this.serverProcess = null;
    this.testResults = [];
  }

  async startServer() {
    console.log("🚀 Starting USRP MCP Proxy server...");
    
    const serverPath = join(__dirname, "server", "index.js");
    
    this.serverProcess = spawn("node", [serverPath], {
      stdio: ["pipe", "pipe", "pipe"],
      env: {
        ...process.env,
        USRP_SERVER_URL: "https://uhd-mcp.your-domain.example/mcp",
        DEBUG_MODE: "true",
        REQUEST_TIMEOUT: "30"
      }
    });

    // Wait for server to start
    await new Promise((resolve) => {
      this.serverProcess.stderr.on("data", (data) => {
        const message = data.toString();
        console.log(`[SERVER] ${message.trim()}`);
        if (message.includes("USRP Proxy MCP server started successfully")) {
          resolve();
        }
      });
    });

    console.log("✅ Server started successfully");
  }

  async sendRequest(request) {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error("Request timeout"));
      }, 30000);

      this.serverProcess.stdout.on("data", (data) => {
        clearTimeout(timeout);
        try {
          const response = JSON.parse(data.toString());
          resolve(response);
        } catch (error) {
          reject(new Error(`Failed to parse response: ${data.toString()}`));
        }
      });

      this.serverProcess.stdin.write(JSON.stringify(request) + "\n");
    });
  }

  async testInitialize() {
    console.log("\n🔧 Testing initialize...");
    
    const request = {
      jsonrpc: "2.0",
      id: this.requestId++,
      method: "initialize",
      params: {
        protocolVersion: "2024-11-05",
        capabilities: {},
        clientInfo: { name: "mcp-test-client", version: "1.0.0" }
      }
    };

    try {
      const response = await this.sendRequest(request);
      console.log("✅ Initialize successful");
      console.log(`   Server capabilities: ${JSON.stringify(response.result?.capabilities || {})}`);
      this.testResults.push({ test: "initialize", success: true });
    } catch (error) {
      console.log(`❌ Initialize failed: ${error.message}`);
      this.testResults.push({ test: "initialize", success: false, error: error.message });
    }
  }

  async testListTools() {
    console.log("\n🔧 Testing tools/list...");
    
    const request = {
      jsonrpc: "2.0",
      id: this.requestId++,
      method: "tools/list",
      params: {}
    };

    try {
      const response = await this.sendRequest(request);
      const tools = response.result?.tools || [];
      console.log("✅ List tools successful");
      console.log(`   Found ${tools.length} tools:`);
      tools.forEach(tool => {
        console.log(`   - ${tool.name}: ${tool.description}`);
      });
      this.testResults.push({ test: "list_tools", success: true, toolCount: tools.length });
    } catch (error) {
      console.log(`❌ List tools failed: ${error.message}`);
      this.testResults.push({ test: "list_tools", success: false, error: error.message });
    }
  }

  async testToolCall(toolName, args = {}) {
    console.log(`\n🔧 Testing tools/call: ${toolName}...`);
    
    const request = {
      jsonrpc: "2.0",
      id: this.requestId++,
      method: "tools/call",
      params: {
        name: toolName,
        arguments: args
      }
    };

    try {
      const response = await this.sendRequest(request);
      console.log(`✅ Tool call successful: ${toolName}`);
      
      if (response.result?.content?.[0]?.text) {
        const resultText = response.result.content[0].text;
        const preview = resultText.length > 200 ? resultText.substring(0, 200) + "..." : resultText;
        console.log(`   Result preview: ${preview}`);
      }
      
      this.testResults.push({ test: `tool_${toolName}`, success: true });
    } catch (error) {
      console.log(`❌ Tool call failed: ${toolName} - ${error.message}`);
      this.testResults.push({ test: `tool_${toolName}`, success: false, error: error.message });
    }
  }

  async runTests() {
    try {
      await this.startServer();
      
      // Core MCP protocol tests
      await this.testInitialize();
      await this.testListTools();
      
      // Tool functionality tests
      await this.testToolCall("get_uhd_info");
      await this.testToolCall("uhd_find_devices");
      await this.testToolCall("list_processes");
      await this.testToolCall("download_file", { filename: "nonexistent.txt" }); // Test error handling
      
      // Test with arguments
      await this.testToolCall("uhd_usrp_probe", { args: "--tree" });
      
      console.log("\n📊 Test Results Summary:");
      console.log("========================");
      
      let passed = 0;
      let failed = 0;
      
      this.testResults.forEach(result => {
        const status = result.success ? "✅ PASS" : "❌ FAIL";
        const error = result.error ? ` (${result.error})` : "";
        console.log(`${status} ${result.test}${error}`);
        
        if (result.success) passed++;
        else failed++;
      });
      
      console.log(`\n📈 Total: ${passed + failed} tests, ${passed} passed, ${failed} failed`);
      
      if (failed === 0) {
        console.log("🎉 All tests passed! The USRP MCP Proxy is working correctly.");
      } else {
        console.log("⚠️  Some tests failed. Check the logs above for details.");
      }
      
    } catch (error) {
      console.error("💥 Test runner failed:", error);
    } finally {
      if (this.serverProcess) {
        this.serverProcess.kill();
        console.log("\n🛑 Server stopped");
      }
    }
  }
}

// Run the tests
const tester = new MCPProxyTester();
tester.runTests().catch(console.error);
