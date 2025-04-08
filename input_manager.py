import pygame

class InputManager:
    def __init__(self):
        # Controller state
        self.joystick = None
        self.joystick_connected = False
        
        # Position values
        self.horizontal = 0
        self.vertical = 0
        self.focus = 0
        
        # Initialize joystick if available
        self._init_joystick()
    
    def _init_joystick(self):
        """Initialize the game controller"""
        try:
            pygame.joystick.init()
            if pygame.joystick.get_count() > 0:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                self.joystick_connected = True
                print("Controller connected:", self.joystick.get_name())
            else:
                print("No controllers found")
        except Exception as e:
            print(f"Joystick error: {e}")
            self.joystick_connected = False
            print("Using keyboard controls")
    
    def process_events(self):
        """Process input events and update positions"""
        quit_requested = False
        
        # Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_requested = True
            
            # Keyboard controls
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.horizontal = max(-1, self.horizontal - 0.1)
                elif event.key == pygame.K_RIGHT:
                    self.horizontal = min(1, self.horizontal + 0.1)
                elif event.key == pygame.K_UP:
                    self.vertical = max(-1, self.vertical - 0.1)
                elif event.key == pygame.K_DOWN:
                    self.vertical = min(1, self.vertical + 0.1)
                elif event.key == pygame.K_a:
                    self.focus = max(-1, self.focus - 0.1)
                elif event.key == pygame.K_d:
                    self.focus = min(1, self.focus + 0.1)
        
        # If joystick is connected, get values from it
        if self.joystick_connected:
            pygame.event.pump()  # Process joystick events
            
            # Get analog stick values
            self.horizontal = self.joystick.get_axis(0)  # Left stick horizontal
            self.vertical = self.joystick.get_axis(1)    # Left stick vertical
            
            # Use both triggers for bidirectional focus
            left_trigger = self.joystick.get_axis(2)    # Left trigger
            right_trigger = self.joystick.get_axis(5)   # Right trigger
            
            # Combine triggers: right focuses in, left focuses out
            self.focus = right_trigger - left_trigger
            self.focus = max(-1, min(1, self.focus))  # Clamp to -1,1
            
        return quit_requested
    
    def get_control_values(self):
        """Get the current control values"""
        return {
            'horizontal': self.horizontal,
            'vertical': self.vertical,
            'focus': self.focus
        } 