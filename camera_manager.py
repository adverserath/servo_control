import cv2
import threading
import time
import os
import platform
import gc # Import garbage collector
from config import SCREEN_WIDTH, SCREEN_HEIGHT, FRAME_RATE
from dotenv import load_dotenv
from typing import Optional, Tuple
import numpy as np

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
        
        # Initialize capture thread
        self.capture_thread = None
        
    def connect(self) -> bool:
        """Establish connection to the Raspberry Pi camera."""
        try:
            if self.camera is not None:
                self.disconnect()
            
            if not IS_RASPBERRY_PI:
                self.connection_error = "Not running on a Raspberry Pi"
                return False
            
            # Try to use PiCamera2 if available
            if picamera2_available:
                # Create Picamera2 object
                self.camera = Picamera2()
                
                # Configure camera
                config = self.camera.create_preview_configuration(
                    main={"size": (self.frame_width, self.frame_height), "format": "RGB888"},
                    lores={"size": (320, 240), "format": "YUV420"}
                )
                self.camera.configure(config)
                
                # Start camera
                self.camera.start()
                
                # Start capture thread
                self.is_running = True
                self.capture_thread = threading.Thread(target=self._capture_loop)
                self.capture_thread.daemon = True
                self.capture_thread.start()
                
                self.is_connected = True
                self.connection_error = None
                print("Successfully connected to Raspberry Pi camera using PiCamera2")
                return True
            else:
                # Fallback to OpenCV with Pi's camera device
                print("PiCamera2 not available, falling back to OpenCV with Pi's camera device")
                
                # Try different video devices
                video_devices = [0, 1, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 23, 31]
                for device_id in video_devices:
                    print(f"Trying video device /dev/video{device_id}")
                    self.camera = cv2.VideoCapture(device_id)
                    
                    if self.camera.isOpened():
                        # Test if we can read a frame
                        ret, frame = self.camera.read()
                        if ret:
                            print(f"Successfully connected to video device /dev/video{device_id}")
                            
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
                            print(f"Successfully connected to Raspberry Pi camera using OpenCV with device /dev/video{device_id}")
                            return True
                        else:
                            print(f"Failed to read frame from video device /dev/video{device_id}")
                            self.camera.release()
                    else:
                        print(f"Failed to open video device /dev/video{device_id}")
                
                # If no camera is available, create a dummy camera
                print("No camera available, creating dummy camera")
                self.camera = None
                self.is_running = True
                self.capture_thread = threading.Thread(target=self._dummy_capture_loop)
                self.capture_thread.daemon = True
                self.capture_thread.start()
                
                self.is_connected = True
                self.connection_error = "Using dummy camera (no real camera available)"
                print("Successfully created dummy camera")
                return True
            
        except Exception as e:
            self.connection_error = str(e)
            self.is_connected = False
            print(f"Failed to connect to camera: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the camera and clean up resources."""
        self.is_running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=1.0)
        
        if self.camera is not None:
            try:
                if picamera2_available and isinstance(self.camera, Picamera2):
                    self.camera.stop()
                else:
                    self.camera.release()
            except Exception as e:
                print(f"Error stopping/releasing camera: {e}")
            finally:
                self.camera = None
        
        self.is_connected = False
        self.current_frame = None
    
    def _capture_loop(self):
        """Background thread for continuous frame capture."""
        print("DEBUG: Starting capture loop")
        while self.is_running:
            try:
                if self.camera is None:
                    print("DEBUG: Camera is None, waiting...")
                    time.sleep(0.1)
                    continue
                
                # Check if it's time for next frame
                current_time = time.time()
                if current_time - self.last_frame_time < self.frame_interval:
                    time.sleep(0.001)  # Small sleep to prevent CPU hogging
                    continue
                
                # Capture frame
                if picamera2_available and isinstance(self.camera, Picamera2):
                    print("DEBUG: Capturing frame with PiCamera2")
                    frame = self.camera.capture_array()
                else:
                    # OpenCV
                    print("DEBUG: Capturing frame with OpenCV")
                    ret, frame = self.camera.read()
                    if not ret:
                        self.connection_error = "Failed to read frame"
                        print("DEBUG: Failed to read frame with OpenCV")
                        time.sleep(0.1)
                        continue
                
                # Update frame
                with self.frame_lock:
                    self.current_frame = frame
                    self.last_frame_time = current_time
                    self.connection_error = None
                    print("DEBUG: Frame updated successfully")
                
            except Exception as e:
                self.connection_error = str(e)
                print(f"DEBUG: Error in capture loop: {e}")
                time.sleep(0.1)
    
    def _dummy_capture_loop(self):
        """Background thread for generating dummy frames."""
        print("DEBUG: Starting dummy capture loop")
        
        while self.is_running:
            try:
                # Check if it's time for next frame
                current_time = time.time()
                if current_time - self.last_frame_time < self.frame_interval:
                    time.sleep(0.001)  # Small sleep to prevent CPU hogging
                    continue
                
                # Create a dummy frame (blue background with text)
                frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
                frame[:, :, 0] = 255  # Blue channel
                
                # Add text to the frame
                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(frame, "No Camera Available", (50, 50), font, 1, (255, 255, 255), 2)
                cv2.putText(frame, "Using Dummy Camera", (50, 100), font, 1, (255, 255, 255), 2)
                
                # Update frame
                with self.frame_lock:
                    self.current_frame = frame
                    self.last_frame_time = current_time
                    self.connection_error = "Using dummy camera (no real camera available)"
                    print("DEBUG: Dummy frame updated successfully")
                
            except Exception as e:
                self.connection_error = str(e)
                print(f"DEBUG: Error in dummy capture loop: {e}")
                time.sleep(0.1)
    
    def get_frame(self) -> Tuple[bool, Optional[bytes]]:
        """
        Get the most recent frame as JPEG bytes.
        Returns: (success, frame_bytes)
        """
        try:
            with self.frame_lock:
                if self.current_frame is None:
                    print("DEBUG: No frame available")
                    return False, None
                
                # Convert frame to JPEG
                ret, buffer = cv2.imencode('.jpg', self.current_frame)
                if not ret:
                    print("DEBUG: Failed to encode frame as JPEG")
                    return False, None
                
                print("DEBUG: Frame captured and encoded successfully")
                return True, buffer.tobytes()
                
        except Exception as e:
            self.connection_error = str(e)
            print(f"DEBUG: Error in get_frame: {e}")
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
             if picamera2_available and isinstance(self.camera, Picamera2):
                 camera_type_to_clean = "PiCamera2"
                 print(f"Cleaning up {camera_type_to_clean} object...")
                 try:
                     self.camera.stop()
                     print("Camera stopped.")
                 except Exception as e:
                     print(f"Error during camera object cleanup: {e}")
             else:
                 camera_type_to_clean = "OpenCV"
                 print(f"Cleaning up {camera_type_to_clean} object...")
                 try:
                     self.camera.release()
                     print("Camera released.")
                 except Exception as e:
                     print(f"Error during camera object cleanup: {e}")
             
             self.camera = None # Set to None regardless of cleanup success
             # --- Explicit Garbage Collection --- 
             print("Running garbage collection...")
             gc.collect()
             # --- Add Delay Here --- 
             print("Waiting briefly after camera cleanup...")
             time.sleep(1.5) # Give 1.5 seconds for resource release
         else:
             pass

    def cleanup(self):
        """Clean up all resources"""
        print("Cleaning up camera manager...")
        self.is_running = False
        if hasattr(self, 'capture_thread') and self.capture_thread:
            print("Waiting for capture thread to finish...")
            self.capture_thread.join(timeout=2.0) # Wait for thread with timeout
            if self.capture_thread.is_alive():
                 print("Warning: Capture thread did not terminate gracefully.")
        # Clean up camera object itself
        self._cleanup_camera_object()
        print("Camera manager cleaned up.")

    # Remove old __del__ if it exists, cleanup() is preferred
    # def __del__(self): ... 