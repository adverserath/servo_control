import os
import time
import threading
import cv2
import numpy as np
import sys
from flask import Flask, Response, render_template, request, jsonify

# Create Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

# Simulated servo positions
horizontal_pos = 0.0
vertical_pos = 0.0
focus_pos = 0.0

# Create simulated camera frame
frame = None
frame_lock = threading.Lock()
camera_connected = True
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Create templates directory if it doesn't exist
os.makedirs('templates', exist_ok=True)

def create_template():
    """Create the index.html template if it doesn't exist"""
    template_path = os.path.join('templates', 'index.html')
    
    if not os.path.exists(template_path):
        with open(template_path, 'w') as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Servo Camera Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f0f0f0;
        }
        .container {
            display: flex;
            flex-direction: column;
            max-width: 800px;
            margin: 0 auto;
        }
        .video-container {
            position: relative;
            width: 100%;
            margin-bottom: 20px;
        }
        .video-feed {
            width: 100%;
            border: 1px solid #ccc;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .control-panel {
            background: white;
            border-radius: 5px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .control-group {
            margin-bottom: 15px;
        }
        h1, h2 {
            color: #333;
        }
        .slider-container {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }
        .slider-label {
            width: 100px;
        }
        .slider {
            flex-grow: 1;
        }
        .value-display {
            width: 50px;
            text-align: right;
            margin-left: 10px;
        }
        .status {
            margin-top: 20px;
            padding: 10px;
            background-color: #eee;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Servo Camera Control</h1>
        
        <div class="video-container">
            <img class="video-feed" src="/video_feed" alt="Camera Feed">
        </div>
        
        <div class="control-panel">
            <h2>Controls</h2>
            
            <div class="control-group">
                <div class="slider-container">
                    <span class="slider-label">Horizontal:</span>
                    <input type="range" id="horizontal" class="slider" min="-100" max="100" value="0">
                    <span class="value-display" id="horizontal-value">0</span>
                </div>
                
                <div class="slider-container">
                    <span class="slider-label">Vertical:</span>
                    <input type="range" id="vertical" class="slider" min="-100" max="100" value="0">
                    <span class="value-display" id="vertical-value">0</span>
                </div>
                
                <div class="slider-container">
                    <span class="slider-label">Focus:</span>
                    <input type="range" id="focus" class="slider" min="-100" max="100" value="0">
                    <span class="value-display" id="focus-value">0</span>
                </div>
            </div>
            
            <div class="status" id="status">
                Camera status: Connecting...
            </div>
        </div>
    </div>
    
    <script>
        // Elements
        const horizontalSlider = document.getElementById('horizontal');
        const verticalSlider = document.getElementById('vertical');
        const focusSlider = document.getElementById('focus');
        const horizontalValue = document.getElementById('horizontal-value');
        const verticalValue = document.getElementById('vertical-value');
        const focusValue = document.getElementById('focus-value');
        const statusEl = document.getElementById('status');
        
        // Update servo position when sliders change
        horizontalSlider.addEventListener('input', updateValues);
        verticalSlider.addEventListener('input', updateValues);
        focusSlider.addEventListener('input', updateValues);
        
        // Convert slider value (0-100) to servo value (-1 to 1)
        function sliderToServo(value) {
            return value / 100;
        }
        
        // Convert servo value (-1 to 1) to slider value (-100 to 100)
        function servoToSlider(value) {
            return value * 100;
        }
        
        // Update display and send values to server
        function updateValues() {
            // Update display values
            horizontalValue.textContent = horizontalSlider.value / 100;
            verticalValue.textContent = verticalSlider.value / 100;
            focusValue.textContent = focusSlider.value / 100;
            
            // Send to server
            fetch('/api/control', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    horizontal: sliderToServo(horizontalSlider.value),
                    vertical: sliderToServo(verticalSlider.value),
                    focus: sliderToServo(focusSlider.value)
                })
            });
        }
        
        // Update status from server
        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // Update status text
                    statusEl.innerHTML = `
                        Camera status: ${data.camera_connected ? 'Connected' : 'Disconnected'}<br>
                        Horizontal: ${data.horizontal_pos.toFixed(2)}<br>
                        Vertical: ${data.vertical_pos.toFixed(2)}<br>
                        Focus: ${data.focus_pos.toFixed(2)}
                    `;
                    
                    // Update sliders without triggering events
                    horizontalSlider.value = servoToSlider(data.horizontal_pos);
                    verticalSlider.value = servoToSlider(data.vertical_pos);
                    focusSlider.value = servoToSlider(data.focus_pos);
                    
                    horizontalValue.textContent = data.horizontal_pos.toFixed(2);
                    verticalValue.textContent = data.vertical_pos.toFixed(2);
                    focusValue.textContent = data.focus_pos.toFixed(2);
                })
                .catch(error => {
                    console.error('Error:', error);
                });
        }
        
        // Update status every 2 seconds
        setInterval(updateStatus, 2000);
        
        // Initial update
        updateStatus();
    </script>
</body>
</html>""")

# Create the template
create_template()

def generate_simulated_frame():
    """Generate a simulated camera view"""
    global horizontal_pos, vertical_pos, focus_pos
    
    # Convert normalized positions (-1 to 1) to image positions (0 to 1)
    h_pos = (horizontal_pos + 1) * 0.5
    v_pos = (vertical_pos + 1) * 0.5
    f_level = (focus_pos + 1) * 0.5
    
    # Create a blank frame
    frame = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)
    
    # Add a grid
    for x in range(0, SCREEN_WIDTH, 50):
        cv2.line(frame, (x, 0), (x, SCREEN_HEIGHT), (30, 30, 30), 1)
    for y in range(0, SCREEN_HEIGHT, 50):
        cv2.line(frame, (0, y), (SCREEN_WIDTH, y), (30, 30, 30), 1)
    
    # Add a horizon line
    horizon_y = int(SCREEN_HEIGHT * v_pos)
    cv2.line(frame, (0, horizon_y), (SCREEN_WIDTH, horizon_y), (0, 100, 0), 2)
    
    # Add a vertical line for horizontal servo position
    vertical_x = int(SCREEN_WIDTH * h_pos)
    cv2.line(frame, (vertical_x, 0), (vertical_x, SCREEN_HEIGHT), (100, 0, 0), 2)
    
    # Draw a rectangle to represent the camera view boundaries
    cv2.rectangle(frame, (100, 100), (SCREEN_WIDTH-100, SCREEN_HEIGHT-100), (50, 50, 100), 2)
    
    # Add crosshair in center
    center_x = int(SCREEN_WIDTH * h_pos)
    center_y = int(SCREEN_HEIGHT * v_pos)
    cv2.line(frame, (center_x-20, center_y), (center_x+20, center_y), (200, 200, 0), 2)
    cv2.line(frame, (center_x, center_y-20), (center_x, center_y+20), (200, 200, 0), 2)
    
    # Apply "blur" based on focus
    blur_amount = int(abs(f_level - 0.5) * 20) + 1
    if blur_amount > 1:
        frame = cv2.GaussianBlur(frame, (blur_amount*2+1, blur_amount*2+1), 0)
    
    return frame

# Function to generate frames for MJPEG stream
def generate_frames():
    """Generate frames for MJPEG streaming"""
    while True:
        # Generate a new frame
        frame = generate_simulated_frame()
        
        # Encode as JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        # Yield for MJPEG streaming
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        time.sleep(0.033)  # ~30fps

# Set up Flask routes
@app.route('/')
def index():
    return render_template('index.html')

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
        
    if 'vertical' in data:
        vertical_pos = max(-1, min(1, float(data['vertical'])))
        
    if 'focus' in data:
        focus_pos = max(-1, min(1, float(data['focus'])))
    
    print(f"Controls updated: H={horizontal_pos:.2f}, V={vertical_pos:.2f}, F={focus_pos:.2f}")
    
    return jsonify({
        'success': True,
        'horizontal_pos': horizontal_pos,
        'vertical_pos': vertical_pos,
        'focus_pos': focus_pos
    })

if __name__ == '__main__':
    print("Starting web server on http://localhost:8080")
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=True) 