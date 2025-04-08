import RPi.GPIO as GPIO
from config import (
    HORIZONTAL_PIN, 
    VERTICAL_PIN, 
    FOCUS_PIN,
    PWM_FREQ
)

class ServoManager:
    def __init__(self):
        # Set up the Raspberry Pi GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Initialize servo positions
        self.horizontal_pos = 0
        self.vertical_pos = 0
        self.focus_pos = 0
        
        # Set up pins and PWM
        self._setup_pins()
        self._setup_pwm()
        
        # Error tracking
        self.error = None
        self.connected = True
    
    def _setup_pins(self):
        """Set up GPIO pins for servos"""
        GPIO.setup(HORIZONTAL_PIN, GPIO.OUT)
        GPIO.setup(VERTICAL_PIN, GPIO.OUT)
        GPIO.setup(FOCUS_PIN, GPIO.OUT)
    
    def _setup_pwm(self):
        """Set up PWM for servos"""
        self.horizontal_pwm = GPIO.PWM(HORIZONTAL_PIN, PWM_FREQ)
        self.vertical_pwm = GPIO.PWM(VERTICAL_PIN, PWM_FREQ)
        self.focus_pwm = GPIO.PWM(FOCUS_PIN, PWM_FREQ)
        
        # Start PWM with 0% duty cycle
        self.horizontal_pwm.start(0)
        self.vertical_pwm.start(0)
        self.focus_pwm.start(0)
    
    def update_position(self, horizontal=None, vertical=None, focus=None):
        """Update servo positions"""
        try:
            if horizontal is not None:
                self.horizontal_pos = max(-1, min(1, horizontal))
                self.horizontal_pwm.ChangeDutyCycle(self._map_to_pwm(self.horizontal_pos))
            
            if vertical is not None:
                self.vertical_pos = max(-1, min(1, vertical))
                self.vertical_pwm.ChangeDutyCycle(self._map_to_pwm(self.vertical_pos))
            
            if focus is not None:
                self.focus_pos = max(-1, min(1, focus))
                self.focus_pwm.ChangeDutyCycle(self._map_to_pwm(self.focus_pos))
            
            self.error = None
            self.connected = True
            
        except Exception as e:
            self.error = str(e)
            self.connected = False
    
    def _map_to_pwm(self, value):
        """Map from -1,1 range to PWM duty cycle (0-100)"""
        return (value + 1) * 50
    
    def cleanup(self):
        """Clean up GPIO resources"""
        try:
            self.horizontal_pwm.stop()
            self.vertical_pwm.stop()
            self.focus_pwm.stop()
            GPIO.cleanup()
        except:
            pass 