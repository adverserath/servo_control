import os
import sys
import time
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from camera_manager import CameraManager
from servo_controller import ServoController
from input_manager import InputManager
from config import SCREEN_WIDTH, SCREEN_HEIGHT, FRAME_RATE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CameraStreamHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.camera_manager = kwargs.pop('camera_manager', None)
        self.servo_controller = kwargs.pop('servo_controller', None)
        self.input_manager = kwargs.pop('input_manager', None)
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self._get_html().encode())
        elif self.path == '/stream':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            self._stream_camera()
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            status = {
                'camera': self.camera_manager.get_status(),
                'servo': self.servo_controller.get_status(),
                'input': self.input_manager.get_status()
            }
            self.wfile.write(str(status).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def _stream_camera(self):
        """Stream camera frames to the client."""
        print("DEBUG: Starting camera stream")
        try:
            while True:
                success, frame_bytes = self.camera_manager.get_frame()
                if not success:
                    print("DEBUG: Failed to get frame from camera manager")
                    time.sleep(0.1)
                    continue

                # Send frame
                print("DEBUG: Sending frame to client")
                self.wfile.write(b'--frame\r\n')
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', len(frame_bytes))
                self.end_headers()
                self.wfile.write(frame_bytes)
                self.wfile.write(b'\r\n')

                # Control frame rate
                time.sleep(1.0 / FRAME_RATE)

        except Exception as e:
            logger.error(f"DEBUG: Error in camera stream: {e}")
            return

    def _get_html(self):
        """Return the HTML page for the camera stream."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Camera Stream</title>
            <style>
                body { margin: 0; padding: 20px; background: #1a1a1a; color: #fff; font-family: Arial, sans-serif; }
                .container { max-width: 1200px; margin: 0 auto; }
                .video-container { margin: 20px 0; text-align: center; }
                img { max-width: 100%; height: auto; border: 2px solid #333; }
                .status { margin: 20px 0; padding: 15px; background: #333; border-radius: 5px; }
                .controls { margin: 20px 0; }
                button { padding: 10px 20px; margin: 5px; background: #4CAF50; border: none; color: white; cursor: pointer; }
                button:hover { background: #45a049; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Camera Stream</h1>
                <div class="video-container">
                    <img src="/stream" alt="Camera Stream">
                </div>
                <div class="status" id="status">
                    Loading status...
                </div>
                <div class="controls">
                    <button onclick="toggleRecording()">Toggle Recording</button>
                </div>
            </div>
            <script>
                function updateStatus() {
                    fetch('/status')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('status').innerHTML = 
                                '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                        });
                }
                
                setInterval(updateStatus, 1000);
                
                function toggleRecording() {
                    // Add recording toggle functionality here
                }
            </script>
        </body>
        </html>
        """

def run_server(camera_manager, servo_controller, input_manager, port=8000):
    """Run the HTTP server with the camera stream."""
    class Handler(CameraStreamHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, camera_manager=camera_manager,
                            servo_controller=servo_controller,
                            input_manager=input_manager, **kwargs)

    server = HTTPServer(('', port), Handler)
    logger.info(f"Starting server on port {port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
        server.server_close()
        camera_manager.cleanup()
        servo_controller.cleanup()
        input_manager.cleanup()

if __name__ == '__main__':
    # Initialize components
    camera_manager = CameraManager()
    servo_controller = ServoController()
    input_manager = InputManager(servo_controller)

    # Connect to camera
    if not camera_manager.connect():
        logger.error("Failed to connect to camera")
        sys.exit(1)

    # Start input manager thread
    input_thread = threading.Thread(target=input_manager.run)
    input_thread.daemon = True
    input_thread.start()

    # Run the server
    run_server(camera_manager, servo_controller, input_manager) 