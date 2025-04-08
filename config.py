import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Display settings
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
DISPLAY_CAPTION = "Servo Controller with RTSP Camera"
FRAME_RATE = 60

# RTSP Camera settings
RTSP_URL = os.environ.get('RTSP_URL', 'rtsp://admin:admin@192.168.1.100:554/stream1')

# Motor type selection (servo or stepper)
MOTOR_TYPE = os.environ.get('MOTOR_TYPE', 'servo')  # 'servo' or 'stepper'

# GPIO pins for servos
SERVO_HORIZONTAL_PIN = int(os.environ.get('SERVO_HORIZONTAL_PIN', 17))  # Azimuth (Horizontal)
SERVO_VERTICAL_PIN = int(os.environ.get('SERVO_VERTICAL_PIN', 18))      # Elevation (Vertical)
SERVO_FOCUS_PIN = int(os.environ.get('SERVO_FOCUS_PIN', 27))            # Focus

# GPIO pins for stepper motors
STEPPER_H_STEP_PIN = int(os.environ.get('STEPPER_H_STEP_PIN', 17))    # Step pin
STEPPER_H_DIR_PIN = int(os.environ.get('STEPPER_H_DIR_PIN', 27))      # Direction pin
STEPPER_H_EN_PIN = int(os.environ.get('STEPPER_H_EN_PIN', 22))        # Enable pin

STEPPER_V_STEP_PIN = int(os.environ.get('STEPPER_V_STEP_PIN', 18))    # Step pin
STEPPER_V_DIR_PIN = int(os.environ.get('STEPPER_V_DIR_PIN', 23))      # Direction pin
STEPPER_V_EN_PIN = int(os.environ.get('STEPPER_V_EN_PIN', 24))        # Enable pin

STEPPER_F_STEP_PIN = int(os.environ.get('STEPPER_F_STEP_PIN', 25))    # Step pin
STEPPER_F_DIR_PIN = int(os.environ.get('STEPPER_F_DIR_PIN', 8))       # Direction pin
STEPPER_F_EN_PIN = int(os.environ.get('STEPPER_F_EN_PIN', 7))         # Enable pin

# PWM Settings
PWM_FREQUENCY = 50  # Hz

# Stepper motor settings
STEPPER_DELAY = float(os.environ.get('STEPPER_DELAY', 0.001))  # Delay between steps in seconds 