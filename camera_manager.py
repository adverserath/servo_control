import cv2
import threading
import time
import os
import platform
import gc # Import garbage collector
import subprocess
import numpy as np
from config import SCREEN_WIDTH, SCREEN_HEIGHT, FRAME_RATE
from dotenv import load_dotenv
from typing import Optional, Tuple

# Configure logging
import logging
logger = logging.getLogger(__name__)

IS_RASPBERRY_PI = (platform.system() == 'Linux' and 
                   os.path.exists('/proc/device-tree/model') and 
                   'raspberry pi' in open('/proc/device-tree/model', 'r').read().lower())

# DEBUG: Print initial detection status
logger.info(f"IS_RASPBERRY_PI = {IS_RASPBERRY_PI}")

if IS_RASPBERRY_PI:
    logger.info("Detected Raspberry Pi system.")
else:
    logger.info("Not detected as Raspberry Pi system (or /proc/device-tree/model check failed).")

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
        
        # Libcamera process
        self.libcamera_process = None
        
    def connect(self) -> bool:
        """Establish connection to the Raspberry Pi camera."""
        try:
            if self.camera is not None:
                self.disconnect()
            
            if not IS_RASPBERRY_PI:
                self.connection_error = "Not running on a Raspberry Pi"
                return False
            
            # Check if libcamera-vid is available
            try:
                subprocess.run(['which', 'libcamera-vid'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                logger.info("libcamera-vid is available")
            except subprocess.CalledProcessError:
                logger.error("libcamera-vid is not available")
                self.connection_error = "libcamera-vid is not available"
                return False
            
            # Start libcamera-vid process
            self.libcamera_process = subprocess.Popen(
                [
                    'libcamera-vid',
                    '--width', str(self.frame_width),
                    '--height', str(self.frame_height),
                    '--framerate', str(self.fps),
                    '--codec', 'h264',
                    '--inline',  # Enable h264 inline headers
                    '--listen',  # Enable TCP connection
                    '-t', '0',  # Run indefinitely
                    '-o', 'tcp://127.0.0.1:8888'  # Output to TCP
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for the process to start
            time.sleep(2)
            
            # Check if the process is still running
            if self.libcamera_process.poll() is not None:
                error = self.libcamera_process.stderr.read().decode()
                logger.error(f"libcamera-vid failed to start: {error}")
                self.connection_error = f"libcamera-vid failed to start: {error}"
                return False
            
            # Create OpenCV VideoCapture object to read from TCP
            self.camera = cv2.VideoCapture('tcp://127.0.0.1:8888')
            
            if not self.camera.isOpened():
                logger.error("Failed to open TCP connection to libcamera-vid")
                self.connection_error = "Failed to open TCP connection to libcamera-vid"
                return False
            
            # Start capture thread
            self.is_running = True
            self.capture_thread = threading.Thread(target=self._capture_loop)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            
            self.is_connected = True
            self.connection_error = None
            logger.info("Successfully connected to Raspberry Pi camera using libcamera-vid")
            return True
            
        except Exception as e:
            self.connection_error = str(e)
            self.is_connected = False
            logger.error(f"Failed to connect to camera: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the camera and clean up resources."""
        self.is_running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=1.0)
        
        if self.camera is not None:
            try:
                self.camera.release()
            except Exception as e:
                logger.error(f"Error releasing camera: {e}")
            finally:
                self.camera = None
        
        if self.libcamera_process is not None:
            try:
                self.libcamera_process.terminate()
                self.libcamera_process.wait(timeout=5)
            except Exception as e:
                logger.error(f"Error terminating libcamera-vid process: {e}")
                try:
                    self.libcamera_process.kill()
                except:
                    pass
            finally:
                self.libcamera_process = None
        
        self.is_connected = False
        self.current_frame = None
    
    def _capture_loop(self):
        """Background thread for continuous frame capture."""
        logger.info("Starting capture loop")
        while self.is_running:
            try:
                if self.camera is None:
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
                    logger.error("Failed to read frame")
                    time.sleep(0.1)
                    continue
                
                # Update frame
                with self.frame_lock:
                    self.current_frame = frame
                    self.last_frame_time = current_time
                    self.connection_error = None
                    logger.debug("Frame updated successfully")
                
            except Exception as e:
                self.connection_error = str(e)
                logger.error(f"Error in capture loop: {e}")
                time.sleep(0.1)
    
    def get_frame(self) -> Tuple[bool, Optional[bytes]]:
        """
        Get the most recent frame as JPEG bytes.
        Returns: (success, frame_bytes)
        """
        try:
            with self.frame_lock:
                if self.current_frame is None:
                    logger.debug("No frame available")
                    return False, None
                
                # Convert frame to JPEG
                ret, buffer = cv2.imencode('.jpg', self.current_frame)
                if not ret:
                    logger.debug("Failed to encode frame as JPEG")
                    return False, None
                
                logger.debug("Frame captured and encoded successfully")
                return True, buffer.tobytes()
                
        except Exception as e:
            self.connection_error = str(e)
            logger.error(f"Error in get_frame: {e}")
            return False, None
    
    def get_status(self) -> dict:
        """Get the current status of the camera."""
        return {
            'connected': self.is_connected,
            'error': self.connection_error,
            'frame_width': self.frame_width,
            'frame_height': self.frame_height,
            'fps': self.fps,
            'camera_type': 'libcamera-vid'
        }

    def _cleanup_camera_object(self):
         """Safely close/release the current camera object"""
         if self.camera:
             camera_type_to_clean = "OpenCV"
             logger.info(f"Cleaning up {camera_type_to_clean} object...")
             try:
                 self.camera.release()
                 logger.info("Camera released.")
             except Exception as e:
                 logger.error(f"Error during camera object cleanup: {e}")
             
             self.camera = None # Set to None regardless of cleanup success
             # --- Explicit Garbage Collection --- 
             logger.info("Running garbage collection...")
             gc.collect()
             # --- Add Delay Here --- 
             logger.info("Waiting briefly after camera cleanup...")
             time.sleep(1.5) # Give 1.5 seconds for resource release
         else:
             pass

    def cleanup(self):
        """Clean up all resources"""
        logger.info("Cleaning up camera manager...")
        self.is_running = False
        if hasattr(self, 'capture_thread') and self.capture_thread:
            logger.info("Waiting for capture thread to finish...")
            self.capture_thread.join(timeout=2.0) # Wait for thread with timeout
            if self.capture_thread.is_alive():
                 logger.warning("Capture thread did not terminate gracefully.")
        # Clean up camera object itself
        self._cleanup_camera_object()
        logger.info("Camera manager cleaned up.")

    # Remove old __del__ if it exists, cleanup() is preferred
    # def __del__(self): ... 