import pygame
import time
import cv2
import numpy as np
import threading
import sys
import os
from config import SCREEN_WIDTH, SCREEN_HEIGHT, DISPLAY_CAPTION, FRAME_RATE
from motor_controller import create_motor_controller

# Initialize pygame for controller input and display
pygame.init()

# Set up display for camera feed
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption(DISPLAY_CAPTION)

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

# Create motor controller based on configuration
motor_controller = create_motor_controller()

# Function to capture frames from the camera
def camera_stream_thread():
    global frame, camera_connected
    
    try:
        # Initialize camera
        cap = cv2.VideoCapture(0)  # Use default camera
        if not cap.isOpened():
            print("Cannot open camera")
            return
            
        camera_connected = True
        print("Camera connected")
        
        while True:
            ret, new_frame = cap.read()
            if not ret:
                print("Failed to get frame")
                break
                
            with frame_lock:
                # Convert to RGB for Pygame
                frame = cv2.cvtColor(new_frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
            
            time.sleep(0.033)  # ~30fps
                
    except Exception as e:
        print(f"Camera Error: {e}")
        camera_connected = False
        time.sleep(5)  # Wait before retrying

# Start the camera capture in a separate thread
camera_thread = threading.Thread(target=camera_stream_thread, daemon=True)
camera_thread.start()

# Main loop
running = True
clock = pygame.time.Clock()

while running:
    # Process events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # Keyboard controls
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                motor_controller.update_position('horizontal', max(-1, motor_controller.horizontal_pos - 0.1))
            elif event.key == pygame.K_RIGHT:
                motor_controller.update_position('horizontal', min(1, motor_controller.horizontal_pos + 0.1))
            elif event.key == pygame.K_UP:
                motor_controller.update_position('vertical', max(-1, motor_controller.vertical_pos - 0.1))
            elif event.key == pygame.K_DOWN:
                motor_controller.update_position('vertical', min(1, motor_controller.vertical_pos + 0.1))
            elif event.key == pygame.K_a:
                motor_controller.update_position('focus', max(-1, motor_controller.focus_pos - 0.1))
            elif event.key == pygame.K_d:
                motor_controller.update_position('focus', min(1, motor_controller.focus_pos + 0.1))
    
    # If joystick is connected, get values from it
    if joystick_connected:
        pygame.event.pump()  # Process joystick events
        
        # Get analog stick values
        horizontal = joystick.get_axis(0)  # Left stick horizontal
        vertical = joystick.get_axis(1)    # Left stick vertical
        
        # Use both triggers for bidirectional focus
        left_trigger = joystick.get_axis(2)    # Left trigger
        right_trigger = joystick.get_axis(5)   # Right trigger
        
        # Combine triggers: right focuses in, left focuses out
        focus = right_trigger - left_trigger
        focus = max(-1, min(1, focus))  # Clamp to -1,1
        
        # Update motor positions
        motor_controller.update_position('horizontal', horizontal)
        motor_controller.update_position('vertical', -vertical)  # Invert Y axis
        motor_controller.update_position('focus', focus)
    
    # Draw camera feed if available
    if frame is not None:
        # Convert frame to pygame surface
        frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        screen.blit(frame_surface, (0, 0))
    
    # Draw status information
    status = motor_controller.get_status()
    status_text = f"Mode: {status['connected'] and 'Connected' or 'Disconnected'}"
    if status['error']:
        status_text += f" Error: {status['error']}"
    
    text_surface = font.render(status_text, True, (255, 255, 255))
    screen.blit(text_surface, (10, 10))
    
    # Update display
    pygame.display.flip()
    clock.tick(FRAME_RATE)

# Cleanup
motor_controller.cleanup()
pygame.quit()
sys.exit() 