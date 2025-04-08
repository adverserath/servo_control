import os
import time
import threading
import cv2
import numpy as np
from flask import Flask, Response, render_template, request, jsonify
from dotenv import load_dotenv
import RPi.GPIO as GPIO
from config import SCREEN_WIDTH, SCREEN_HEIGHT
from motor_controller import create_motor_controller

# Load environment variables
load_dotenv()

# Handle XDG_RUNTIME_DIR issue on Raspberry Pi OS
if not os.environ.get('XDG_RUNTIME_DIR'):
    # Create runtime directory in /run/user/$(id -u)
    user_id = os.getuid()
    runtime_dir = f'/run/user/{user_id}'
    os.makedirs(runtime_dir, exist_ok=True)
    os.environ['XDG_RUNTIME_DIR'] = runtime_dir

app = Flask(__name__)

# Camera Configuration
camera_connected = False
frame = None
frame_lock = threading.Lock()

# Define GPIO pins for servos
SERVO_HORIZONTAL_PIN = int(os.environ.get('SERVO_HORIZONTAL_PIN', 17))
SERVO_VERTICAL_PIN = int(os.environ.get('SERVO_VERTICAL_PIN', 18))
SERVO_FOCUS_PIN = int(os.environ.get('SERVO_FOCUS_PIN', 27))

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(SERVO_HORIZONTAL_PIN, GPIO.OUT)
GPIO.setup(SERVO_VERTICAL_PIN, GPIO.OUT)
GPIO.setup(SERVO_FOCUS_PIN, GPIO.OUT)

pwm_horizontal = GPIO.PWM(SERVO_HORIZONTAL_PIN, 50)
pwm_vertical = GPIO.PWM(SERVO_VERTICAL_PIN, 50)
pwm_focus = GPIO.PWM(SERVO_FOCUS_PIN, 50)

pwm_horizontal.start(0)
pwm_vertical.start(0)
pwm_focus.start(0)

# Current servo positions (normalized -1 to 1)
horizontal_pos = 0
vertical_pos = 0
focus_pos = 0

# Thread to capture from Pi camera
def camera_stream_thread():
    global frame, camera_connected
    
    try:
        # Initialize Pi camera
        import picamera
        import picamera.array
        
        with picamera.PiCamera() as camera:
            camera.resolution = (800, 600)
            camera.framerate = 30
            
            # Create a numpy array to store the frame
            output = picamera.array.PiRGBArray(camera, size=(800, 600))
            
            camera_connected = True
            print("Pi camera connected")
            
            for frame_array in camera.capture_continuous(output, format='bgr', use_video_port=True):
                with frame_lock:
                    frame = frame_array.array
                output.truncate(0)
                time.sleep(0.033)  # ~30fps
                
    except Exception as e:
        print(f"Camera Error: {e}")
        camera_connected = False
        time.sleep(5)  # Wait before retrying

# Function to map from -1,1 range to PWM duty cycle
def map_to_pwm(value):
    return (value + 1) * 50  # Map from -1,1 to 0,100

# Start the camera capture thread
camera_thread = threading.Thread(target=camera_stream_thread, daemon=True)
camera_thread.start()

# Generate frames for MJPEG stream
def generate_frames():
    global frame
    
    while True:
        with frame_lock:
            if frame is not None:
                # Encode frame as JPEG
                _, buffer = cv2.imencode('.jpg', frame)
                jpg_bytes = buffer.tobytes()
                
                # Yield for MJPEG streaming
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpg_bytes + b'\r\n')
        
        time.sleep(0.033)  # ~30fps

# Web routes
@app.route('/')
def index():
    return render_template('index.html', 
                          camera_connected=camera_connected,
                          horizontal_pos=horizontal_pos,
                          vertical_pos=vertical_pos,
                          focus_pos=focus_pos)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status')
def status():
    return jsonify({
        'camera_connected': camera_connected,
        'horizontal_pos': horizontal_pos,
        'vertical_pos': vertical_pos,
        'focus_pos': focus_pos
    })

@app.route('/api/control', methods=['POST'])
def control():
    global horizontal_pos, vertical_pos, focus_pos
    
    data = request.json
    if 'horizontal' in data:
        horizontal_pos = max(-1, min(1, float(data['horizontal'])))
        pwm_horizontal.ChangeDutyCycle(map_to_pwm(horizontal_pos))
        
    if 'vertical' in data:
        vertical_pos = max(-1, min(1, float(data['vertical'])))
        pwm_vertical.ChangeDutyCycle(map_to_pwm(vertical_pos))
        
    if 'focus' in data:
        focus_pos = max(-1, min(1, float(data['focus'])))
        pwm_focus.ChangeDutyCycle(map_to_pwm(focus_pos))
    
    return jsonify({
        'success': True,
        'horizontal_pos': horizontal_pos,
        'vertical_pos': vertical_pos,
        'focus_pos': focus_pos
    })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    try:
        app.run(host='0.0.0.0', port=8080, threaded=True)
    except KeyboardInterrupt:
        print("Web server shutting down...")
    finally:
        # Clean up GPIO
        pwm_horizontal.stop()
        pwm_vertical.stop()
        pwm_focus.stop()
        GPIO.cleanup() 