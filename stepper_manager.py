import RPi.GPIO as GPIO
import time
from config import (
    STEPPER_H_STEP_PIN, 
    STEPPER_H_DIR_PIN, 
    STEPPER_H_EN_PIN,
    STEPPER_V_STEP_PIN, 
    STEPPER_V_DIR_PIN, 
    STEPPER_V_EN_PIN,
    STEPPER_F_STEP_PIN, 
    STEPPER_F_DIR_PIN, 
    STEPPER_F_EN_PIN,
    STEPPER_DELAY
)

class StepperManager:
    def __init__(self):
        # Set up the Raspberry Pi GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Set up GPIO pins for steppers
        self._setup_pins()
        
        # Current position values (-1 to 1 range)
        self.horizontal_pos = 0
        self.vertical_pos = 0
        self.focus_pos = 0
        
        # Disable motors initially
        self._disable_all_motors()
    
    def _setup_pins(self):
        """Configure the GPIO pins for stepper motor control"""
        # Horizontal Stepper (Azimuth)
        GPIO.setup(STEPPER_H_STEP_PIN, GPIO.OUT)
        GPIO.setup(STEPPER_H_DIR_PIN, GPIO.OUT)
        GPIO.setup(STEPPER_H_EN_PIN, GPIO.OUT)
        
        # Vertical Stepper (Elevation)
        GPIO.setup(STEPPER_V_STEP_PIN, GPIO.OUT)
        GPIO.setup(STEPPER_V_DIR_PIN, GPIO.OUT)
        GPIO.setup(STEPPER_V_EN_PIN, GPIO.OUT)
        
        # Focus Stepper
        GPIO.setup(STEPPER_F_STEP_PIN, GPIO.OUT)
        GPIO.setup(STEPPER_F_DIR_PIN, GPIO.OUT)
        GPIO.setup(STEPPER_F_EN_PIN, GPIO.OUT)
        
        # Initialize all pins to LOW
        for pin in [STEPPER_H_STEP_PIN, STEPPER_H_DIR_PIN, 
                   STEPPER_V_STEP_PIN, STEPPER_V_DIR_PIN,
                   STEPPER_F_STEP_PIN, STEPPER_F_DIR_PIN]:
            GPIO.output(pin, GPIO.LOW)
    
    def _step_motor(self, step_pin, dir_pin, direction, steps=1):
        """Control a stepper motor with direction and number of steps"""
        GPIO.output(dir_pin, GPIO.HIGH if direction else GPIO.LOW)
        for _ in range(steps):
            GPIO.output(step_pin, GPIO.HIGH)
            time.sleep(STEPPER_DELAY)
            GPIO.output(step_pin, GPIO.LOW)
            time.sleep(STEPPER_DELAY)
    
    def _map_to_steps(self, value, max_steps=10):
        """Map joystick value (-1 to 1) to number of steps"""
        return int(abs(value) * max_steps)
    
    def _enable_all_motors(self):
        """Enable all stepper motors"""
        GPIO.output(STEPPER_H_EN_PIN, GPIO.LOW)
        GPIO.output(STEPPER_V_EN_PIN, GPIO.LOW)
        GPIO.output(STEPPER_F_EN_PIN, GPIO.LOW)
    
    def _disable_all_motors(self):
        """Disable all stepper motors"""
        GPIO.output(STEPPER_H_EN_PIN, GPIO.HIGH)
        GPIO.output(STEPPER_V_EN_PIN, GPIO.HIGH)
        GPIO.output(STEPPER_F_EN_PIN, GPIO.HIGH)
    
    def update_position(self, horizontal=None, vertical=None, focus=None):
        """Update the stepper positions with new values"""
        # Enable motors before moving
        self._enable_all_motors()
        
        if horizontal is not None:
            self.horizontal_pos = max(-1, min(1, horizontal))
            if abs(self.horizontal_pos) > 0.1:  # Dead zone
                steps = self._map_to_steps(self.horizontal_pos)
                self._step_motor(STEPPER_H_STEP_PIN, STEPPER_H_DIR_PIN, 
                                self.horizontal_pos > 0, steps)
            
        if vertical is not None:
            self.vertical_pos = max(-1, min(1, vertical))
            if abs(self.vertical_pos) > 0.1:  # Dead zone
                steps = self._map_to_steps(self.vertical_pos)
                self._step_motor(STEPPER_V_STEP_PIN, STEPPER_V_DIR_PIN, 
                                self.vertical_pos > 0, steps)
            
        if focus is not None:
            self.focus_pos = max(-1, min(1, focus))
            if abs(self.focus_pos) > 0.1:  # Dead zone
                steps = self._map_to_steps(self.focus_pos)
                self._step_motor(STEPPER_F_STEP_PIN, STEPPER_F_DIR_PIN, 
                                self.focus_pos > 0, steps)
        
        # Disable motors when not moving
        if (abs(self.horizontal_pos) <= 0.1 and 
            abs(self.vertical_pos) <= 0.1 and 
            abs(self.focus_pos) <= 0.1):
            self._disable_all_motors()
    
    def cleanup(self):
        """Clean up GPIO"""
        self._disable_all_motors()
        GPIO.cleanup() 