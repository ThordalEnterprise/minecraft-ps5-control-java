# PS5 Controller for Minecraft Java (macOS)

Turn your DualSense into a Minecraft Java controller on macOS.

No mods. No launchers. No cursed remapping apps.
Just Python, a PS5 controller, and mildly questionable life choices.

## Why this exists
Minecraft Java has keyboard + mouse controls, but many of us want couch energy.
This bridge translates DualSense input into keyboard/mouse events so Minecraft Java feels controller-native.

## Features
- Left stick movement (W/A/S/D)
- Right stick camera look (mouse movement)
- R2 = `P` key
- L2 = `O` key
- X/Cross = jump
- Circle = sneak
- L3 click = sprint
- Triangle = inventory
- Share = swap hands
- Options = pause/ESC
- L1/R1 = hotbar slot cycling (mouse wheel, one slot per tap)
- D-pad up = F5 perspective toggle
- D-pad down = hotbar scroll
- D-pad left = Q/drop
- D-pad right = U
- Cursor anchor mode for multi-monitor setups

## Works with
- macOS
- Python 3.10+
- `pygame`
- `pynput`
- PS5 DualSense (wired or Bluetooth)
- Minecraft Java Edition

## Install
```bash
git clone https://github.com/ThordalEnterprise/minecraft-ps5-control-java.git
cd minecraft-ps5-control-java
python3 -m venv .venv-ps5
source .venv-ps5/bin/activate
pip install pygame pynput pyobjc-framework-Quartz
```

## macOS permissions (important)
Enable Accessibility permissions for the terminal app running Python:
- System Settings -> Privacy & Security -> Accessibility
- Enable Terminal / iTerm / your Python host app

Without this, camera/click inputs may fail even if controller input is detected.

## Run
```bash
python3 ps5_minecraft_bridge.py
```

Debug camera:
```bash
python3 ps5_minecraft_bridge.py --debug-look
```

Debug triggers:
```bash
python3 ps5_minecraft_bridge.py --debug-triggers
```

Disable cursor anchoring:
```bash
python3 ps5_minecraft_bridge.py --no-lock-cursor
```

Input test mode (see button/axis indexes):
```bash
python3 ps5_minecraft_bridge.py --test-inputs
```

## Config
Edit `ps5_minecraft_bindings.json` to remap buttons/axes and keyboard keys.

Useful sections:
- `minecraft_keys`: keyboard mapping
- `controller_buttons`: button index mapping
- `controller_axes`: stick/trigger axis mapping

If your camera or triggers feel wrong on your setup, run `--test-inputs` and update axis indexes.

## Default mapping
| Control | Action |
|---|---|
| Left stick | Move |
| Right stick | Look |
| R2 | P key |
| L2 | O key |
| Cross (X) | Jump |
| Circle | Sneak |
| L3 (press) | Sprint |
| Triangle | Inventory |
| Square | Drop |
| Share | Swap hands |
| Options | ESC / Pause |
| L1 | Hotbar previous slot |
| R1 | Hotbar next slot |
| D-pad up | F5 / perspective |
| D-pad down | Hotbar scroll down |
| D-pad left | Q / drop |
| D-pad right | U key |

## Troubleshooting
- Camera not moving:
  - Verify Accessibility permission.
  - Try `--mouse-backend pynput`.
  - Check `controller_axes.rx/ry` in config.
- Trigger keys not working:
  - Use `--debug-triggers`.
  - Confirm `controller_axes.l2/r2` indexes.
- Cursor drifts onto another monitor:
  - Start the bridge with the cursor inside the Minecraft window.
  - Leave cursor anchoring enabled, which is the default.
  - Use `--no-lock-cursor` only if you want raw cursor movement.
- Wrong button mapping:
  - Run `--test-inputs` and update `controller_buttons`.

## Contributing
PRs are welcome.
If you can improve latency, aiming smoothness, or compatibility with other controllers, send it.

## License
MIT.

---
If this made your mining life better, star the repo and tell your friends the keyboard era is over.
