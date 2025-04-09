import logging
import platform
import threading
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServoController:
    def __init__(self):
        self.is_raspberry_pi = (platform.system() == 'Linux' and 
                               platform.machine().startswith('arm'))
        
        # Initialize positions
        self.horizontal_pos = 90
        self.vertical_pos = 90
        self.focus_pos = 90
        
        # Initialize error tracking
        self.error_count = 0
        self.last_error = None
        
        # Initialize connection status
        self.is_connected = False
        
        # Thread safety
        self.lock = threading.Lock()
        
        if self.is_raspberry_pi:
            try:
                import RPi.GPIO as GPIO
                from config import HORIZONTAL_PIN, VERTICAL_PIN, FOCUS_PIN, PWM_FREQ
                
                # Set up GPIO pins
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(HORIZONTAL_PIN, GPIO.OUT)
                GPIO.setup(VERTICAL_PIN, GPIO.OUT)
                GPIO.setup(FOCUS_PIN, GPIO.OUT)
                
                # Create PWM objects
                self.horizontal_pwm = GPIO.PWM(HORIZONTAL_PIN, PWM_FREQ)
                self.vertical_pwm = GPIO.PWM(VERTICAL_PIN, PWM_FREQ)
                self.focus_pwm = GPIO.PWM(FOCUS_PIN, PWM_FREQ)
                
                # Start PWM
                self.horizontal_pwm.start(0)
                self.vertical_pwm.start(0)
                self.focus_pwm.start(0)
                
                self.is_connected = True
                logger.info("Servo controller initialized on Raspberry Pi")
            except Exception as e:
                logger.error(f"Failed to initialize servo controller: {e}")
                self.is_connected = False
        else:
            logger.info("Running in development mode - using mock servo controller")
    
    def update_position(self, axis: str, position: int) -> None:
        """Update the position of a servo."""
        try:
            with self.lock:
                if axis == 'horizontal':
                    self.horizontal_pos = position
                    if self.is_raspberry_pi:
                        self.horizontal_pwm.ChangeDutyCycle(self._position_to_duty(position))
                elif axis == 'vertical':
                    self.vertical_pos = position
                    if self.is_raspberry_pi:
                        self.vertical_pwm.ChangeDutyCycle(self._position_to_duty(position))
                elif axis == 'focus':
                    self.focus_pos = position
                    if self.is_raspberry_pi:
                        self.focus_pwm.ChangeDutyCycle(self._position_to_duty(position))
                else:
                    raise ValueError(f"Invalid axis: {axis}")
                
                logger.debug(f"Updated {axis} position to {position}")
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"Error updating {axis} position: {e}")
            raise
    
    def _position_to_duty(self, position: int) -> float:
        """Convert position (0-180) to duty cycle (0-100)."""
        return position / 18.0
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the servo controller."""
        with self.lock:
            return {
                'connected': self.is_connected,
                'error_count': self.error_count,
                'last_error': self.last_error,
                'positions': {
                    'horizontal': self.horizontal_pos,
                    'vertical': self.vertical_pos,
                    'focus': self.focus_pos
                }
            }
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.is_raspberry_pi:
                import RPi.GPIO as GPIO
                self.horizontal_pwm.stop()
                self.vertical_pwm.stop()
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