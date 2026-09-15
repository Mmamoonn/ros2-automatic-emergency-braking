import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy

from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TwistStamped

import numpy as np


# ── tuneable constants ────────────────────────────────────────────────────────
DEFAULT_ITTC_THRESHOLD  = 0.8    # seconds  – trigger brake below this value
DEFAULT_FORWARD_ARC_DEG = 90.0   # degrees  – half-angle of monitored arc (±)
MIN_RANGE_FILTER        = 0.05   # metres   – ignore beams closer than this
# ─────────────────────────────────────────────────────────────────────────────


class SafetyNode(Node):
    """
    Subscribes to /scan (LaserScan) and /odom (Odometry).
    Publishes a zero-velocity TwistStamped to /cmd_vel when a
    collision is predicted within ITTC_THRESHOLD seconds.
    """

    def __init__(self) -> None:
        super().__init__('safety_node')

        # ── ROS 2 parameters (overridable at launch) ──────────────────────────
        self.declare_parameter('ittc_threshold',  DEFAULT_ITTC_THRESHOLD)
        self.declare_parameter('forward_arc_deg', DEFAULT_FORWARD_ARC_DEG)

        self.ittc_threshold  = self.get_parameter('ittc_threshold').value
        self.forward_arc_rad = np.deg2rad(
            self.get_parameter('forward_arc_deg').value
        )

        # ── internal state ────────────────────────────────────────────────────
        self.speed: float = 0.0          # longitudinal speed  [m/s]
        self.braking: bool = False       # debounce flag

        # ── QoS: best-effort matches sensor publishers ────────────────────────
        sensor_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )

        # ── subscribers ───────────────────────────────────────────────────────
        self.create_subscription(
            LaserScan, '/scan', self.scan_callback, sensor_qos
        )
        self.create_subscription(
            Odometry, '/odom', self.odom_callback, 10
        )

        # ── publisher ─────────────────────────────────────────────────────────
        self.drive_pub = self.create_publisher(TwistStamped, '/cmd_vel', 10)

        self.get_logger().info(
            f'SafetyNode ready — iTTC threshold: {self.ittc_threshold:.2f}s | '
            f'Forward arc: ±{np.rad2deg(self.forward_arc_rad):.0f}°'
        )

    # ── odometry callback ─────────────────────────────────────────────────────
    def odom_callback(self, msg: Odometry) -> None:
        """Store the robot's forward (longitudinal) speed."""
        self.speed = msg.twist.twist.linear.x

    # ── scan callback — core AEB logic ────────────────────────────────────────
    def scan_callback(self, msg: LaserScan) -> None:
        """
        For every LiDAR beam:
          1. Clean NaN / Inf / out-of-range values.
          2. Compute beam angle θ.
          3. Compute range-rate  ṙ = −vₓ · cos(θ).
          4. Compute iTTC = r / max(−ṙ, 0).
          5. Mask to forward arc only.
          6. Brake if min(iTTC) < threshold.
        """

        # ── Step 1 — clean ranges ─────────────────────────────────────────────
        ranges = np.array(msg.ranges, dtype=np.float64)

        # Replace inf / NaN with max-range (safe — no obstacle detected)
        ranges = np.where(np.isfinite(ranges), ranges, msg.range_max)

        # Clamp below minimum sensing distance (avoids spurious readings)
        ranges = np.where(ranges >= MIN_RANGE_FILTER, ranges, msg.range_max)

        # ── Step 2 — beam angles ──────────────────────────────────────────────
        n = len(ranges)
        angles = msg.angle_min + np.arange(n) * msg.angle_increment   # [rad]

        # ── Step 3 — range-rate (Method A: project velocity onto beam) ────────
        # When the robot approaches an obstacle, the range shrinks → ṙ < 0.
        # ṙ = −vₓ · cos(θ)  produces a negative value for forward-facing beams.
        r_dot = -self.speed * np.cos(angles)

        # ── Step 4 — iTTC ─────────────────────────────────────────────────────
        # Denominator = max(−ṙ, 0): only count beams where range is shrinking.
        # Small epsilon prevents division-by-zero.
        denom = np.maximum(-r_dot, 0.0)
        ittc  = np.where(denom > 1e-9, ranges / denom, np.inf)

        # ── Step 5 — restrict to forward arc ─────────────────────────────────
        forward_mask = np.abs(angles) <= self.forward_arc_rad
        ittc_fwd     = np.where(forward_mask, ittc, np.inf)

        # ── Step 6 — collision decision ───────────────────────────────────────
        min_ittc = float(np.min(ittc_fwd))

        if min_ittc < self.ittc_threshold:
            if not self.braking:
                self.braking = True
                self.get_logger().warn(
                    f'⚠  COLLISION IMMINENT — min iTTC = {min_ittc:.3f}s  → BRAKING'
                )
            self._publish_brake()
        else:
            if self.braking:
                self.get_logger().info('✓  Path clear — AEB released.')
            self.braking = False

    # ── brake command ─────────────────────────────────────────────────────────
    def _publish_brake(self) -> None:
        """Publish a zero-velocity TwistStamped to immediately stop the robot."""
        msg = TwistStamped()
        msg.header.stamp    = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        msg.twist.linear.x  = 0.0
        msg.twist.angular.z = 0.0
        self.drive_pub.publish(msg)


# ── entry point ───────────────────────────────────────────────────────────────
def main(args=None) -> None:
    rclpy.init(args=args)
    node = SafetyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('SafetyNode shutting down gracefully.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
