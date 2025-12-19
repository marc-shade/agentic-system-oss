#!/usr/bin/env python3
"""
Gamepad Reader - Read input from USB game controller
Requires pygame for game controller support
"""

try:
    import pygame
    import sys
    
    # Initialize pygame
    pygame.init()
    pygame.joystick.init()
    
    # Check for joysticks
    joystick_count = pygame.joystick.get_count()
    
    if joystick_count == 0:
        print("❌ No game controllers found")
        print("\nNote: Make sure pygame can access HID devices")
        sys.exit(1)
    
    print(f"✅ Found {joystick_count} game controller(s)\n")
    
    # Get first joystick
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    
    print(f"Controller Info:")
    print(f"  Name: {joystick.get_name()}")
    print(f"  Axes: {joystick.get_numaxes()}")
    print(f"  Buttons: {joystick.get_numbuttons()}")
    print(f"  Hats: {joystick.get_numhats()}")
    print(f"\nPress Ctrl+C to stop\n")
    
    # Read loop
    clock = pygame.time.Clock()
    
    while True:
        pygame.event.pump()
        
        # Read axes
        axes = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]
        
        # Read buttons
        buttons = [joystick.get_button(i) for i in range(joystick.get_numbuttons())]
        
        # Print if something changed
        if any(abs(a) > 0.1 for a in axes) or any(buttons):
            print(f"Axes: {['%.2f' % a for a in axes]} | Buttons: {['✓' if b else '-' for b in buttons]}")
        
        clock.tick(60)  # 60 Hz
        
except ImportError:
    print("❌ pygame not installed")
    print("\nInstall with: pip3 install pygame")
except KeyboardInterrupt:
    print("\n\n✅ Stopped")
    pygame.quit()
except Exception as e:
    print(f"❌ Error: {e}")
