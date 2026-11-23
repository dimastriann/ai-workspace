"""Minimal stdio MCP server used by tests to exercise the stdio transport."""

import asyncio

from mcp.server.mcpserver import MCPServer

server = MCPServer("mini")


@server.tool()
def echo(text: str) -> str:
    """Echo the text back."""
    return f"echo: {text}"


if __name__ == "__main__":
    asyncio.run(server.run_stdio_async())
