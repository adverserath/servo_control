import platform
import time
import logging
import threading
from config import HORIZONTAL_PIN, VERTICAL_PIN, FOCUS_PIN, PWM_FREQ

# Configure logging
logger = logging.getLogger(__name__)

# Check if running on Raspberry Pi
IS_RASPBERRY_PI = (platform.system() == 'Linux' and 
                   platform.machine().startswith('arm'))

if IS_RASPBERRY_PI:
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
    except ImportError:
        logger.warning("RPi.GPIO not available, using mock implementation")
        IS_RASPBERRY_PI = False

class ServoController:
    def __init__(self):
        self.horizontal_pin = HORIZONTAL_PIN
        self.vertical_pin = VERTICAL_PIN
        self.focus_pin = FOCUS_PIN
        self.pwm_freq = PWM_FREQ
        
        # Initialize current positions
        self.horizontal_pos = 0
        self.vertical_pos = 0
        self.focus_pos = 0
        
        # Initialize error tracking
        self.error_count = 0
        self.last_error_time = 0
        
        # Initialize connection status
        self.is_connected = False
        
        # Initialize lock for thread safety
        self.lock = threading.Lock()
        
        # Initialize PWM objects
        if IS_RASPBERRY_PI:
            self.horizontal_pwm = GPIO.PWM(self.horizontal_pin, self.pwm_freq)
            self.vertical_pwm = GPIO.PWM(self.vertical_pin, self.pwm_freq)
            self.focus_pwm = GPIO.PWM(self.focus_pin, self.pwm_freq)
            
            # Start PWM
            self.horizontal_pwm.start(0)
            self.vertical_pwm.start(0)
            self.focus_pwm.start(0)
            
            self.is_connected = True
        else:
            logger.info("Using mock servo controller")
            self.horizontal_pwm = None
            self.vertical_pwm = None
            self.focus_pwm = None
    
    def update_position(self, horizontal=None, vertical=None, focus=None):
        """Update servo positions."""
        try:
            with self.lock:
                if horizontal is not None:
                    self.horizontal_pos = max(-1.0, min(1.0, horizontal))
                    if IS_RASPBERRY_PI:
                        self.horizontal_pwm.ChangeDutyCycle(self._set_servo(self.horizontal_pos))
                    else:
                        logger.debug(f"Mock horizontal servo: {self.horizontal_pos}")
                
                if vertical is not None:
                    self.vertical_pos = max(-1.0, min(1.0, vertical))
                    if IS_RASPBERRY_PI:
                        self.vertical_pwm.ChangeDutyCycle(self._set_servo(self.vertical_pos))
                    else:
                        logger.debug(f"Mock vertical servo: {self.vertical_pos}")
                
                if focus is not None:
                    self.focus_pos = max(-1.0, min(1.0, focus))
                    if IS_RASPBERRY_PI:
                        self.focus_pwm.ChangeDutyCycle(self._set_servo(self.focus_pos))
                    else:
                        logger.debug(f"Mock focus servo: {self.focus_pos}")
                
                return True
        except Exception as e:
            logger.error(f"Error updating servo position: {e}")
            self.error_count += 1
            self.last_error_time = time.time()
            return False
    
    def _set_servo(self, value):
        """Convert position value (-1.0 to 1.0) to PWM duty cycle (0 to 100)."""
        # Map -1.0 to 1.0 to 0 to 100
        return (value + 1.0) * 50
    
    def get_status(self):
        """Get the current status of the servo controller."""
        return {
            'connected': self.is_connected,
            'error_count': self.error_count,
            'last_error_time': self.last_error_time,
            'horizontal_pos': self.horizontal_pos,
            'vertical_pos': self.vertical_pos,
            'focus_pos': self.focus_pos
        }
    
    def cleanup(self):
        """Clean up resources."""
        try:
            if IS_RASPBERRY_PI:
                if self.horizontal_pwm:
                    self.horizontal_pwm.stop()
                if self.vertical_pwm:
                    self.vertical_pwm.stop()
                if self.focus_pwm:
                    self.focus_pwm.stop()
                GPIO.cleanup()
            logger.info("Servo controller cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Function to map joystick values to PWM duty cycle
# This function seems specific to the old structure, ServoManager has its own mapping
# def map_to_pwm(value):
#     # Map the joystick range (-1 to 1) to PWM range (0 to 100)
#     return (value + 1) * 50  # PWM duty cycle is between 0 and 100

# Note: This file might become redundant if ServoManager handles everything.
# Consider if this file is still needed at all, or if its remaining 
# GPIO setup logic belongs in ServoManager's __init__. 