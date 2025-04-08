import RPi.GPIO as GPIO
import time
from config import (
    HORIZONTAL_PIN, 
    VERTICAL_PIN, 
    FOCUS_PIN,
    PWM_FREQ
)

class ServoManager:
    def __init__(self):
        # Set up the Raspberry Pi GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Initialize servo positions
        self.horizontal_pos = 0
        self.vertical_pos = 0
        self.focus_pos = 0
        
        # MG996R Power Pro specific settings
        # NOTE: Ensure servos have a STABLE and SUFFICIENT power supply (e.g., 5V, >1A per servo),
        # separate from the Raspberry Pi's logic power.
        # NOTE: This pulse range (500-2400us) is typical for MG996R, but may need
        # fine-tuning (+/- 100us) for your specific servos if jitter persists.
        self.min_pulse = 500  # microseconds
        self.max_pulse = 2400  # microseconds
        self.center_pulse = 1500  # microseconds
        
        # Set up pins and PWM
        self._setup_pins()
        self._setup_pwm()
        
        # Error tracking
        self.error = None
        self.connected = True
        
        # Debug flag
        self.debug = True
    
    def _setup_pins(self):
        """Set up GPIO pins for servos"""
        GPIO.setup(HORIZONTAL_PIN, GPIO.OUT)
        GPIO.setup(VERTICAL_PIN, GPIO.OUT)
        GPIO.setup(FOCUS_PIN, GPIO.OUT)
    
    def _setup_pwm(self):
        """Set up PWM for servos"""
        self.horizontal_pwm = GPIO.PWM(HORIZONTAL_PIN, PWM_FREQ)
        self.vertical_pwm = GPIO.PWM(VERTICAL_PIN, PWM_FREQ)
        self.focus_pwm = GPIO.PWM(FOCUS_PIN, PWM_FREQ)
        
        # Start PWM with center position
        self.horizontal_pwm.start(self._pulse_to_duty(self.center_pulse))
        self.vertical_pwm.start(self._pulse_to_duty(self.center_pulse))
        self.focus_pwm.start(self._pulse_to_duty(self.center_pulse))
        
        # Give servos time to reach center position
        time.sleep(1)
    
    def update_position(self, horizontal=None, vertical=None, focus=None):
        """Update servo positions"""
        try:
            duty_changed = False
            if horizontal is not None:
                new_pos = max(-1, min(1, horizontal))
                # Only update if the position changed significantly (optional threshold)
                # if abs(new_pos - self.horizontal_pos) > 0.01:
                self.horizontal_pos = new_pos
                duty = self._value_to_duty(self.horizontal_pos)
                self.horizontal_pwm.ChangeDutyCycle(duty)
                duty_changed = True
                if self.debug:
                    print(f"Horizontal: {self.horizontal_pos:.2f} -> Duty: {duty:.2f}%")
            
            if vertical is not None:
                new_pos = max(-1, min(1, vertical))
                # if abs(new_pos - self.vertical_pos) > 0.01:
                self.vertical_pos = new_pos
                duty = self._value_to_duty(self.vertical_pos)
                self.vertical_pwm.ChangeDutyCycle(duty)
                duty_changed = True
                if self.debug:
                    print(f"Vertical: {self.vertical_pos:.2f} -> Duty: {duty:.2f}%")
            
            if focus is not None:
                new_pos = max(-1, min(1, focus))
                # if abs(new_pos - self.focus_pos) > 0.01:
                self.focus_pos = new_pos
                duty = self._value_to_duty(self.focus_pos)
                self.focus_pwm.ChangeDutyCycle(duty)
                duty_changed = True
                if self.debug:
                    print(f"Focus: {self.focus_pos:.2f} -> Duty: {duty:.2f}%")
            
            # If any duty cycle was changed, give a tiny pause for stability
            if duty_changed:
                time.sleep(0.005) # Small delay after changing duty cycle
                
            self.error = None
            self.connected = True
            
        except Exception as e:
            self.error = str(e)
            self.connected = False
            print(f"Error updating servo position: {e}")
    
    def _value_to_duty(self, value):
        """Map from -1,1 range to PWM duty cycle (0-100) with proper pulse width"""
        # Map value (-1 to 1) to pulse width (min_pulse to max_pulse)
        pulse = self.center_pulse + value * (self.max_pulse - self.min_pulse) / 2
        
        # Convert pulse width to duty cycle
        return self._pulse_to_duty(pulse)
    
    def _pulse_to_duty(self, pulse_width):
        """Convert pulse width in microseconds to duty cycle percentage"""
        # Duty cycle = (pulse_width / 20000) * 100
        # 20000 microseconds = 20ms = 1/50Hz
        return (pulse_width / 20000) * 100
    
    def get_status(self):
        """Get the current status of the servo controller"""
        return {
            'connected': self.connected,
            'error': self.error,
            'horizontal_pos': self.horizontal_pos,
            'vertical_pos': self.vertical_pos,
            'focus_pos': self.focus_pos
        }
    
    def cleanup(self):
        """Clean up GPIO resources"""
        try:
            # Return servos to center position before stopping
            self.update_position(0, 0, 0)
            time.sleep(0.5)
            
            self.horizontal_pwm.stop()
            self.vertical_pwm.stop()
            self.focus_pwm.stop()
            GPIO.cleanup()
        except Exception as e:
            print(f"Error during cleanup: {e}") 