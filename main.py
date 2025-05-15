"""
Entry point for winsys-mcp-server, providing window system access to LLMs.

This module initializes the server with proper error handling and logging.
"""

import logging
import sys

from server import main as server_main

# Set up minimal logging for errors only
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger("winsys-mcp")


def main() -> None:
    """
    Start the winsys-mcp-server application.

    This function serves as a wrapper around the server's main function,
    providing additional setup, argument processing, and error handling.
    """
    try:
        # Pass along any command line arguments
        server_main()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
