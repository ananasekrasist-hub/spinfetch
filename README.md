# spinfetch

fastfetch, but the ASCII logo is a **solid 3D object** that rotates continuously.

The logo is extruded into a real 3D body with front/back faces, side walls
along the contour, and Lambert shading. It spins smoothly around the vertical
axis + a diagonal axis, passing through its original orientation every full
cycle with zero pause.

Your fastfetch system info is displayed to the right, untouched.


## How it works

| | |
|---|---|
| **3D model** | Each logo character becomes front + back face + side walls. Wall characters (`▒▓█`) and shading are determined by surface normals and a directional light (Lambert). |
| **Rotation** | Continuous, constant speed, one direction. No pause at the return point — the angle grows without `mod`, so the logo flies through its original orientation at full speed. |
| **Return** | Every `CYCLE` seconds (default 12s) the orientation is mathematically identical to the start — verified pixel-for-pixel. |
| **Info panel** | `fastfetch --pipe --logo none` runs once; its output is displayed to the right and never redrawn. |
| **Rendering** | ANSI truecolor, z-buffer, perspective projection. ~4ms/frame at 30 FPS. Zero dependencies beyond Python stdlib. |

## Requirements

- Python 3.8+
- [fastfetch](https://github.com/fastfetch-cli/fastfetch) (installed and in `$PATH`)
- A terminal with truecolor support (basically any modern terminal)

## Install

```bash
git clone https://github.com/ananasekrasist-hub/spinfetch.git
cd spinfetch
cp spinfetch.py ~/.local/bin/spinfetch.py
```

## Usage

```bash
spinfetch.py                        # uses the bundled arch-logo.txt
spinfetch.py /path/to/your/logo.txt # any ASCII art file
```

Add to your shell config for quick access:

```bash
# ~/.zshrc or ~/.bashrc
alias spinfetch='~/.local/bin/spinfetch.py'
```

## Customization

All tunables are at the top of `spinfetch.py`:

| Variable | Default | Description |
|---|---|---|
| `CYCLE` | `12.0` | Seconds per full rotation (logo returns to original orientation). |
| `DEPTH` | `4.0` | Extrusion thickness in character cells. |
| `PERSPECTIVE` | `40.0` | Camera distance. Higher = flatter, lower = more dramatic 3D. |
| `AMBIENT` | `0.45` | Base light level (0–1). Lower = harsher shadows. |
| `FPS` | `30` | Target frame rate. |
| `ARCH_BLUE` | `(23, 147, 209)` | Fill color as RGB (`#1793D1`). |
| `WHITE` | `(255, 255, 255)` | Outline color as RGB. |
| `WALL_CHARS` | `("▒", "▓", "█")` | Characters for side walls (low → high brightness). |
| `LIGHT` | `(0.25, -0.35, 0.9)` | Light direction vector (normalized automatically). |

### Using your own logo

Any ASCII art text file works — just pass the path as an argument. Characters
on the silhouette edge are colored as the outline (`WHITE`), everything inside
uses the fill color (`ARCH_BLUE` — rename it if you want). The 3D extrusion
and shading work regardless of the logo shape.

## License

[MIT](LICENSE)