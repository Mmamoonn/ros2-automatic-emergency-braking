# 🛑 Automatic Emergency Braking (AEB) — ROS 2

<p align="center">
  <img src="https://img.shields.io/badge/ROS2-Jazzy-blue?logo=ros&logoColor=white" />
  <img src="https://img.shields.io/badge/Ubuntu-24.04_LTS-orange?logo=ubuntu&logoColor=white" />
  <img src="https://img.shields.io/badge/Gazebo-Harmonic_8.x-informational?logo=gazebo" />
  <img src="https://img.shields.io/badge/Python-3.12-yellow?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/TurtleBot3-Burger-green" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" />
</p>

> A safety-critical ROS 2 node that uses real-time LiDAR data to compute
> **Instantaneous Time to Collision (iTTC)** and automatically stops a robot
> before impact — the same principle behind AEB in modern road vehicles.

---

## 📋 Table of Contents

- [Overview](#overview)
- [How iTTC Works](#how-ittc-works)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Testing](#testing)
- [Results](#results)
- [Acknowledgements](#acknowledgements)

---

## Overview

This project implements a **Safety Node** for a simulated differential-drive
robot (TurtleBot3 Burger) in Gazebo Harmonic. The node:

1. Subscribes to `/scan` (360° LiDAR) and `/odom` (odometry).
2. Computes iTTC for every beam in a configurable forward arc.
3. Publishes a zero-velocity command to `/cmd_vel` the instant any beam's
   iTTC drops below the threshold.

The implementation follows the **F1Tenth Robotics curriculum** (Lab 2) and
was developed as part of the **Robotics Design Lab II (RDL-II)** course at
the **University of Central Punjab (UCP)**.

---

## How iTTC Works

The core formula is:

```
iTTC = r / max(−ṙ, 0)
```

| Symbol | Meaning | Source |
|--------|---------|--------|
| `r` | Current range to obstacle at beam angle θ | `ranges[i]` from LaserScan |
| `ṙ` | Rate of change of range | `−vₓ · cos(θ)` from Odometry |
| `max(−ṙ, 0)` | Only count closing beams | Beams moving away → iTTC = ∞ |

**Sign convention:** when the robot moves toward a wall, range shrinks → ṙ < 0.
The formula flips the sign so the denominator is positive, giving a meaningful
time value. If the robot moves away, the denominator is zero and iTTC = ∞ (safe).

### Step-by-Step Calculation

```
Step 1 — Clean:   Replace NaN / Inf in ranges[] with range_max
Step 2 — Angles:  θᵢ = angle_min + i × angle_increment
Step 3 — ṙ:       ṙᵢ = −vₓ · cos(θᵢ)
Step 4 — iTTC:    iTTCᵢ = rᵢ / max(−ṙᵢ, 0)   [∞ when denominator = 0]
Step 5 — Mask:    Only consider beams within ±90° forward arc
Step 6 — Decide:  If min(iTTC_forward) < threshold → BRAKE
```

---

## System Architecture

```
┌──────────────────┐      /scan (LaserScan)       ┌─────────────────────┐
│   LiDAR Sensor   │ ──────────────────────────►  │                     │
└──────────────────┘                              │    Safety Node      │
                                                  │                     │
┌──────────────────┐      /odom (Odometry)        │  • Cleans ranges    │
│    Odometry      │ ──────────────────────────►  │  • Computes iTTC    │     /cmd_vel
└──────────────────┘                              │  • Masks arc        │  ──────────────► Motor Controller
                                                  │  • Thresholds       │  (TwistStamped
                                                  │  • Publishes brake  │   speed = 0.0)
                                                  └─────────────────────┘
```

---

## Project Structure

```
ros2_aeb/
└── src/
    └── safety_node/
        ├── safety_node/
        │   ├── __init__.py
        │   └── safety_node.py      ← Core AEB logic
        ├── package.xml
        ├── setup.py
        ├── setup.cfg
        └── test/
Makefile                            ← Build & simulation automation
README.md                           ← This file
USAGE.md                            ← Detailed usage guide
.gitignore
```

---

## Quick Start

### Prerequisites

```bash
# ROS 2 Jazzy
sudo apt install ros-jazzy-turtlebot3-gazebo \
                 ros-jazzy-teleop-twist-keyboard \
                 ros-jazzy-ackermann-msgs

echo "export TURTLEBOT3_MODEL=burger" >> ~/.bashrc
source ~/.bashrc
```

### Build

```bash
cd ~/ros2_aeb
make build
```

### Run Everything (one command)

```bash
make run-all
```

This opens three terminals automatically:
- **Terminal 1** — Gazebo simulation
- **Terminal 2** — Keyboard teleop
- **Terminal 3** — AEB Safety Node

### Or Launch Manually

```bash
# Terminal 1 — Simulator
make sim

# Terminal 2 — Teleop
make teleop

# Terminal 3 — Safety Node
make safety
```

See [USAGE.md](USAGE.md) for the full guide including tuning and testing.

---

## Configuration

Parameters can be overridden at launch:

```bash
ros2 run safety_node safety_node \
  --ros-args \
  -p ittc_threshold:=1.0 \
  -p forward_arc_deg:=60.0
```

Or via the Makefile:

```bash
make safety-tune THRESHOLD=1.2
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ittc_threshold` | `0.8` s | Brake trigger time |
| `forward_arc_deg` | `90.0` ° | Half-angle of monitored arc |

---

## Testing

| Test | Expected Behaviour |
|------|--------------------|
| Drive straight down open hallway | Node stays silent — no false braking |
| Drive directly at a wall | Node logs warning and stops before impact |
| Drive at an angle toward a wall | Node brakes only when forward iTTC < threshold |
| Robot stationary near wall | No brake — speed = 0 → ṙ = 0 → iTTC = ∞ |

---

## Results

- ✅ Zero false positives in open TurtleBot3 world
- ✅ Consistent braking before wall impact at all tested speeds
- ✅ iTTC warning logged with exact time-to-collision value
- ✅ AEB release logged when path clears

---


