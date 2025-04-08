import threading
import time
import os
import cv2
from flask import Flask, Response, render_template, request, jsonify
from dotenv import load_dotenv
from config import RTSP_URL, MOTOR_TYPE

class WebCameraServer:
    def __init__(self, motor_manager, camera_manager, telegram_manager=None, port=8080):
        self.app = Flask(__name__, template_folder='templates')
        self.port = port
        self.motor_manager = motor_manager
        self.camera_manager = camera_manager
        self.telegram_manager = telegram_manager
        
        # Ensure templates directory exists
        os.makedirs('templates', exist_ok=True)
        
        # Create index.html template if it doesn't exist
        self._create_template_if_missing()
        
        # Set up routes
        self._setup_routes()
        
    def _create_template_if_missing(self):
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
        .button {
            background-color: #4CAF50;
            border: none;
            color: white;
            padding: 10px 20px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 10px 0;
            cursor: pointer;
            border-radius: 5px;
        }
        .button:hover {
            background-color: #45a049;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Camera Control</h1>
        
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
            
            <div class="control-group">
                <button id="take-photo" class="button">Take Photo</button>
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
        const takePhotoButton = document.getElementById('take-photo');
        
        // Update motor position when sliders change
        horizontalSlider.addEventListener('input', updateValues);
        verticalSlider.addEventListener('input', updateValues);
        focusSlider.addEventListener('input', updateValues);
        
        // Take photo button
        takePhotoButton.addEventListener('click', takePhoto);
        
        // Convert slider value (0-100) to motor value (-1 to 1)
        function sliderToMotor(value) {
            return value / 100;
        }
        
        // Convert motor value (-1 to 1) to slider value (-100 to 100)
        function motorToSlider(value) {
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
                    horizontal: sliderToMotor(horizontalSlider.value),
                    vertical: sliderToMotor(verticalSlider.value),
                    focus: sliderToMotor(focusSlider.value)
                })
            });
        }
        
        // Take photo function
        function takePhoto() {
            takePhotoButton.disabled = true;
            takePhotoButton.textContent = 'Taking Photo...';
            
            fetch('/api/take_photo', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    statusEl.innerHTML += `<br>Photo taken: ${data.filename}`;
                } else {
                    statusEl.innerHTML += `<br>Failed to take photo: ${data.error}`;
                }
                takePhotoButton.disabled = false;
                takePhotoButton.textContent = 'Take Photo';
            })
            .catch(error => {
                console.error('Error:', error);
                statusEl.innerHTML += '<br>Error taking photo';
                takePhotoButton.disabled = false;
                takePhotoButton.textContent = 'Take Photo';
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
                        Motor type: ${data.motor_type}<br>
                        Horizontal: ${data.horizontal_pos.toFixed(2)}<br>
                        Vertical: ${data.vertical_pos.toFixed(2)}<br>
                        Focus: ${data.focus_pos.toFixed(2)}
                    `;
                    
                    // Update sliders without triggering events
                    horizontalSlider.value = motorToSlider(data.horizontal_pos);
                    verticalSlider.value = motorToSlider(data.vertical_pos);
                    focusSlider.value = motorToSlider(data.focus_pos);
                    
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
    
    def _setup_routes(self):
        """Set up Flask routes"""
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/video_feed')
        def video_feed():
            return Response(self._generate_frames(),
                           mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.app.route('/api/status')
        def status():
            return jsonify({
                'camera_connected': self.camera_manager.connected,
                'motor_type': MOTOR_TYPE,
                'horizontal_pos': self.motor_manager.horizontal_pos,
                'vertical_pos': self.motor_manager.vertical_pos,
                'focus_pos': self.motor_manager.focus_pos
            })
        
        @self.app.route('/api/control', methods=['POST'])
        def control():
            data = request.json
            
            if 'horizontal' in data:
                self.motor_manager.update_position(horizontal=float(data['horizontal']))
                
            if 'vertical' in data:
                self.motor_manager.update_position(vertical=float(data['vertical']))
                
            if 'focus' in data:
                self.motor_manager.update_position(focus=float(data['focus']))
            
            return jsonify({
                'success': True,
                'horizontal_pos': self.motor_manager.horizontal_pos,
                'vertical_pos': self.motor_manager.vertical_pos,
                'focus_pos': self.motor_manager.focus_pos
            })
            
        @self.app.route('/api/take_photo', methods=['POST'])
        def take_photo():
            try:
                # Take a photo at full resolution
                photo_path = self.camera_manager.take_photo()
                
                if photo_path:
                    # Send to Telegram if configured
                    if self.telegram_manager and self.telegram_manager.is_configured:
                        self.telegram_manager.send_photo_async(photo_path)
                    
                    return jsonify({
                        'success': True,
                        'filename': os.path.basename(photo_path)
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to capture photo'
                    })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                })
    
    def _generate_frames(self):
        """Generate frames for MJPEG streaming"""
        while True:
            frame = self.camera_manager.get_frame()
            
            if frame is not None:
                # Encode as JPEG
                _, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                
                # Yield for MJPEG streaming
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            time.sleep(0.033)  # ~30fps
    
    def start(self):
        """Start the web server in a separate thread"""
        server_thread = threading.Thread(target=self._run_server, daemon=True)
        server_thread.start()
        print(f"Web server started at http://0.0.0.0:{self.port}")
    
    def _run_server(self):
        """Run the Flask server"""
        self.app.run(host='0.0.0.0', port=self.port, threaded=True) 