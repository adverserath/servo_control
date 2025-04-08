import cv2
import threading
import time
import os
from datetime import datetime
from config import RTSP_URL, SCREEN_WIDTH, SCREEN_HEIGHT

class CameraManager:
    def __init__(self):
        # Camera state
        self.connected = False
        self.frame = None
        self.frame_lock = threading.Lock()
        self.capture = None  # Store capture object for direct access
        
        # Create photos directory if it doesn't exist
        os.makedirs('photos', exist_ok=True)
        
        # Start the camera thread
        self.camera_thread = threading.Thread(target=self._rtsp_stream_thread, daemon=True)
        self.camera_thread.start()
    
    def _rtsp_stream_thread(self):
        """Background thread to capture frames from RTSP stream"""
        while True:
            try:
                self.capture = cv2.VideoCapture(RTSP_URL)
                if not self.capture.isOpened():
                    print("Cannot open RTSP stream")
                    time.sleep(5)  # Wait before retrying
                    continue
                    
                self.connected = True
                print("RTSP camera connected")
                
                while True:
                    ret, new_frame = self.capture.read()
                    if not ret:
                        print("Failed to get frame")
                        break
                    
                    with self.frame_lock:
                        # Convert to RGB for Pygame
                        self.frame = cv2.cvtColor(new_frame, cv2.COLOR_BGR2RGB)
                        self.frame = cv2.resize(self.frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
                    
                    time.sleep(0.033)  # ~30fps
                    
            except Exception as e:
                print(f"RTSP Error: {e}")
                
            self.connected = False
            if self.capture:
                self.capture.release()
                self.capture = None
            time.sleep(5)  # Wait before reconnecting
    
    def get_frame(self):
        """Get the current camera frame (thread-safe)"""
        with self.frame_lock:
            return self.frame
    
    def take_photo(self):
        """
        Take a full resolution photo and save it to the photos directory
        
        Returns:
            str: Path to the saved photo or None if failed
        """
        if not self.connected or self.capture is None:
            print("Cannot take photo: Camera not connected")
            return None
            
        try:
            # Set higher resolution for photo capture
            # Note: These settings might need to be adjusted based on your camera's capabilities
            # self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            # self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            
            # Take a photo at full resolution
            ret, frame = self.capture.read()
            if not ret:
                print("Failed to capture photo")
                return None
                
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"photo_{timestamp}.jpg"
            filepath = os.path.join("photos", filename)
            
            # Save the image in high quality
            cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            print(f"Photo saved to {filepath}")
            
            return filepath
            
        except Exception as e:
            print(f"Error taking photo: {e}")
            return None 