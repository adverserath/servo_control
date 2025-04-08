import pygame
import time
import sys
from config import FRAME_RATE
from servo_manager import ServoManager
from camera_manager import CameraManager
from input_manager import InputManager
from display_manager import DisplayManager
from web_camera import WebCameraServer

def main():
    """Main entry point for the servo camera application"""
    try:
        # Initialize pygame
        pygame.init()
        
        # Initialize managers
        servo_manager = ServoManager()
        camera_manager = CameraManager()
        input_manager = InputManager()
        display_manager = DisplayManager()
        
        # Start web server
        web_server = WebCameraServer(servo_manager, camera_manager)
        web_server.start()
        
        print("Servo Camera Controller started")
        print("Press Ctrl+C to exit")
        
        # Main loop
        running = True
        while running:
            # Process input events
            quit_requested = input_manager.process_events()
            if quit_requested:
                running = False
            
            # Get control values
            controls = input_manager.get_control_values()
            
            # Update servo positions
            servo_manager.update_position(
                horizontal=controls['horizontal'],
                vertical=controls['vertical'],
                focus=controls['focus']
            )
            
            # Get current frame
            frame = camera_manager.get_frame()
            
            # Update display
            display_manager.update_display(
                frame=frame,
                camera_connected=camera_manager.connected,
                input_manager=input_manager,
                servo_positions={
                    'horizontal': servo_manager.horizontal_pos,
                    'vertical': servo_manager.vertical_pos,
                    'focus': servo_manager.focus_pos
                }
            )
            
            # Limit frame rate
            display_manager.limit_fps(FRAME_RATE)
            
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up resources
        servo_manager.cleanup()
        pygame.quit()
        print("Program terminated")

if __name__ == "__main__":
    main() 