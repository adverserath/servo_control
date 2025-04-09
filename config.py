import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# RTSP camera settings
RTSP_URL = os.getenv('RTSP_URL', 'rtsp://admin:admin@192.168.0.236:554/stream1')

# GPIO pins for servos
HORIZONTAL_PIN = int(os.environ.get('SERVO_HORIZONTAL_PIN', 17))
VERTICAL_PIN = int(os.environ.get('SERVO_VERTICAL_PIN', 18))
FOCUS_PIN = int(os.environ.get('SERVO_FOCUS_PIN', 27))

# PWM frequency for servos
PWM_FREQ = 50  # Standard 50Hz for servos

# Joystick settings
JOYSTICK_DEADZONE = 0.1  # 10% deadzone to prevent servo jitter

# Display settings
DISPLAY_CAPTION = "Servo Controller with Camera"
FRAME_RATE = 60 