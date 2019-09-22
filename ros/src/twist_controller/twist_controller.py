from pid import PID
import rospy
from lowpass import LowPassFilter
from yaw_controller import YawController

GAS_DENSITY = 2.858
ONE_MPH = 0.44704


class Controller(object):
    def __init__(self, vehicle_mass, brake_deadband, decel_limit, accel_limit, wheel_radius, wheel_base, steer_ratio, max_lat_accel, max_steer_angle):

        kp = 0.001 #0.3  0.5 Need to tune   0.001
        ki = 0.1 #0.1  0.1                 0.01
        kd = 0.01 #0.0  2.5                 0.01 with no derivative

        mn = 0.0 # minimum throttle
        mx = 0.3 # maximum throttle
        self.throttle_controller = PID(kp, ki, kd, mn, mx)

        tau = 0.5
        ts = 0.02
        self.vel_lpf = LowPassFilter(tau, ts)

        self.yaw_controller = YawController(wheel_base, steer_ratio, 0.1, max_lat_accel, max_steer_angle)

        self.vehicle_mass = vehicle_mass
        self.brake_deadband = brake_deadband
        self.decel_limit = decel_limit
        self.accel_limit = accel_limit
        self.wheel_radius = wheel_radius

        self.last_time = rospy.get_time()

    def control(self, current_vel, dbw_enabled, linear_vel, angular_vel):
        if dbw_enabled is False:
            rospy.loginfo_throttle(1.0, "DBW INACTIVE")
            self.throttle_controller.reset()
            return 0.0, 0.0, 0.0  # Return throttle, brake, steer

        current_vel = self.vel_lpf.filt(current_vel)
        vel_error = linear_vel - current_vel
        self.last_vel = current_vel

        steering = self.yaw_controller.get_steering(linear_vel, angular_vel, current_vel)

        current_time = rospy.get_time()
        sample_time = current_time - self.last_time
        self.last_time = current_time

        throttle = self.throttle_controller.step(vel_error, sample_time)
        brake = 0.0

        if linear_vel == 0.0 and current_vel < 0.1: # todo: jerk-minimizing brake application
            throttle = 0.0
            brake = 750.0 #N.m  was 400

        elif throttle < 0.1 and vel_error < 0:
            throttle = 0.0
            decel = max(vel_error, self.decel_limit)
            brake = abs(decel) * self.vehicle_mass * self.wheel_radius
        
        #if brake > 0.0:
        #    throttle = 0.0

        return throttle, brake, steering
