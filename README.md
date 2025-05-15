# winsys-mcp-server

MCP server to allow llm to interact with os window systems

## Tools used

- [Python](https://www.python.org/)
- [UV](https://docs.astral.sh/uv/getting-started/installation/) Project manager
- [ASDF](https://asdf-vm.com/) [Optional]
- [Quartz](https://github.com/ronaldoussoren/pyobjc/tree/master/pyobjc-framework-Quartz) bridge b/w python and XQuartz (MacOS only)
- [MCP SDK](https://github.com/modelcontextprotocol/python-sdk)

## Installation

1. Make sure you have Python 3.9+ installed
2. Install dependencies:

   ```bash
   pip install "mcp[cli]" pyobjc-framework-Quartz Pillow
   ```

   Or using UV:

   ```bash
   uv pip install "mcp[cli]" pyobjc-framework-Quartz Pillow
   ```

## Usage

### Starting the server

```bash
python server.py
```

This will start the MCP server using the standard STDIO transport. To use the server with Claude Desktop, you can install it using:

```bash
mcp install server.py
```

You can also specify a transport type as a command-line argument:

```bash
python server.py stdio     # Use STDIO transport (default)
python server.py sse       # Use SSE transport
python server.py streamable-http  # Use Streamable HTTP transport
```

### Available tools

The server provides the following tools:

1. `list_windows(exclude_zero_area=True, only_on_screen=True)`: Lists all windows in the system with their details (PID, Window ID, position, size, title).
2. `take_window_screenshot(window_id)`: Takes a screenshot of a specific window.
3. `take_fullscreen_screenshot()`: Takes a screenshot of the entire screen.
4. `find_window_by_title(title_search)`: Finds windows by searching in their titles.

### Example usage

With an AI assistant like Claude, you can use commands like:

1. "List all windows currently on my screen"
2. "Take a screenshot of the window with ID 12345"
3. "Take a full screenshot of my screen"
4. "Find all windows that have 'Chrome' in their title"

## Graceful Shutdown

This server implements comprehensive graceful shutdown handling that works across different transport types:

### Features

- Signal handling for SIGINT (Ctrl+C) and SIGTERM
- Transport-specific shutdown procedures for both STDIO and SSE
- Proper cleanup of resources and connections
- Customizable shutdown timeouts
- Detailed shutdown logging

### How it works

1. **Signal Handling**: The server captures SIGINT and SIGTERM signals and initiates a coordinated shutdown.
2. **Transport-Specific Handling**: Each transport type (STDIO, SSE, etc.) has specialized handlers that ensure proper cleanup.
3. **Resource Cleanup**: All resources are properly closed before the process terminates.
4. **Connection Management**: Active connections are tracked and gracefully closed with notifications to clients.

### Customizing Shutdown Behavior

Shutdown timeout and other behavior can be customized by editing the `server_shutdown.py` file:

- `default_timeout`: Default maximum time (in seconds) to wait for shutdown operations
- Adding custom pre-shutdown or post-shutdown hooks
- Implementing specialized cleanup for different resources

## Limitations

This MCP server is currently only compatible with macOS, as it relies on the Quartz framework for window management.

## Future Work

- Add support for Windows and Linux platforms
- Implement more window management features (focus, resize, move)
- Add ability to get window content for accessibility purposes
