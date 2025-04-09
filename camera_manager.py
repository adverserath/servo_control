import cv2
import threading
import time
import os
import platform
import gc # Import garbage collector
from config import SCREEN_WIDTH, SCREEN_HEIGHT, FRAME_RATE
from dotenv import load_dotenv
from typing import Optional, Tuple

# Try importing picamera2, handle failure gracefully
try:
    from picamera2 import Picamera2
    # Import encoder and quality enums for recording
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import FileOutput # For potentially smoother recording
    from libcamera import controls, Transform, StreamFormat # For controls and formats
    from picamera2.utils import Quality # Enum for recording quality
    picamera2_available = True
    print("DEBUG: picamera2 imported successfully.") # DEBUG
except ImportError:
    picamera2_available = False
    print("DEBUG: picamera2 import FAILED (ImportError).") # DEBUG
except Exception as e:
    picamera2_available = False
    print(f"DEBUG: picamera2 import FAILED (Other Exception: {e}).") # DEBUG
    # Optionally print traceback here too for import errors
    # import traceback
    # traceback.print_exc()

IS_RASPBERRY_PI = (platform.system() == 'Linux' and 
                   os.path.exists('/proc/device-tree/model') and 
                   'raspberry pi' in open('/proc/device-tree/model', 'r').read().lower())

# DEBUG: Print initial detection status
print(f"DEBUG: IS_RASPBERRY_PI = {IS_RASPBERRY_PI}")
print(f"DEBUG: picamera2_available = {picamera2_available}")

if IS_RASPBERRY_PI:
    print("Info: Detected Raspberry Pi system.")
else:
    print("Info: Not detected as Raspberry Pi system (or /proc/device-tree/model check failed).")

class CameraManager:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Camera settings
        self.rtsp_url = os.getenv('RTSP_URL')
        self.frame_width = 640
        self.frame_height = 480
        self.fps = 30
        
        # Camera state
        self.camera = None
        self.is_running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.last_frame_time = 0
        self.frame_interval = 1.0 / self.fps
        
        # Connection state
        self.is_connected = False
        self.connection_error = None
        
    def connect(self) -> bool:
        """Establish connection to the RTSP camera."""
        try:
            if self.camera is not None:
                self.disconnect()
            
            # Configure OpenCV for RTSP
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            
            # Create VideoCapture object
            self.camera = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            
            if not self.camera.isOpened():
                self.connection_error = "Failed to open camera connection"
                return False
            
            # Set camera properties
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Start capture thread
            self.is_running = True
            self.capture_thread = threading.Thread(target=self._capture_loop)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            
            self.is_connected = True
            self.connection_error = None
            return True
            
        except Exception as e:
            self.connection_error = str(e)
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from the camera and clean up resources."""
        self.is_running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=1.0)
        
        if self.camera is not None:
            self.camera.release()
            self.camera = None
        
        self.is_connected = False
        self.current_frame = None
    
    def _capture_loop(self):
        """Background thread for continuous frame capture."""
        while self.is_running:
            try:
                if self.camera is None or not self.camera.isOpened():
                    time.sleep(0.1)
                    continue
                
                # Check if it's time for next frame
                current_time = time.time()
                if current_time - self.last_frame_time < self.frame_interval:
                    time.sleep(0.001)  # Small sleep to prevent CPU hogging
                    continue
                
                # Capture frame
                ret, frame = self.camera.read()
                if not ret:
                    self.connection_error = "Failed to read frame"
                    time.sleep(0.1)
                    continue
                
                # Update frame
                with self.frame_lock:
                    self.current_frame = frame
                    self.last_frame_time = current_time
                    self.connection_error = None
                
            except Exception as e:
                self.connection_error = str(e)
                time.sleep(0.1)
    
    def get_frame(self) -> Tuple[bool, Optional[bytes]]:
        """
        Get the most recent frame as JPEG bytes.
        Returns: (success, frame_bytes)
        """
        try:
            with self.frame_lock:
                if self.current_frame is None:
                    return False, None
                
                # Convert frame to JPEG
                ret, buffer = cv2.imencode('.jpg', self.current_frame)
                if not ret:
                    return False, None
                
                return True, buffer.tobytes()
                
        except Exception as e:
            self.connection_error = str(e)
            return False, None
    
    def get_status(self) -> dict:
        """Get the current status of the camera."""
        return {
            'connected': self.is_connected,
            'error': self.connection_error,
            'frame_width': self.frame_width,
            'frame_height': self.frame_height,
            'fps': self.fps
        }

    def _cleanup_camera_object(self):
         """Safely close/release the current camera object"""
         if self.camera:
             camera_type_to_clean = "RTSP"
             print(f"Cleaning up {camera_type_to_clean} object...")
             try:
                 self.camera.release()
                 print("RTSP camera released.")
             except Exception as e:
                 print(f"Error during camera object cleanup: {e}")
             finally:
                 self.camera = None # Set to None regardless of cleanup success
                 # --- Explicit Garbage Collection --- 
                 print("Running garbage collection...")
                 gc.collect()
                 # --- Add Delay Here --- 
                 print("Waiting briefly after camera cleanup...")
                 time.sleep(1.5) # Give 1.5 seconds for resource release
         else:
             # If self.camera was already None, maybe still collect?
             # print("Running garbage collection (camera was None)...")
             # gc.collect()
             pass

    def cleanup(self):
        """Clean up all resources"""
        print("Cleaning up camera manager...")
        self.is_running = False
        if self.capture_thread:
            print("Waiting for capture thread to finish...")
            self.capture_thread.join(timeout=2.0) # Wait for thread with timeout
            if self.capture_thread.is_alive():
                 print("Warning: Capture thread did not terminate gracefully.")
        # Clean up camera object itself
        self._cleanup_camera_object()
        # Optional: Add gc.collect() here too?
        # gc.collect()
        print("Camera manager cleaned up.")

    # Remove old __del__ if it exists, cleanup() is preferred
    # def __del__(self): ... 