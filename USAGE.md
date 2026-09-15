# USAGE GUIDE — Automatic Emergency Braking (AEB)

Complete setup, operation, and tuning guide for the AEB Safety Node.

---

## Environment Requirements

| Requirement | Version |
|-------------|---------|
| OS | Ubuntu 24.04 LTS |
| ROS 2 | Jazzy |
| Gazebo | Harmonic 8.x |
| Python | 3.12 |
| TurtleBot3 Model | burger |

---

## 1 — First-Time Setup

```bash
# Install dependencies
sudo apt update
sudo apt install -y \
  ros-jazzy-turtlebot3-gazebo \
  ros-jazzy-teleop-twist-keyboard \
  ros-jazzy-nav-msgs \
  ros-jazzy-sensor-msgs

# Set TurtleBot3 model (only needed once)
echo "export TURTLEBOT3_MODEL=burger" >> ~/.bashrc
source ~/.bashrc

# Build the safety node
cd ~/ros2_aeb
make build
```

---

## 2 — Running the Simulation

### Option A — One Command (Recommended)

```bash
make run-all
```

Opens Gazebo, teleop, and the safety node in separate terminal tabs
automatically. Wait ~5 seconds for Gazebo to fully load before driving.

---

### Option B — Manual (3 Terminals)

**Terminal 1 — Start Gazebo:**
```bash
make sim
```

Wait until you see the TurtleBot3 world render fully before proceeding.

**Terminal 2 — Start Teleop:**
```bash
make teleop
```

**Terminal 3 — Start Safety Node:**
```bash
make safety
```

---

## 3 — Driving Controls

> ⚠️ The teleop terminal **must be the focused/active window** for keys to register.

```
Keyboard layout:
   u    i    o
   j    k    l
   m    ,    .

i       → Move forward
,       → Move backward
k       → Full stop
u / o   → Forward-left / Forward-right
j / l   → Rotate left / right in place
q       → Increase linear speed by 10%
z       → Decrease linear speed by 10%
w       → Increase angular speed by 10%
x       → Decrease angular speed by 10%
```

Start with a low speed (press `z` twice before driving).

---

## 4 — What to Expect

### Safety Node Output (Terminal 3)

Normal operation:
```
[INFO] [safety_node]: SafetyNode ready — iTTC threshold: 0.80s | Forward arc: ±90°
```

Collision detected:
```
[WARN] [safety_node]: ⚠  COLLISION IMMINENT — min iTTC = 0.623s  → BRAKING
```

Path cleared:
```
[INFO] [safety_node]: ✓  Path clear — AEB released.
```

---

## 5 — Tuning the Threshold

### Problem: Car stops too early (false positives in open space)
```bash
# Increase threshold or tighten the arc
make safety-tune THRESHOLD=0.5

# Or tighten the forward arc to ±45°:
ros2 run safety_node safety_node \
  --ros-args -p forward_arc_deg:=45.0
```

### Problem: Car doesn't brake in time
```bash
# Increase threshold
make safety-tune THRESHOLD=1.2
```

### Recommended Starting Values

| Environment | Threshold | Arc |
|-------------|-----------|-----|
| Open world | 0.8 s | ±90° |
| Narrow hallway | 0.6 s | ±60° |
| High speed | 1.2 s | ±90° |
| Low speed | 0.5 s | ±90° |

---

## 6 — Monitoring & Debugging

### Check All Topics Are Active
```bash
make monitor
```

### Check LiDAR Publish Rate
```bash
make hz
```
Expected: ~10 Hz for TurtleBot3 burger.

### Manually Inspect LiDAR Data
```bash
source ~/ros2_aeb/install/setup.bash
ros2 topic echo /scan --once
```

### Manually Inspect Odometry
```bash
ros2 topic echo /odom --once
```

### Watch Brake Commands in Real-Time
```bash
ros2 topic echo /cmd_vel
```

---

## 7 — Required Test Scenarios

Per the lab rubric, record both of the following:

**Test 1 — No False Positives:**
Drive the robot straight through the open TurtleBot3 world.
The safety node must NOT trigger any braking.

**Test 2 — Correct Braking:**
Drive the robot directly toward a wall at moderate speed.
The robot must stop before making contact.

Record your screen and upload to YouTube as Unlisted.
Paste the link in `SUBMISSION.md`.

---

## 8 — Common Issues

| Issue | Likely Cause | Fix |
|-------|-------------|-----|
| Car won't move | `/cmd_vel` type mismatch | Ensure teleop uses `stamped:=true` |
| Safety node crashes | Missing `geometry_msgs` dep | `sudo apt install ros-jazzy-geometry-msgs` |
| Gazebo won't open | Missing model files | Run `make build-all` first |
| False braking everywhere | Threshold too high or arc too wide | Lower threshold or use `forward_arc_deg:=45.0` |
| Never brakes at wall | Threshold too low | Increase to 1.0–1.5 s |
| `NaN` in scan data | Not filtering scan | Already handled in node — check numpy version |

---

## 9 — Rebuild After Code Changes

```bash
# Edit the node
nano ~/ros2_aeb/src/safety_node/safety_node/safety_node.py

# Rebuild only the changed package
make build

# Relaunch
make safety
```

No need to restart Gazebo or teleop — only restart the safety node.
