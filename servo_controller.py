import pygame
import RPi.GPIO as GPIO
import time

# Set up the Raspberry Pi GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Define GPIO pins for the servos
SERVO_HORIZONTAL_PIN = 17  # Azimuth (Horizontal)
SERVO_VERTICAL_PIN = 18    # Elevation (Vertical)
SERVO_FOCUS_PIN = 27       # Focus

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

# Initialize pygame for controller input
pygame.init()

# Initialize the Xbox controller (index may vary)
pygame.joystick.init()
joystick = pygame.joystick.Joystick(0)
joystick.init()

# Function to map joystick values to PWM duty cycle
def map_to_pwm(value):
    # Map the joystick range (-1 to 1) to PWM range (0 to 100)
    return (value + 1) * 50  # PWM duty cycle is between 0 and 100

try:
    while True:
        pygame.event.pump()  # Process joystick events

        # Get analog stick values (joystick axes)
        horizontal_axis = joystick.get_axis(0)  # Left stick horizontal
        vertical_axis = joystick.get_axis(1)    # Left stick vertical
        focus_axis = joystick.get_axis(2)       # Right trigger for focus

        # Map the joystick values to PWM duty cycle
        horizontal_pwm = map_to_pwm(horizontal_axis)
        vertical_pwm = map_to_pwm(vertical_axis)
        focus_pwm = map_to_pwm(focus_axis)

        # Set the PWM duty cycles
        pwm_horizontal.ChangeDutyCycle(horizontal_pwm)
        pwm_vertical.ChangeDutyCycle(vertical_pwm)
        pwm_focus.ChangeDutyCycle(focus_pwm)

        # Delay to give time for PWM updates
        time.sleep(0.1)

except KeyboardInterrupt:
    pass

# Clean up on exit
pwm_horizontal.stop()
pwm_vertical.stop()
pwm_focus.stop()
GPIO.cleanup()
pygame.quit() 