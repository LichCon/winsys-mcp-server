# winsys-mcp-server

MCP server to allow llm to list and take screenshots of os windows

## Installation

1. Make sure you have Python 3.13+ installed
2. Install uv
3. download the repo:
   ```bash
   git clone https://github.com/aurea-dev/winsys-mcp-server.git
   ```

## Usage

### MCP Client Configuration

Below is an example configuration snippet for an MCP client, like Cursor. This configuration would typically be part of a larger JSON configuration file for the MCP client (e.g., `.cursor/mcp.json`):

```json
{
  "winsys": {
    "command": "uv",
    "args": [
      "run",
      "--directory=PATH_TO_DOWNLOADED_REPO",
      "mcp",
      "run",
      "server.py"
    ]
  }
}
```

### Available tools

The server provides the following tools:

1. `list_windows(exclude_zero_area=True, only_on_screen=True)`: Lists all windows in the system with their details (PID, Window ID, position, size, title).
2. `take_window_screenshot(window_id)`: Takes a screenshot of a specific window.
3. `take_fullscreen_screenshot()`: Takes a screenshot of the entire screen.
4. `find_window_by_title(title_search)`: Finds windows by searching in their titles.
5. `activate_window(window_id)`: Brings the application that owns the given window to the foreground.

### Example usage

With an AI assistant like Claude, you can use commands like:

1. "List all windows currently on my screen"
2. "Take a screenshot of the window with name 'Google Chrome'"
3. "Take a full screenshot of my screen"
4. "Find all windows that have 'Chrome' in their title"

## Tools used

- [Python](https://www.python.org/)
- [UV](https://docs.astral.sh/uv/getting-started/installation/) Project manager
- [ASDF](https://asdf-vm.com/) [Optional]
- [Quartz](https://github.com/ronaldoussoren/pyobjc/tree/master/pyobjc-framework-Quartz) bridge b/w python and XQuartz (MacOS only)
- [MCP SDK](https://github.com/modelcontextprotocol/python-sdk)

## Limitations

This MCP server is currently only compatible with macOS, as it relies on the Quartz framework for window management.

## New Interaction Tools (macOS)

These tools allow mouse, keyboard, and query-style interactions with the window system.
All coordinates are in pixels.

| Tool                | Signature                                                     | Description                                                                 |
| ------------------- | ------------------------------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `move_mouse`        | `(x: int, y: int, window_id: int                              | None = None)`                                                               | Move cursor. If `window_id` provided, coordinates are relative to that window.                                            |
| `click_at`          | `(x: int, y: int, button: str = "left", window_id: int        | None = None)`                                                               | Click at position.                                                                                                        |
| `drag`              | `(from_x, from_y, to_x, to_y, button="left", window_id=None)` | Drag from point A to B.                                                     |
| `type_text`         | `(text: str, window_id: int                                   | None = None)`                                                               | Type Unicode text (up to 200 characters per call; exceeding the limit returns an error); window activated first if given. |
| `key_press`         | `(key: str, modifiers: list[str] = [])`                       | Press a single key with optional modifiers (`cmd`, `ctrl`, `alt`, `shift`). |
| `get_window_bounds` | `(window_id: int)`                                            | Returns `{x, y, width, height}`.                                            |
| `mouse_position`    | `()`                                                          | Returns current cursor coordinates `(x, y)`.                                |
| `activate_window`   | `(window_id: int)`                                            | Brings the owning application of the window to the foreground.              |

### Accessibility Permission

macOS requires explicit permission for apps that control the UI.
After the first run you will likely see a system prompt:

1. Open **System Settings › Privacy & Security › Accessibility**.
2. Add the Python executable (or your terminal app) to the list and enable it.

Once permission is granted, rerun the server and the tools should succeed.
