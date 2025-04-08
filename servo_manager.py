import RPi.GPIO as GPIO
import threading
import time
from config import (
    SERVO_HORIZONTAL_PIN,
    SERVO_VERTICAL_PIN,
    SERVO_FOCUS_PIN,
    PWM_FREQ
)

class ServoManager:
    def __init__(self):
        # Initialize GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup PWM pins
        GPIO.setup(SERVO_HORIZONTAL_PIN, GPIO.OUT)
        GPIO.setup(SERVO_VERTICAL_PIN, GPIO.OUT)
        GPIO.setup(SERVO_FOCUS_PIN, GPIO.OUT)
        
        # Create PWM objects
        self.pwm_horizontal = GPIO.PWM(SERVO_HORIZONTAL_PIN, PWM_FREQ)
        self.pwm_vertical = GPIO.PWM(SERVO_VERTICAL_PIN, PWM_FREQ)
        self.pwm_focus = GPIO.PWM(SERVO_FOCUS_PIN, PWM_FREQ)
        
        # Start PWM
        self.pwm_horizontal.start(0)
        self.pwm_vertical.start(0)
        self.pwm_focus.start(0)
        
        # Current positions (-1 to 1)
        self.horizontal_pos = 0
        self.vertical_pos = 0
        self.focus_pos = 0
        
        # Error tracking
        self.error = None
        self.connected = True
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
        print("Servo manager initialized")
    
    def update_position(self, horizontal=None, vertical=None, focus=None):
        """Update servo positions. Values should be between -1 and 1."""
        with self.lock:
            try:
                # Update positions
                if horizontal is not None:
                    self.horizontal_pos = max(-1, min(1, horizontal))
                    self._set_servo(self.pwm_horizontal, self.horizontal_pos)
                
                if vertical is not None:
                    self.vertical_pos = max(-1, min(1, vertical))
                    self._set_servo(self.pwm_vertical, self.vertical_pos)
                
                if focus is not None:
                    self.focus_pos = max(-1, min(1, focus))
                    self._set_servo(self.pwm_focus, self.focus_pos)
                
                self.error = None
                self.connected = True
                
            except Exception as e:
                self.error = str(e)
                self.connected = False
                print(f"Error updating servo position: {e}")
    
    def _set_servo(self, pwm, value):
        """Convert -1 to 1 value to PWM duty cycle (5 to 10)"""
        duty_cycle = 7.5 + (value * 2.5)  # 5 to 10
        pwm.ChangeDutyCycle(duty_cycle)
    
    def get_status(self):
        """Get the current status of the servo controller"""
        return {
            'connected': self.connected,
            'error': self.error,
            'positions': {
                'horizontal': self.horizontal_pos,
                'vertical': self.vertical_pos,
                'focus': self.focus_pos
            }
        }
    
    def cleanup(self):
        """Clean up GPIO resources"""
        try:
            self.pwm_horizontal.stop()
            self.pwm_vertical.stop()
            self.pwm_focus.stop()
            GPIO.cleanup()
            print("Servo manager cleaned up")
        except Exception as e:
            print(f"Error cleaning up servo manager: {e}") 