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
from typing import Optional, Tuple

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

class WebServer:
    def __init__(self, servo_controller: ServoController, input_manager: InputManager):
        self.servo_controller = servo_controller
        self.input_manager = input_manager
        self.app = Flask(__name__)
        self.is_running = False
        self.server_thread: Optional[threading.Thread] = None
        
        # Set up routes
        self.app.route('/')(self.index)
        self.app.route('/video_feed')(self.video_feed)
        self.app.route('/status')(self.status)
        self.app.route('/update_position/<servo>/<int:position>')(self.update_position)
        
        # Create templates directory if it doesn't exist
        os.makedirs('templates', exist_ok=True)
        
        # Create index.html template
        with open('templates/index.html', 'w') as f:
            f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Servo Control</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .video-container { margin: 20px 0; }
        .video-feed { width: 100%; max-width: 800px; }
        .controls { margin: 20px 0; }
        .slider { width: 100%; margin: 10px 0; }
        .status { margin: 20px 0; padding: 10px; background: #f0f0f0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Servo Control</h1>
        
        <div class="video-container">
            <img src="{{ url_for('video_feed') }}" class="video-feed">
        </div>
        
        <div class="controls">
            <h2>Horizontal Servo</h2>
            <input type="range" min="0" max="180" value="90" class="slider" 
                   oninput="updatePosition('horizontal', this.value)">
            
            <h2>Vertical Servo</h2>
            <input type="range" min="0" max="180" value="90" class="slider" 
                   oninput="updatePosition('vertical', this.value)">
            
            <h2>Focus Servo</h2>
            <input type="range" min="0" max="180" value="90" class="slider" 
                   oninput="updatePosition('focus', this.value)">
        </div>
        
        <div class="status">
            <h2>Status</h2>
            <pre id="status">Loading...</pre>
        </div>
    </div>
    
    <script>
        function updatePosition(servo, position) {
            fetch(`/update_position/${servo}/${position}`)
                .then(response => response.json())
                .then(data => console.log(data))
                .catch(error => console.error('Error:', error));
        }
        
        function updateStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('status').textContent = 
                        JSON.stringify(data, null, 2);
                })
                .catch(error => console.error('Error:', error));
        }
        
        // Update status every second
        setInterval(updateStatus, 1000);
    </script>
</body>
</html>
            ''')
    
    def index(self):
        """Render the main page."""
        return render_template('index.html')
    
    def video_feed(self):
        """Generate mock video feed."""
        def generate():
            while self.is_running:
                # Create a blank frame
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                frame[:] = (0, 0, 255)  # Blue background
                
                # Add text
                cv2.putText(frame, "No Camera Available", (50, 240),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(frame, "Using Mock Camera", (50, 280),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
                # Add servo positions
                status = self.servo_controller.get_status()
                cv2.putText(frame, f"H: {status['horizontal']}°", (50, 320),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(frame, f"V: {status['vertical']}°", (50, 360),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(frame, f"F: {status['focus']}°", (50, 400),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
                # Encode frame
                ret, buffer = cv2.imencode('.jpg', frame)
                if not ret:
                    continue
                
                # Yield frame
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        return Response(generate(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    
    def status(self):
        """Get the current status of all components."""
        return jsonify({
            'servo_controller': self.servo_controller.get_status(),
            'input_manager': {
                'running': self.input_manager.is_running,
                'has_joystick': self.input_manager.has_joystick
            },
            'platform': {
                'system': platform.system(),
                'machine': platform.machine(),
                'is_raspberry_pi': (platform.system() == 'Linux' and 
                                  platform.machine().startswith('arm'))
            }
        })
    
    def update_position(self, servo: str, position: int) -> Tuple[dict, int]:
        """Update the position of a servo."""
        try:
            if servo == 'horizontal':
                self.servo_controller.update_position('horizontal', position)
            elif servo == 'vertical':
                self.servo_controller.update_position('vertical', position)
            elif servo == 'focus':
                self.servo_controller.update_position('focus', position)
            else:
                return {'error': 'Invalid servo'}, 400
            
            return {'success': True}, 200
        except Exception as e:
            logger.error(f"Error updating {servo} servo: {e}")
            return {'error': str(e)}, 500
    
    def start(self, host: str = '0.0.0.0', port: int = 5000):
        """Start the web server in a separate thread."""
        if self.is_running:
            return
        
        self.is_running = True
        self.server_thread = threading.Thread(
            target=self.app.run,
            kwargs={'host': host, 'port': port, 'debug': False}
        )
        self.server_thread.daemon = True
        self.server_thread.start()
        logger.info(f"Web server started on {host}:{port}")
    
    def stop(self):
        """Stop the web server."""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.server_thread:
            self.server_thread.join(timeout=5)
            self.server_thread = None
        logger.info("Web server stopped")

if __name__ == "__main__":
    # Create and start server
    server = WebServer()
    server.start()
    
    try:
        # Keep the main thread running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.stop() 