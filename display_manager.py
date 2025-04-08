import pygame
import numpy as np
from config import SCREEN_WIDTH, SCREEN_HEIGHT, DISPLAY_CAPTION

class DisplayManager:
    def __init__(self):
        # Initialize display
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(DISPLAY_CAPTION)
        
        # Initialize font for status text
        self.font = pygame.font.Font(None, 36)
        
        # Create a clock for frame rate control
        self.clock = pygame.time.Clock()
    
    def update_display(self, frame, camera_connected, input_manager, servo_positions):
        """Update the display with camera feed and status information"""
        # Clear screen
        self.screen.fill((0, 0, 0))
        
        # Draw camera feed if available
        if frame is not None:
            # Convert numpy array to pygame surface
            camera_surface = pygame.surfarray.make_surface(frame)
            self.screen.blit(camera_surface, (0, 0))
        
        # Draw status text
        status_text = []
        status_text.append(f"Camera: {'Connected' if camera_connected else 'Disconnected'}")
        status_text.append(f"Controls: {'Joystick' if input_manager.connected else 'Keyboard'}")
        if input_manager.error:
            status_text.append(f"Input Error: {input_manager.error}")
        status_text.append(f"Horizontal: {servo_positions['horizontal']:.2f}")
        status_text.append(f"Vertical: {servo_positions['vertical']:.2f}")
        status_text.append(f"Focus: {servo_positions['focus']:.2f}")
        
        for i, text in enumerate(status_text):
            text_surface = self.font.render(text, True, (255, 255, 255))
            self.screen.blit(text_surface, (10, 10 + i * 30))
        
        # Update display
        pygame.display.flip()
    
    def limit_fps(self, fps):
        """Limit the frame rate"""
        self.clock.tick(fps) 