"""
Mouse, keyboard, and utility interaction tools for winsys-mcp-server.

All functionality is macOS-only and relies on Quartz / Accessibility (AX) APIs.
The module is imported by server.py so that the tools are automatically
registered on startup (via the shared FastMCP instance defined there).

Logging is kept to ERROR level only - we only log unexpected exceptions.
"""

from __future__ import annotations

# Standard library
import logging
import time

try:
    from AppKit import (
        NSApplicationActivateIgnoringOtherApps,
        NSRunningApplication,
    )

    # Third-party (PyObjC - already a dependency of Quartz in this project)
    from Quartz import (
        CGEventCreateKeyboardEvent,
        CGEventCreateMouseEvent,
        CGEventKeyboardSetUnicodeString,
        CGEventPost,
        CGEventSetFlags,
        CGEventSourceCreate,
        CGEventType,
        CGWindowListCopyWindowInfo,
        CoreGraphics,
        kCGEventLeftMouseDown,
        kCGEventLeftMouseDragged,
        kCGEventLeftMouseUp,
        kCGEventMouseMoved,
        kCGEventOtherMouseDown,
        kCGEventOtherMouseDragged,
        kCGEventOtherMouseUp,
        kCGEventRightMouseDown,
        kCGEventRightMouseDragged,
        kCGEventRightMouseUp,
        kCGEventSourceStateCombinedSessionState,
        kCGHIDEventTap,
        kCGMouseButtonCenter,
        kCGMouseButtonLeft,
        kCGMouseButtonRight,
        kCGNullWindowID,
        kCGWindowListOptionAll,
        kCGWindowListOptionOnScreenOnly,
    )
except ImportError as e:
    raise ImportError(f"Failed to import required macOS frameworks: {e}") from e

# Mapping utilities
from keycodes import KEYCODES, MODIFIER_FLAGS

# Local imports - avoid circular deps by importing *after* mcp is created.
from mcp_shared import logger, mcp

# Ensure minimal logging
logger = logging.getLogger(__name__)  # noqa: F811
logger.setLevel(logging.ERROR)

# Maximum number of characters processed by type_text per call
MAX_TYPE_TEXT_CHARS = 200

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _fetch_bounds(window_id: int) -> dict[str, int] | None:
    """Return bounds dict {{X,Y,Width,Height}} for *window_id* or None if not found."""
    window_list = CGWindowListCopyWindowInfo(
        kCGWindowListOptionAll | kCGWindowListOptionOnScreenOnly, kCGNullWindowID
    )
    for win in window_list:
        if win.get("kCGWindowNumber") == window_id:
            return win.get("kCGWindowBounds")  # type: ignore[return-value]
    return None


def _to_abs(x: int, y: int, window_id: int | None = None) -> tuple[int, int]:
    """Convert (x,y) to absolute screen coords, using *window_id* as origin if provided."""
    if window_id is None:
        return x, y
    bounds = _fetch_bounds(window_id)
    if not bounds:
        raise ValueError(f"Window id {window_id} not found")
    return int(bounds.get("X", 0) + x), int(bounds.get("Y", 0) + y)


def _mouse_event(event_type: CGEventType, abs_x: int, abs_y: int, button_idx: int) -> None:
    """Create and post a CG mouse event."""
    event = CGEventCreateMouseEvent(None, event_type, (abs_x, abs_y), button_idx)
    CGEventPost(kCGHIDEventTap, event)


def _post_mouse_move(abs_x: int, abs_y: int) -> None:
    _mouse_event(kCGEventMouseMoved, abs_x, abs_y, kCGMouseButtonLeft)


def _post_mouse_click(abs_x: int, abs_y: int, button: str) -> None:
    mapping: dict[str, tuple[CGEventType, CGEventType, CGEventType]] = {
        "left": (kCGEventLeftMouseDown, kCGEventLeftMouseUp, kCGMouseButtonLeft),
        "right": (kCGEventRightMouseDown, kCGEventRightMouseUp, kCGMouseButtonRight),
        "middle": (kCGEventOtherMouseDown, kCGEventOtherMouseUp, kCGMouseButtonCenter),
    }
    if button not in mapping:
        raise ValueError("Invalid button. Must be 'left', 'right', or 'middle'.")
    down_type, up_type, btn_idx = mapping[button]
    _mouse_event(down_type, abs_x, abs_y, btn_idx)
    _mouse_event(up_type, abs_x, abs_y, btn_idx)


def _post_mouse_drag(
    from_abs: tuple[int, int],
    to_abs: tuple[int, int],
    button: str,
) -> None:
    mapping: dict[str, tuple[CGEventType, CGEventType, CGEventType]] = {
        "left": (kCGEventLeftMouseDown, kCGEventLeftMouseDragged, kCGEventLeftMouseUp),
        "right": (kCGEventRightMouseDown, kCGEventRightMouseDragged, kCGEventRightMouseUp),
        "middle": (kCGEventOtherMouseDown, kCGEventOtherMouseDragged, kCGEventOtherMouseUp),
    }
    if button not in mapping:
        raise ValueError("Invalid button. Must be 'left', 'right', or 'middle'.")
    down_type, drag_type, up_type = mapping[button]
    btn_idx = {
        "left": kCGMouseButtonLeft,
        "right": kCGMouseButtonRight,
        "middle": kCGMouseButtonCenter,
    }[button]

    # Press
    _mouse_event(down_type, *from_abs, btn_idx)
    # Drag - we interpolate a few points for smoother behaviour
    steps = 10
    dx = (to_abs[0] - from_abs[0]) / steps
    dy = (to_abs[1] - from_abs[1]) / steps
    for i in range(1, steps + 1):
        _mouse_event(drag_type, int(from_abs[0] + dx * i), int(from_abs[1] + dy * i), btn_idx)
    # Release
    _mouse_event(up_type, *to_abs, btn_idx)


def _activate_app_for_window(window_id: int) -> None:
    """Bring the owning application of *window_id* to the front, ignoring other apps."""
    window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionAll, kCGNullWindowID)
    pid: int | None = None
    for win in window_list:
        if win.get("kCGWindowNumber") == window_id:
            pid = win.get("kCGWindowOwnerPID")
            break
    if pid is None:
        raise ValueError("window_id not found when activating app")
    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    if app is not None:
        app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)


def _post_keyboard_unicode(char: str, source: any) -> None:
    """Send a single unicode character via CG events using *source*."""
    if len(char) != 1:
        raise ValueError("_post_keyboard_unicode expects a single character")
    event_down = CGEventCreateKeyboardEvent(source, 0, True)
    CGEventKeyboardSetUnicodeString(event_down, 1, char)
    CGEventPost(kCGHIDEventTap, event_down)

    event_up = CGEventCreateKeyboardEvent(source, 0, False)
    CGEventKeyboardSetUnicodeString(event_up, 1, char)
    CGEventPost(kCGHIDEventTap, event_up)


def _post_keycode_type(keycode: int, flags: int, source: any) -> None:
    """Type a single key by *keycode* using *source* with optional *flags*."""
    event_down = CGEventCreateKeyboardEvent(source, keycode, True)
    CGEventSetFlags(event_down, flags)
    CGEventPost(kCGHIDEventTap, event_down)

    event_up = CGEventCreateKeyboardEvent(source, keycode, False)
    CGEventSetFlags(event_up, flags)
    CGEventPost(kCGHIDEventTap, event_up)


def _post_keycode_press(keycode: int, flags: int) -> None:
    """Press and release a *keycode* with *flags* (modifier mask)."""
    event_down = CGEventCreateKeyboardEvent(None, keycode, True)
    CGEventSetFlags(event_down, flags)
    CGEventPost(kCGHIDEventTap, event_down)

    event_up = CGEventCreateKeyboardEvent(None, keycode, False)
    CGEventSetFlags(event_up, flags)
    CGEventPost(kCGHIDEventTap, event_up)


# ---------------------------------------------------------------------------
# MCP TOOLS
# ---------------------------------------------------------------------------


@mcp.tool()
def move_mouse(x: int, y: int, window_id: int | None = None) -> str:
    """
    Move the mouse cursor to (x, y).

    If *window_id* is supplied, (x, y) are relative to that window's top-left
    corner; otherwise they are absolute screen coordinates.
    """
    try:
        abs_x, abs_y = _to_abs(x, y, window_id)
        _post_mouse_move(abs_x, abs_y)
        return "OK"
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("move_mouse failed: %s", exc)
        return f"Error: {exc}"


@mcp.tool()
def click_at(
    x: int,
    y: int,
    button: str = "left",
    window_id: float | int | None = None,
) -> str:
    """
    Perform a mouse click at (x, y).

    *button* may be "left", "right", or "middle".
    Coordinates are relative to *window_id* if provided, else absolute.
    """
    try:
        window_id_int = int(window_id) if window_id is not None else None
        abs_x, abs_y = _to_abs(x, y, window_id_int)
        _post_mouse_click(abs_x, abs_y, button)
        return "OK"
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("click_at failed: %s", exc)
        return f"Error: {exc}"


@mcp.tool()
def drag(
    from_x: int,
    from_y: int,
    to_x: int,
    to_y: int,
    button: str = "left",
    window_id: int | None = None,
) -> str:
    """
    Drag the mouse from (from_x, from_y) to (to_x, to_y).

    Coordinates are interpreted relative to *window_id* if supplied.
    """
    try:
        from_abs = _to_abs(from_x, from_y, window_id)
        to_abs = _to_abs(to_x, to_y, window_id)
        _post_mouse_drag(from_abs, to_abs, button)
        return "OK"
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("drag failed: %s", exc)
        return f"Error: {exc}"


@mcp.tool()
def type_text(text: str, window_id: int | None = None) -> str:
    """
    Type *text* with realistic keystrokes and human-like delay.

    A combined-session `CGEventSource` is used to make the events appear as if
    they originate from a real keyboard.

    Processes at most 200 characters per call. If the input exceeds this limit,
    an error is returned and no text is typed.
    """
    try:
        if len(text) > MAX_TYPE_TEXT_CHARS:
            return f"Error: type_text input exceeds {MAX_TYPE_TEXT_CHARS} characters"
        # Create a unified event source once per call
        source = CGEventSourceCreate(kCGEventSourceStateCombinedSessionState)

        # Bring target application to front if we know its window id
        if window_id is not None:
            _activate_app_for_window(window_id)

        limited_text = text[:MAX_TYPE_TEXT_CHARS]

        for ch in limited_text:
            # Try realistic keycode first
            keycode = KEYCODES.get(ch.lower())
            if keycode is not None:
                _post_keycode_type(keycode, 0, source)
            else:
                _post_keyboard_unicode(ch, source)

            # Small delay for human-like typing speed
            time.sleep(0.05)

        return "OK"
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("type_text failed: %s", exc)
        return f"Error: {exc}"


@mcp.tool()
def key_press(key: str, modifiers: list[str] | None = None) -> str:
    """Press a single *key* with optional *modifiers* (cmd, ctrl, alt, shift)."""
    try:
        keycode = KEYCODES.get(key.lower())
        if keycode is None:
            return f"Error: Unknown key '{key}'"

        modifiers = modifiers or []
        flags = 0
        for mod in modifiers:
            flag = MODIFIER_FLAGS.get(mod.lower())
            if flag is None:
                return f"Error: Unknown modifier '{mod}'"
            flags |= flag

        _post_keycode_press(keycode, flags)
        return "OK"
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("key_press failed: %s", exc)
        return f"Error: {exc}"


@mcp.tool()
def get_window_bounds(window_id: int) -> dict[str, int] | str:
    """Return the on-screen bounds of *window_id* as a dict."""
    try:
        bounds = _fetch_bounds(window_id)
        if bounds is None:
            return f"Error: Window id {window_id} not found"
        return {k.lower(): int(v) for k, v in bounds.items()}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("get_window_bounds failed: %s", exc)
        return f"Error: {exc}"


@mcp.tool()
def mouse_position() -> tuple[int, int] | str:
    """Return current mouse cursor position as (x, y)."""
    try:
        event = CoreGraphics.CGEventCreate(None)
        point = CoreGraphics.CGEventGetLocation(event)
        return int(point.x), int(point.y)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("mouse_position failed: %s", exc)
        return f"Error: {exc}"


# ---------------------------------------------------------------------------
# New window-activation tool
# ---------------------------------------------------------------------------


@mcp.tool()
def activate_window(window_id: int) -> str:
    """
    Activate (bring to foreground) the application that owns *window_id*.

    Args:
        window_id: The ID of the target window whose owning application should
            be focused.

    Returns:
        "OK" on success, or an error message string on failure.

    """
    try:
        _activate_app_for_window(window_id)
        return "OK"
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("activate_window failed: %s", exc)
        return f"Error: {exc}"
