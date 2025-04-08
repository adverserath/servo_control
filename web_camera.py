import threading
import time
import os
import cv2
import pygame
from flask import Flask, Response, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv
from camera_manager import CameraManager
from servo_manager import ServoManager
from input_manager import InputManager

# Handle XDG_RUNTIME_DIR issue on Raspberry Pi OS
if not os.environ.get('XDG_RUNTIME_DIR'):
    # Create runtime directory in user's home directory
    home_dir = os.path.expanduser('~')
    runtime_dir = os.path.join(home_dir, '.runtime')
    os.makedirs(runtime_dir, exist_ok=True)
    os.environ['XDG_RUNTIME_DIR'] = runtime_dir

CAPTURE_DIR = "captures"

class WebCameraServer:
    def __init__(self, servo_manager: ServoManager, camera_manager: CameraManager, input_manager: InputManager, port=8080):
        self.app = Flask(__name__, template_folder='templates')
        self.port = port
        self.servo_manager = servo_manager
        self.camera_manager = camera_manager
        self.input_manager = input_manager
        
        # Ensure captures directory exists (used by CameraManager too)
        os.makedirs(CAPTURE_DIR, exist_ok=True)
        self.app.config['CAPTURE_DIR'] = CAPTURE_DIR
        
        # Ensure templates directory exists
        os.makedirs('templates', exist_ok=True)
        
        # Create index.html template if it doesn't exist
        self._create_template_if_missing()
        
        # Set up routes
        self._setup_routes()
        
        # Initialize pygame if not already initialized
        if not pygame.get_init():
            pygame.init()
        
        # Initialize joystick module if not already initialized
        if not pygame.joystick.get_init():
            pygame.joystick.init()
        
    def _create_template_if_missing(self):
        """Create/Update the index.html template with capture display"""
        template_path = os.path.join('templates', 'index.html')
        
        # Updated HTML content
        html_content = """<!DOCTYPE html>
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
        .capture-button {
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
        .capture-button:hover {
            background-color: #45a049;
        }
        .capture-button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        .capture-status {
            margin-top: 10px;
            padding: 10px;
            border-radius: 5px;
            display: none;
        }
        .capture-success {
            background-color: #dff0d8;
            color: #3c763d;
        }
        .capture-error {
            background-color: #f2dede;
            color: #a94442;
        }
        .status-panel {
            margin-top: 20px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
            border: 1px solid #ddd;
        }
        .status-item {
            margin-bottom: 10px;
            padding: 5px;
            border-radius: 3px;
        }
        .status-item.connected {
            background-color: #d4edda;
            color: #155724;
        }
        .status-item.disconnected {
            background-color: #f8d7da;
            color: #721c24;
        }
        .status-item.warning {
            background-color: #fff3cd;
            color: #856404;
        }
        .status-label {
            font-weight: bold;
        }
        .status-value {
            margin-left: 5px;
        }
        .status-error {
            color: #dc3545;
            font-style: italic;
            margin-top: 5px;
        }
        .captures-list {
            margin-top: 20px;
            background: white;
            border-radius: 5px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .captures-list h2 {
            margin-top: 0;
        }
        .captures-list ul {
            list-style: none;
            padding: 0;
            max-height: 200px;
            overflow-y: auto;
        }
        .captures-list li {
            margin-bottom: 5px;
            padding: 5px;
            background-color: #f9f9f9;
            border-radius: 3px;
        }
        .captures-list a {
            text-decoration: none;
            color: #007bff;
        }
        .captures-list a:hover {
            text-decoration: underline;
        }
        .recording-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            background-color: red;
            border-radius: 50%;
            margin-left: 10px;
            animation: blink 1s infinite;
            vertical-align: middle;
        }
        @keyframes blink {
            0% { opacity: 1; }
            50% { opacity: 0; }
            100% { opacity: 1; }
        }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Servo Camera Control</h1>
        
        <div class="video-container">
            <img class="video-feed" src="/video_feed" alt="Camera Feed">
            <div>
                 <button id="captureButton" class="capture-button">Capture Still Image (X)</button>
                 <button id="recordButton" class="capture-button">Start Recording (Square)</button>
                 <span id="recordingIndicator" class="recording-indicator hidden"></span>
            </div>
            <div id="captureStatus" class="capture-status"></div>
            <div id="recordStatus" class="capture-status"></div>
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
        
        <div class="status-panel">
            <h2>System Status</h2>
            <div id="systemStatus">
                <div class="status-item">
                    <span class="status-label">Camera:</span>
                    <span class="status-value" id="cameraStatus">Checking...</span>
                    <div class="status-error" id="cameraError"></div>
                </div>
                <div class="status-item">
                    <span class="status-label">Controller:</span>
                    <span class="status-value" id="controllerStatus">Checking...</span>
                    <div class="status-error" id="controllerError"></div>
                </div>
                <div class="status-item">
                    <span class="status-label">Servos:</span>
                    <span class="status-value" id="servoStatus">Checking...</span>
                    <div class="status-error" id="servoError"></div>
                </div>
            </div>
        </div>

        <div class="captures-list">
             <h2>Captured Files</h2>
             <ul id="capturesList">
                 <li>Loading captures...</li>
             </ul>
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
        const captureButton = document.getElementById('captureButton');
        const captureStatus = document.getElementById('captureStatus');
        const recordButton = document.getElementById('recordButton');
        const recordStatus = document.getElementById('recordStatus');
        const recordingIndicator = document.getElementById('recordingIndicator');
        const capturesList = document.getElementById('capturesList');
        
        // Status elements
        const cameraStatus = document.getElementById('cameraStatus');
        const cameraError = document.getElementById('cameraError');
        const controllerStatus = document.getElementById('controllerStatus');
        const controllerError = document.getElementById('controllerError');
        const servoStatus = document.getElementById('servoStatus');
        const servoError = document.getElementById('servoError');
        
        // Update servo position when sliders change
        horizontalSlider.addEventListener('input', updateValues);
        verticalSlider.addEventListener('input', updateValues);
        focusSlider.addEventListener('input', updateValues);
        
        // Capture still image when button is clicked
        captureButton.addEventListener('click', captureStillWeb);
        recordButton.addEventListener('click', toggleRecordingWeb);
        
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
        
        // Capture still image
        function captureStillWeb() {
            captureButton.disabled = true;
            captureStatus.style.display = 'none';
            
            fetch('/api/capture', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    showCaptureStatus(data.success, data.success ? `Image captured: ${data.filename}` : `Error: ${data.error}`);
                    if(data.success) { fetchCaptures(); } // Refresh list on success
                })
                .catch(error => { showCaptureStatus(false, `Error: ${error}`); })
                .finally(() => { captureButton.disabled = false; });
        }
        
        // Toggle recording
        function toggleRecordingWeb() {
            recordButton.disabled = true;
            recordStatus.style.display = 'none';
            
            fetch('/api/record/toggle', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    showRecordStatus(data.success, data.message);
                    // Update button text and indicator based on new state
                    updateRecordingUI(data.is_recording);
                    if(data.success && !data.is_recording) { fetchCaptures(); } // Refresh list when recording stops
                })
                .catch(error => { showRecordStatus(false, `Error: ${error}`); })
                .finally(() => { recordButton.disabled = false; });
        }
        
        function showCaptureStatus(success, message) {
            captureStatus.textContent = message;
            captureStatus.className = 'capture-status ' + (success ? 'capture-success' : 'capture-error');
            captureStatus.style.display = 'block';
            // Auto-hide after a few seconds
            setTimeout(() => { captureStatus.style.display = 'none'; }, 5000);
        }

        function showRecordStatus(success, message) {
            recordStatus.textContent = message;
            recordStatus.className = 'capture-status ' + (success ? 'capture-success' : 'capture-error');
            recordStatus.style.display = 'block';
             // Auto-hide after a few seconds
            setTimeout(() => { recordStatus.style.display = 'none'; }, 5000);
        }
        
        function updateRecordingUI(isRecording) {
             recordButton.textContent = isRecording ? 'Stop Recording (Square)' : 'Start Recording (Square)';
             recordingIndicator.classList.toggle('hidden', !isRecording);
        }

        // Fetch and display captured files
        function fetchCaptures() {
            fetch('/api/captures')
                .then(response => response.json())
                .then(data => {
                    capturesList.innerHTML = ''; // Clear existing list
                    if (data.files && data.files.length > 0) {
                        // Sort files reverse chronologically (newest first)
                        data.files.sort().reverse(); 
                        data.files.forEach(file => {
                            const li = document.createElement('li');
                            const a = document.createElement('a');
                            a.href = `/captures/${file}`;
                            a.textContent = file;
                            a.target = '_blank'; // Open in new tab
                            li.appendChild(a);
                            capturesList.appendChild(li);
                        });
                    } else {
                        capturesList.innerHTML = '<li>No captures found.</li>';
                    }
                })
                .catch(error => {
                    console.error('Error fetching captures:', error);
                    capturesList.innerHTML = '<li>Error loading captures.</li>';
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
                    
                    // Update system status
                    updateSystemStatus(data);
                    
                    // Update Recording UI
                    if (data.camera_status && data.camera_status.recording_status) {
                        updateRecordingUI(data.camera_status.recording_status.is_recording);
                    }
                    
                    // Update capture/record button states
                    captureButton.disabled = !data.camera_connected;
                    recordButton.disabled = !data.camera_connected; // Can't record if not connected
                })
                .catch(error => {
                    console.error('Error:', error);
                    // Show error in status
                    statusEl.innerHTML = `Error connecting to server: ${error}`;
                });
        }
        
        // Update system status display
        function updateSystemStatus(data) {
            // Camera status
            if (data.camera_status) {
                const connected = data.camera_status.connected;
                cameraStatus.textContent = connected ? 'Connected' : 'Disconnected';
                cameraStatus.parentElement.className = 'status-item ' + 
                    (connected ? 'connected' : 'disconnected');
                
                if (data.camera_status.camera_type) {
                    cameraStatus.textContent += ` (${data.camera_status.camera_type})`;
                }
                
                if (data.camera_status.error) {
                    cameraError.textContent = data.camera_status.error;
                    cameraError.style.display = 'block';
                } else {
                    cameraError.style.display = 'none';
                }
                
                // Add recording status display
                if (data.camera_status.recording_status) {
                    cameraStatus.textContent += data.camera_status.recording_status.is_recording ? ' (Recording)' : '';
                }
            }
            
            // Controller status
            if (data.controller_status) {
                const connected = data.controller_status.connected;
                controllerStatus.textContent = connected ? 'Connected' : 'Disconnected';
                controllerStatus.parentElement.className = 'status-item ' + 
                    (connected ? 'connected' : 'disconnected');
                
                if (data.controller_status.controller_type) {
                    controllerStatus.textContent += ` (${data.controller_status.controller_type})`;
                }
                
                if (data.controller_status.error) {
                    controllerError.textContent = data.controller_status.error;
                    controllerError.style.display = 'block';
                } else {
                    controllerError.style.display = 'none';
                }
            }
            
            // Servo status
            if (data.servo_status) {
                const connected = data.servo_status.connected;
                servoStatus.textContent = connected ? 'Connected' : 'Disconnected';
                servoStatus.parentElement.className = 'status-item ' + 
                    (connected ? 'connected' : 'disconnected');
                
                if (data.servo_status.error) {
                    servoError.textContent = data.servo_status.error;
                    servoError.style.display = 'block';
                } else {
                    servoError.style.display = 'none';
                }
            }
        }
        
        // Update status every 2 seconds
        setInterval(updateStatus, 2000);
        
        // Initial update
        updateStatus();
    </script>
</body>
</html>"""
        
        # Write the updated content
        # Check if file exists and content is different to avoid unnecessary writes
        needs_update = True
        if os.path.exists(template_path):
            with open(template_path, 'r') as f_read:
                if f_read.read() == html_content:
                    needs_update = False
                    
        if needs_update:
            with open(template_path, 'w') as f:
                f.write(html_content)
            print("Updated index.html template.")

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
            # Get camera status
            camera_status = self.camera_manager.get_status() if hasattr(self.camera_manager, 'get_status') else {
                'connected': self.camera_manager.connected,
                'camera_type': 'Unknown',
                'error': None
            }
            
            # Get controller status
            controller_status = {
                'connected': self.input_manager.connected,
                'controller_type': 'Keyboard' if not self.input_manager.connected else 'Joystick',
                'error': self.input_manager.error
            }
            
            # Get servo status
            servo_status = {
                'connected': True,  # Assume connected if no error
                'error': None
            }
            
            # Check if servo manager has error reporting
            if hasattr(self.servo_manager, 'get_status'):
                servo_status = self.servo_manager.get_status()
            
            return jsonify({
                'camera_connected': camera_status['connected'],
                'horizontal_pos': self.servo_manager.horizontal_pos,
                'vertical_pos': self.servo_manager.vertical_pos,
                'focus_pos': self.servo_manager.focus_pos,
                'camera_status': camera_status,
                'controller_status': controller_status,
                'servo_status': servo_status
            })
        
        @self.app.route('/api/control', methods=['POST'])
        def control():
            data = request.json
            
            if 'horizontal' in data:
                self.servo_manager.update_position(horizontal=float(data['horizontal']))
                
            if 'vertical' in data:
                self.servo_manager.update_position(vertical=float(data['vertical']))
                
            if 'focus' in data:
                self.servo_manager.update_position(focus=float(data['focus']))
            
            return jsonify({
                'success': True,
                'horizontal_pos': self.servo_manager.horizontal_pos,
                'vertical_pos': self.servo_manager.vertical_pos,
                'focus_pos': self.servo_manager.focus_pos
            })
        
        @self.app.route('/api/capture', methods=['POST'])
        def capture_web(): # Renamed to avoid conflict with CameraManager method
            success, result = self.camera_manager.capture_still()
            return jsonify({
                'success': success,
                'filename': result if success else None,
                'error': None if success else result
            })
        
        @self.app.route('/api/record/toggle', methods=['POST'])
        def toggle_record_web():
             success, result_msg_or_file = self.camera_manager.toggle_recording()
             # Get current recording state AFTER toggling
             current_rec_status = self.camera_manager.get_status()['recording_status']
             return jsonify({
                 'success': success,
                 'message': result_msg_or_file, # Contains filename or error message
                 'is_recording': current_rec_status['is_recording'] 
             })
             
        # New route to list captures
        @self.app.route('/api/captures')
        def list_captures():
            try:
                files = [f for f in os.listdir(self.app.config['CAPTURE_DIR']) 
                         if os.path.isfile(os.path.join(self.app.config['CAPTURE_DIR'], f))]
                files.sort(key=lambda x: os.path.getmtime(os.path.join(self.app.config['CAPTURE_DIR'], x)), reverse=True)
                return jsonify({'files': files})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        # New route to serve captured files
        @self.app.route('/captures/<path:filename>')
        def serve_capture(filename):
            return send_from_directory(self.app.config['CAPTURE_DIR'], filename)
    
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
        self.server_thread = threading.Thread(target=self._run_server)
        self.server_thread.daemon = False  # Make it a non-daemon thread
        self.server_thread.start()
        print(f"Web server started at http://0.0.0.0:{self.port}")
    
    def _run_server(self):
        """Run the Flask server"""
        self.app.run(host='0.0.0.0', port=self.port, threaded=True)
    
    def stop(self):
        """Stop the web server"""
        # This is a placeholder for now - Flask doesn't have a clean way to stop
        # We'll need to implement a proper shutdown mechanism in the future
        print("Web server stopping...")
        # For now, we'll just let the thread continue running
        # In a future version, we can implement a proper shutdown mechanism 