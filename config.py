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

# GPIO pins for servos
SERVO_HORIZONTAL_PIN = int(os.environ.get('SERVO_HORIZONTAL_PIN', 17))  # Azimuth (Horizontal)
SERVO_VERTICAL_PIN = int(os.environ.get('SERVO_VERTICAL_PIN', 18))      # Elevation (Vertical)
SERVO_FOCUS_PIN = int(os.environ.get('SERVO_FOCUS_PIN', 27))            # Focus

# PWM Settings
PWM_FREQUENCY = 50  # Hz 