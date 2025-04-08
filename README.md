# Servo Camera Control System

A Python-based system for controlling servo motors with a camera feed and joystick/keyboard input.

## Features

- Servo motor control with joystick or keyboard input
- Real-time camera feed display
- Web interface for remote control
- Support for Raspberry Pi and standard webcams

## Installation

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

### Using the Camera View

When you run `servo_controller.py`, the camera feed will be displayed in the pygame window. The servo controls work as before, but now you can see what the camera is pointing at.

- If a joystick is connected, it will be used for controlling the servos.
- If no joystick is detected, you can use keyboard controls:
  - Arrow keys: Control horizontal and vertical servos
  - A/D keys: Control focus servo

## Refactored Code Structure

The project has been refactored into a modular structure:

- `main.py` - Main entry point that coordinates all components
- `config.py` - Configuration settings and constants
- `servo_manager.py` - Handles servo motor control
- `camera_manager.py` - Manages the camera feed
- `input_manager.py` - Processes joystick and keyboard input
- `display_manager.py` - Handles the pygame display and UI
- `web_camera.py` - Provides a web interface for remote control

### Running the Application

To run the application:

```bash
python main.py
```

This will:
1. Start the servo control system with pygame display
2. Connect to the camera stream
3. Start a web server on port 8080 for remote control

### Web Interface

The application includes a web interface that can be accessed at:

```
http://[raspberry-pi-ip]:8080
```

This allows you to:
- View the camera feed in your browser
- Control the servo positions using sliders
- See the current status of the system

The web interface works on desktop and mobile browsers, making it easy to control your servos from any device. 