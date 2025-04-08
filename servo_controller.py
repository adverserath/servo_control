import pygame
import RPi.GPIO as GPIO
import time
import cv2
import numpy as np
import threading
import sys
import os
from config import HORIZONTAL_PIN, VERTICAL_PIN, FOCUS_PIN, PWM_FREQ

# Set up the Raspberry Pi GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Define GPIO pins for the servos
SERVO_HORIZONTAL_PIN = HORIZONTAL_PIN
SERVO_VERTICAL_PIN = VERTICAL_PIN
SERVO_FOCUS_PIN = FOCUS_PIN

# Set up PWM for each servo
GPIO.setup(SERVO_HORIZONTAL_PIN, GPIO.OUT)
GPIO.setup(SERVO_VERTICAL_PIN, GPIO.OUT)
GPIO.setup(SERVO_FOCUS_PIN, GPIO.OUT)

pwm_horizontal = GPIO.PWM(SERVO_HORIZONTAL_PIN, PWM_FREQ)
pwm_vertical = GPIO.PWM(SERVO_VERTICAL_PIN, PWM_FREQ)
pwm_focus = GPIO.PWM(SERVO_FOCUS_PIN, PWM_FREQ)

pwm_horizontal.start(0)
pwm_vertical.start(0)
pwm_focus.start(0)

# Initialize pygame for controller input and display
pygame.init()

# Set up display for camera feed
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Servo Controller with Pi Camera")

# Font for displaying information
font = pygame.font.Font(None, 36)

# Camera Configuration
camera_connected = False
frame = None
frame_lock = threading.Lock()

# Initialize the Xbox controller (index may vary)
try:
    pygame.joystick.init()
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    joystick_connected = True
    print("Controller connected:", joystick.get_name())
except:
    joystick_connected = False
    print("No controller detected. Using keyboard controls.")

# Function to map joystick values to PWM duty cycle
def map_to_pwm(value):
    # Map the joystick range (-1 to 1) to PWM range (0 to 100)
    return (value + 1) * 50  # PWM duty cycle is between 0 and 100

# Function to capture frames from the Pi camera
def camera_stream_thread():
    global frame, camera_connected
    
    try:
        # Initialize Pi camera
        import picamera
        import picamera.array
        
        with picamera.PiCamera() as camera:
            camera.resolution = (SCREEN_WIDTH, SCREEN_HEIGHT)
            camera.framerate = 30
            
            # Create a numpy array to store the frame
            output = picamera.array.PiRGBArray(camera, size=(SCREEN_WIDTH, SCREEN_HEIGHT))
            
            camera_connected = True
            print("Pi camera connected")
            
            for frame_array in camera.capture_continuous(output, format='rgb', use_video_port=True):
                with frame_lock:
                    frame = frame_array.array
                output.truncate(0)
                time.sleep(0.033)  # ~30fps
                
    except Exception as e:
        print(f"Camera Error: {e}")
        camera_connected = False
        time.sleep(5)  # Wait before retrying

# Start the camera capture in a separate thread
camera_thread = threading.Thread(target=camera_stream_thread, daemon=True)
camera_thread.start()

# Create a clock to control the frame rate
clock = pygame.time.Clock()

class ServoController:
    def __init__(self):
        # Initialize GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup PWM pins
        GPIO.setup(SERVO_HORIZONTAL_PIN, GPIO.OUT)
        GPIO.setup(SERVO_VERTICAL_PIN, GPIO.OUT)
        GPIO.setup(SERVO_FOCUS_PIN, GPIO.OUT)
        
        # Create PWM objects
        self.horizontal_pwm = GPIO.PWM(SERVO_HORIZONTAL_PIN, PWM_FREQ)
        self.vertical_pwm = GPIO.PWM(SERVO_VERTICAL_PIN, PWM_FREQ)
        self.focus_pwm = GPIO.PWM(SERVO_FOCUS_PIN, PWM_FREQ)
        
        # Start PWM
        self.horizontal_pwm.start(0)
        self.vertical_pwm.start(0)
        self.focus_pwm.start(0)
        
        # Current positions (-1 to 1)
        self.horizontal_pos = 0
        self.vertical_pos = 0
        self.focus_pos = 0
        
        # Error tracking
        self.error = None
        self.connected = True
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
        print("Servo controller initialized")
    
    def update_position(self, horizontal=None, vertical=None, focus=None):
        """Update servo positions. Values should be between -1 and 1."""
        with self.lock:
            try:
                # Update positions
                if horizontal is not None:
                    self.horizontal_pos = max(-1, min(1, horizontal))
                    self._set_servo(self.horizontal_pwm, self.horizontal_pos)
                
                if vertical is not None:
                    self.vertical_pos = max(-1, min(1, vertical))
                    self._set_servo(self.vertical_pwm, self.vertical_pos)
                
                if focus is not None:
                    self.focus_pos = max(-1, min(1, focus))
                    self._set_servo(self.focus_pwm, self.focus_pos)
                
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
            self.horizontal_pwm.stop()
            self.vertical_pwm.stop()
            self.focus_pwm.stop()
            GPIO.cleanup()
            print("Servo controller cleaned up")
        except Exception as e:
            print(f"Error cleaning up servo controller: {e}")

try:
    running = True
    
    horizontal_value = 0
    vertical_value = 0
    focus_value = 0
    
    while running:
        # Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # Keyboard controls as fallback
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    horizontal_value = max(-1, horizontal_value - 0.1)
                elif event.key == pygame.K_RIGHT:
                    horizontal_value = min(1, horizontal_value + 0.1)
                elif event.key == pygame.K_UP:
                    vertical_value = max(-1, vertical_value - 0.1)
                elif event.key == pygame.K_DOWN:
                    vertical_value = min(1, vertical_value + 0.1)
                elif event.key == pygame.K_a:
                    focus_value = max(-1, focus_value - 0.1)
                elif event.key == pygame.K_d:
                    focus_value = min(1, focus_value + 0.1)
        
        # If joystick is connected, get values from it
        if joystick_connected:
            pygame.event.pump()  # Process joystick events
            
            # Get analog stick values
            horizontal_value = joystick.get_axis(0)  # Left stick horizontal
            vertical_value = joystick.get_axis(1)    # Left stick vertical
            
            # Use both triggers for focus control
            left_trigger = joystick.get_axis(2)      # Left trigger (typically axis 2)
            right_trigger = joystick.get_axis(5)     # Right trigger (typically axis 5)
            
            # Combine triggers for bidirectional focus
            # Left trigger focuses out, right trigger focuses in
            focus_value = right_trigger - left_trigger
            # Normalize to -1 to 1 range
            focus_value = max(-1, min(1, focus_value))
        
        # Map the values to PWM duty cycle
        horizontal_pwm = map_to_pwm(horizontal_value)
        vertical_pwm = map_to_pwm(vertical_value)
        focus_pwm = map_to_pwm(focus_value)
        
        # Set the PWM duty cycles
        pwm_horizontal.ChangeDutyCycle(horizontal_pwm)
        pwm_vertical.ChangeDutyCycle(vertical_pwm)
        pwm_focus.ChangeDutyCycle(focus_pwm)
        
        # Clear the screen
        screen.fill((0, 0, 0))
        
        # Render the camera feed if available
        with frame_lock:
            if frame is not None:
                # Convert numpy array to pygame surface
                camera_surface = pygame.surfarray.make_surface(frame)
                screen.blit(camera_surface, (0, 0))
        
        # Render status text
        status_text = []
        status_text.append(f"RTSP: {'Connected' if camera_connected else 'Disconnected'}")
        status_text.append(f"Controls: {'Joystick' if joystick_connected else 'Keyboard'}")
        status_text.append(f"Horizontal: {horizontal_value:.2f}")
        status_text.append(f"Vertical: {vertical_value:.2f}")
        status_text.append(f"Focus: {focus_value:.2f}")
        
        for i, text in enumerate(status_text):
            text_surface = font.render(text, True, (255, 255, 255))
            screen.blit(text_surface, (10, 10 + i * 30))
        
        # Update the display
        pygame.display.flip()
        
        # Limit to 60 FPS
        clock.tick(60)

except KeyboardInterrupt:
    print("Program interrupted by user")
except Exception as e:
    print(f"Error: {e}")
finally:
    # Clean up on exit
    pwm_horizontal.stop()
    pwm_vertical.stop()
    pwm_focus.stop()
    GPIO.cleanup()
    pygame.quit()
    print("Program terminated") 