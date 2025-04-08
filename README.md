# Stepper Motor Controller

This project implements a stepper motor control system using an Xbox controller on a Raspberry Pi. It allows you to control three NEMA17 stepper motors (horizontal, vertical, and focus) using the analog sticks and triggers of an Xbox controller.

## Hardware Requirements

- Raspberry Pi (any model with GPIO pins)
- 3x NEMA17 stepper motors
- 3x Stepper motor drivers (A4988 or DRV8825 recommended)
- Xbox controller (wired or wireless with adapter)
- Jumper wires for connecting stepper drivers to GPIO pins
- Power supply for stepper motors (12V recommended)

## Pin Configuration

### Horizontal Stepper (Azimuth)
- Step Pin: GPIO 17
- Direction Pin: GPIO 27
- Enable Pin: GPIO 22

### Vertical Stepper (Elevation)
- Step Pin: GPIO 18
- Direction Pin: GPIO 23
- Enable Pin: GPIO 24

### Focus Stepper
- Step Pin: GPIO 25
- Direction Pin: GPIO 8
- Enable Pin: GPIO 7

## Wiring Instructions

1. Connect each stepper motor driver to the Raspberry Pi:
   - STEP pin → corresponding GPIO pin
   - DIR pin → corresponding GPIO pin
   - EN pin → corresponding GPIO pin
   - GND → Raspberry Pi GND
   - VCC → 5V from Raspberry Pi
   - VMOT → 12V power supply positive
   - GND → 12V power supply negative

2. Connect the stepper motors to their respective drivers:
   - A1, A2, B1, B2 → corresponding motor coils

## Software Requirements

- Python 3.x
- pygame
- RPi.GPIO

## Installation

1. Clone this repository or download the files
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Connect your stepper motors and drivers to the specified GPIO pins
2. Connect your Xbox controller to the Raspberry Pi
3. Run the script:
   ```bash
   python stepper_controller.py
   ```

## Controls

- Left Stick Horizontal: Controls horizontal stepper movement
- Left Stick Vertical: Controls vertical stepper movement
- Right Trigger: Controls focus stepper movement

## Safety Notes

- Ensure proper power supply for your stepper motors
- Double-check all connections before powering on
- Always use a clean shutdown (Ctrl+C) to stop the program
- The motors are automatically disabled when not moving to prevent overheating

## License

This project is open source and available under the MIT License.

## RTSP Camera Integration

The servo controller now includes integration with an RTSP camera stream. This allows you to view the camera feed while controlling the servos.

### Setting Up the RTSP Stream

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

### Using the Camera View

When you run `servo_controller.py`, the RTSP camera feed will be displayed in the pygame window. The servo controls work as before, but now you can see what the camera is pointing at.

- If a joystick is connected, it will be used for controlling the servos.
- If no joystick is detected, you can use keyboard controls:
  - Arrow keys: Control horizontal and vertical servos
  - A/D keys: Control focus servo

### Troubleshooting RTSP Connection

If you're having trouble connecting to your RTSP camera:

1. Make sure your camera is properly configured for RTSP streaming
2. Verify that the username, password, IP address, and port are correct
3. Try the RTSP URL in VLC player to confirm it works
4. Check your network connectivity to the camera
5. Some cameras require specific path formats for their RTSP streams - check your camera's documentation

## Refactored Code Structure

The project has been refactored into a modular structure:

- `main.py` - Main entry point that coordinates all components
- `config.py` - Configuration settings and constants
- `servo_manager.py` - Handles servo motor control
- `camera_manager.py` - Manages the RTSP camera feed
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
2. Connect to the RTSP camera stream
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