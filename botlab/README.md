# BotLab

BotLab is a browser-based robotics playground for building and testing virtual robots. The 2D simulator provides real-time movement, LiDAR, a camera view, and a robotic arm. The 3D assembler adds a gesture-controlled robot-building experience.

## Live site

Open the deployed playground at [botlab.alphaonelabs.com](https://botlab.alphaonelabs.com/). The 2D simulator is available at [/home.html](https://botlab.alphaonelabs.com/home.html), and the 3D assembler is at [/3D/](https://botlab.alphaonelabs.com/3D/).

## Features

- **Robot builder:** Add a chassis, wheels, LiDAR, camera, and robotic arm.
- **Movement:** Drive with WASD or the arrow keys; adjust motor power and turning speed.
- **LiDAR:** Scan for nearby blocks and see their shape and color in the detection panel.
- **Camera view:** See a first-person view from the robot.
- **Robotic arm:** Pick up and drop blocks with the Space key.
- **Telemetry:** View the robot's position, heading, and speed.

## Getting started

Clone the monorepo and change to the BotLab directory:

```bash
git clone https://github.com/alphaonelabs/website.git
cd website/botlab
```

Run BotLab locally using either option:

```bash
npx wrangler dev
```

Or, if you have Python 3 installed:

```bash
python3 -m http.server 8000
```

Open the local URL printed by Wrangler, or visit [http://localhost:8000](http://localhost:8000) when using Python. The landing page links to the 2D simulator and 3D assembler.

## 2D simulator controls

| Key or action | Function |
|---|---|
| `W` / `↑` | Move forward |
| `S` / `↓` | Move backward |
| `A` / `←` | Turn left |
| `D` / `→` | Turn right |
| `Space` | Pick up or drop a block when the robot has an arm |

Add or remove components from the Toolbox. Add a chassis before other components.

## 3D assembler

Open the 3D assembler from the landing page or go to `/3D/`. It supports hand-gesture controls and keyboard controls:

- In gesture mode, the right hand aims and moves the robot; the left hand freezes the robot and picks up objects.
- In manual mode, use `W`, `A`, `S`, and `D` to move, `1`–`5` to cycle through component categories, and `Space` to pick up or drop an object.
- Press `Q` or `Escape` to stop the 3D experience.

Gesture control requires camera access. Use HTTPS or `localhost`, and allow camera permission when the browser prompts. If camera access or hand tracking is unavailable, the assembler falls back to manual keyboard controls.

## LiDAR detection

When LiDAR is installed, its beam sweeps around the robot. When it intersects a block within range, the detection panel reports the shape (`Square`, `Circle`, or `Triangle`) and color.

## Project structure

```text
botlab/
├── 3D/              # 3D gesture-controlled robot assembler
├── assets/          # Shared visual assets
├── home.html        # 2D simulator
├── index.html       # Landing page
├── README.md        # Project overview and setup
├── CONTRIBUTING.md  # BotLab contribution guide
└── wrangler.toml    # Cloudflare static asset settings
```

## Contributing

Contributions, bug reports, and feature requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) for BotLab setup and contribution steps. Browse [open BotLab issues](https://github.com/alphaonelabs/website/issues?q=is%3Aissue+is%3Aopen+label%3A%22project%3A+botlab%22) or open an issue with the `project: botlab` label.
