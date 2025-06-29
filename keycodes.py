"""
Keycode mapping for macOS virtual key codes.

This is **not** exhaustive—only common keys required by the current project are included.
All codes are taken from <HIToolbox/Events.h>.
"""

from Quartz import (
    kCGEventFlagMaskAlternate,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskControl,
    kCGEventFlagMaskShift,
)

# Letter keys
KEYCODES: dict[str, int] = {
    "a": 0x00,
    "s": 0x01,
    "d": 0x02,
    "f": 0x03,
    "h": 0x04,
    "g": 0x05,
    "z": 0x06,
    "x": 0x07,
    "c": 0x08,
    "v": 0x09,
    "b": 0x0B,
    "q": 0x0C,
    "w": 0x0D,
    "e": 0x0E,
    "r": 0x0F,
    "y": 0x10,
    "t": 0x11,
    "1": 0x12,
    "2": 0x13,
    "3": 0x14,
    "4": 0x15,
    "6": 0x16,
    "5": 0x17,
    "equal": 0x18,
    "9": 0x19,
    "7": 0x1A,
    "minus": 0x1B,
    "8": 0x1C,
    "0": 0x1D,
    "rightbracket": 0x1E,
    "o": 0x1F,
    "u": 0x20,
    "leftbracket": 0x21,
    "i": 0x22,
    "p": 0x23,
    "l": 0x25,
    "j": 0x26,
    "quote": 0x27,
    "k": 0x28,
    "semicolon": 0x29,
    "backslash": 0x2A,
    "comma": 0x2B,
    "slash": 0x2C,
    "n": 0x2D,
    "m": 0x2E,
    "period": 0x2F,
    "grave": 0x32,
    # Modifier/function keys
    "return": 0x24,
    "enter": 0x4C,
    "escape": 0x35,
    "delete": 0x33,
    "tab": 0x30,
    "space": 0x31,
    "left": 0x7B,
    "right": 0x7C,
    "down": 0x7D,
    "up": 0x7E,
}

MODIFIER_FLAGS: dict[str, int] = {
    "cmd": kCGEventFlagMaskCommand,
    "command": kCGEventFlagMaskCommand,
    "ctrl": kCGEventFlagMaskControl,
    "control": kCGEventFlagMaskControl,
    "alt": kCGEventFlagMaskAlternate,
    "option": kCGEventFlagMaskAlternate,
    "shift": kCGEventFlagMaskShift,
}
