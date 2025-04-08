import cv2
import threading
import time
import os
import platform
from config import SCREEN_WIDTH, SCREEN_HEIGHT

class CameraManager:
    def __init__(self):
        # Camera state
        self.connected = False
        self.frame = None
        self.frame_lock = threading.Lock()
        self.camera = None
        self.error_message = None
        self.camera_type = "Unknown"
        
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
                    # Check if we're on a Raspberry Pi
                    if platform.system() == 'Linux' and os.path.exists('/proc/device-tree/model'):
                        with open('/proc/device-tree/model', 'r') as f:
                            model = f.read().lower()
                            if 'raspberry pi' in model:
                                self.camera_type = "Raspberry Pi Camera"
                                self._init_pi_camera()
                            else:
                                self.error_message = "Not running on a Raspberry Pi"
                                self.connected = False
                                time.sleep(5)
                    else:
                        self.camera_type = "Webcam"
                        self._init_webcam()
                
                if self.connected and self.camera is not None:
                    # Capture frame
                    frame = self._capture_frame()
                    if frame is not None:
                        with self.frame_lock:
                            self.frame = frame
                
                time.sleep(0.033)  # ~30fps
                    
            except Exception as e:
                print(f"Camera Error: {e}")
                self.error_message = str(e)
                self.connected = False
                if self.camera:
                    try:
                        self.camera.stop()
                    except:
                        pass
                    self.camera = None
                time.sleep(5)  # Wait before reconnecting
    
    def _init_pi_camera(self):
        """Initialize the Raspberry Pi camera"""
        try:
            from picamera2 import Picamera2
            
            # Initialize the camera
            self.camera = Picamera2()
            
            # Configure the camera
            config = self.camera.create_preview_configuration(
                main={"size": (SCREEN_WIDTH, SCREEN_HEIGHT), "format": "RGB888"}
            )
            self.camera.configure(config)
            self.camera.start()
            
            self.connected = True
            self.error_message = None
            print("Pi camera connected")
            
        except ImportError:
            self.error_message = "picamera2 module not installed"
            self.connected = False
        except Exception as e:
            self.error_message = f"Pi camera error: {str(e)}"
            self.connected = False
    
    def _init_webcam(self):
        """Initialize a standard webcam as fallback"""
        try:
            # Try to open the first available camera
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                self.error_message = "Could not open webcam"
                self.connected = False
                return
            
            self.connected = True
            self.error_message = None
            print("Webcam connected")
            
        except Exception as e:
            self.error_message = f"Webcam error: {str(e)}"
            self.connected = False
    
    def _capture_frame(self):
        """Capture a frame from the active camera"""
        try:
            if self.camera_type == "Raspberry Pi Camera":
                return self.camera.capture_array()
            else:
                ret, frame = self.camera.read()
                if ret:
                    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                return None
        except Exception as e:
            print(f"Frame capture error: {e}")
            return None
    
    def get_frame(self):
        """Get the current camera frame (thread-safe)"""
        with self.frame_lock:
            return self.frame
    
    def get_status(self):
        """Get the current camera status"""
        return {
            'connected': self.connected,
            'camera_type': self.camera_type,
            'error': self.error_message
        }
    
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
            
            # Capture still image based on camera type
            if self.camera_type == "Raspberry Pi Camera":
                self.camera.capture_file(filename, use_video_port=False)
            else:
                ret, frame = self.camera.read()
                if ret:
                    cv2.imwrite(filename, frame)
                else:
                    return False, "Failed to capture frame"
                
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