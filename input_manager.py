import pygame
import threading
import time
import os

class InputManager:
    def __init__(self):
        # Initialize pygame if not already initialized
        if not pygame.get_init():
            pygame.init()
        
        # Initialize display before joystick to ensure video system is initialized
        if not pygame.display.get_init():
            # Set SDL_VIDEODRIVER to dummy if on headless system
            if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
                os.environ['SDL_VIDEODRIVER'] = 'dummy'
            pygame.display.init()
            pygame.display.set_mode((1, 1), pygame.HIDDEN)
        
        # Initialize joystick module if not already initialized
        try:
            if not pygame.joystick.get_init():
                pygame.joystick.init()
        except pygame.error as e:
            print(f"Error initializing joystick module: {e}")
            self.error = str(e)
        
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
            if pygame.joystick.get_init():  # Check if joystick system is initialized
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
            else:
                self.connected = False
                self.error = "Joystick system not initialized"
                print("Joystick system not initialized")
        except Exception as e:
            self.connected = False
            self.error = str(e)
            print(f"Error connecting to joystick: {e}")
    
    def _input_loop(self):
        """Main input processing loop"""
        while self.running:
            try:
                if pygame.joystick.get_init():  # Check if joystick system is initialized
                    # Check joystick connection
                    if not self.connected and pygame.joystick.get_count() > 0:
                        self._connect_joystick()
                    elif self.connected and pygame.joystick.get_count() == 0:
                        self.connected = False
                        self.error = "Joystick disconnected"
                    
                    # Process events in the main loop
                    self.process_events()
                else:
                    # Try to initialize joystick system if it's not initialized
                    try:
                        pygame.joystick.init()
                        print("Joystick system initialized")
                    except pygame.error as e:
                        self.error = f"Failed to initialize joystick system: {e}"
                        print(self.error)
                
                time.sleep(0.01)  # Small delay to prevent CPU overuse
                
            except Exception as e:
                self.error = str(e)
                print(f"Error in input loop: {e}")
                time.sleep(1)  # Longer delay on error
    
    def process_events(self):
        """Process pygame events and return True if quit requested"""
        quit_requested = False
        with self.lock:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    quit_requested = True
                elif event.type == pygame.JOYAXISMOTION and self.connected:
                    # Map joystick axes to controls
                    if event.axis == 0:  # Left stick X
                        self.horizontal = event.value
                    elif event.axis == 1:  # Left stick Y
                        self.vertical = -event.value  # Invert Y axis
                    elif event.axis == 3:  # Right stick X
                        self.focus = event.value
        return quit_requested
    
    def get_control_values(self):
        """Get current control values"""
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
                'values': self.get_control_values()
            }
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        if self.thread.is_alive():
            self.thread.join()
        # Don't quit pygame here, as it might be used by other parts of the application
        print("Input manager cleaned up") 