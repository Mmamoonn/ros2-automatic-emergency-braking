import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped

class AutoDriver(Node):
    """
    A simple node for AEB testing. Constantly publishes a forward 
    velocity to /drive_cmd so the safety_node can intercept it.
    """
    def __init__(self):
        super().__init__('auto_driver')
        
        # Note: Publishing to /drive_cmd, NOT /cmd_vel
        self.publisher_ = self.create_publisher(TwistStamped, '/drive_cmd', 10)
        
        # Publish at 20 Hz
        self.timer = self.create_timer(0.05, self.timer_callback) 
        self.speed = 0.5  # m/s

        self.get_logger().info(f'AutoDriver active: Cruising at {self.speed} m/s')

    def timer_callback(self):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        
        # Constant forward velocity, zero steering
        msg.twist.linear.x = self.speed
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
