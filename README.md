# winsys-mcp-server

MCP server to allow llm to list and take screenshots of os windows

## Tools used

- [Python](https://www.python.org/)
- [UV](https://docs.astral.sh/uv/getting-started/installation/) Project manager
- [ASDF](https://asdf-vm.com/) [Optional]
- [Quartz](https://github.com/ronaldoussoren/pyobjc/tree/master/pyobjc-framework-Quartz) bridge b/w python and XQuartz (MacOS only)
- [MCP SDK](https://github.com/modelcontextprotocol/python-sdk)

## Installation

1. Make sure you have Python 3.13+ installed
2. Install uv
3. clone the repo and `cd` into it:
   ```bash
   git clone https://github.com/aurea-dev/winsys-mcp-server.git
   cd winsys-mcp-server
   ```
4. Create a virtual environment:
   ```bash
   uv venv
   ```
5. Install dependencies:
   ```bash
   uv pip sync
   ```

## Usage

### MCP Client Configuration

Below is an example configuration snippet for an MCP client, like Cursor, to run this server as a tool named 'winsys'. This configuration would typically be part of a larger JSON configuration file for the MCP client (e.g., `.cursor/mcp.json`):

```json
{
  "winsys": {
    "command": "uv",
    "args": ["run", "--directory=PATH_TO_REPO", "mcp", "run", "server.py"]
  }
}
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
2. "Take a screenshot of the window with name 'Google Chrome'"
3. "Take a full screenshot of my screen"
4. "Find all windows that have 'Chrome' in their title"

## Limitations

This MCP server is currently only compatible with macOS, as it relies on the Quartz framework for window management.
