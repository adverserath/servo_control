import pygame
import RPi.GPIO as GPIO
import time

# Set up the Raspberry Pi GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Define GPIO pins for the stepper motors
# Horizontal Stepper (Azimuth)
H_STEP_PIN = 17    # Step pin
H_DIR_PIN = 27     # Direction pin
H_EN_PIN = 22      # Enable pin

# Vertical Stepper (Elevation)
V_STEP_PIN = 18    # Step pin
V_DIR_PIN = 23     # Direction pin
V_EN_PIN = 24      # Enable pin

# Focus Stepper
F_STEP_PIN = 25    # Step pin
F_DIR_PIN = 8      # Direction pin
F_EN_PIN = 7       # Enable pin

# Set up GPIO pins
for pin in [H_STEP_PIN, H_DIR_PIN, H_EN_PIN,
           V_STEP_PIN, V_DIR_PIN, V_EN_PIN,
           F_STEP_PIN, F_DIR_PIN, F_EN_PIN]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# Initialize pygame for controller input
pygame.init()
pygame.joystick.init()
joystick = pygame.joystick.Joystick(0)
joystick.init()

def step_motor(step_pin, dir_pin, direction, steps=1, delay=0.001):
    """Control a stepper motor with direction and number of steps"""
    GPIO.output(dir_pin, GPIO.HIGH if direction else GPIO.LOW)
    for _ in range(steps):
        GPIO.output(step_pin, GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(step_pin, GPIO.LOW)
        time.sleep(delay)

def map_to_steps(value, max_steps=10):
    """Map joystick value (-1 to 1) to number of steps"""
    return int(abs(value) * max_steps)

try:
    while True:
        pygame.event.pump()  # Process joystick events

        # Get analog stick values
        horizontal_axis = joystick.get_axis(0)  # Left stick horizontal
        vertical_axis = joystick.get_axis(1)    # Left stick vertical
        focus_axis = joystick.get_axis(2)       # Right trigger for focus

        # Enable all motors
        GPIO.output(H_EN_PIN, GPIO.LOW)
        GPIO.output(V_EN_PIN, GPIO.LOW)
        GPIO.output(F_EN_PIN, GPIO.LOW)

        # Control horizontal motor
        if abs(horizontal_axis) > 0.1:  # Dead zone
            steps = map_to_steps(horizontal_axis)
            step_motor(H_STEP_PIN, H_DIR_PIN, horizontal_axis > 0, steps)

        # Control vertical motor
        if abs(vertical_axis) > 0.1:  # Dead zone
            steps = map_to_steps(vertical_axis)
            step_motor(V_STEP_PIN, V_DIR_PIN, vertical_axis > 0, steps)

        # Control focus motor
        if abs(focus_axis) > 0.1:  # Dead zone
            steps = map_to_steps(focus_axis)
            step_motor(F_STEP_PIN, F_DIR_PIN, focus_axis > 0, steps)

        # Disable motors when not moving
        if abs(horizontal_axis) <= 0.1 and abs(vertical_axis) <= 0.1 and abs(focus_axis) <= 0.1:
            GPIO.output(H_EN_PIN, GPIO.HIGH)
            GPIO.output(V_EN_PIN, GPIO.HIGH)
            GPIO.output(F_EN_PIN, GPIO.HIGH)

        time.sleep(0.01)  # Small delay to prevent overwhelming the system

except KeyboardInterrupt:
    # Disable all motors on exit
    GPIO.output(H_EN_PIN, GPIO.HIGH)
    GPIO.output(V_EN_PIN, GPIO.HIGH)
    GPIO.output(F_EN_PIN, GPIO.HIGH)
    GPIO.cleanup()
    pygame.quit() 