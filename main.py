import pygame
import time
import sys
import os
from config import FRAME_RATE
from servo_manager import ServoManager
from camera_manager import CameraManager
from input_manager import InputManager
from display_manager import DisplayManager
from web_camera import WebCameraServer

# Handle XDG_RUNTIME_DIR issue on Raspberry Pi OS
if not os.environ.get('XDG_RUNTIME_DIR'):
    # Create runtime directory in user's home directory
    home_dir = os.path.expanduser('~')
    runtime_dir = os.path.join(home_dir, '.runtime')
    os.makedirs(runtime_dir, exist_ok=True)
    os.environ['XDG_RUNTIME_DIR'] = runtime_dir

def main():
    """Main entry point for the servo camera application"""
    web_server = None
    try:
        print("Starting Servo Camera Controller...")
        
        # Initialize pygame if not already initialized
        if not pygame.get_init():
            pygame.init()
            print("Pygame initialized")
        
        # Initialize managers
        print("Initializing servo manager...")
        servo_manager = ServoManager()
        
        print("Initializing camera manager...")
        camera_manager = CameraManager()
        
        print("Initializing input manager...")
        input_manager = InputManager()
        
        print("Initializing display manager...")
        display_manager = DisplayManager()
        
        # Start web server
        print("Starting web server...")
        web_server = WebCameraServer(servo_manager, camera_manager, input_manager)
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
                print("Quit requested")
                continue
            
            # Check for capture/record requests
            if input_manager.check_capture_request():
                print("Capture requested via button...")
                success, result = camera_manager.capture_still()
                if success:
                    print(f"Image captured successfully: {result}")
                else:
                    print(f"Image capture failed: {result}")

            if input_manager.check_toggle_recording_request():
                print("Toggle recording requested via button...")
                success, result = camera_manager.toggle_recording()
                if success:
                    if camera_manager.is_recording:
                        print(f"Recording started: {result}")
                    else:
                        print(f"Recording stopped: {result}")
                else:
                    print(f"Toggle recording failed: {result}")
            
            # Get control values
            controls = input_manager.get_control_values()
            
            # Debug output for control values
            if controls['horizontal'] != 0 or controls['vertical'] != 0 or controls['focus'] != 0:
                print(f"Control values: H={controls['horizontal']:.2f}, V={controls['vertical']:.2f}, F={controls['focus']:.2f}")
            
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
        import traceback
        traceback.print_exc()
    finally:
        # Clean up resources
        print("Cleaning up resources...")
        if web_server:
            web_server.stop()
        servo_manager.cleanup()
        pygame.quit()
        print("Program terminated")

if __name__ == "__main__":
    main() 