import pygame
import threading
import time

class InputManager:
    def __init__(self):
        # Initialize pygame if not already initialized
        if not pygame.get_init():
            pygame.init()
        
        # Initialize joystick module if not already initialized
        if not pygame.joystick.get_init():
            pygame.joystick.init()
        
        # Initialize joystick
        self.joystick = None
        self.connected = False
        self.error = None
        
        # Joystick values
        self.horizontal = 0
        self.vertical = 0
        self.focus = 0
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
        # Try to connect to joystick
        self._connect_joystick()
        
        # Start input thread
        self.running = True
        self.thread = threading.Thread(target=self._input_loop)
        self.thread.daemon = True
        self.thread.start()
    
    def _connect_joystick(self):
        """Try to connect to the first available joystick"""
        try:
            if pygame.joystick.get_count() > 0:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                self.connected = True
                self.error = None
                print(f"Connected to joystick: {self.joystick.get_name()}")
            else:
                self.connected = False
                self.error = "No joystick found"
                print("No joystick found")
        except Exception as e:
            self.connected = False
            self.error = str(e)
            print(f"Error connecting to joystick: {e}")
    
    def _input_loop(self):
        """Main input processing loop"""
        while self.running:
            try:
                # Process pygame events
                for event in pygame.event.get():
                    if event.type == pygame.JOYAXISMOTION:
                        with self.lock:
                            # Map joystick axes to controls
                            if event.axis == 0:  # Left stick X
                                self.horizontal = event.value
                            elif event.axis == 1:  # Left stick Y
                                self.vertical = -event.value  # Invert Y axis
                            elif event.axis == 3:  # Right stick X
                                self.focus = event.value
                
                # Check joystick connection
                if not self.connected and pygame.joystick.get_count() > 0:
                    self._connect_joystick()
                elif self.connected and pygame.joystick.get_count() == 0:
                    self.connected = False
                    self.error = "Joystick disconnected"
                
                time.sleep(0.01)  # Small delay to prevent CPU overuse
                
            except Exception as e:
                self.error = str(e)
                print(f"Error in input loop: {e}")
                time.sleep(1)  # Longer delay on error
    
    def get_values(self):
        """Get current joystick values"""
        with self.lock:
            return {
                'horizontal': self.horizontal,
                'vertical': self.vertical,
                'focus': self.focus
            }
    
    def get_status(self):
        """Get the current status of the input manager"""
        with self.lock:
            return {
                'connected': self.connected,
                'error': self.error,
                'values': self.get_values()
            }
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        if self.thread.is_alive():
            self.thread.join()
        # Don't quit pygame here, as it might be used by other parts of the application
        print("Input manager cleaned up") 