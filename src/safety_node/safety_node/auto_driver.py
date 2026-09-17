import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from geometry_msgs.msg import TwistStamped
from sensor_msgs.msg import LaserScan
import numpy as np

class AutoDriver(Node):
    """
    An intelligent driver that drives forward but steers away from obstacles.
    Tuned to allow the SafetyNode (AEB) to trigger first.
    """
    def __init__(self):
        super().__init__('auto_driver')
        
        # ── Configuration ─────────────────────────────────────────────────────
        self.cruise_speed = 0.7      # m/s (Fast enough to trigger AEB early)
        self.turn_speed = 0.5        # rad/s
        self.turn_threshold = 0.45   # meters (Closer than the AEB trigger distance)
        
        # ── State ─────────────────────────────────────────────────────────────
        self.min_front_dist = 999.0  # Safe default
        
        # ── QoS Profile for LiDAR ─────────────────────────────────────────────
        sensor_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # ── Subscriptions & Publishers ────────────────────────────────────────
        self.create_subscription(LaserScan, '/scan', self.scan_callback, sensor_qos)
        self.publisher_ = self.create_publisher(TwistStamped, '/drive_cmd', 10)
        
        # Publish driving commands at 20 Hz
        self.timer = self.create_timer(0.05, self.timer_callback) 
        self.get_logger().info('Intelligent AutoDriver active. Looking for clear paths.')

    def scan_callback(self, msg: LaserScan):
        """Find the closest object in the front arc of the robot."""
        ranges = np.array(msg.ranges, dtype=np.float64)
        ranges = np.where(np.isfinite(ranges), ranges, msg.range_max)
        
        # Focus on a ±30 degree arc right in front of the robot
        n = len(ranges)
        angles = msg.angle_min + np.arange(n) * msg.angle_increment
        front_mask = np.abs(angles) <= np.deg2rad(30.0)
        
        # Update our state with the closest object in that forward view
        if np.any(front_mask):
            self.min_front_dist = np.min(ranges[front_mask])

    def timer_callback(self):
        """Decide whether to drive straight or turn."""
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        
        # If the path is blocked (or if AEB just stopped us in front of a wall)
        if self.min_front_dist < self.turn_threshold:
            # Spin in place to find a new path
            msg.twist.linear.x = 0.0
            msg.twist.angular.z = self.turn_speed
        else:
            # Coast is clear, floor it
            msg.twist.linear.x = self.cruise_speed
            msg.twist.angular.z = 0.0
            
        self.publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = AutoDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('AutoDriver stopped.')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
