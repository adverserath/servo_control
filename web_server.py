import os
import time
import threading
import cv2
import pygame
import asyncio
import urllib.parse
from flask import Flask, Response, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv
import RPi.GPIO as GPIO
from config import SCREEN_WIDTH, SCREEN_HEIGHT, HORIZONTAL_PIN, VERTICAL_PIN, FOCUS_PIN, PWM_FREQ, FRAME_RATE
from motor_controller import create_motor_controller
from camera_manager import CameraManager
from servo_manager import ServoManager
from input_manager import InputManager
from telegram_sender import send_photo_to_telegram

# Load environment variables
load_dotenv()

# Handle XDG_RUNTIME_DIR issue on Raspberry Pi OS
if not os.environ.get('XDG_RUNTIME_DIR'):
    # Create runtime directory in user's home directory
    home_dir = os.path.expanduser('~')
    runtime_dir = os.path.join(home_dir, '.runtime')
    os.makedirs(runtime_dir, exist_ok=True)
    os.environ['XDG_RUNTIME_DIR'] = runtime_dir

app = Flask(__name__)

# Camera Configuration

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(HORIZONTAL_PIN, GPIO.OUT)
GPIO.setup(VERTICAL_PIN, GPIO.OUT)
GPIO.setup(FOCUS_PIN, GPIO.OUT)

pwm_horizontal = GPIO.PWM(HORIZONTAL_PIN, PWM_FREQ)
pwm_vertical = GPIO.PWM(VERTICAL_PIN, PWM_FREQ)
pwm_focus = GPIO.PWM(FOCUS_PIN, PWM_FREQ)

pwm_horizontal.start(0)
pwm_vertical.start(0)
pwm_focus.start(0)

# Current servo positions (normalized -1 to 1)
horizontal_pos = 0
vertical_pos = 0
focus_pos = 0

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