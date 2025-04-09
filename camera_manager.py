import cv2
import threading
import time
import os
import platform
import gc # Import garbage collector
from config import SCREEN_WIDTH, SCREEN_HEIGHT, FRAME_RATE
# Remove dotenv import if not used elsewhere
# from dotenv import load_dotenv
# load_dotenv()

# Try importing picamera2, handle failure gracefully
try:
    from picamera2 import Picamera2
    picamera2_available = True
except ImportError:
    picamera2_available = False
    print("Info: picamera2 module not found. Pi Camera support disabled.")
except Exception as e:
    picamera2_available = False
    print(f"Warning: Error importing picamera2: {e}. Pi Camera support disabled.")

IS_RASPBERRY_PI = (platform.system() == 'Linux' and 
                   os.path.exists('/proc/device-tree/model') and 
                   'raspberry pi' in open('/proc/device-tree/model', 'r').read().lower())

if IS_RASPBERRY_PI:
    print("Info: Detected Raspberry Pi system.")
else:
    print("Info: Not detected as Raspberry Pi system (or /proc/device-tree/model check failed).")

class CameraManager:
    def __init__(self):
        # Camera state
        self.connected = False
        self.error = None
        self.frame = None
        self.frame_lock = threading.Lock()
        self.camera = None
        self.camera_type = "Unknown"
        
        # Capture/Record settings
        self.capture_dir = "captures"
        os.makedirs(self.capture_dir, exist_ok=True)
        self.is_recording = False
        self.video_writer = None
        self.recording_filename = None
        self.recording_lock = threading.Lock()
        
        # Start the camera thread (handles PiCam/Webcam)
        self.running = True
        self.thread = threading.Thread(target=self._camera_thread)
        self.thread.daemon = True
        self.thread.start()
        
    def _camera_thread(self):
        """Background thread to initialize camera ONCE and then capture frames"""
        print("Camera thread started. Attempting initialization...")
        
        # --- Determine Camera Type and Initialize ONCE --- 
        initialization_success = False
        try:
            use_pi_camera = IS_RASPBERRY_PI and picamera2_available
            if use_pi_camera:
                print("Attempting Pi Camera initialization...")
                self._init_pi_camera() # This sets self.connected, self.error
            else:
                if not IS_RASPBERRY_PI:
                     print("Not on Raspberry Pi, trying webcam...")
                elif not picamera2_available:
                     print("Picamera2 library not available/functional, trying webcam...")
                self._init_webcam() # This sets self.connected, self.error
            
            initialization_success = self.connected
        except Exception as e:
             # Catch errors during the init selection itself
             print(f"Critical error during camera type selection/init call: {e}")
             self.error = str(e)
             self.connected = False
             initialization_success = False
        # --- End Initialization Attempt ---

        if not initialization_success:
            print(f"Camera initialization failed: {self.error}. Camera thread exiting.")
            self._cleanup_camera_object() # Clean up if init failed
            return # Exit the thread

        print(f"Camera thread: {self.camera_type} initialized successfully. Entering capture loop.")
        
        # --- Capture Loop (Only runs if init succeeded) ---
        while self.running:
            if not self.connected or self.camera is None:
                # Should not happen if init succeeded, but safety check
                print("Camera became disconnected unexpectedly. Camera thread exiting.")
                self.error = "Camera disconnected unexpectedly."
                break # Exit capture loop
                
            try:
                if self.connected and self.camera is not None:
                    frame_data = self._capture_frame()
                    if frame_data is not None:
                        # --- Store the captured frame (likely RGB from PiCam) --- 
                        with self.frame_lock:
                            self.frame = frame_data 
                        self.error = None # Clear error on successful frame
                        
                        # Write frame if recording
                        with self.recording_lock:
                            if self.is_recording and self.video_writer:
                                # Ensure frame is in BGR format for VideoWriter
                                if self.camera_type == "Raspberry Pi Camera":
                                    # Picamera2 configured for RGB888, convert to BGR for saving
                                    # print("Converting frame to BGR for recording...") # Debug print
                                    try:
                                        bgr_frame = cv2.cvtColor(frame_data, cv2.COLOR_RGB2BGR)
                                        self.video_writer.write(bgr_frame)
                                    except cv2.error as cv_err:
                                        print(f"OpenCV error during BGR conversion for recording: {cv_err}")
                                        # Optionally stop recording or handle error
                                else: # Webcam likely BGR already from OpenCV
                                    self.video_writer.write(frame_data)
                    else:
                         # Failed to capture frame - exit loop
                         print(f"Failed to capture frame using {self.camera_type}. Camera thread exiting.")
                         self.error = "Failed to capture frame."
                         break # Exit capture loop
                
                # Frame rate handled by sleep
                time.sleep(max(0.001, 1.0 / FRAME_RATE)) 
                    
            except Exception as e:
                print(f"Critical Camera Error during capture: {e}")
                import traceback
                traceback.print_exc()
                self.error = str(e)
                break # Exit capture loop on error
        # --- End Capture Loop ---
        
        print("Camera thread loop finished. Cleaning up...")
        self._cleanup_camera_object() # Ensure cleanup when thread exits
        self.connected = False # Mark as disconnected
        print("Camera thread finished cleanup.")

    def _init_pi_camera(self):
        """Initialize the Raspberry Pi camera using picamera2"""
        if not picamera2_available:
            self.error = "picamera2 module not available."
            self.connected = False
            return
        print("Initializing Pi Camera (picamera2)...")
        try:
            self._cleanup_camera_object() # Ensure any previous instance is closed
            self.camera = Picamera2()
            
            # --- Use Preview Configuration with Size --- 
            print(f"Attempting preview configuration with size {SCREEN_WIDTH}x{SCREEN_HEIGHT}...")
            # Specify main stream size and potentially format (e.g., RGB888)
            config = self.camera.create_preview_configuration(
                main={"size": (SCREEN_WIDTH, SCREEN_HEIGHT), "format": "RGB888"} 
                # Add other streams if needed, e.g., lores for low-res stream
                # lores={"size": (320, 240)}, display="lores"
            )
            print(f"Configuration created: {config}") # Print the config dict
            # --- End Preview Configuration ---
            
            # Apply the configuration
            print("Configuring Pi Camera...")
            self.camera.configure(config)
            print("Configuration applied.")

            # Optional: Add transformations AFTER configure/start if needed
            # self.camera.options['transform'] = libcamera.Transform(hflip=1, vflip=1) # Old method, likely wrong
            # New method (preferred): Use controls AFTER start()
            # controls = {"hflip": 0, "vflip": 0} # 0=False, 1=True
            # self.camera.set_controls(controls)
            
            print("Starting Pi Camera...")
            self.camera.start()
            print("Pi Camera started.")

            # Optional: Apply controls like flip *after* starting
            # controls = {"hflip": 0, "vflip": 0} # Example: No flip
            # self.camera.set_controls(controls)
            # print("Applied controls (flip/rotate).")
            
            self.connected = True
            self.error = None
            self.camera_type = "Raspberry Pi Camera"
            print("Pi camera connected successfully.")
            
        except Exception as e:
            self.error = f"Pi camera initialization error: {str(e)}"
            print(self.error)
            import traceback
            traceback.print_exc() # Print full traceback for debugging
            self.connected = False
            self._cleanup_camera_object() # Ensure cleanup on failure

    def _init_webcam(self):
        """Initialize a standard webcam using OpenCV"""
        print("Initializing Webcam (OpenCV) index 0...")
        try:
            self.camera = cv2.VideoCapture(0) 
            if not self.camera.isOpened():
                # Try index 1 if 0 fails
                print("Webcam index 0 failed, trying index 1...")
                self.camera.release() # Release the failed attempt
                self.camera = cv2.VideoCapture(1)
                if not self.camera.isOpened():
                     raise IOError("Could not open webcam index 0 or 1")
                else:
                     print("Using Webcam index 1.")
            else:
                print("Using Webcam index 0.")
            
            # Give the camera a moment to initialize after opening
            print("Waiting briefly for webcam to initialize...")
            time.sleep(1.0) 
            
            # Try reading a test frame immediately after init
            test_ret, _ = self.camera.read()
            if not test_ret:
                 # If read fails immediately, likely permissions or device issue
                 raise IOError("Webcam opened but failed to read initial frame. Check permissions/device.")
            else:
                 print("Successfully read initial test frame from webcam.")
                 
            # Set desired resolution (optional, might not be supported by all webcams)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, SCREEN_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, SCREEN_HEIGHT)
            
            # Check if resolution was set (optional)
            # actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            # actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            # print(f"Webcam resolution set to: {actual_width}x{actual_height}")
            
            self.connected = True
            self.error = None
            self.camera_type = "Webcam"
            print("Webcam initialization successful.")
            
        except Exception as e:
            self.error = f"Webcam initialization error: {str(e)}"
            print(self.error)
            self.connected = False
            if self.camera: self.camera.release()
            self.camera = None

    def _capture_frame(self):
        """Capture a single frame from the active camera"""
        if not self.connected or self.camera is None:
            return None
        try:
            if self.camera_type == "Raspberry Pi Camera":
                # Capture frame from picamera2 (already RGB)
                frame = self.camera.capture_array()
                return frame
            elif self.camera_type == "Webcam":
                # Capture frame from OpenCV VideoCapture
                ret, frame = self.camera.read() # Reads in BGR format
                if ret:
                    return frame # Return BGR frame directly
                else:
                    print("Webcam read() failed.")
                    return None
            else:
                 return None # Should not happen
        except Exception as e:
            print(f"Frame capture error: {e}")
            self.error = f"Frame capture error: {e}" # Store error
            self.connected = False # Assume connection lost on capture error
            return None
            
    def get_frame(self):
        """Get the current camera frame (RGB format preferred for display)"""
        with self.frame_lock:
            if self.frame is None:
                return None
            # Ensure the frame is in RGB for consistency if needed elsewhere
            # Currently, PiCam is RGB, Webcam is BGR. Decide on standard.
            # Let's return raw frame for now, convert later if needed.
            return self.frame.copy() # Return a copy
            
    def capture_still(self):
        """Capture a still image (saves as JPG)"""
        frame_data = self.get_frame() # Gets a copy
        if frame_data is not None:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = os.path.join(self.capture_dir, f"capture_{timestamp}.jpg")
            try:
                # OpenCV imwrite expects BGR format.
                if self.camera_type == "Raspberry Pi Camera":
                    # Convert RGB frame from PiCam to BGR for saving
                    save_frame = cv2.cvtColor(frame_data, cv2.COLOR_RGB2BGR)
                else: # Webcam frame is already BGR
                    save_frame = frame_data
                    
                cv2.imwrite(filename, save_frame)
                print(f"Image captured: {filename}")
                return True, filename
            except Exception as e:
                error_msg = f"Failed to save image: {e}"
                print(error_msg)
                return False, error_msg
        else:
            return False, "No frame available to capture."
            
    def start_recording(self):
        """Start recording video (saves as MP4)"""
        with self.recording_lock:
            if self.is_recording:
                return False, "Already recording."
            
            # Use the raw frame from get_frame() to get dimensions
            frame_data = self.get_frame()
            if frame_data is None:
                return False, "No frame available to start recording."

            timestamp = time.strftime("%Y%m%d-%H%M%S")
            self.recording_filename = os.path.join(self.capture_dir, f"video_{timestamp}.mp4")
            
            # Get frame dimensions (height, width)
            height, width, _ = frame_data.shape
            
            # Define the codec and create VideoWriter object (using mp4v for MP4)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
            
            # Use FRAME_RATE from config as FPS
            fps = float(FRAME_RATE)
            print(f"Starting recording at {fps:.1f} FPS, dimensions {width}x{height}")
            
            try:
                # VideoWriter expects (width, height)
                self.video_writer = cv2.VideoWriter(self.recording_filename, fourcc, fps, (width, height))
                if not self.video_writer.isOpened():
                     raise IOError(f"Could not open video writer for file: {self.recording_filename}")
                self.is_recording = True
                print(f"Started recording: {self.recording_filename}")
                return True, self.recording_filename
            except Exception as e:
                error_msg = f"Failed to start recording: {e}"
                print(error_msg)
                self.video_writer = None
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
        """Get the current status including recording state"""
        with self.recording_lock:
            rec_status = {
                'is_recording': self.is_recording,
                'filename': self.recording_filename
            }
        # Ensure error reflects current state
        current_error = self.error 
        return {
            'connected': self.connected,
            'camera_type': self.camera_type if self.connected else 'Unknown',
            'error': current_error,
            'recording_status': rec_status
        }

    def _cleanup_camera_object(self):
         """Safely close/release the current camera object"""
         if self.camera:
             camera_type_to_clean = self.camera_type # Store type before setting camera to None
             print(f"Cleaning up {camera_type_to_clean} object...")
             try:
                 if camera_type_to_clean == "Raspberry Pi Camera" and picamera2_available:
                     self.camera.close() # Use close() for Picamera2
                     print("Pi Camera closed.")
                 elif camera_type_to_clean == "Webcam":
                     self.camera.release() # Use release() for VideoCapture
                     print("Webcam released.")
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
        self.running = False
        if self.is_recording:
            self.stop_recording() # Ensure recording is stopped
        if self.thread.is_alive():
            print("Waiting for camera thread to finish...")
            self.thread.join(timeout=2.0) # Wait for thread with timeout
            if self.thread.is_alive():
                 print("Warning: Camera thread did not terminate gracefully.")
        # Clean up camera object itself
        self._cleanup_camera_object()
        # Optional: Add gc.collect() here too?
        # gc.collect()
        print("Camera manager cleaned up.")

    # Remove old __del__ if it exists, cleanup() is preferred
    # def __del__(self): ... 