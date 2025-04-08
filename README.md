# Camera Control System

This project implements a camera control system using either MG996R servos or NEMA17 stepper motors on a Raspberry Pi. It allows you to control three motors (horizontal, vertical, and focus) using the analog sticks and triggers of an Xbox controller or through a web interface.

## Hardware Requirements

- Raspberry Pi (any model with GPIO pins)
- Either:
  - 3x MG996R servos, or
  - 3x NEMA17 stepper motors with drivers (A4988 or DRV8825 recommended)
- Xbox controller (wired or wireless with adapter)
- Jumper wires for connecting motors to GPIO pins
- Power supply for motors (12V recommended for steppers, 5V for servos)
- RTSP camera

## Pin Configuration

### MG996R Servos
- Horizontal Servo (Azimuth): GPIO 17
- Vertical Servo (Elevation): GPIO 18
- Focus Servo: GPIO 27

### NEMA17 Stepper Motors
#### Horizontal Stepper (Azimuth)
- Step Pin: GPIO 17
- Direction Pin: GPIO 27
- Enable Pin: GPIO 22

#### Vertical Stepper (Elevation)
- Step Pin: GPIO 18
- Direction Pin: GPIO 23
- Enable Pin: GPIO 24

#### Focus Stepper
- Step Pin: GPIO 25
- Direction Pin: GPIO 8
- Enable Pin: GPIO 7

## Wiring Instructions

### For MG996R Servos
1. Connect each servo to the Raspberry Pi:
   - Signal wire → corresponding GPIO pin
   - Power wire → 5V from Raspberry Pi or external power supply
   - Ground wire → Raspberry Pi GND

### For NEMA17 Stepper Motors
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
- Flask
- OpenCV
- python-dotenv
- requests

## Installation

1. Clone this repository or download the files
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. Edit the `.env` file to configure your system:
   ```
   # RTSP Camera Settings
   RTSP_URL=rtsp://username:password@camera-ip-address:port/stream
   
   # Motor type selection (servo or stepper)
   MOTOR_TYPE=servo
   
   # Servo settings
   SERVO_HORIZONTAL_PIN=17
   SERVO_VERTICAL_PIN=18
   SERVO_FOCUS_PIN=27
   
   # Stepper motor settings
   STEPPER_H_STEP_PIN=17
   STEPPER_H_DIR_PIN=27
   STEPPER_H_EN_PIN=22
   
   STEPPER_V_STEP_PIN=18
   STEPPER_V_DIR_PIN=23
   STEPPER_V_EN_PIN=24
   
   STEPPER_F_STEP_PIN=25
   STEPPER_F_DIR_PIN=8
   STEPPER_F_EN_PIN=7
   
   STEPPER_DELAY=0.001
   
   # Telegram settings
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```

2. For Telegram integration, you need to:
   - Create a bot using BotFather on Telegram
   - Get your bot token
   - Get your chat ID (you can use @userinfobot)
   - Add these to your .env file

## Usage

1. Connect your motors to the specified GPIO pins
2. Connect your Xbox controller to the Raspberry Pi (optional)
3. Run the script:
   ```bash
   python main.py
   ```

## Controls

### Xbox Controller
- Left Stick Horizontal: Controls horizontal movement
- Left Stick Vertical: Controls vertical movement
- Right Trigger: Controls focus movement

### Keyboard (when no controller is connected)
- Arrow keys: Control horizontal and vertical movement
- A/D keys: Control focus movement

### Web Interface
- Access the web interface at `http://[raspberry-pi-ip]:8080`
- Use sliders to control motor positions
- Click "Take Photo" to capture a full-resolution photo and send it to Telegram

## Photo Capture and Telegram Integration

The system now includes the ability to take full-resolution photos and send them to a Telegram chat:

1. Configure your Telegram bot token and chat ID in the `.env` file
2. Use the "Take Photo" button in the web interface to capture a photo
3. The photo will be saved to the `photos` directory and sent to your Telegram chat

## Safety Notes

- Ensure proper power supply for your motors
- Double-check all connections before powering on
- Always use a clean shutdown (Ctrl+C) to stop the program
- Stepper motors are automatically disabled when not moving to prevent overheating

## License

This project is open source and available under the MIT License.

## RTSP Camera Integration

The system includes integration with an RTSP camera stream. This allows you to view the camera feed while controlling the motors.

### Setting Up the RTSP Stream

1. Update the `.env` file with your camera's RTSP URL:
   ```
   RTSP_URL=rtsp://username:password@camera-ip-address:port/stream
   ```
   
   Example formats for common cameras:
   - Generic: `rtsp://username:password@192.168.1.100:554/stream1`
   - Hikvision: `rtsp://username:password@192.168.1.100:554/h264/ch1/main/av_stream`
   - Dahua: `rtsp://username:password@192.168.1.100:554/cam/realmonitor?channel=1&subtype=0`
   - Axis: `rtsp://username:password@192.168.1.100:554/axis-media/media.amp`

### Troubleshooting RTSP Connection

If you're having trouble connecting to your RTSP camera:

1. Make sure your camera is properly configured for RTSP streaming
2. Verify that the username, password, IP address, and port are correct
3. Try the RTSP URL in VLC player to confirm it works
4. Check your network connectivity to the camera
5. Some cameras require specific path formats for their RTSP streams - check your camera's documentation

## Code Structure

The project has a modular structure:

- `main.py` - Main entry point that coordinates all components
- `config.py` - Configuration settings and constants
- `servo_manager.py` - Handles servo motor control
- `stepper_manager.py` - Handles stepper motor control
- `camera_manager.py` - Manages the RTSP camera feed and photo capture
- `input_manager.py` - Processes joystick and keyboard input
- `display_manager.py` - Handles the pygame display and UI
- `web_camera.py` - Provides a web interface for remote control
- `telegram_manager.py` - Handles sending photos to Telegram

### Running the Application

To run the application:

```bash
python main.py
```

This will:
1. Start the motor control system with pygame display
2. Connect to the RTSP camera stream
3. Start a web server on port 8080 for remote control
4. Initialize Telegram integration if configured 