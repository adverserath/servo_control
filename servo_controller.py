import pygame
import RPi.GPIO as GPIO
import time
# import cv2 # No longer needed here if camera is managed elsewhere
# import numpy as np # No longer needed here
import threading
import sys
import os
import logging
from config import HORIZONTAL_PIN, VERTICAL_PIN, FOCUS_PIN, PWM_FREQ

# Configure logging
logger = logging.getLogger(__name__)

# Handle XDG_RUNTIME_DIR issue on Raspberry Pi OS
if not os.environ.get('XDG_RUNTIME_DIR'):
    # Create runtime directory in user's home directory
    home_dir = os.path.expanduser('~')
    runtime_dir = os.path.join(home_dir, '.runtime')
    os.makedirs(runtime_dir, exist_ok=True)
    os.environ['XDG_RUNTIME_DIR'] = runtime_dir

class ServoController:
    def __init__(self):
        # Set up the Raspberry Pi GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Set up PWM for each servo
        GPIO.setup(HORIZONTAL_PIN, GPIO.OUT)
        GPIO.setup(VERTICAL_PIN, GPIO.OUT)
        GPIO.setup(FOCUS_PIN, GPIO.OUT)

        self.pwm_horizontal = GPIO.PWM(HORIZONTAL_PIN, PWM_FREQ)
        self.pwm_vertical = GPIO.PWM(VERTICAL_PIN, PWM_FREQ)
        self.pwm_focus = GPIO.PWM(FOCUS_PIN, PWM_FREQ)

        self.pwm_horizontal.start(0)
        self.pwm_vertical.start(0)
        self.pwm_focus.start(0)

        # Current positions
        self.horizontal_pos = 0
        self.vertical_pos = 0
        self.focus_pos = 0

        # Thread safety
        self.lock = threading.Lock()
        
        # Error tracking
        self.error = None
        self.is_connected = True
        
        logger.info("ServoController initialized")
    
    def update_position(self, horizontal=None, vertical=None, focus=None):
        """Update servo positions with thread safety"""
        try:
            with self.lock:
                if horizontal is not None:
                    self.horizontal_pos = horizontal
                    self.pwm_horizontal.ChangeDutyCycle(self._map_to_pwm(horizontal))
                
                if vertical is not None:
                    self.vertical_pos = vertical
                    self.pwm_vertical.ChangeDutyCycle(self._map_to_pwm(vertical))
                
                if focus is not None:
                    self.focus_pos = focus
                    self.pwm_focus.ChangeDutyCycle(self._map_to_pwm(focus))
                
                self.error = None
                return True
        except Exception as e:
            self.error = str(e)
            logger.error(f"Error updating servo position: {e}")
            return False
    
    def _map_to_pwm(self, value):
        """Map joystick values (-1 to 1) to PWM duty cycle (0 to 100)"""
        # Apply deadzone
        if abs(value) < 0.1:  # 10% deadzone
            return 0
        
        # Map the joystick range (-1 to 1) to PWM range (0 to 100)
        return (value + 1) * 50  # PWM duty cycle is between 0 and 100
    
    def get_status(self):
        """Get the current status of the servo controller"""
        with self.lock:
            return {
                'connected': self.is_connected,
                'error': self.error,
                'horizontal_pos': self.horizontal_pos,
                'vertical_pos': self.vertical_pos,
                'focus_pos': self.focus_pos
            }
    
    def cleanup(self):
        """Clean up GPIO resources"""
        try:
            logger.info("Cleaning up ServoController...")
            self.pwm_horizontal.stop()
            self.pwm_vertical.stop()
            self.pwm_focus.stop()
            GPIO.cleanup()
            logger.info("ServoController cleaned up")
        except Exception as e:
            logger.error(f"Error during ServoController cleanup: {e}")

# Function to map joystick values to PWM duty cycle
# This function seems specific to the old structure, ServoManager has its own mapping
# def map_to_pwm(value):
#     # Map the joystick range (-1 to 1) to PWM range (0 to 100)
#     return (value + 1) * 50  # PWM duty cycle is between 0 and 100

# Note: This file might become redundant if ServoManager handles everything.
# Consider if this file is still needed at all, or if its remaining 
# GPIO setup logic belongs in ServoManager's __init__. 