import RPi.GPIO as GPIO
import time
import threading
from config import (
    MOTOR_MODE,
    SERVO_HORIZONTAL_PIN, SERVO_VERTICAL_PIN, SERVO_FOCUS_PIN, PWM_FREQ,
    STEPPER_ENABLE_PIN, STEPPER_DIR_PIN, STEPPER_STEP_PIN,
    STEPPER_MICROSTEPS, STEPPER_STEPS_PER_REV
)

class BaseMotorController:
    def __init__(self):
        self.lock = threading.Lock()
        self.horizontal_pos = 0
        self.vertical_pos = 0
        self.focus_pos = 0
        self.connected = False
        self.error = None

    def update_position(self, axis, value):
        """Update position for specified axis (-1 to 1)"""
        with self.lock:
            if axis == 'horizontal':
                self.horizontal_pos = max(-1, min(1, value))
            elif axis == 'vertical':
                self.vertical_pos = max(-1, min(1, value))
            elif axis == 'focus':
                self.focus_pos = max(-1, min(1, value))
            else:
                raise ValueError(f"Invalid axis: {axis}")

    def get_status(self):
        """Get current status of the controller"""
        with self.lock:
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
        """Clean up resources"""
        pass

class ServoController(BaseMotorController):
    def __init__(self):
        super().__init__()
        # Set up GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Set up PWM for each servo
        GPIO.setup(SERVO_HORIZONTAL_PIN, GPIO.OUT)
        GPIO.setup(SERVO_VERTICAL_PIN, GPIO.OUT)
        GPIO.setup(SERVO_FOCUS_PIN, GPIO.OUT)

        self.pwm_horizontal = GPIO.PWM(SERVO_HORIZONTAL_PIN, PWM_FREQ)
        self.pwm_vertical = GPIO.PWM(SERVO_VERTICAL_PIN, PWM_FREQ)
        self.pwm_focus = GPIO.PWM(SERVO_FOCUS_PIN, PWM_FREQ)

        self.pwm_horizontal.start(0)
        self.pwm_vertical.start(0)
        self.pwm_focus.start(0)

        self.connected = True

    def update_position(self, axis, value):
        """Update servo position (-1 to 1)"""
        super().update_position(axis, value)
        
        # Convert -1 to 1 range to PWM duty cycle (0 to 100)
        duty_cycle = (value + 1) * 50

        with self.lock:
            if axis == 'horizontal':
                self.pwm_horizontal.ChangeDutyCycle(duty_cycle)
            elif axis == 'vertical':
                self.pwm_vertical.ChangeDutyCycle(duty_cycle)
            elif axis == 'focus':
                self.pwm_focus.ChangeDutyCycle(duty_cycle)

    def cleanup(self):
        """Stop PWM and clean up GPIO"""
        self.pwm_horizontal.stop()
        self.pwm_vertical.stop()
        self.pwm_focus.stop()
        GPIO.cleanup()

class StepperController(BaseMotorController):
    def __init__(self):
        super().__init__()
        # Set up GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Set up stepper pins
        GPIO.setup(STEPPER_ENABLE_PIN, GPIO.OUT)
        GPIO.setup(STEPPER_DIR_PIN, GPIO.OUT)
        GPIO.setup(STEPPER_STEP_PIN, GPIO.OUT)

        # Initialize pins
        GPIO.output(STEPPER_ENABLE_PIN, GPIO.LOW)  # Enable stepper
        GPIO.output(STEPPER_DIR_PIN, GPIO.LOW)
        GPIO.output(STEPPER_STEP_PIN, GPIO.LOW)

        self.connected = True
        self.step_delay = 0.001  # 1ms delay between steps
        self.current_position = 0  # Current position in steps

    def update_position(self, axis, value):
        """Update stepper position (-1 to 1)"""
        super().update_position(axis, value)
        
        # Calculate target position in steps
        target_steps = int(value * STEPPER_STEPS_PER_REV / 2)
        steps_to_move = target_steps - self.current_position

        if steps_to_move != 0:
            # Set direction
            GPIO.output(STEPPER_DIR_PIN, GPIO.HIGH if steps_to_move > 0 else GPIO.LOW)
            
            # Move steps
            for _ in range(abs(steps_to_move)):
                GPIO.output(STEPPER_STEP_PIN, GPIO.HIGH)
                time.sleep(self.step_delay)
                GPIO.output(STEPPER_STEP_PIN, GPIO.LOW)
                time.sleep(self.step_delay)
            
            self.current_position = target_steps

    def cleanup(self):
        """Disable stepper and clean up GPIO"""
        GPIO.output(STEPPER_ENABLE_PIN, GPIO.HIGH)  # Disable stepper
        GPIO.cleanup()

def create_motor_controller():
    """Factory function to create the appropriate motor controller"""
    if MOTOR_MODE == 'servo':
        return ServoController()
    elif MOTOR_MODE == 'stepper':
        return StepperController()
    else:
        raise ValueError(f"Invalid motor mode: {MOTOR_MODE}") 