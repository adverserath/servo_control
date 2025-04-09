import os
import sys
import time
import threading
import logging
import cv2
import numpy as np
from http.server import HTTPServer, BaseHTTPRequestHandler
from camera_manager import CameraManager
from servo_controller import ServoController
from input_manager import InputManager
from config import SCREEN_WIDTH, SCREEN_HEIGHT, FRAME_RATE
from dotenv import load_dotenv
import json
import base64
from datetime import datetime
import shutil
import platform
from flask import Flask, Response, render_template, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create photos directory if it doesn't exist
PHOTOS_DIR = "photos"
if not os.path.exists(PHOTOS_DIR):
    os.makedirs(PHOTOS_DIR)

class WebCameraServer:
    def __init__(self, camera_manager: CameraManager, servo_controller: ServoController):
        self.camera_manager = camera_manager
        self.servo_controller = servo_controller
        self.app = Flask(__name__)
        self.server_thread = None
        self.is_running = False
        
        # Check if running on Raspberry Pi
        self.is_raspberry_pi = (platform.system() == 'Linux' and 
                               platform.machine().startswith('arm'))
        
        # Set up routes
        self.app.route('/')(self.index)
        self.app.route('/video_feed')(self.video_feed)
        self.app.route('/status')(self.status)
        self.app.route('/update_position/<axis>/<int:position>')(self.update_position)
    
    def start(self, host='0.0.0.0', port=5000):
        """Start the web server in a separate thread."""
        self.is_running = True
        self.server_thread = threading.Thread(
            target=self.app.run,
            kwargs={'host': host, 'port': port, 'debug': False, 'use_reloader': False}
        )
        self.server_thread.daemon = True
        self.server_thread.start()
        logger.info(f"Web server started on {host}:{port}")
    
    def stop(self):
        """Stop the web server."""
        self.is_running = False
        if self.server_thread:
            self.server_thread.join(timeout=5)
        logger.info("Web server stopped")
    
    def index(self):
        """Render the main page."""
        return render_template('index.html')
    
    def video_feed(self):
        """Stream video from the camera."""
        def generate():
            while self.is_running:
                frame = self.camera_manager.get_frame()
                if frame is not None:
                    ret, buffer = cv2.imencode('.jpg', frame)
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                time.sleep(0.1)  # Limit frame rate
        
        return Response(generate(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    
    def status(self):
        """Get the current status of the system."""
        status = {
            'camera': self.camera_manager.get_status(),
            'servo': self.servo_controller.get_status(),
            'platform': 'Raspberry Pi' if self.is_raspberry_pi else 'Development'
        }
        return jsonify(status)
    
    def update_position(self, axis, position):
        """Update the position of a servo."""
        try:
            self.servo_controller.update_position(axis, position)
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Error updating position: {e}")
            return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == "__main__":
    # Create and start server
    server = WebCameraServer()
    server.start()
    
    try:
        # Keep the main thread running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.stop() 