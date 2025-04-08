import cv2
import threading
import time
import os
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
from config import SCREEN_WIDTH, SCREEN_HEIGHT

class CameraManager:
    def __init__(self):
        # Camera state
        self.connected = False
        self.frame = None
        self.frame_lock = threading.Lock()
        self.camera = None
        
        # Create directory for still images if it doesn't exist
        os.makedirs('captures', exist_ok=True)
        
        # Start the camera thread
        self.camera_thread = threading.Thread(target=self._camera_thread, daemon=True)
        self.camera_thread.start()
    
    def _camera_thread(self):
        """Background thread to capture frames from Pi camera"""
        while True:
            try:
                if self.camera is None:
                    # Initialize the camera
                    self.camera = Picamera2()
                    
                    # Configure the camera
                    config = self.camera.create_preview_configuration(
                        main={"size": (SCREEN_WIDTH, SCREEN_HEIGHT), "format": "RGB888"}
                    )
                    self.camera.configure(config)
                    self.camera.start()
                    
                    self.connected = True
                    print("Pi camera connected")
                
                while self.connected:
                    # Capture frame
                    frame = self.camera.capture_array()
                    
                    with self.frame_lock:
                        self.frame = frame
                    
                    time.sleep(0.033)  # ~30fps
                    
            except Exception as e:
                print(f"Camera Error: {e}")
                self.connected = False
                if self.camera:
                    try:
                        self.camera.stop()
                    except:
                        pass
                    self.camera = None
                time.sleep(5)  # Wait before reconnecting
    
    def get_frame(self):
        """Get the current camera frame (thread-safe)"""
        with self.frame_lock:
            return self.frame
    
    def capture_still(self, filename=None):
        """Capture a still image from the camera"""
        if not self.connected or self.camera is None:
            return False, "Camera not connected"
        
        try:
            if filename is None:
                # Generate filename with timestamp
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filename = f"captures/image_{timestamp}.jpg"
            
            # Ensure the captures directory exists
            os.makedirs('captures', exist_ok=True)
            
            # Capture still image
            self.camera.capture_file(filename, use_video_port=False)
            return True, filename
            
        except Exception as e:
            return False, str(e)
    
    def __del__(self):
        """Cleanup when the object is destroyed"""
        if self.camera:
            try:
                self.camera.stop()
            except:
                pass 