# Alpha One Labs — Virtual Robotics Playground

A browser-based virtual robotics simulation environment for building, configuring, and testing autonomous mobile robots with real-time physics and sensor telemetry — no installation required.

---

## 🚀 Features

- **Modular Robot Builder** — Start from a blank chassis and attach sensors, wheels, and a manipulator arm.
- **Omni-Directional Movement** — Drive your robot with WASD or Arrow keys; adjust motor power and turning speed in real-time.
- **LiDAR Scanning** — A rotating 360° LiDAR sensor casts a detection beam. When it passes over an object, the **Detection Panel** reports the object's **shape** and **color**.
- **First-Person Camera** — Live FPV camera feed rendered from the robot's perspective directly in the browser.
- **Robotic Arm** — Pick up and drop coloured blocks using the SPACE key.
- **Telemetry HUD** — Real-time position, heading, and speed readout overlaid on the simulation canvas.

---

## 🛠️ Getting Started

No build tools or server required — just open the files directly in your browser.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/alphaonelabs/alphaonelabs-virtual-robotics-playground.git
   ```
2. Open `index.html` in any modern web browser to view the landing page.
3. Click **Enter System** to launch the interactive playground (`home.html`).

---

## 🎮 Controls

| Key / Action | Function |
|---|---|
| `W` / `↑` | Move forward |
| `S` / `↓` | Move backward |
| `A` / `←` | Turn left |
| `D` / `→` | Turn right |
| `SPACE` | Pick up / Drop block (requires Arm) |

---

## 🧩 Robot Components

Add or remove components from the **Toolbox** panel on the left:

| Component | Description |
|---|---|
| **Chassis** | Core robot body — must be added before any other part |
| **Wheels (WASD)** | Enables keyboard-driven movement |
| **LiDAR** | Rotating laser scanner; detects nearby objects and reports shape & color |
| **Camera (View)** | First-person camera feed shown in the top-left overlay |
| **Arm (SPACE)** | Allows picking up and dropping blocks with the SPACE key |

---

## 📡 LiDAR Detection

When the LiDAR sensor is active, its beam sweeps 360° around the robot. When the beam intersects an object within range, the **Detection Panel** (bottom of the right sidebar) instantly displays:

- The **shape** of the detected object — `Square`, `Circle`, or `Triangle`
- The **color** of the detected object — e.g. `Red`, `Orange`, `Green`, `Blue`

---

## ⚙️ Settings (Right Sidebar)

| Setting | Description |
|---|---|
| **Power** | Motor power level (10 % – 100 %) |
| **Turn** | Turning speed (1° – 15°) |
| **Color** | Chassis colour picker |

---

## 🤝 Contributing

Contributions, bug reports, and feature requests are welcome!

1. Fork this repository
2. Create a new branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m 'Add your feature'`
4. Push to your fork: `git push origin feature/your-feature-name`
5. Open a **Pull Request** against `main`

Please open an [issue](https://github.com/alphaonelabs/alphaonelabs-virtual-robotics-playground/issues) first to discuss major changes before starting work.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

*Built by [Alpha One Labs](https://github.com/alphaonelabs) — Advancing open science through education and robotics.*
