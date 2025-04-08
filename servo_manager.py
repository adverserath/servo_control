import RPi.GPIO as GPIO
from config import (
    SERVO_HORIZONTAL_PIN, 
    SERVO_VERTICAL_PIN, 
    SERVO_FOCUS_PIN,
    PWM_FREQUENCY
)

class ServoManager:
    def __init__(self):
        # Set up the Raspberry Pi GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Set up GPIO pins for servos
        self._setup_pins()
        
        # Initialize PWM controllers
        self._setup_pwm()
        
        # Current position values (-1 to 1 range)
        self.horizontal_pos = 0
        self.vertical_pos = 0
        self.focus_pos = 0
    
    def _setup_pins(self):
        """Configure the GPIO pins for servo control"""
        GPIO.setup(SERVO_HORIZONTAL_PIN, GPIO.OUT)
        GPIO.setup(SERVO_VERTICAL_PIN, GPIO.OUT)
        GPIO.setup(SERVO_FOCUS_PIN, GPIO.OUT)
    
    def _setup_pwm(self):
        """Set up PWM for each servo motor"""
        self.pwm_horizontal = GPIO.PWM(SERVO_HORIZONTAL_PIN, PWM_FREQUENCY)
        self.pwm_vertical = GPIO.PWM(SERVO_VERTICAL_PIN, PWM_FREQUENCY)
        self.pwm_focus = GPIO.PWM(SERVO_FOCUS_PIN, PWM_FREQUENCY)
        
        # Start with 0 duty cycle
        self.pwm_horizontal.start(0)
        self.pwm_vertical.start(0)
        self.pwm_focus.start(0)
    
    def update_position(self, horizontal=None, vertical=None, focus=None):
        """Update the servo positions with new values"""
        if horizontal is not None:
            self.horizontal_pos = max(-1, min(1, horizontal))
            self.pwm_horizontal.ChangeDutyCycle(self._map_to_pwm(self.horizontal_pos))
            
        if vertical is not None:
            self.vertical_pos = max(-1, min(1, vertical))
            self.pwm_vertical.ChangeDutyCycle(self._map_to_pwm(self.vertical_pos))
            
        if focus is not None:
            self.focus_pos = max(-1, min(1, focus))
            self.pwm_focus.ChangeDutyCycle(self._map_to_pwm(self.focus_pos))
    
    def _map_to_pwm(self, value):
        """Map from -1,1 range to PWM duty cycle (0-100)"""
        return (value + 1) * 50
    
    def cleanup(self):
        """Stop PWM and clean up GPIO"""
        self.pwm_horizontal.stop()
        self.pwm_vertical.stop()
        self.pwm_focus.stop()
        GPIO.cleanup() 