# REQUIREMENTS — Automatic Emergency Braking (AEB)

Complete specification of system, software, hardware, and functional
requirements for the AEB Safety Node.

---

## 1 — System Requirements

### 1.1 Operating Environment

| Requirement | Specification |
|-------------|---------------|
| Operating System | Ubuntu 24.04 LTS (Noble Numbat) |
| ROS 2 Distribution | Jazzy Jalisco |
| Simulation Engine | Gazebo Harmonic 8.x |
| Robot Model | TurtleBot3 Burger |
| Python Version | 3.12 |
| Architecture | x86_64 |

### 1.2 Hardware Requirements (for native simulation)

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4-core 2.0 GHz | 6-core 3.0 GHz+ |
| RAM | 8 GB | 16 GB |
| Disk | 10 GB free | 20 GB free |
| GPU | OpenGL 3.3 support | Dedicated GPU (for Gazebo rendering) |

---

## 2 — Software Dependencies

### 2.1 ROS 2 Packages

Install with:
```bash
sudo apt install -y \
  ros-jazzy-turtlebot3-gazebo \
  ros-jazzy-teleop-twist-keyboard \
  ros-jazzy-nav-msgs \
  ros-jazzy-sensor-msgs \
  ros-jazzy-geometry-msgs \
  ros-jazzy-ackermann-msgs \
  ros-jazzy-ros-gz
```

| Package | Version | Purpose |
|---------|---------|---------|
| `ros-jazzy-turtlebot3-gazebo` | ≥ 2.3.7 | Simulation environment and robot model |
| `ros-jazzy-teleop-twist-keyboard` | any | Manual keyboard control for testing |
| `ros-jazzy-nav-msgs` | any | `Odometry` message type |
| `ros-jazzy-sensor-msgs` | any | `LaserScan` message type |
| `ros-jazzy-geometry-msgs` | any | `TwistStamped` message type |
| `ros-jazzy-ros-gz` | ≥ 1.0.22 | ROS 2 ↔ Gazebo Harmonic bridge |

### 2.2 Python Packages

| Package | Version | Purpose |
|---------|---------|---------|
| `numpy` | ≥ 1.24 | Vectorised iTTC computation across all beams |
| `rclpy` | (bundled with ROS 2) | ROS 2 Python client library |

### 2.3 Build Tools

| Tool | Purpose |
|------|---------|
| `colcon` | ROS 2 workspace build system |
| `rosdep` | Automatic dependency resolution |
| `make` | Build and simulation automation (Makefile) |

---

## 3 — ROS 2 Interface Requirements

### 3.1 Subscribed Topics

| Topic | Message Type | QoS | Required Field(s) |
|-------|-------------|-----|------------------|
| `/scan` | `sensor_msgs/msg/LaserScan` | BEST_EFFORT, depth 10 | `ranges[]`, `angle_min`, `angle_max`, `angle_increment`, `range_max` |
| `/odom` | `nav_msgs/msg/Odometry` | RELIABLE, depth 10 | `twist.twist.linear.x` |

### 3.2 Published Topics

| Topic | Message Type | QoS | Published When |
|-------|-------------|-----|---------------|
| `/cmd_vel` | `geometry_msgs/msg/TwistStamped` | RELIABLE, depth 10 | iTTC < threshold |

### 3.3 ROS 2 Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ittc_threshold` | `double` | `0.8` | Collision time threshold in seconds |
| `forward_arc_deg` | `double` | `90.0` | Half-angle of monitored arc in degrees |

---

## 4 — Functional Requirements

### 4.1 Core AEB Behaviour

| ID | Requirement |
|----|-------------|
| FR-01 | The node SHALL subscribe to `/scan` and process every incoming LaserScan message |
| FR-02 | The node SHALL subscribe to `/odom` and maintain the robot's current longitudinal speed |
| FR-03 | The node SHALL replace all `NaN` and `Inf` values in `ranges[]` with `range_max` before computation |
| FR-04 | The node SHALL compute beam angle `θᵢ = angle_min + i × angle_increment` for every beam index `i` |
| FR-05 | The node SHALL compute range-rate `ṙᵢ = −vₓ · cos(θᵢ)` for every beam |
| FR-06 | The node SHALL compute `iTTCᵢ = rᵢ / max(−ṙᵢ, 0)` and set `iTTCᵢ = ∞` when denominator ≤ 0 |
| FR-07 | The node SHALL restrict collision checking to beams within `±forward_arc_deg` of the robot's heading |
| FR-08 | The node SHALL publish a zero-velocity `TwistStamped` to `/cmd_vel` when `min(iTTC_forward) < ittc_threshold` |
| FR-09 | The node SHALL log a `WARN` message including the exact minimum iTTC value when braking is triggered |
| FR-10 | The node SHALL log an `INFO` message when the brake is released and the path is clear |

### 4.2 Safety Requirements

| ID | Requirement |
|----|-------------|
| SR-01 | The node SHALL NOT cause false-positive braking when driving through open space |
| SR-02 | The node SHALL stop the robot before physical contact with any obstacle in the forward arc |
| SR-03 | The node SHALL handle a stationary robot correctly — `vₓ = 0` produces `ṙ = 0`, iTTC = ∞ (no brake) |
| SR-04 | The node SHALL handle the robot reversing correctly — negative `vₓ` shall not trigger forward braking |
| SR-05 | The node SHALL remain operational and non-crashing when receiving malformed or all-`NaN` scan data |

### 4.3 Performance Requirements

| ID | Requirement |
|----|-------------|
| PR-01 | The node SHALL process each LaserScan message within a single callback (no queuing lag) |
| PR-02 | iTTC computation SHALL use NumPy vectorised operations — no Python `for` loops over beams |
| PR-03 | The brake command SHALL be published in the same callback cycle that detects the threshold breach |

---

## 5 — Non-Functional Requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-01 | Configurability | All tuneable constants SHALL be exposed as ROS 2 parameters, not hard-coded |
| NFR-02 | Portability | The node SHALL run on any ROS 2 Jazzy installation without modification |
| NFR-03 | Readability | Code SHALL include inline comments explaining each step of the iTTC calculation |
| NFR-04 | Maintainability | The node SHALL follow PEP 8 style and include Python type annotations |
| NFR-05 | Build | The project SHALL build with a single `make build` command |
| NFR-06 | Simulation | All three simulation components SHALL be launchable with a single `make run-all` command |

---

## 6 — Verification & Test Requirements

| ID | Test | Pass Condition |
|----|------|---------------|
| VT-01 | Open world drive | Robot traverses open TurtleBot3 world — no brake triggered |
| VT-02 | Wall approach | Robot stops before contacting a wall when driven directly toward it |
| VT-03 | Angled approach | Robot brakes only when forward iTTC < threshold, not on side walls |
| VT-04 | Stationary near wall | No brake command when robot is stationary, regardless of proximity |
| VT-05 | Reverse drive | Robot can reverse without triggering forward AEB |
| VT-06 | Parameter override | `ittc_threshold` and `forward_arc_deg` can be changed at launch without recompiling |

---

## 7 — Deliverables

| Item | Description |
|------|-------------|
| `safety_node.py` | Fully documented AEB node source code |
| `package.xml` | ROS 2 package manifest with all dependencies declared |
| `setup.py` | Python package entry point configuration |
| `Makefile` | Build and simulation automation |
| `README.md` | Project overview, architecture, and quick-start guide |
| `USAGE.md` | Detailed setup, operation, tuning, and troubleshooting guide |
| `REQUIREMENTS.md` | This document |
| `.gitignore` | Excludes all build artifacts from version control |
| Screen recording | Two scenarios: open-world (no false positive) + wall-brake |

---

## 8 — Constraints

- The project uses **TurtleBot3 Burger** specifically because it ships a LiDAR and odometry compatible with Gazebo Harmonic on ROS 2 Jazzy natively — no Docker required.
- The node uses **`TwistStamped`** (not plain `Twist`) because the Gazebo Harmonic ROS bridge for TurtleBot3 Jazzy routes `/cmd_vel` as `geometry_msgs/msg/TwistStamped`.
- **Docker is not used** — the entire stack runs natively on Ubuntu 24.04 to avoid compatibility layers.
- The F1Tenth gym simulator is **not used** — it requires Docker and is incompatible with Python 3.12 and Jazzy natively.
