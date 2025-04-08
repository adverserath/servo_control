import pygame
import time
import sys
from config import FRAME_RATE, MOTOR_TYPE
from servo_manager import ServoManager
from stepper_manager import StepperManager
from camera_manager import CameraManager
from input_manager import InputManager
from display_manager import DisplayManager
from web_camera import WebCameraServer
from telegram_manager import TelegramManager

def main():
    """Main entry point for the servo camera application"""
    try:
        # Initialize pygame
        pygame.init()
        
        # Initialize managers
        if MOTOR_TYPE.lower() == 'stepper':
            print("Using NEMA17 stepper motors")
            motor_manager = StepperManager()
        else:
            print("Using MG996R servos")
            motor_manager = ServoManager()
            
        camera_manager = CameraManager()
        input_manager = InputManager()
        display_manager = DisplayManager()
        telegram_manager = TelegramManager()
        
        # Start web server
        web_server = WebCameraServer(motor_manager, camera_manager, telegram_manager)
        web_server.start()
        
        print("Camera Controller started")
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
            
            # Update motor positions
            motor_manager.update_position(
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
                motor_positions={
                    'horizontal': motor_manager.horizontal_pos,
                    'vertical': motor_manager.vertical_pos,
                    'focus': motor_manager.focus_pos
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
        motor_manager.cleanup()
        pygame.quit()
        print("Program terminated")

if __name__ == "__main__":
    main() 