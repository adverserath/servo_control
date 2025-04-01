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