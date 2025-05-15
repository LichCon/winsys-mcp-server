import os
import sys
from io import BytesIO
from typing import Any, Dict, List, Optional

# Check if we're on macOS
if sys.platform != 'darwin':
    print("Error: This MCP server is only compatible with macOS.")
    sys.exit(1)

try:
    # Import macOS specific libraries
    import Quartz.CoreGraphics as CG
    from Foundation import NSData
    from PIL import Image
    from Quartz import (
        CGDataProviderCopyData,
        CGImageGetDataProvider,
        CGImageGetHeight,
        CGImageGetWidth,
        CGRectMake,
        CGRectNull,
        CGWindowListCopyWindowInfo,
        CGWindowListCreateImage,
        NSBitmapImageRep,
        NSImage,
        kCGNullWindowID,
        kCGWindowImageDefault,
        kCGWindowListExcludeDesktopElements,
        kCGWindowListOptionAll,
        kCGWindowListOptionOnScreenOnly,
    )
except ImportError as e:
    print(f"Error importing macOS libraries: {e}")
    print("Please ensure pyobjc-framework-Quartz is installed.")
    sys.exit(1)

# Import MCP SDK for server implementation
import logging

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp import Image as McpImage

# Set up minimal logging for errors only
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("winsys-mcp-server")

from server_shutdown import ShutdownReason, shutdown_manager

# Import shutdown handling utilities
from signal_handler import graceful_shutdown
from transport_handlers import sse_handler, stdio_handler

# Create MCP server
mcp = FastMCP(
    "WindowManager", 
    description="MCP server for interacting with OS window systems",
    dependencies=["pyobjc-framework-Quartz", "Pillow"]
)

@mcp.tool()
def list_windows(exclude_zero_area: bool = True, only_on_screen: bool = True) -> str:
    """List all windows in the system with their details.
    
    Args:
        exclude_zero_area: If True, windows with zero area will be excluded.
        only_on_screen: If True, only windows currently on screen will be listed.
    
    Returns:
        Formatted string containing window details including PID, Window ID, 
        position, size, and title.
    """
    # Set options for window listing
    options = kCGWindowListOptionAll
    if only_on_screen:
        options = options | kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements
    
    # Get window list
    window_list = CGWindowListCopyWindowInfo(options, kCGNullWindowID)
    
    # Format the result
    result = "  PID  WinID  (x, y, w, h)           [Title] SubTitle\n"
    result += "-----  -----  ---------------------  -------------------------------------------\n"
    
    for window in window_list:
        # Get window properties
        pid = window.get('kCGWindowOwnerPID', 0)
        win_id = window.get('kCGWindowNumber', 0)
        
        # Get window bounds
        bounds = window.get('kCGWindowBounds', {})
        x = bounds.get('X', 0)
        y = bounds.get('Y', 0)
        width = bounds.get('Width', 0)
        height = bounds.get('Height', 0)
        
        # Skip windows with zero area if requested
        if exclude_zero_area and (width == 0 or height == 0):
            continue
        
        # Get window title and owner name
        title = window.get('kCGWindowOwnerName', '')
        subtitle = window.get('kCGWindowName', '')
        
        # Format the line
        result += f"{pid:5d}  {win_id:5d}  ({x:4.0f}, {y:4.0f}, {width:4.0f}, {height:4.0f})  [{title}] {subtitle}\n"
    
    return result

@mcp.tool()
def take_window_screenshot(window_id: int) -> McpImage:
    """Take a screenshot of a specific window.
    
    Args:
        window_id: The ID of the window to capture.
    
    Returns:
        An image of the specified window.
    """
    try:
        # Create a screenshot of the specified window
        image_ref = CGWindowListCreateImage(
            CGRectNull,  # Null rect means capture the entire window
            kCGWindowListOptionAll,
            window_id,  # The specific window ID to capture
            kCGWindowImageDefault
        )
        
        if not image_ref:
            return "Error: Could not capture window. The window ID may be invalid."
        
        # Get image dimensions
        width = CGImageGetWidth(image_ref)
        height = CGImageGetHeight(image_ref)
        
        # Convert the CGImage to PNG data
        bitmap_rep = NSBitmapImageRep.alloc().initWithCGImage_(image_ref)
        png_data = bitmap_rep.representationUsingType_properties_(3, None)  # 3 = NSPNGFileType
        
        # Convert to bytes and create an MCP Image
        png_bytes = bytes(png_data)
        
        # Return the image
        return McpImage(data=png_bytes, format="png")
    
    except Exception as e:
        logger.error(f"Error taking screenshot: {str(e)}")
        return f"Error taking screenshot: {str(e)}"

@mcp.tool()
def take_fullscreen_screenshot() -> McpImage:
    """Take a screenshot of the entire screen.
    
    Returns:
        An image of the entire screen.
    """
    try:
        # Create a screenshot of the entire screen
        image_ref = CGWindowListCreateImage(
            CGRectNull,  # Null rect means capture the entire screen
            kCGWindowListOptionOnScreenOnly,
            kCGNullWindowID,  # Null window ID means all windows
            kCGWindowImageDefault
        )
        
        if not image_ref:
            return "Error: Could not capture screen."
        
        # Get image dimensions
        width = CGImageGetWidth(image_ref)
        height = CGImageGetHeight(image_ref)
        
        # Convert the CGImage to PNG data
        bitmap_rep = NSBitmapImageRep.alloc().initWithCGImage_(image_ref)
        png_data = bitmap_rep.representationUsingType_properties_(3, None)  # 3 = NSPNGFileType
        
        # Convert to bytes and create an MCP Image
        png_bytes = bytes(png_data)
        
        # Return the image
        return McpImage(data=png_bytes, format="png")
    
    except Exception as e:
        logger.error(f"Error taking screenshot: {str(e)}")
        return f"Error taking screenshot: {str(e)}"

@mcp.tool()
def find_window_by_title(title_search: str) -> str:
    """Find windows by searching in their titles.
    
    Args:
        title_search: Text to search for in window titles and application names.
    
    Returns:
        Formatted string containing matching window details.
    """
    title_search = title_search.lower()
    
    # Get window list
    window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionAll, kCGNullWindowID)
    
    # Format the result
    result = "  PID  WinID  (x, y, w, h)           [Title] SubTitle\n"
    result += "-----  -----  ---------------------  -------------------------------------------\n"
    matching_windows = False
    
    for window in window_list:
        # Get window properties
        pid = window.get('kCGWindowOwnerPID', 0)
        win_id = window.get('kCGWindowNumber', 0)
        
        # Get window title and owner name
        title = window.get('kCGWindowOwnerName', '')
        subtitle = window.get('kCGWindowName', '')
        
        # Check if the search term is in the title or subtitle
        if (title_search in title.lower() or title_search in subtitle.lower()):
            matching_windows = True
            
            # Get window bounds
            bounds = window.get('kCGWindowBounds', {})
            x = bounds.get('X', 0)
            y = bounds.get('Y', 0)
            width = bounds.get('Width', 0)
            height = bounds.get('Height', 0)
            
            # Format the line
            result += f"{pid:5d}  {win_id:5d}  ({x:4.0f}, {y:4.0f}, {width:4.0f}, {height:4.0f})  [{title}] {subtitle}\n"
    
    if not matching_windows:
        return f"No windows found with title containing '{title_search}'"
    
    return result

# Register custom handlers for specific transports
def _register_transport_streams(transport_type, *args):
    """
    Register transport streams with the appropriate handler.
    
    Args:
        transport_type: The type of transport being used
        *args: Transport-specific stream objects
    """
    if transport_type == "stdio" and len(args) >= 2:
        # Register stdio streams
        read_stream, write_stream = args[:2]
        stdio_handler.set_streams(read_stream, write_stream)
    elif transport_type == "sse" and len(args) >= 1:
        # Register SSE app
        app = args[0]
        # Note: SSE sessions would be registered separately when they connect
        pass

# Store original run method
original_run = mcp.run

# Override run to add shutdown handling
def run_with_shutdown(*args, **kwargs):
    """
    Wrap the original run method with shutdown handling.
    
    This intercepts the run method to add signal handling and 
    graceful shutdown support.
    """
    # Set up signal handlers
    graceful_shutdown.setup_signal_handlers()
    
    # Extract transport type
    transport = kwargs.get('transport', 'stdio')
    
    try:
        # Call original run method
        result = original_run(*args, **kwargs)
        return result
    except KeyboardInterrupt:
        # Handle KeyboardInterrupt gracefully
        import asyncio
        asyncio.run(shutdown_manager.shutdown(ShutdownReason.SIGNAL))
    except Exception as e:
        logger.error(f"Error during server execution: {e}")
        # Handle other exceptions with graceful shutdown
        import asyncio
        asyncio.run(shutdown_manager.shutdown(ShutdownReason.ERROR))
        raise
    finally:
        # Restore signal handlers
        graceful_shutdown.restore_signal_handlers()

# Replace run method with our wrapped version
mcp.run = run_with_shutdown

# Add cleanup function for graceful shutdown
def cleanup():
    """Perform clean-up operations before shutdown."""
    pass  # No logging needed

# Register cleanup with shutdown manager
shutdown_manager.register_pre_shutdown_hook(cleanup)

def main():
    """Main entry point for the MCP server."""
    # Detect if a transport type is specified as command-line argument
    transport = "stdio"  # Default
    if len(sys.argv) > 1 and sys.argv[1] in ["stdio", "sse", "streamable-http"]:
        transport = sys.argv[1]
    
    try:
        if transport == "sse":
            mcp.run(transport="sse")
        elif transport == "streamable-http":
            mcp.run(transport="streamable-http")
        else:  # Default to stdio
            mcp.run()
    except Exception as e:
        logger.error(f"Error running server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 