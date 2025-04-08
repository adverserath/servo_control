import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Mode Configuration
MOTOR_MODE = os.environ.get('MOTOR_MODE', 'servo').lower()
if MOTOR_MODE not in ['servo', 'stepper']:
    raise ValueError("MOTOR_MODE must be either 'servo' or 'stepper'")

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# GPIO pins for servos
HORIZONTAL_PIN = int(os.environ.get('SERVO_HORIZONTAL_PIN', 17))
VERTICAL_PIN = int(os.environ.get('SERVO_VERTICAL_PIN', 18))
FOCUS_PIN = int(os.environ.get('SERVO_FOCUS_PIN', 27))

# PWM frequency for servos
PWM_FREQ = 50  # Standard 50Hz for servos

# Stepper Motor Configuration
STEPPER_ENABLE_PIN = int(os.environ.get('STEPPER_ENABLE_PIN', 22))
STEPPER_DIR_PIN = int(os.environ.get('STEPPER_DIR_PIN', 23))
STEPPER_STEP_PIN = int(os.environ.get('STEPPER_STEP_PIN', 24))
STEPPER_MICROSTEPS = int(os.environ.get('STEPPER_MICROSTEPS', 16))
STEPPER_STEPS_PER_REV = int(os.environ.get('STEPPER_STEPS_PER_REV', 200))

# Display settings
DISPLAY_CAPTION = f"Motor Controller ({MOTOR_MODE.capitalize()} Mode)"
FRAME_RATE = 60 