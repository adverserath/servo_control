import cv2
import threading
import time
import os
import platform
from config import SCREEN_WIDTH, SCREEN_HEIGHT
from dotenv import load_dotenv

load_dotenv()

class CameraManager:
    def __init__(self):
        self.rtsp_url = os.environ.get("RTSP_URL")
        if not self.rtsp_url:
            print("RTSP_URL not found in environment variables.")
            # Fallback or raise error?
        
        self.cap = None
        self.connected = False
        self.error = None
        self.frame = None
        self.frame_lock = threading.Lock()
        self.capture_dir = "captures"
        os.makedirs(self.capture_dir, exist_ok=True)
        
        # Recording state
        self.is_recording = False
        self.video_writer = None
        self.recording_filename = None
        self.recording_lock = threading.Lock()
        
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop)
        self.thread.daemon = True
        self.thread.start()
    
    def _connect(self):
        print(f"Attempting to connect to RTSP stream: {self.rtsp_url}")
        # Set environment variable for OpenCV to use TCP for RTSP
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        
        # Check if connection is established after a short delay
        time.sleep(2) # Give time for connection
        
        if self.cap.isOpened():
            self.connected = True
            self.error = None
            print("Successfully connected to RTSP stream.")
        else:
            self.connected = False
            self.error = "Failed to connect to RTSP stream."
            print(self.error)
            if self.cap: # Release if connection failed but object exists
                self.cap.release()
            self.cap = None
            
    def _capture_loop(self):
        retry_delay = 5 # seconds
        while self.running:
            if not self.connected or not self.cap or not self.cap.isOpened():
                self._connect()
                if not self.connected:
                    time.sleep(retry_delay)
                    continue # Retry connection
                    
            try:
                ret, frame = self.cap.read()
                if ret:
                    with self.frame_lock:
                        self.frame = frame
                    self.error = None # Clear error on successful read
                    
                    # Write frame if recording
                    with self.recording_lock:
                        if self.is_recording and self.video_writer:
                            self.video_writer.write(frame)
                else:
                    print("Failed to read frame from RTSP stream. Reconnecting...")
                    self.connected = False
                    if self.cap:
                        self.cap.release()
                    self.cap = None
                    time.sleep(retry_delay)
                    
            except Exception as e:
                self.error = f"Error in capture loop: {e}"
                print(self.error)
                self.connected = False
                if self.cap:
                    self.cap.release()
                self.cap = None
                time.sleep(retry_delay)
                
            time.sleep(0.01) # Small delay to prevent high CPU usage
            
    def get_frame(self):
        with self.frame_lock:
            return self.frame
            
    def capture_still(self):
        frame = self.get_frame()
        if frame is not None:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = os.path.join(self.capture_dir, f"capture_{timestamp}.jpg")
            try:
                cv2.imwrite(filename, frame)
                print(f"Image captured: {filename}")
                return True, filename
            except Exception as e:
                error_msg = f"Failed to save image: {e}"
                print(error_msg)
                return False, error_msg
        else:
            return False, "No frame available to capture."
            
    def start_recording(self):
        with self.recording_lock:
            if self.is_recording:
                return False, "Already recording."
            
            frame = self.get_frame()
            if frame is None:
                return False, "No frame available to start recording."

            timestamp = time.strftime("%Y%m%d-%H%M%S")
            self.recording_filename = os.path.join(self.capture_dir, f"video_{timestamp}.mp4")
            
            # Get frame dimensions
            height, width, _ = frame.shape
            
            # Define the codec and create VideoWriter object (using mp4v for MP4)
            # Adjust codec/extension as needed (e.g., 'XVID' for AVI)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
            # Use camera's FPS if available, otherwise default (e.g., 20)
            fps = self.cap.get(cv2.CAP_PROP_FPS) if self.cap else 20.0 
            if fps <= 0: # Handle case where FPS is not available or invalid
                fps = 20.0
                print(f"Warning: Could not get camera FPS, defaulting to {fps:.1f}")
                
            try:
                self.video_writer = cv2.VideoWriter(self.recording_filename, fourcc, fps, (width, height))
                if not self.video_writer.isOpened():
                     raise IOError(f"Could not open video writer for file: {self.recording_filename}")
                self.is_recording = True
                print(f"Started recording: {self.recording_filename}")
                return True, self.recording_filename
            except Exception as e:
                error_msg = f"Failed to start recording: {e}"
                print(error_msg)
                self.video_writer = None # Ensure writer is None on failure
                self.recording_filename = None
                return False, error_msg

    def stop_recording(self):
        with self.recording_lock:
            if not self.is_recording:
                return False, "Not currently recording."
            
            if self.video_writer:
                self.video_writer.release()
                print(f"Stopped recording: {self.recording_filename}")
                recorded_file = self.recording_filename
                self.video_writer = None
                self.recording_filename = None
                self.is_recording = False
                return True, recorded_file
            else:
                # Should not happen if is_recording is True, but handle defensively
                self.is_recording = False
                self.recording_filename = None
                return False, "Recording was active but writer was not found."

    def toggle_recording(self):
         with self.recording_lock:
             if self.is_recording:
                 return self.stop_recording()
             else:
                 return self.start_recording()
                 
    def get_status(self):
        with self.recording_lock:
            rec_status = {
                'is_recording': self.is_recording,
                'filename': self.recording_filename
            }
        return {
            'connected': self.connected,
            'camera_type': 'RTSP',
            'error': self.error,
            'recording_status': rec_status
        }

    def cleanup(self):
        print("Cleaning up camera manager...")
        self.running = False
        if self.is_recording:
            self.stop_recording()
        if self.thread.is_alive():
            self.thread.join()
        if self.cap:
            self.cap.release()
        print("Camera manager cleaned up.")

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
    
    def __del__(self):
        """Cleanup when the object is destroyed"""
        if self.camera:
            try:
                self.camera.stop()
            except:
                pass 