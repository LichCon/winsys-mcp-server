import logging
import sys

from server import main as server_main

# Set up root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("winsys-mcp")

def main():
    """
    Main entry point for the winsys-mcp-server application.
    
    This function serves as a wrapper around the server's main function,
    providing additional setup, argument processing, and error handling.
    """
    logger.info("Starting winsys-mcp-server")
    
    try:
        # Pass along any command line arguments
        server_main()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Exiting gracefully.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
