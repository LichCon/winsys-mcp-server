"""
Shared FastMCP instance and logger for winsys-mcp-server.

This module must be imported by *server.py* and any other modules that need
access to the global `mcp` object so that a single instance is used
throughout the process.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Logging configuration (errors only, stderr handler)
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger("winsys-mcp-server")

# ---------------------------------------------------------------------------
# Shared FastMCP instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "WindowManager",
    description="MCP server for interacting with OS window systems",
    dependencies=["pyobjc-framework-Quartz", "Pillow", "pyobjc-framework-Cocoa"],
)

__all__ = ["logger", "mcp"]
