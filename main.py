import os
import sys
import time
import logging
import platform
from web_server import WebCameraServer
from camera_manager import CameraManager
from servo_controller import ServoController
from config import WEB_PORT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Check if running on Raspberry Pi
        is_raspberry_pi = (platform.system() == 'Linux' and 
                          platform.machine().startswith('arm'))
        
        if not is_raspberry_pi:
            logger.info("Running in development mode (not on Raspberry Pi)")
        
        # Initialize components
        camera_manager = CameraManager()
        servo_controller = ServoController()
        web_server = WebCameraServer(camera_manager, servo_controller)
        
        # Start the web server
        web_server.start(port=WEB_PORT)
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            # Cleanup
            web_server.stop()
            camera_manager.cleanup()
            servo_controller.cleanup()
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 