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
        self.recording_filename = None
        self.recording_lock = threading.Lock()
        self.encoder = None # Store encoder instance
        
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
            # DEBUG: Print values used for decision
            print(f"DEBUG: Checking camera type: IS_RASPBERRY_PI={IS_RASPBERRY_PI}, picamera2_available={picamera2_available}")
            use_pi_camera = IS_RASPBERRY_PI and picamera2_available
            if use_pi_camera:
                print("Attempting Pi Camera initialization...")
                self._init_pi_camera() # This sets self.connected, self.error
            else:
                # Add specific reason log here
                if not IS_RASPBERRY_PI:
                     reason = "Not on Raspberry Pi"
                elif not picamera2_available:
                     reason = "Picamera2 library not available/functional"
                else:
                     reason = "Unknown"
                print(f"DEBUG: Condition for Pi Camera not met ({reason}). Falling back to webcam...")
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

        print(f"Camera thread: {self.camera_type} initialized successfully. Entering LORES capture loop.")
        
        # --- Capture Loop (Only runs if init succeeded) ---
        while self.running:
            if not self.connected or self.camera is None:
                # Should not happen if init succeeded, but safety check
                print("Camera became disconnected unexpectedly. Camera thread exiting.")
                self.error = "Camera disconnected unexpectedly."
                break # Exit capture loop
                
            try:
                # Capture from the low-resolution stream for preview
                frame_data = self._capture_frame("lores") 
                
                if frame_data is not None:
                    processed_frame = None
                    # --- Convert frame for storage/display (expecting BGR) --- 
                    if self.camera_type == "Raspberry Pi Camera":
                        # Lores stream is YUV420, convert to BGR
                        try:
                            processed_frame = cv2.cvtColor(frame_data, cv2.COLOR_YUV420p_to_BGR) # Or COLOR_YUV2BGR_I420 if needed
                        except cv2.error as cv_err:
                            print(f"OpenCV error converting lores YUV420->BGR: {cv_err}")
                            # Fallback or handle error - maybe skip frame?
                            continue
                    elif self.camera_type == "Webcam": # Webcam is likely BGR already
                        processed_frame = frame_data
                    else: # Should not happen
                        continue 
                    # --- End Conversion --- 

                    if processed_frame is not None:
                        with self.frame_lock:
                            self.frame = processed_frame # Store the BGR frame
                        self.error = None
                    # No video writing logic here anymore
                else:
                     print(f"Failed to capture lores frame using {self.camera_type}. Camera thread exiting.")
                     self.error = "Failed to capture lores frame."
                     break # Exit capture loop
                
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
        """Initialize Pi camera with full-res main stream and low-res preview stream"""
        if not picamera2_available:
            self.error = "picamera2 module not available."
            self.connected = False
            return
        print("Initializing Pi Camera (picamera2)...")
        try:
            self._cleanup_camera_object() # Ensure any previous instance is closed
            self.camera = Picamera2()
            
            # --- Configure Full-Res Main and Low-Res Lores Streams --- 
            print(f"Attempting video configuration... Preview: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
            # Main stream: Use sensor's full resolution (omit size). RGB888 for stills.
            # Lores stream: For preview/web stream. YUV420 is efficient.
            config = self.camera.create_video_configuration(
                main={"format": "RGB888"}, # Full resolution for stills/recording source
                lores={"size": (SCREEN_WIDTH, SCREEN_HEIGHT), "format": "YUV420"},
                controls={"FrameRate": float(FRAME_RATE)} # Set frame rate
            )
            print(f"Initial Configuration created: {config}")
            
            # Optional: Align lores stream size if necessary (e.g., to hardware constraints)
            # self.camera.align_configuration(config)
            # print(f"Aligned Configuration: {config}")
            
            # Apply the configuration
            print("Configuring Pi Camera...")
            self.camera.configure(config)
            print("Configuration applied.")

            # Set display stream to lores (important!)
            self.camera.display_stream_name = "lores"
            print(f"Using '{self.camera.display_stream_name}' stream for preview.")

            print("Starting Pi Camera...")
            self.camera.start()
            print("Pi Camera started.")
            
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
                 error_msg = "Webcam opened but failed to read initial frame."
                 print(f"ERROR: {error_msg}")
                 print("TROUBLESHOOTING HINTS:")
                 print("  1. Check permissions: Run 'ls -l /dev/video*' in terminal.")
                 print("     Your user needs read/write access (often via 'video' group).")
                 print("     If needed, run 'sudo usermod -a -G video $USER' then LOG OUT and back in.")
                 print("  2. Check if another application is using the webcam.")
                 print("  3. Ensure the webcam is securely connected and functional.")
                 raise IOError(error_msg + " Check permissions/device.")
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

    def _capture_frame(self, stream_name="lores"):
        """Capture a single frame from the specified camera stream"""
        if not self.connected or self.camera is None:
            return None
        try:
            if self.camera_type == "Raspberry Pi Camera":
                # Capture frame from picamera2 from the specified stream
                # capture_array defaults to the 'display_stream_name' if stream_name is None
                frame = self.camera.capture_array(stream_name)
                # print(f"Captured {stream_name} frame. Shape: {frame.shape}, Dtype: {frame.dtype}") # Debug
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
        """Get the current preview camera frame (should be BGR)"""
        with self.frame_lock:
            if self.frame is None:
                return None
            return self.frame.copy() # Return a copy
            
    def capture_still(self):
        """Capture a full-resolution still image (saves as JPG)"""
        if not self.connected or self.camera is None or self.camera_type != "Raspberry Pi Camera":
             return False, "Pi Camera not connected or available for full-res capture."
        
        print("Capturing full-resolution still (main stream)...")
        try:
            # Capture from the main stream explicitly
            frame_data = self._capture_frame("main") # RGB888 format expected
            if frame_data is not None:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filename = os.path.join(self.capture_dir, f"capture_{timestamp}.jpg")
                # Convert RGB frame from PiCam main stream to BGR for saving
                save_frame = cv2.cvtColor(frame_data, cv2.COLOR_RGB2BGR)
                cv2.imwrite(filename, save_frame)
                print(f"Full-res image captured: {filename}")
                return True, filename
            else:
                return False, "Failed to capture main stream frame."
        except Exception as e:
            error_msg = f"Failed to save full-res image: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return False, error_msg
            
    def start_recording(self):
        """Start recording video using picamera2's H264Encoder"""
        if not self.connected or self.camera is None or self.camera_type != "Raspberry Pi Camera":
             return False, "Pi Camera not connected or available for recording."
             
        with self.recording_lock:
            if self.is_recording:
                return False, "Already recording."
            
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            # Output raw H.264 video stream
            self.recording_filename = os.path.join(self.capture_dir, f"video_{timestamp}.h264") 
            
            try:
                # Create an encoder instance (e.g., 10Mbps bitrate)
                # Quality setting might override bitrate, check documentation
                self.encoder = H264Encoder(bitrate=10000000)
                print(f"Starting H.264 recording to {self.recording_filename} at ~{FRAME_RATE}fps, quality VERY_HIGH...")
                
                # Use start_recording - this uses the 'main' stream by default for video config
                self.camera.start_recording(self.encoder, self.recording_filename, quality=Quality.VERY_HIGH)
                
                self.is_recording = True
                print(f"Started recording: {self.recording_filename}")
                return True, self.recording_filename
                
            except Exception as e:
                error_msg = f"Failed to start H.264 recording: {e}"
                print(error_msg)
                import traceback
                traceback.print_exc()
                self.recording_filename = None
                self.encoder = None
                return False, error_msg

    def stop_recording(self):
        """Stop recording video"""
        if not self.connected or self.camera is None or self.camera_type != "Raspberry Pi Camera":
             return False, "Pi Camera not available to stop recording."
             
        with self.recording_lock:
            if not self.is_recording:
                return False, "Not currently recording."
            
            try:
                print(f"Stopping recording: {self.recording_filename}")
                self.camera.stop_recording()
                recorded_file = self.recording_filename
                self.is_recording = False
                self.recording_filename = None
                self.encoder = None # Clear encoder instance
                print("Stopped recording successfully.")
                return True, recorded_file
            except Exception as e:
                error_msg = f"Error stopping recording: {e}"
                print(error_msg)
                # Attempt to mark as not recording anyway
                self.is_recording = False 
                self.recording_filename = None
                self.encoder = None
                return False, error_msg

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