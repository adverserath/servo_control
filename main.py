import logging
import platform
import signal
import sys
import threading
from typing import Optional

from servo_controller import ServoController
from input_manager import InputManager
from web_server import WebServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Application:
    def __init__(self):
        self.servo_controller: Optional[ServoController] = None
        self.input_manager: Optional[InputManager] = None
        self.web_server: Optional[WebServer] = None
        self.is_running = False
        self.cleanup_lock = threading.Lock()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
    
    def _handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}")
        self.stop()
    
    def start(self):
        """Start the application components."""
        try:
            logger.info("Starting application")
            self.is_running = True
            
            # Initialize components
            self.servo_controller = ServoController()
            self.input_manager = InputManager(self.servo_controller)
            self.web_server = WebServer(self.servo_controller, self.input_manager)
            
            # Start components
            self.input_manager.start()
            self.web_server.start()
            
            logger.info("Application started successfully")
            
            # Wait for shutdown signal
            while self.is_running:
                signal.pause()
                
        except Exception as e:
            logger.error(f"Error starting application: {e}")
            self.stop()
    
    def stop(self):
        """Stop the application and clean up resources."""
        with self.cleanup_lock:
            if not self.is_running:
                return
            
            logger.info("Stopping application")
            self.is_running = False
            
            # Stop components in reverse order
            if self.web_server:
                self.web_server.stop()
                self.web_server = None
            
            if self.input_manager:
                self.input_manager.stop()
                self.input_manager = None
            
            if self.servo_controller:
                self.servo_controller.cleanup()
                self.servo_controller = None
            
            logger.info("Application stopped")

def main():
    """Main entry point."""
    app = Application()
    app.start()

if __name__ == "__main__":
    main() 