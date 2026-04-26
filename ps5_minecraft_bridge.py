#!/usr/bin/env python3
"""
PS5 controller -> Minecraft keyboard/mouse bridge for macOS.

Requirements:
  pip3 install pygame pynput

macOS permissions:
  System Settings -> Privacy & Security -> Accessibility
  Add/enable your terminal (or Python app) so key/mouse events can be sent.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import pygame
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Button, Controller as MouseController

try:
    from Quartz import (  # type: ignore
        CGEventCreate,
        CGEventCreateMouseEvent,
        CGEventGetLocation,
        CGEventPost,
        CGEventSetIntegerValueField,
        kCGEventLeftMouseDown,
        kCGEventLeftMouseUp,
        kCGEventMouseMoved,
        kCGEventRightMouseDown,
        kCGEventRightMouseUp,
        kCGHIDEventTap,
        kCGMouseButtonLeft,
        kCGMouseButtonRight,
        kCGMouseEventDeltaX,
        kCGMouseEventDeltaY,
    )
except Exception:
    CGEventCreate = None


# ------------------------- Editable keybindings ------------------------- #
# Change these to match your preferred Minecraft controls.
KEYBINDINGS = {
    "forward": "w",
    "back": "s",
    "left": "a",
    "right": "d",
    "jump": Key.space,
    "sneak": Key.shift,
    "sprint": Key.ctrl,
    "inventory": "e",
    "drop": "q",
    "swap_hands": "f",
    "esc": Key.esc,
    "hotbar_prev": None,  # Mouse wheel up
    "hotbar_next": None,  # Mouse wheel down
}

DEFAULT_BUTTON_MAP = {
    "cross": 0,
    "circle": 1,
    "square": 2,
    "triangle": 3,
    "share": 4,
    "options": 6,
    "l3": 7,
    "r3": 8,
    "l1": 9,
    "r1": 10,
    "dpad_up": 11,
    "dpad_down": 12,
    "dpad_left": 13,
    "dpad_right": 14,
}

DEFAULT_AXIS_MAP = {
    "lx": 0,
    "ly": 1,
    "rx": 2,
    "ry": 3,
    "l2": 4,
    "r2": 5,
}


@dataclass
class Settings:
    deadzone_move: float = 0.20
    deadzone_look: float = 0.05
    look_sensitivity: float = 28.0
    poll_hz: int = 120
    trigger_threshold: float = 0.35
    trigger_delta_threshold: float = 0.35
    scroll_cooldown_s: float = 0.15


class MouseBackend:
    def __init__(self, mode: str = "auto") -> None:
        self.mode = mode
        self.pynput_mouse = MouseController()
        self.left_down = False
        self.right_down = False

        if self.mode == "auto":
            self.mode = "quartz" if CGEventCreate is not None else "pynput"
        if self.mode == "quartz" and CGEventCreate is None:
            self.mode = "pynput"

    def move(self, dx: int, dy: int) -> None:
        if self.mode == "quartz":
            x, y = self._current_pos()
            event = CGEventCreateMouseEvent(
                None, kCGEventMouseMoved, (x + dx, y + dy), kCGMouseButtonLeft
            )
            CGEventSetIntegerValueField(event, kCGMouseEventDeltaX, dx)
            CGEventSetIntegerValueField(event, kCGMouseEventDeltaY, dy)
            CGEventPost(kCGHIDEventTap, event)
            return
        self.pynput_mouse.move(dx, dy)

    def scroll(self, dy: int) -> None:
        self.pynput_mouse.scroll(0, dy)

    def _current_pos(self) -> Tuple[float, float]:
        event = CGEventCreate(None)
        loc = CGEventGetLocation(event)
        return loc.x, loc.y

    def press_left(self) -> None:
        if self.left_down:
            return
        self.left_down = True
        if self.mode == "quartz":
            x, y = self._current_pos()
            event = CGEventCreateMouseEvent(
                None, kCGEventLeftMouseDown, (x, y), kCGMouseButtonLeft
            )
            CGEventPost(kCGHIDEventTap, event)
            return
        self.pynput_mouse.press(Button.left)

    def release_left(self) -> None:
        if not self.left_down:
            return
        self.left_down = False
        if self.mode == "quartz":
            x, y = self._current_pos()
            event = CGEventCreateMouseEvent(
                None, kCGEventLeftMouseUp, (x, y), kCGMouseButtonLeft
            )
            CGEventPost(kCGHIDEventTap, event)
            return
        self.pynput_mouse.release(Button.left)

    def press_right(self) -> None:
        if self.right_down:
            return
        self.right_down = True
        if self.mode == "quartz":
            x, y = self._current_pos()
            event = CGEventCreateMouseEvent(
                None, kCGEventRightMouseDown, (x, y), kCGMouseButtonRight
            )
            CGEventPost(kCGHIDEventTap, event)
            return
        self.pynput_mouse.press(Button.right)

    def release_right(self) -> None:
        if not self.right_down:
            return
        self.right_down = False
        if self.mode == "quartz":
            x, y = self._current_pos()
            event = CGEventCreateMouseEvent(
                None, kCGEventRightMouseUp, (x, y), kCGMouseButtonRight
            )
            CGEventPost(kCGHIDEventTap, event)
            return
        self.pynput_mouse.release(Button.right)


def parse_key_name(name: str) -> object:
    key_lookup = {
        "space": Key.space,
        "shift": Key.shift,
        "ctrl": Key.ctrl,
        "esc": Key.esc,
        "tab": Key.tab,
        "enter": Key.enter,
        "up": Key.up,
        "down": Key.down,
        "left": Key.left,
        "right": Key.right,
    }
    normalized = name.strip().lower()
    if normalized in key_lookup:
        return key_lookup[normalized]
    if len(normalized) == 1:
        return normalized
    return normalized


def load_or_create_bindings(config_path: Path) -> Dict[str, object]:
    if not config_path.exists():
        template = {
            "minecraft_keys": {
                "forward": "w",
                "back": "s",
                "left": "a",
                "right": "d",
                "jump": "space",
                "sneak": "shift",
                "sprint": "ctrl",
                "inventory": "e",
                "drop": "q",
                "swap_hands": "f",
                "esc": "esc",
            },
            "controller_buttons": DEFAULT_BUTTON_MAP,
            "controller_axes": DEFAULT_AXIS_MAP,
        }
        config_path.write_text(json.dumps(template, indent=2), encoding="utf-8")
        print(f"Created default config at: {config_path}")

    raw = json.loads(config_path.read_text(encoding="utf-8"))
    loaded = dict(KEYBINDINGS)
    keys_json = raw.get("minecraft_keys", {})
    for action, value in keys_json.items():
        if isinstance(value, str):
            loaded[action] = parse_key_name(value)
    return loaded


def load_button_map(config_path: Path) -> Dict[str, int]:
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    button_map = dict(DEFAULT_BUTTON_MAP)
    from_file = raw.get("controller_buttons", {})
    for k, v in from_file.items():
        if isinstance(v, int):
            button_map[k] = v
    return button_map


def load_axis_map(config_path: Path) -> Dict[str, int]:
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    axis_map = dict(DEFAULT_AXIS_MAP)
    from_file = raw.get("controller_axes", {})
    for k, v in from_file.items():
        if isinstance(v, int):
            axis_map[k] = v
    return axis_map


class KeyState:
    def __init__(self, keyboard: KeyboardController) -> None:
        self.keyboard = keyboard
        self.down: Dict[object, bool] = {}

    def press(self, key: object) -> None:
        if key is None:
            return
        if not self.down.get(key, False):
            self.keyboard.press(key)
            self.down[key] = True

    def release(self, key: object) -> None:
        if key is None:
            return
        if self.down.get(key, False):
            self.keyboard.release(key)
            self.down[key] = False

    def release_all(self) -> None:
        for key, is_down in list(self.down.items()):
            if is_down:
                self.keyboard.release(key)
                self.down[key] = False


def clamp_deadzone(value: float, deadzone: float) -> float:
    if abs(value) < deadzone:
        return 0.0
    # Re-scale remaining range back to 0..1 for smoother control
    sign = 1.0 if value >= 0.0 else -1.0
    return sign * (abs(value) - deadzone) / (1.0 - deadzone)


def get_axes(
    joy: pygame.joystick.Joystick, axis_map: Dict[str, int]
) -> Tuple[float, float, float, float, float, float]:
    """
    Returns:
      lx, ly, rx, ry, l2, r2
    Uses configurable SDL axis indices.
    """
    axis_count = joy.get_numaxes()

    def read_axis(name: str) -> float:
        idx = axis_map.get(name, DEFAULT_AXIS_MAP[name])
        if idx < 0 or idx >= axis_count:
            return 0.0
        return joy.get_axis(idx)

    lx = read_axis("lx")
    ly = read_axis("ly")
    rx = read_axis("rx")
    ry = read_axis("ry")
    l2 = read_axis("l2")
    r2 = read_axis("r2")
    return lx, ly, rx, ry, l2, r2


def axis_to_bool_pair(value: float) -> Tuple[bool, bool]:
    """Convert one axis to negative/positive directional booleans."""
    return value < 0.0, value > 0.0


def calibrate_trigger_rest(
    joy: pygame.joystick.Joystick, axis_map: Dict[str, int], samples: int = 20
) -> Tuple[float, float]:
    """Sample trigger idle positions so press detection works across mappings/ranges."""
    l2_samples = []
    r2_samples = []
    for _ in range(samples):
        pygame.event.pump()
        _, _, _, _, l2, r2 = get_axes(joy, axis_map)
        l2_samples.append(l2)
        r2_samples.append(r2)
        time.sleep(0.005)
    return statistics.median(l2_samples), statistics.median(r2_samples)


def run_input_test(joy: pygame.joystick.Joystick) -> int:
    print("Input test mode. Press buttons/sticks/triggers. Ctrl+C to stop.")
    last_buttons: Dict[int, bool] = {}
    last_hat = (0, 0)
    last_axes = [0.0] * joy.get_numaxes()
    try:
        while True:
            pygame.event.pump()
            current_buttons = {i: bool(joy.get_button(i)) for i in range(joy.get_numbuttons())}
            for idx, pressed in current_buttons.items():
                if pressed and not last_buttons.get(idx, False):
                    print(f"button pressed -> index {idx}")
            last_buttons = current_buttons

            if joy.get_numhats() > 0:
                hat = joy.get_hat(0)
                if hat != last_hat:
                    print(f"dpad/hat -> {hat}")
                    last_hat = hat

            for i in range(joy.get_numaxes()):
                v = joy.get_axis(i)
                if abs(v - last_axes[i]) >= 0.25:
                    print(f"axis {i} -> {v:.2f}")
                    last_axes[i] = v
            time.sleep(0.02)
    except KeyboardInterrupt:
        print("\nExiting input test.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="PS5 controller to Minecraft bridge")
    parser.add_argument("--look-sensitivity", type=float, default=Settings.look_sensitivity)
    parser.add_argument("--poll-hz", type=int, default=Settings.poll_hz)
    parser.add_argument("--config", default="ps5_minecraft_bindings.json")
    parser.add_argument("--test-inputs", action="store_true")
    parser.add_argument("--debug-look", action="store_true")
    parser.add_argument("--debug-triggers", action="store_true")
    parser.add_argument("--mouse-backend", choices=["auto", "pynput", "quartz"], default="auto")
    args = parser.parse_args()

    settings = Settings(look_sensitivity=args.look_sensitivity, poll_hz=args.poll_hz)

    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No controller detected. Plug in PS5 controller and try again.")
        return 1

    joy = pygame.joystick.Joystick(0)
    joy.init()
    print(f"Controller connected: {joy.get_name()}")

    config_path = Path(args.config).expanduser().resolve()
    bindings = load_or_create_bindings(config_path)
    button_map = load_button_map(config_path)
    axis_map = load_axis_map(config_path)

    if args.test_inputs:
        return run_input_test(joy)

    print("Focus Minecraft window. Press Ctrl+C here to stop.")
    print(f"Using config: {config_path}")
    print(f"Using axes: {axis_map}")
    l2_rest, r2_rest = calibrate_trigger_rest(joy, axis_map)
    print(f"Trigger rest values: L2={l2_rest:.2f}, R2={r2_rest:.2f}")

    keyboard = KeyboardController()
    mouse = MouseBackend(args.mouse_backend)
    keys = KeyState(keyboard)

    # Track button states for edge-triggered actions
    last_buttons: Dict[int, bool] = {}
    last_hat = (0, 0)
    last_scroll_at = 0.0

    dt_target = 1.0 / max(30, settings.poll_hz)

    # Default DS5 indices can be overridden in config JSON.
    BTN_CROSS = button_map["cross"]
    BTN_CIRCLE = button_map["circle"]
    BTN_SQUARE = button_map["square"]
    BTN_TRIANGLE = button_map["triangle"]
    BTN_L1 = button_map["l1"]
    BTN_R1 = button_map["r1"]
    BTN_SHARE = button_map["share"]
    BTN_OPTIONS = button_map["options"]
    BTN_L3 = button_map["l3"]
    BTN_R3 = button_map["r3"]

    try:
        while True:
            frame_start = time.perf_counter()
            pygame.event.pump()

            # Axes: left stick movement, right stick camera, triggers attack/use
            lx, ly, rx, ry, l2, r2 = get_axes(joy, axis_map)
            lx = clamp_deadzone(lx, settings.deadzone_move)
            ly = clamp_deadzone(ly, settings.deadzone_move)
            rx = clamp_deadzone(rx, settings.deadzone_look)
            ry = clamp_deadzone(ry, settings.deadzone_look)

            # Minecraft movement
            # Forward/back: stick up should be forward in Minecraft.
            fwd, back = axis_to_bool_pair(ly)
            left, right = axis_to_bool_pair(lx)
            if fwd:
                keys.press(bindings["forward"])
            else:
                keys.release(bindings["forward"])
            if back:
                keys.press(bindings["back"])
            else:
                keys.release(bindings["back"])
            if left:
                keys.press(bindings["left"])
            else:
                keys.release(bindings["left"])
            if right:
                keys.press(bindings["right"])
            else:
                keys.release(bindings["right"])

            # Camera look as relative mouse movement
            # Small values are rounded, keeping smoother behavior.
            move_x = int(round(rx * settings.look_sensitivity))
            move_y = int(round(ry * settings.look_sensitivity))
            if move_x != 0 or move_y != 0:
                mouse.move(move_x, move_y)
                if args.debug_look:
                    print(f"look rx={rx:.2f} ry={ry:.2f} -> dx={move_x} dy={move_y}")

            # Triggers as mouse buttons (user mapping):
            # R2 -> left click, L2 -> right click
            # Use delta from calibrated idle values so this works across
            # trigger ranges/inversion differences.
            attack_down = abs(r2 - r2_rest) > settings.trigger_delta_threshold
            use_down = abs(l2 - l2_rest) > settings.trigger_delta_threshold
            if attack_down:
                mouse.press_left()
            else:
                mouse.release_left()
            if use_down:
                mouse.press_right()
            else:
                mouse.release_right()
            if args.debug_triggers:
                print(
                    f"triggers L2={l2:.2f} (rest {l2_rest:.2f}) "
                    f"R2={r2:.2f} (rest {r2_rest:.2f}) -> "
                    f"use={use_down} attack={attack_down}"
                )

            # Buttons
            current_buttons = {i: bool(joy.get_button(i)) for i in range(joy.get_numbuttons())}

            # Hold actions
            if current_buttons.get(BTN_CROSS, False):
                keys.press(bindings["jump"])
            else:
                keys.release(bindings["jump"])

            if current_buttons.get(BTN_CIRCLE, False):
                keys.press(bindings["sneak"])
            else:
                keys.release(bindings["sneak"])

            if current_buttons.get(BTN_L3, False):
                keys.press(bindings["sprint"])
            else:
                keys.release(bindings["sprint"])

            # Edge-trigger actions
            def pressed_once(btn: int) -> bool:
                now = current_buttons.get(btn, False)
                prev = last_buttons.get(btn, False)
                return now and not prev

            if pressed_once(BTN_TRIANGLE):
                keyboard.press(bindings["inventory"])
                keyboard.release(bindings["inventory"])

            if pressed_once(BTN_SQUARE):
                keyboard.press(bindings["drop"])
                keyboard.release(bindings["drop"])

            if pressed_once(BTN_OPTIONS):
                keyboard.press(bindings["esc"])
                keyboard.release(bindings["esc"])

            if pressed_once(BTN_SHARE):
                keyboard.press(bindings["swap_hands"])
                keyboard.release(bindings["swap_hands"])

            # Shoulder buttons: hotbar cycle (scroll while held)
            now_ts = time.time()
            if now_ts - last_scroll_at >= settings.scroll_cooldown_s:
                l1_down = current_buttons.get(BTN_L1, False)
                r1_down = current_buttons.get(BTN_R1, False)
                if l1_down:
                    mouse.scroll(1)
                    last_scroll_at = now_ts
                elif r1_down:
                    mouse.scroll(-1)
                    last_scroll_at = now_ts

            # D-pad support:
            # - Some controllers expose D-pad as a hat.
            # - Others expose D-pad as buttons (often 11-14 on macOS SDL).
            dpad_used = False
            if joy.get_numhats() > 0:
                hat = joy.get_hat(0)
                if hat != last_hat and now_ts - last_scroll_at >= settings.scroll_cooldown_s:
                    if hat[1] > 0:
                        mouse.scroll(1)
                        last_scroll_at = now_ts
                        dpad_used = True
                    elif hat[1] < 0:
                        mouse.scroll(-1)
                        last_scroll_at = now_ts
                        dpad_used = True
                last_hat = hat

            if not dpad_used and now_ts - last_scroll_at >= settings.scroll_cooldown_s:
                dpad_up = button_map.get("dpad_up", -1)
                dpad_down = button_map.get("dpad_down", -1)
                if dpad_up >= 0 and pressed_once(dpad_up):
                    mouse.scroll(1)
                    last_scroll_at = now_ts
                elif dpad_down >= 0 and pressed_once(dpad_down):
                    mouse.scroll(-1)
                    last_scroll_at = now_ts

            # D-pad right can be used as a quick "Q" action (swap_hands binding).
            dpad_right = button_map.get("dpad_right", -1)
            if dpad_right >= 0 and pressed_once(dpad_right):
                keyboard.press(bindings["swap_hands"])
                keyboard.release(bindings["swap_hands"])
            last_buttons = current_buttons

            elapsed = time.perf_counter() - frame_start
            sleep_time = dt_target - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nStopping bridge...")
    finally:
        keys.release_all()
        mouse.release_left()
        mouse.release_right()
        pygame.quit()

    return 0


if __name__ == "__main__":
    sys.exit(main())
