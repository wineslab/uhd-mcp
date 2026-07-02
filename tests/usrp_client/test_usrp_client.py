#!/usr/bin/env python3
"""Live end-to-end test for the USRP MCP server over HTTP.

Skipped unless UHD_MCP_LIVE_URL points at a running server, e.g.:

    UHD_MCP_LIVE_URL=http://127.0.0.1:8080/mcp hatch -e dev run test tests/usrp_client/

Can also be run standalone against a host/port:

    hatch run python tests/usrp_client/test_usrp_client.py 127.0.0.1 8080

The signal-generation and capture tests additionally require a reachable USRP;
they fail with the server-reported error if no device is present.
"""

import asyncio
import json
import os
import sys

import aiohttp
import pytest
import toons

LIVE_URL = os.environ.get("UHD_MCP_LIVE_URL", "")

pytestmark = pytest.mark.skipif(
    not LIVE_URL,
    reason="live e2e test: set UHD_MCP_LIVE_URL to a running server's /mcp endpoint",
)

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


class McpClient:
    """Minimal MCP-over-HTTP client (JSON-RPC with session header + SSE responses)."""

    def __init__(self, url: str):
        self.url = url
        self.session: aiohttp.ClientSession | None = None
        self.session_id: str | None = None
        self._next_id = 0

    async def __aenter__(self) -> "McpClient":
        # force_close avoids reusing a keep-alive connection the server may have
        # dropped while a test sleeps between calls.
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(force_close=True)
        )
        init_response = await self._post({
            "jsonrpc": "2.0",
            "id": self._request_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "usrp-live-test", "version": "1.0.0"},
            },
        })
        assert "result" in init_response, f"initialize failed: {init_response}"
        await self._post({"jsonrpc": "2.0", "method": "notifications/initialized"},
                         expect_body=False)
        return self

    async def __aexit__(self, *exc) -> None:
        assert self.session is not None
        await self.session.close()

    def _request_id(self) -> int:
        self._next_id += 1
        return self._next_id

    @staticmethod
    def _parse_sse(text: str) -> dict:
        for line in text.strip().split("\n"):
            if line.startswith("data: "):
                return json.loads(line[len("data: "):])
        raise AssertionError(f"no JSON data line in SSE response: {text!r}")

    async def _post(self, payload: dict, expect_body: bool = True) -> dict:
        assert self.session is not None
        headers = dict(HEADERS)
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        async with self.session.post(self.url, json=payload, headers=headers) as response:
            body = await response.text()
            assert response.status in (200, 202), (
                f"HTTP {response.status} {response.reason}: {body}"
            )
            if sid := response.headers.get("mcp-session-id"):
                self.session_id = sid
            if not expect_body:
                return {}
            if "text/event-stream" in response.headers.get("Content-Type", ""):
                return self._parse_sse(body)
            return json.loads(body)

    async def request(self, method: str, params: dict | None = None) -> dict:
        response = await self._post({
            "jsonrpc": "2.0",
            "id": self._request_id(),
            "method": method,
            "params": params or {},
        })
        assert "error" not in response, f"{method} returned error: {response['error']}"
        return response["result"]

    async def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        """Call a tool and parse its TOON text payload into a dict."""
        result = await self.request("tools/call", {"name": name, "arguments": arguments or {}})
        assert not result.get("isError"), f"tool {name} errored: {result}"
        text = result.get("content", [{}])[0].get("text", "")
        assert text, f"tool {name} returned empty content: {result}"
        return toons.loads(text)


async def test_list_tools():
    async with McpClient(LIVE_URL) as client:
        result = await client.request("tools/list")
        tool_names = {tool["name"] for tool in result.get("tools", [])}
        expected = {
            "uhd_find_devices", "uhd_usrp_probe", "uhd_siggen", "uhd_rx_cfile",
            "stop_process", "list_processes", "cleanup_all_processes",
            "get_uhd_info", "list_shared_files", "execute_uhd_script",
        }
        missing = expected - tool_names
        assert not missing, f"server is missing expected tools: {missing}"


async def test_get_uhd_info():
    async with McpClient(LIVE_URL) as client:
        info = await client.call_tool("get_uhd_info")
        assert info.get("success"), f"get_uhd_info failed: {info}"


async def test_find_devices():
    async with McpClient(LIVE_URL) as client:
        result = await client.call_tool("uhd_find_devices")
        assert result.get("success"), f"uhd_find_devices failed: {result}"
        parsed = result.get("parsed_output", {})
        assert parsed.get("total_devices", 0) >= 1, f"no USRP devices found: {result}"


async def test_probe_device():
    async with McpClient(LIVE_URL) as client:
        args = os.environ.get("USRP_ADDR", "")
        result = await client.call_tool(
            "uhd_usrp_probe", {"args": f"--args addr={args}" if args else ""}
        )
        assert result.get("success"), f"uhd_usrp_probe failed: {result}"


async def test_siggen_lifecycle():
    """Start a background siggen, see it in list_processes, then clean up."""
    async with McpClient(LIVE_URL) as client:
        arguments = {
            "freq": 2.4e9,
            "samp_rate": 1e6,
            "gain": 5,
            "waveform_type": "sine",
            "waveform_freq": 1000,
            "amplitude": 0.2,
            "duration": 30.0,
        }
        if addr := os.environ.get("USRP_ADDR"):
            arguments["device_args"] = f"addr={addr}"
        started = await client.call_tool("uhd_siggen", arguments)
        assert started.get("success"), f"uhd_siggen failed to start: {started}"
        process_id = started.get("process_id")
        assert process_id, f"no process_id in siggen response: {started}"

        processes = await client.call_tool("list_processes")
        assert str(process_id) in toons.dumps(processes), (
            f"siggen {process_id} not listed in running processes: {processes}"
        )

        stopped = await client.call_tool("stop_process", {"process_id": process_id})
        assert stopped.get("success"), f"stop_process failed: {stopped}"

        # cleanup_all_processes returns a plain string, not a TOON object
        cleanup = await client.call_tool("cleanup_all_processes")
        assert "No processes" in str(cleanup) or "Cleaned up" in str(cleanup), (
            f"unexpected cleanup_all_processes response: {cleanup}"
        )


async def test_rx_capture():
    """Capture a short burst of samples and verify the capture file is reported."""
    async with McpClient(LIVE_URL) as client:
        arguments = {
            "freq": 2.4e9,
            "samp_rate": 1e6,
            "gain": 10,
            "nsamples": 1e6,
        }
        if addr := os.environ.get("USRP_ADDR"):
            arguments["args"] = f"addr={addr}"
        started = await client.call_tool("uhd_rx_cfile", arguments)
        assert started.get("success"), f"uhd_rx_cfile failed to start: {started}"
        process_id = started.get("process_id")
        assert process_id, f"no process_id in rx_cfile response: {started}"

        await asyncio.sleep(5)

        stopped = await client.call_tool("stop_process", {"process_id": process_id})
        assert stopped.get("success"), f"stop_process failed: {stopped}"
        assert stopped.get("file_created"), f"capture file was not created: {stopped}"
        capture = stopped.get("capture_info", {})
        assert capture.get("samples_captured", 0) > 0, f"no samples captured: {stopped}"


async def _run_all() -> None:
    for test in (test_list_tools, test_get_uhd_info, test_find_devices,
                 test_probe_device, test_siggen_lifecycle, test_rx_capture):
        print(f"→ {test.__name__}")
        await test()
        print(f"✓ {test.__name__}")
    print("🎉 All live tests passed")


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = sys.argv[2] if len(sys.argv) > 2 else "8080"
    LIVE_URL = host if host.startswith("http") else f"http://{host}:{port}/mcp"
    print(f"Testing USRP MCP server at {LIVE_URL}")
    asyncio.run(_run_all())
