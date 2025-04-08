import pygame
import threading
import time
import os

class InputManager:
    def __init__(self):
        # Debug flag
        self.debug = True
        
        # Initialize pygame if not already initialized
        if not pygame.get_init():
            pygame.init()
            if self.debug:
                print("Pygame initialized")
        
        # Initialize display before joystick to ensure video system is initialized
        if not pygame.display.get_init():
            # Set SDL_VIDEODRIVER to dummy if on headless system
            if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
                os.environ['SDL_VIDEODRIVER'] = 'dummy'
                if self.debug:
                    print("Using dummy video driver for headless system")
            pygame.display.init()
            pygame.display.set_mode((1, 1), pygame.HIDDEN)
            if self.debug:
                print("Display initialized")
        
        # Initialize joystick module if not already initialized
        try:
            if not pygame.joystick.get_init():
                pygame.joystick.init()
                if self.debug:
                    print("Joystick module initialized")
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
        self._left_trigger = 0  # Store trigger values separately
        self._right_trigger = 0
        
        # Request flags
        self.capture_requested = False
        self.toggle_recording_requested = False
        
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
                joystick_count = pygame.joystick.get_count()
                if self.debug:
                    print(f"Found {joystick_count} joystick(s)")
                
                if joystick_count > 0:
                    self.joystick = pygame.joystick.Joystick(0)
                    self.joystick.init()
                    self.connected = True
                    self.error = None
                    
                    # Print joystick information
                    if self.debug:
                        print(f"Connected to joystick: {self.joystick.get_name()}")
                        print(f"Joystick ID: {self.joystick.get_id()}")
                        print(f"Number of axes: {self.joystick.get_numaxes()}")
                        print(f"Number of buttons: {self.joystick.get_numbuttons()}")
                        print(f"Number of hats: {self.joystick.get_numhats()}")
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
                        if self.debug:
                            print("Joystick disconnected")
                    
                    # Process events in the main loop
                    quit_requested = self.process_events()
                    if quit_requested:
                        self.running = False
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
            # Reset request flags at the start of processing
            self.capture_requested = False
            self.toggle_recording_requested = False
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    quit_requested = True
                    
                elif event.type == pygame.JOYAXISMOTION and self.connected:
                    # Map joystick axes to controls
                    # Axis mapping might need adjustment based on controller
                    if event.axis == 2:  # Right stick X (Horizontal)
                        self.horizontal = event.value
                        if self.debug: print(f"Joystick axis 2 (H): {event.value:.2f}")
                    elif event.axis == 3:  # Right stick Y (Vertical)
                        self.vertical = -event.value  # Invert Y axis
                        if self.debug: print(f"Joystick axis 3 (V): {event.value:.2f} -> {self.vertical:.2f}")
                    elif event.axis == 4: # Left Trigger (often -1 to 1)
                         # Map trigger from (-1 to 1) to (0 to 1)
                        self._left_trigger = (event.value + 1) / 2
                        if self.debug: print(f"Joystick axis 4 (L Trig): {event.value:.2f} -> {self._left_trigger:.2f}")
                    elif event.axis == 5: # Right Trigger (often -1 to 1)
                        # Map trigger from (-1 to 1) to (0 to 1)
                        self._right_trigger = (event.value + 1) / 2
                        if self.debug: print(f"Joystick axis 5 (R Trig): {event.value:.2f} -> {self._right_trigger:.2f}")

                    # Combine triggers for focus control (-1 to 1)
                    self.focus = self._right_trigger - self._left_trigger
                    # Optional: Add deadzone for focus if needed
                    # focus_deadzone = 0.1
                    # if abs(self.focus) < focus_deadzone:
                    #     self.focus = 0
                        
                elif event.type == pygame.JOYBUTTONDOWN and self.connected:
                    if self.debug: print(f"Joystick button {event.button} pressed")
                    # Button mapping might need adjustment
                    if event.button == 0:  # Cross Button (X)
                        self.capture_requested = True
                        if self.debug: print("Capture requested (Button 0)")
                    elif event.button == 3:  # Square Button
                        self.toggle_recording_requested = True
                        if self.debug: print("Toggle recording requested (Button 3)")
                        
                # Optional: Add JOYHATMOTION or JOYBUTTONUP if needed

        return quit_requested
    
    def check_capture_request(self):
        with self.lock:
            return self.capture_requested

    def check_toggle_recording_request(self):
        with self.lock:
            return self.toggle_recording_requested
    
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