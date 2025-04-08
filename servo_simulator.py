import pygame
import time
import cv2
import numpy as np
import threading
import sys
import os

# Mock GPIO module for local testing
class MockGPIO:
    BCM = 1
    OUT = 1
    
    @staticmethod
    def setmode(mode):
        print(f"GPIO.setmode({mode})")
    
    @staticmethod
    def setwarnings(flag):
        print(f"GPIO.setwarnings({flag})")
    
    @staticmethod
    def setup(pin, mode):
        print(f"GPIO.setup(pin={pin}, mode={mode})")
    
    @staticmethod
    def cleanup():
        print("GPIO.cleanup()")
    
    class PWM:
        def __init__(self, pin, freq):
            self.pin = pin
            self.freq = freq
            self.duty_cycle = 0
            print(f"PWM initialized on pin {pin} with frequency {freq}Hz")
        
        def start(self, duty_cycle):
            self.duty_cycle = duty_cycle
            print(f"PWM started on pin {self.pin} with duty cycle {duty_cycle}%")
        
        def ChangeDutyCycle(self, duty_cycle):
            self.duty_cycle = duty_cycle
            # Don't print this to avoid console spam
        
        def stop(self):
            print(f"PWM stopped on pin {self.pin}")

# Replace GPIO with our mock for local testing
GPIO = MockGPIO

# Define GPIO pins for the servos
SERVO_HORIZONTAL_PIN = 17  # Azimuth (Horizontal)
SERVO_VERTICAL_PIN = 18    # Elevation (Vertical)
SERVO_FOCUS_PIN = 27       # Focus

# Set up the Raspberry Pi GPIO (mocked)
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Set up PWM for each servo
GPIO.setup(SERVO_HORIZONTAL_PIN, GPIO.OUT)
GPIO.setup(SERVO_VERTICAL_PIN, GPIO.OUT)
GPIO.setup(SERVO_FOCUS_PIN, GPIO.OUT)

pwm_horizontal = GPIO.PWM(SERVO_HORIZONTAL_PIN, 50)
pwm_vertical = GPIO.PWM(SERVO_VERTICAL_PIN, 50)
pwm_focus = GPIO.PWM(SERVO_FOCUS_PIN, 50)

pwm_horizontal.start(0)
pwm_vertical.start(0)
pwm_focus.start(0)

# Initialize pygame for controller input and display
pygame.init()

# Set up display for camera feed
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Servo Controller Simulator")

# Font for displaying information
font = pygame.font.Font(None, 36)

# Camera Configuration
USE_WEBCAM = True  # Try to use local webcam
SIMULATE_CAMERA = True  # Generate a simulated view if webcam fails
camera_connected = False
frame = None
frame_lock = threading.Lock()

# Simulated servo positions (for visual feedback)
servo_h_pos = 0.5  # 0 to 1 range (center = 0.5)
servo_v_pos = 0.5  # 0 to 1 range (center = 0.5)
focus_level = 0.5  # 0 to 1 range (focused = 0.5)

# Initialize the controller (index may vary)
try:
    pygame.joystick.init()
    if pygame.joystick.get_count() > 0:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        joystick_connected = True
        print("Controller connected:", joystick.get_name())
    else:
        joystick_connected = False
        print("No controller detected. Using keyboard controls.")
except:
    joystick_connected = False
    print("No controller detected. Using keyboard controls.")

# Function to map joystick values to PWM duty cycle
def map_to_pwm(value):
    # Map the joystick range (-1 to 1) to PWM range (0 to 100)
    return (value + 1) * 50  # PWM duty cycle is between 0 and 100

# Function to map joystick values to servo position for visualization
def map_to_servo_pos(value):
    # Map the joystick range (-1 to 1) to position range (0 to 1)
    return (value + 1) * 0.5

# Function to capture frames from the webcam or generate simulated views
def camera_thread():
    global frame, camera_connected, servo_h_pos, servo_v_pos, focus_level
    
    # Try to connect to webcam if enabled
    if USE_WEBCAM:
        try:
            cap = cv2.VideoCapture(0)  # Use default camera (usually webcam)
            if cap.isOpened():
                camera_connected = True
                print("Webcam connected")
                
                while camera_connected:
                    ret, new_frame = cap.read()
                    if not ret:
                        print("Failed to get webcam frame")
                        break
                    
                    with frame_lock:
                        # Convert to RGB for Pygame
                        frame = cv2.cvtColor(new_frame, cv2.COLOR_BGR2RGB)
                        frame = cv2.resize(frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
                    
                    time.sleep(0.033)  # ~30fps
                
                cap.release()
        except Exception as e:
            print(f"Webcam Error: {e}")
            camera_connected = False
    
    # Use simulated view if webcam fails or is disabled
    if not camera_connected and SIMULATE_CAMERA:
        print("Using simulated camera view")
        camera_connected = True
        
        # Create a "camera view" with a grid and crosshair
        while True:
            # Create a blank frame
            new_frame = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)
            
            # Add a grid
            for x in range(0, SCREEN_WIDTH, 50):
                cv2.line(new_frame, (x, 0), (x, SCREEN_HEIGHT), (30, 30, 30), 1)
            for y in range(0, SCREEN_HEIGHT, 50):
                cv2.line(new_frame, (0, y), (SCREEN_WIDTH, y), (30, 30, 30), 1)
            
            # Add a horizon line
            horizon_y = int(SCREEN_HEIGHT * servo_v_pos)
            cv2.line(new_frame, (0, horizon_y), (SCREEN_WIDTH, horizon_y), (0, 100, 0), 2)
            
            # Add a vertical line for horizontal servo position
            vertical_x = int(SCREEN_WIDTH * servo_h_pos)
            cv2.line(new_frame, (vertical_x, 0), (vertical_x, SCREEN_HEIGHT), (100, 0, 0), 2)
            
            # Draw a rectangle to represent the camera view boundaries
            cv2.rectangle(new_frame, (100, 100), (SCREEN_WIDTH-100, SCREEN_HEIGHT-100), (50, 50, 100), 2)
            
            # Add crosshair in center
            center_x = int(SCREEN_WIDTH * servo_h_pos)
            center_y = int(SCREEN_HEIGHT * servo_v_pos)
            cv2.line(new_frame, (center_x-20, center_y), (center_x+20, center_y), (200, 200, 0), 2)
            cv2.line(new_frame, (center_x, center_y-20), (center_x, center_y+20), (200, 200, 0), 2)
            
            # Apply "blur" based on focus
            blur_amount = int(abs(focus_level - 0.5) * 20) + 1
            if blur_amount > 1:
                new_frame = cv2.GaussianBlur(new_frame, (blur_amount*2+1, blur_amount*2+1), 0)
            
            with frame_lock:
                frame = new_frame
            
            time.sleep(0.033)  # ~30fps

# Start the camera thread
cam_thread = threading.Thread(target=camera_thread, daemon=True)
cam_thread.start()

# Create a clock to control the frame rate
clock = pygame.time.Clock()

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
                elif event.key == pygame.K_ESCAPE:
                    running = False
        
        # If joystick is connected, get values from it
        if joystick_connected:
            pygame.event.pump()  # Process joystick events
            
            # Get analog stick values
            horizontal_value = joystick.get_axis(0)  # Left stick horizontal
            vertical_value = joystick.get_axis(1)    # Left stick vertical
            
            # Use both triggers for bidirectional focus
            try:
                left_trigger = joystick.get_axis(2)      # Left trigger (typically axis 2)
                right_trigger = joystick.get_axis(5)     # Right trigger (typically axis 5)
                
                # Combine triggers for bidirectional focus
                # Left trigger focuses out, right trigger focuses in
                focus_value = right_trigger - left_trigger
            except:
                # Fallback if trigger mapping is different
                focus_value = joystick.get_axis(2)
            
            # Normalize to -1 to 1 range
            focus_value = max(-1, min(1, focus_value))
        
        # Update simulated servo positions for visualization
        servo_h_pos = map_to_servo_pos(horizontal_value)
        servo_v_pos = map_to_servo_pos(vertical_value)
        focus_level = map_to_servo_pos(focus_value)
        
        # Map the values to PWM duty cycle
        horizontal_pwm = map_to_pwm(horizontal_value)
        vertical_pwm = map_to_pwm(vertical_value)
        focus_pwm = map_to_pwm(focus_value)
        
        # Set the PWM duty cycles (mocked)
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
        status_text.append(f"Camera: {'Connected' if camera_connected else 'Disconnected'}")
        status_text.append(f"Controls: {'Joystick' if joystick_connected else 'Keyboard'}")
        status_text.append(f"Horizontal: {horizontal_value:.2f}")
        status_text.append(f"Vertical: {vertical_value:.2f}")
        status_text.append(f"Focus: {focus_value:.2f}")
        
        # Add help text
        help_text = ["[Use Arrow Keys for pan/tilt, A/D for focus]", 
                    "[Press ESC to exit]"]
        
        # Render status text with black outline for better visibility
        for i, text in enumerate(status_text):
            text_surface = font.render(text, True, (255, 255, 255))
            screen.blit(text_surface, (10, 10 + i * 30))
        
        # Render help text at bottom
        for i, text in enumerate(help_text):
            text_surface = font.render(text, True, (180, 180, 180))
            screen.blit(text_surface, (10, SCREEN_HEIGHT - 40 + i * 20))
        
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