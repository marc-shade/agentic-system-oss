# v1_basic_status - General Purpose System Status

**Status**: Production (Current)
**Memory**: 15KB / 32KB (47%)
**Last Updated**: 2025-11-06

## Purpose
General-purpose firmware with balanced feature set for system monitoring and agent interaction.

## Features
- 16x2 LCD text display
- 1x RGB LED (Tier0 - green/yellow/red status)
- Servo motor (0-180° position indicator)
- Piezo buzzer (audio alerts and patterns)
- 2x Buttons (Confirm/Cancel for human-in-loop workflows)
- 4x Sensors (Potentiometer, Temperature, Light, Tilt)
- JSON serial protocol (115200 baud)

## Use Cases
- Standard system status display
- Agent health monitoring
- Human approval workflows
- Environmental context gathering
- Emergency stop via tilt switch

## Commands Supported
- LCD row col text
- LED tier r g b
- SERVO position
- BEEP duration freq
- ALERT type
- CLEAR
- STATUS
- PING

## When to Use
- Default production firmware
- Balanced feature needs
- Standard monitoring operations
- Multi-agent coordination

## Performance
- Startup: 3 seconds
- LCD Update: 20ms
- Sensor Polling: 100ms interval
- Command Response: <50ms
