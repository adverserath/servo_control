import os
import sys
import logging
from web_server import run_server
from camera_manager import CameraManager
from servo_controller import ServoController
from input_manager import InputManager
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Initialize components
        logger.info("Initializing components...")
        camera_manager = CameraManager()
        servo_controller = ServoController()
        input_manager = InputManager(servo_controller)

        # Connect to camera
        logger.info("Connecting to camera...")
        camera_connected = camera_manager.connect()
        if not camera_connected:
            logger.warning("Failed to connect to camera, continuing without camera")
            # We'll continue without the camera

        # Start input manager thread
        logger.info("Starting input manager...")
        input_thread = threading.Thread(target=input_manager.run)
        input_thread.daemon = True
        input_thread.start()

        # Run the server
        logger.info("Starting web server...")
        run_server(camera_manager, servo_controller, input_manager)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        if 'camera_manager' in locals():
            camera_manager.cleanup()
        if 'servo_controller' in locals():
            servo_controller.cleanup()
        if 'input_manager' in locals():
            input_manager.cleanup()

if __name__ == '__main__':
    main() 