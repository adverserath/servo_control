import logging
import platform
import threading
import time
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InputManager:
    def __init__(self, servo_controller):
        self.servo_controller = servo_controller
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.is_raspberry_pi = (platform.system() == 'Linux' and 
                               platform.machine().startswith('arm'))
        
        # Initialize pygame if not already initialized
        try:
            import pygame
            if not pygame.get_init():
                pygame.init()
            if not pygame.joystick.get_init():
                pygame.joystick.init()
            
            # Try to initialize joystick
            if pygame.joystick.get_count() > 0:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                logger.info(f"Joystick initialized: {self.joystick.get_name()}")
            else:
                logger.warning("No joystick found")
                self.joystick = None
        except ImportError:
            logger.warning("Pygame not available, using mock joystick")
            self.joystick = None
        
        # Initialize mock joystick values for non-Raspberry Pi systems
        self.mock_horizontal = 0.0
        self.mock_vertical = 0.0
        self.mock_focus = 0.0
    
    def _apply_deadzone(self, value: float, deadzone: float = 0.1) -> float:
        """Apply deadzone to joystick value."""
        if abs(value) < deadzone:
            return 0.0
        return value
    
    def _process_joystick_input(self) -> None:
        """Process joystick input and update servo positions."""
        try:
            import pygame
            
            # Process pygame events
            for event in pygame.event.get():
                if event.type == pygame.JOYAXISMOTION:
                    if event.axis == 0:  # Left stick horizontal
                        self.mock_horizontal = self._apply_deadzone(event.value)
                    elif event.axis == 1:  # Left stick vertical
                        self.mock_vertical = self._apply_deadzone(event.value)
                    elif event.axis == 3:  # Right stick vertical (focus)
                        self.mock_focus = self._apply_deadzone(event.value)
            
            # Update servo positions
            if self.joystick:
                horizontal = self._apply_deadzone(self.joystick.get_axis(0))
                vertical = self._apply_deadzone(self.joystick.get_axis(1))
                focus = self._apply_deadzone(self.joystick.get_axis(3))
            else:
                # Use mock values
                horizontal = self.mock_horizontal
                vertical = self.mock_vertical
                focus = self.mock_focus
            
            # Convert -1.0 to 1.0 range to 0 to 180 degrees
            h_pos = int((horizontal + 1.0) * 90)
            v_pos = int((vertical + 1.0) * 90)
            f_pos = int((focus + 1.0) * 90)
            
            # Update servo positions
            self.servo_controller.update_position('horizontal', h_pos)
            self.servo_controller.update_position('vertical', v_pos)
            self.servo_controller.update_position('focus', f_pos)
            
        except Exception as e:
            logger.error(f"Error processing joystick input: {e}")
    
    def run(self) -> None:
        """Main input processing loop."""
        logger.info("Starting input manager")
        while self.is_running:
            try:
                self._process_joystick_input()
                time.sleep(0.01)  # 100Hz update rate
            except Exception as e:
                logger.error(f"Error in input manager loop: {e}")
                time.sleep(1)  # Wait longer on error
    
    def start(self) -> None:
        """Start the input manager in a background thread."""
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self.run)
            self.thread.daemon = True
            self.thread.start()
            logger.info("Input manager started")
    
    def stop(self) -> None:
        """Stop the input manager."""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
            logger.info("Input manager stopped")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop()
        try:
            import pygame
            if pygame.get_init():
                pygame.quit()
        except ImportError:
            pass
        logger.info("Input manager cleaned up") 