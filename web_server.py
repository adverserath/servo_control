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
    def __init__(self, host='0.0.0.0', port=8000):
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.camera_manager = CameraManager()
        self.servo_controller = ServoController()
        self.input_manager = InputManager(self.servo_controller)
        self.is_running = False
        self.last_frame_time = 0
        self.frame_interval = 1.0 / FRAME_RATE
        
        # Initialize camera
        self.camera_manager.connect()
        
        # Start input manager
        self.input_manager.start()
        
        # Create handler class with access to server instance
        class Handler(BaseHTTPRequestHandler):
            server_instance = self
            
            def do_GET(self):
                self.server_instance.handle_request(self)
            
            def do_POST(self):
                self.server_instance.handle_request(self)
        
        # Create server with custom handler
        self.server = HTTPServer((self.host, self.port), Handler)
    
    def handle_request(self, handler):
        """Handle incoming HTTP requests"""
        try:
            if handler.path == '/':
                # Serve main page
                handler.send_response(200)
                handler.send_header('Content-type', 'text/html')
                handler.end_headers()
                
                with open('static/index.html', 'rb') as f:
                    handler.wfile.write(f.read())
                
            elif handler.path.startswith('/static/'):
                # Serve static files
                file_path = handler.path[1:]  # Remove leading slash
                if os.path.exists(file_path):
                    handler.send_response(200)
                    if file_path.endswith('.css'):
                        handler.send_header('Content-type', 'text/css')
                    elif file_path.endswith('.js'):
                        handler.send_header('Content-type', 'application/javascript')
                    handler.end_headers()
                    
                    with open(file_path, 'rb') as f:
                        handler.wfile.write(f.read())
                else:
                    handler.send_response(404)
                    handler.end_headers()
                
            elif handler.path == '/video_feed':
                # Stream video feed
                handler.send_response(200)
                handler.send_header('Content-type', 'image/jpeg')
                handler.end_headers()
                
                success, frame_bytes = self.camera_manager.get_frame()
                if success:
                    handler.wfile.write(frame_bytes)
                
            elif handler.path == '/status':
                # Return camera status
                handler.send_response(200)
                handler.send_header('Content-type', 'application/json')
                handler.end_headers()
                
                status = self.camera_manager.get_status()
                handler.wfile.write(json.dumps(status).encode())
                
            elif handler.path == '/capture_photo':
                # Capture photo
                handler.send_response(200)
                handler.send_header('Content-type', 'application/json')
                handler.end_headers()
                
                success, frame_bytes = self.camera_manager.get_frame()
                if success:
                    # Generate filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"photo_{timestamp}.jpg"
                    filepath = os.path.join(PHOTOS_DIR, filename)
                    
                    # Save photo
                    with open(filepath, 'wb') as f:
                        f.write(frame_bytes)
                    
                    handler.wfile.write(json.dumps({
                        'success': True,
                        'filename': filename
                    }).encode())
                else:
                    handler.wfile.write(json.dumps({
                        'success': False,
                        'error': 'Failed to capture frame'
                    }).encode())
                
            elif handler.path == '/library':
                # Return photo library
                handler.send_response(200)
                handler.send_header('Content-type', 'application/json')
                handler.end_headers()
                
                photos = []
                for filename in os.listdir(PHOTOS_DIR):
                    if filename.endswith('.jpg'):
                        filepath = os.path.join(PHOTOS_DIR, filename)
                        timestamp = datetime.fromtimestamp(os.path.getctime(filepath))
                        photos.append({
                            'filename': filename,
                            'timestamp': timestamp.strftime("%Y-%m-%d %H:%M:%S")
                        })
                
                handler.wfile.write(json.dumps({
                    'success': True,
                    'photos': sorted(photos, key=lambda x: x['timestamp'], reverse=True)
                }).encode())
                
            elif handler.path.startswith('/photos/'):
                # Serve photo files
                filename = handler.path.split('/')[-1]
                filepath = os.path.join(PHOTOS_DIR, filename)
                
                if os.path.exists(filepath):
                    handler.send_response(200)
                    handler.send_header('Content-type', 'image/jpeg')
                    handler.end_headers()
                    
                    with open(filepath, 'rb') as f:
                        handler.wfile.write(f.read())
                else:
                    handler.send_response(404)
                    handler.end_headers()
                
            elif handler.path == '/delete_photo':
                # Delete photo
                content_length = int(handler.headers['Content-Length'])
                post_data = handler.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                filename = data.get('filename')
                if filename:
                    filepath = os.path.join(PHOTOS_DIR, filename)
                    try:
                        os.remove(filepath)
                        handler.send_response(200)
                        handler.send_header('Content-type', 'application/json')
                        handler.end_headers()
                        handler.wfile.write(json.dumps({
                            'success': True
                        }).encode())
                    except Exception as e:
                        handler.send_response(500)
                        handler.send_header('Content-type', 'application/json')
                        handler.end_headers()
                        handler.wfile.write(json.dumps({
                            'success': False,
                            'error': str(e)
                        }).encode())
                else:
                    handler.send_response(400)
                    handler.send_header('Content-type', 'application/json')
                    handler.end_headers()
                    handler.wfile.write(json.dumps({
                        'success': False,
                        'error': 'No filename provided'
                    }).encode())
                
            elif handler.path == '/send_to_telegram':
                # Send photo to Telegram
                content_length = int(handler.headers['Content-Length'])
                post_data = handler.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                filename = data.get('filename')
                if filename:
                    filepath = os.path.join(PHOTOS_DIR, filename)
                    try:
                        # TODO: Implement Telegram sending
                        # For now, just return success
                        handler.send_response(200)
                        handler.send_header('Content-type', 'application/json')
                        handler.end_headers()
                        handler.wfile.write(json.dumps({
                            'success': True
                        }).encode())
                    except Exception as e:
                        handler.send_response(500)
                        handler.send_header('Content-type', 'application/json')
                        handler.end_headers()
                        handler.wfile.write(json.dumps({
                            'success': False,
                            'error': str(e)
                        }).encode())
                else:
                    handler.send_response(400)
                    handler.send_header('Content-type', 'application/json')
                    handler.end_headers()
                    handler.wfile.write(json.dumps({
                        'success': False,
                        'error': 'No filename provided'
                    }).encode())
                
            else:
                handler.send_response(404)
                handler.end_headers()
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            handler.send_response(500)
            handler.end_headers()
    
    def start(self):
        """Start the web server"""
        try:
            self.is_running = True
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            logger.info(f"Web server started on {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            self.is_running = False
    
    def stop(self):
        """Stop the web server"""
        try:
            self.is_running = False
            if self.server:
                self.server.shutdown()
                self.server.server_close()
            if self.server_thread:
                self.server_thread.join(timeout=1.0)
            logger.info("Web server stopped")
        except Exception as e:
            logger.error(f"Error stopping web server: {e}")
    
    def cleanup(self):
        """Clean up resources"""
        try:
            self.stop()
            if self.input_manager:
                self.input_manager.cleanup()
            if self.camera_manager:
                self.camera_manager.cleanup()
            if self.servo_controller:
                self.servo_controller.cleanup()
            logger.info("Web server cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

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
        server.cleanup() 