import os
from .tool_registry import register_tools


def run_mcp_server():
    transport = os.getenv("MCP_SERVER_TRANSPORT", "stdio")
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as e:
        print("MCP SDK not available. Install 'mcp' from requirements.txt.")
        raise

    app = FastMCP("dune-mcp")
    register_tools(app)

    if transport == "stdio":
        app.run()
    else:
        # For now fallback to stdio as default
        app.run()
