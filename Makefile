#  Automatic Emergency Braking — Build & Simulation Automation
#  Usage:  make <target>

WORKSPACE   := $(HOME)/ros2_aeb
SHELL       := /bin/bash
ROS_DISTRO  := jazzy
TB3_MODEL   := burger

# Source helpers
SOURCE_ROS   = source /opt/ros/$(ROS_DISTRO)/setup.bash
SOURCE_WS    = source $(WORKSPACE)/install/setup.bash
EXPORT_MODEL = export TURTLEBOT3_MODEL=$(TB3_MODEL)
SETUP        = $(SOURCE_ROS) && $(SOURCE_WS) && $(EXPORT_MODEL)

.PHONY: all build clean sim teleop safety run-all help

# ── default 

all: build

# ── build workspace 

build:
	@echo "Building workspace..."
	@cd $(WORKSPACE) && $(SOURCE_ROS) && colcon build --packages-select safety_node
	@echo "Build complete."

# ── build everything (all packages) 

build-all:
	@echo "Building all packages..."
	@cd $(WORKSPACE) && $(SOURCE_ROS) && colcon build
	@echo "Full build complete."

# ── clean build artifacts 

clean:
	@echo "Cleaning build, install, log directories..."
	@cd $(WORKSPACE) && rm -rf build/ install/ log/
	@echo "Clean complete."

# ── launch Gazebo simulator

sim:
	@echo "Launching TurtleBot3 Gazebo simulation..."
	@$(SETUP) && ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py

# ── launch keyboard teleop

teleop:
	@echo "Launching keyboard teleop (TwistStamped)..."
	@echo "Controls:  i=forward  ,=backward  k=stop  u/o=turn  q/z=speed"
	@$(SETUP) && ros2 run teleop_twist_keyboard teleop_twist_keyboard \
		--ros-args -p stamped:=true

# ── launch safety node

safety:
	@echo "Launching AEB Safety Node..."
	@$(SETUP) && ros2 run safety_node safety_node

# ── launch safety node with custom threshold 

safety-tune:
	@echo "Launching AEB Safety Node (threshold=$(THRESHOLD)s)..."
	@$(SETUP) && ros2 run safety_node safety_node \
		--ros-args -p ittc_threshold:=$(or $(THRESHOLD),0.8)

# ── launch ALL three in separate gnome-terminal tabs 
run-all:
	@echo "Opening all terminals..."
	@gnome-terminal \
		--tab --title="Gazebo Sim"    -- bash -c "$(SETUP) && ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py; exec bash" \
		--tab --title="Teleop"        -- bash -c "sleep 4 && $(SETUP) && ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true; exec bash" \
		--tab --title="Safety Node"   -- bash -c "sleep 5 && $(SETUP) && ros2 run safety_node safety_node; exec bash" \
	|| \
	xterm -T "Gazebo Sim"  -e "bash -c '$(SETUP) && ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py; exec bash'" & \
	sleep 4 && \
	xterm -T "Teleop"      -e "bash -c '$(SETUP) && ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true; exec bash'" & \
	sleep 1 && \
	xterm -T "Safety Node" -e "bash -c '$(SETUP) && ros2 run safety_node safety_node; exec bash'" &
	@echo "All terminals launched."

# ── monitor topics live
monitor:
	@echo "Active topics:"
	@$(SETUP) && ros2 topic list
	@echo ""
	@echo "📡  Watching /cmd_vel for brake commands..."
	@$(SETUP) && ros2 topic echo /cmd_vel

# ── check topic hz 
hz:
	@$(SETUP) && ros2 topic hz /scan

# ── help
help:
	@echo ""
	@echo "  AEB Safety Node — Makefile Targets"
	@echo "  ─────────────────────────────────────────────────────"
	@echo "  make build          Build safety_node package only"
	@echo "  make build-all      Build entire workspace"
	@echo "  make clean          Remove build/install/log dirs"
	@echo "  make sim            Launch Gazebo + TurtleBot3 world"
	@echo "  make teleop         Launch keyboard teleoperation"
	@echo "  make safety         Launch AEB safety node"
	@echo "  make safety-tune    Launch with custom threshold"
	@echo "                      e.g.  make safety-tune THRESHOLD=1.2"
	@echo "  make run-all        Open all 3 terminals at once"
	@echo "  make monitor        Watch /cmd_vel brake commands live"
	@echo "  make hz             Check /scan publish rate"
	@echo "  ─────────────────────────────────────────────────────"
	@echo ""
