import threading
import time
import os
import cv2
import pygame
import asyncio
import urllib.parse
from flask import Flask, Response, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv
from camera_manager import CameraManager
from servo_manager import ServoManager
from input_manager import InputManager
from telegram_sender import send_photo_to_telegram
from config import FRAME_RATE

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
        """Create/Update the index.html template with library management"""
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
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
            padding: 8px;
            background-color: #f9f9f9;
            border-radius: 3px;
            border: 1px solid #eee;
        }
        .captures-list .file-info {
            flex-grow: 1;
            margin-right: 10px;
        }
        .captures-list .file-actions button {
            margin-left: 5px;
            padding: 3px 8px;
            font-size: 0.9em;
            cursor: pointer;
        }
        .btn-delete {
            background-color: #f44336;
            color: white;
            border: none;
            border-radius: 3px;
        }
        .btn-telegram {
            background-color: #0088cc;
            color: white;
            border: none;
            border-radius: 3px;
        }
        .btn-telegram:disabled {
             background-color: #cccccc;
             cursor: not-allowed;
        }
        .btn-refresh {
            margin-left: 10px;
            padding: 3px 8px;
            font-size: 0.9em;
        }
        .file-status {
             font-size: 0.8em; color: grey; margin-left: 5px;
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
                    <div id="controllerRawValues" class="hidden" style="font-size: 0.9em; margin-top: 5px; padding-left: 10px; border-left: 2px solid #eee;">
                        Raw Axis H: <span id="rawAxisH">0.00</span> | 
                        Raw Axis V: <span id="rawAxisV">0.00</span> | 
                        Raw LT: <span id="rawAxisLT">-1.00</span> | 
                        Raw RT: <span id="rawAxisRT">-1.00</span> <br>
                        Button 0 (X): <span id="rawButton0">OFF</span> | 
                        Button 3 (Sq): <span id="rawButton3">OFF</span>
                    </div>
                </div>
                <div class="status-item">
                    <span class="status-label">Servos:</span>
                    <span class="status-value" id="servoStatus">Checking...</span>
                    <div class="status-error" id="servoError"></div>
                </div>
            </div>
        </div>

        <div class="captures-list">
             <h2>
                 Captured Files
                 <button id="refreshCapturesBtn" class="btn-refresh" title="Refresh List">&#x21bb;</button>
             </h2>
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
        const controllerRawValuesEl = document.getElementById('controllerRawValues');
        const rawAxisHEl = document.getElementById('rawAxisH');
        const rawAxisVEl = document.getElementById('rawAxisV');
        const rawAxisLTEl = document.getElementById('rawAxisLT');
        const rawAxisRTEl = document.getElementById('rawAxisRT');
        const rawButton0El = document.getElementById('rawButton0');
        const rawButton3El = document.getElementById('rawButton3');
        
        const refreshCapturesBtn = document.getElementById('refreshCapturesBtn');
        
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
            // Indicate loading
            capturesList.innerHTML = '<li>Loading captures...</li>';
            
            fetch('/api/captures')
                .then(response => response.json())
                .then(data => {
                    capturesList.innerHTML = ''; // Clear existing list
                    if (data.files && data.files.length > 0) {
                        // No need to sort here if server sorts
                        data.files.forEach(file => {
                            const li = document.createElement('li');
                            li.dataset.filename = file; // Store filename

                            const fileInfo = document.createElement('div');
                            fileInfo.classList.add('file-info');

                            const a = document.createElement('a');
                            a.href = `/captures/${encodeURIComponent(file)}`; // Ensure filename is encoded for URL
                            a.textContent = file;
                            a.target = '_blank';
                            fileInfo.appendChild(a);
                            
                            const fileActions = document.createElement('div');
                            fileActions.classList.add('file-actions');

                            // Add Status Span (for Telegram/Delete messages)
                            const statusSpan = document.createElement('span');
                            statusSpan.classList.add('file-status');
                            fileActions.appendChild(statusSpan);

                            // Add Telegram Button (only for images for now)
                            if (file.toLowerCase().endsWith('.jpg') || file.toLowerCase().endsWith('.jpeg') || file.toLowerCase().endsWith('.png')) {
                                const sendBtn = document.createElement('button');
                                sendBtn.textContent = 'Send Telegram';
                                sendBtn.classList.add('btn-telegram');
                                sendBtn.onclick = () => sendToTelegram(file, sendBtn, statusSpan);
                                fileActions.appendChild(sendBtn);
                            }

                            // Add Delete Button
                            const deleteBtn = document.createElement('button');
                            deleteBtn.textContent = 'Delete';
                            deleteBtn.classList.add('btn-delete');
                            deleteBtn.onclick = () => deleteCapture(file, li, deleteBtn, statusSpan);
                            fileActions.appendChild(deleteBtn);

                            li.appendChild(fileInfo);
                            li.appendChild(fileActions);
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
        
        // Function to delete a capture
        function deleteCapture(filename, listItem, button, statusSpan) {
             if (!confirm(`Are you sure you want to delete ${filename}?`)) {
                 return;
             }
             button.disabled = true;
             statusSpan.textContent = 'Deleting...';
             statusSpan.style.color = 'orange';

             fetch(`/api/captures/delete/${encodeURIComponent(filename)}`, { method: 'DELETE' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        listItem.remove(); // Remove from list on success
                    } else {
                        console.error("Delete failed:", data.error);
                        statusSpan.textContent = `Delete failed: ${data.error}`;
                        statusSpan.style.color = 'red';
                        button.disabled = false; // Re-enable button on failure
                        setTimeout(() => { statusSpan.textContent = ''; }, 5000); // Clear status after delay
                    }
                 })
                 .catch(error => {
                     console.error('Error deleting file:', error);
                     statusSpan.textContent = `Error: ${error}`;
                     statusSpan.style.color = 'red';
                     button.disabled = false;
                     setTimeout(() => { statusSpan.textContent = ''; }, 5000);
                 });
        }

        // Function to send image to Telegram
        function sendToTelegram(filename, button, statusSpan) {
             button.disabled = true;
             statusSpan.textContent = 'Sending...';
             statusSpan.style.color = 'orange';
             
             fetch(`/api/captures/send/${encodeURIComponent(filename)}`, { method: 'POST' })
                 .then(response => response.json())
                 .then(data => {
                     if (data.success) {
                         statusSpan.textContent = 'Sent!';
                         statusSpan.style.color = 'green';
                     } else {
                         console.error("Telegram send failed:", data.error);
                         statusSpan.textContent = `Send failed: ${data.error}`;
                         statusSpan.style.color = 'red';
                     }
                     // Re-enable button after a short delay, clear status
                     setTimeout(() => { 
                         button.disabled = false; 
                         statusSpan.textContent = ''; 
                     }, 5000);
                 })
                 .catch(error => {
                     console.error('Error sending to Telegram:', error);
                     statusSpan.textContent = `Error: ${error}`;
                     statusSpan.style.color = 'red';
                      setTimeout(() => { 
                         button.disabled = false; 
                         statusSpan.textContent = ''; 
                     }, 5000);
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
                    console.error('Error fetching status:', error);
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
                controllerRawValuesEl.classList.toggle('hidden', !connected);

                if (connected) {
                     controllerStatus.textContent += ` (${data.controller_status.controller_type})`;
                     // Display raw values if available
                     if (data.controller_status.raw_values) {
                         const raw = data.controller_status.raw_values;
                         rawAxisHEl.textContent = raw.axis_h !== undefined ? raw.axis_h.toFixed(2) : 'N/A';
                         rawAxisVEl.textContent = raw.axis_v !== undefined ? raw.axis_v.toFixed(2) : 'N/A';
                         rawAxisLTEl.textContent = raw.axis_lt !== undefined ? raw.axis_lt.toFixed(2) : 'N/A';
                         rawAxisRTEl.textContent = raw.axis_rt !== undefined ? raw.axis_rt.toFixed(2) : 'N/A';
                         if (raw.buttons) {
                             rawButton0El.textContent = raw.buttons['0'] ? 'ON' : 'OFF';
                             rawButton3El.textContent = raw.buttons['3'] ? 'ON' : 'OFF';
                         }
                     }
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
        
        // Add event listener for refresh button
        refreshCapturesBtn.addEventListener('click', fetchCaptures);
        
        // Initial calls and interval
        fetchCaptures(); // Load captures on page load
        updateStatus(); // Update status on page load
        setInterval(updateStatus, 2000); // Update status every 2 seconds
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
            camera_status = self.camera_manager.get_status() # Already includes recording
            
            # Get controller status (now includes raw values)
            controller_status = self.input_manager.get_status() 
            # Add controller type for convenience if not already in get_status
            if 'controller_type' not in controller_status:
                controller_status['controller_type'] = 'Keyboard' if not controller_status['connected'] else 'Joystick'

            # Get servo status
            servo_status = self.servo_manager.get_status()
            
            return jsonify({
                'camera_connected': camera_status['connected'],
                'horizontal_pos': self.servo_manager.horizontal_pos,
                'vertical_pos': self.servo_manager.vertical_pos,
                'focus_pos': self.servo_manager.focus_pos,
                'camera_status': camera_status,
                'controller_status': controller_status, # Now has raw_values
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
             
        # Modified route to list captures
        @self.app.route('/api/captures')
        def list_captures():
            try:
                capture_dir = self.app.config['CAPTURE_DIR']
                files = [f for f in os.listdir(capture_dir) 
                         if os.path.isfile(os.path.join(capture_dir, f))]
                # Sort by modification time, newest first
                files.sort(key=lambda x: os.path.getmtime(os.path.join(capture_dir, x)), reverse=True)
                return jsonify({'files': files})
            except Exception as e:
                print(f"Error listing captures: {e}")
                return jsonify({'error': str(e)}), 500
        
        # Route to serve captured files (ensure filename is handled safely)
        @self.app.route('/captures/<path:filename>')
        def serve_capture(filename):
            # Basic security check: prevent accessing files outside capture dir
            safe_filename = os.path.basename(filename) # Use only the filename part
            if safe_filename != filename: # Check if path traversal was attempted
                 return "Invalid filename", 400
            return send_from_directory(self.app.config['CAPTURE_DIR'], safe_filename)
            
        # New route to DELETE a capture
        @self.app.route('/api/captures/delete/<path:filename>', methods=['DELETE'])
        def delete_capture_api(filename):
            try:
                capture_dir = self.app.config['CAPTURE_DIR']
                # Basic security check
                safe_filename = os.path.basename(filename)
                if safe_filename != filename:
                     return jsonify({'success': False, 'error': 'Invalid filename'}), 400
                
                file_path = os.path.join(capture_dir, safe_filename)
                
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Deleted capture: {safe_filename}")
                    return jsonify({'success': True, 'message': f'{safe_filename} deleted.'})
                else:
                    return jsonify({'success': False, 'error': 'File not found'}), 404
            except Exception as e:
                print(f"Error deleting capture {filename}: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
                
        # New route to send a capture to Telegram
        @self.app.route('/api/captures/send/<path:filename>', methods=['POST'])
        def send_capture_telegram_api(filename):
            try:
                capture_dir = self.app.config['CAPTURE_DIR']
                # Basic security check
                safe_filename = os.path.basename(filename)
                if safe_filename != filename:
                     return jsonify({'success': False, 'error': 'Invalid filename'}), 400
                
                file_path = os.path.join(capture_dir, safe_filename)
                
                if not os.path.exists(file_path):
                     return jsonify({'success': False, 'error': 'File not found'}), 404
                
                # Run the async function in the event loop
                # Flask runs in its own thread, so get/create an event loop
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:  # No event loop running in this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Run send_photo_to_telegram and wait for result
                success, message = loop.run_until_complete(send_photo_to_telegram(file_path, caption=safe_filename))
                
                return jsonify({'success': success, 'error': None if success else message, 'message': message if success else None})

            except Exception as e:
                print(f"Error sending capture {filename} to Telegram: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

    def _generate_frames(self):
        """Generate frames for MJPEG streaming"""
        while True:
            # Get the latest frame from the camera manager
            frame = self.camera_manager.get_frame() 
            
            if frame is not None:
                processed_frame = frame # Assume BGR by default
                # --- Convert PiCamera frame to BGR for JPEG encoding --- 
                if self.camera_manager.camera_type == "Raspberry Pi Camera":
                    try:
                        # Frame from get_frame() should be RGB888 based on config
                        # print("Converting frame to BGR for JPEG stream...") # Debug
                        processed_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    except cv2.error as cv_err:
                        print(f"OpenCV error during BGR conversion for streaming: {cv_err}")
                        # Send a placeholder or skip frame?
                        # For now, try to stream the original frame
                        processed_frame = frame 
                # --- End Conversion --- 
                
                # Encode as JPEG (expects BGR)
                ret, buffer = cv2.imencode('.jpg', processed_frame)
                if ret:
                    frame_bytes = buffer.tobytes()
                    # Yield for MJPEG streaming
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                else:
                     print("JPEG encoding failed.")
            else:
                # print("No frame available from camera manager.") # Debug
                # Send a placeholder image if no frame? (optional)
                pass # Or just wait
            
            # Adjust sleep time - maybe slightly longer if frames are slow
            time.sleep(max(0.01, 1.0 / FRAME_RATE)) # Use FRAME_RATE from config
    
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