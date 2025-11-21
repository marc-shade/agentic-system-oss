#!/usr/bin/env python3
"""
Ember Web API Server
Provides HTTP API for controller interactions
"""

import sys
from pathlib import Path
from flask import Flask, jsonify, send_file
from flask_cors import CORS

# Add ember_integration to path
sys.path.insert(0, str(Path(__file__).parent.parent / "ember_integration"))
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))

from ember_pet import EmberPet
from surface_bridge import ArduinoSurface

app = Flask(__name__)
CORS(app)

# Global instances
ember = EmberPet()
surface = None

# Initialize Arduino connection
try:
    surface = ArduinoSurface('/dev/tty.usbmodem8344401')
    if surface.connect():
        print("✓ Arduino connected for API")
except Exception as e:
    print(f"⚠ Arduino not connected: {e}")
    print("  (Controller will still work, just no Arduino feedback)")


@app.route('/')
def index():
    """Serve the controller interface"""
    return send_file('ember_controller.html')


@app.route('/api/ember/status')
def get_status():
    """Get Ember's current status"""
    ember.load_state()  # Reload from file
    stats = ember.get_stats()

    return jsonify({
        'hunger': stats['hunger'],
        'energy': stats['energy'],
        'happiness': stats['happiness'],
        'cleanliness': stats['cleanliness'],
        'mood': ember.get_mood()
    })


@app.route('/api/ember/feed', methods=['POST'])
def feed():
    """Feed Ember"""
    ember.feed()
    stats = ember.get_stats()

    if surface:
        try:
            surface.lcd_write(0, 0, "🔥*nom nom nom*")
            surface.lcd_write(1, 0, f"Yummy! H:{stats['hunger']}")
            surface.alert('success')
        except:
            pass

    return jsonify({
        'success': True,
        'message': f"Fed Ember! Hunger: {stats['hunger']}/100",
        'stats': stats
    })


@app.route('/api/ember/play', methods=['POST'])
def play():
    """Play with Ember"""
    ember.play()
    stats = ember.get_stats()

    if surface:
        try:
            surface.lcd_write(0, 0, "🔥*bounce* Fun!")
            surface.lcd_write(1, 0, f"Happy! E:{stats['energy']}")
            surface.set_led(0, 0, 255, 0)  # Green (playing)
        except:
            pass

    return jsonify({
        'success': True,
        'message': f"Played with Ember! Energy: {stats['energy']}/100",
        'stats': stats
    })


@app.route('/api/ember/clean', methods=['POST'])
def clean():
    """Clean Ember"""
    ember.clean()
    stats = ember.get_stats()

    if surface:
        try:
            surface.lcd_write(0, 0, "🔥*splash splash*")
            surface.lcd_write(1, 0, f"Clean! C:{stats['cleanliness']}")
            surface.beep(200, 800)
        except:
            pass

    return jsonify({
        'success': True,
        'message': f"Cleaned Ember! Cleanliness: {stats['cleanliness']}/100",
        'stats': stats
    })


@app.route('/api/ember/pet', methods=['POST'])
def pet():
    """Pet Ember"""
    ember.pet()
    stats = ember.get_stats()

    if surface:
        try:
            surface.lcd_write(0, 0, "🔥*purr*")
            surface.lcd_write(1, 0, f"<3 Hap:{stats['happiness']}")
            surface.beep(150, 1200)
        except:
            pass

    return jsonify({
        'success': True,
        'message': f"Pet Ember! Happiness: {stats['happiness']}/100",
        'stats': stats
    })


@app.route('/api/system/mode', methods=['POST'])
def cycle_mode():
    """Cycle display mode (for system monitor daemon)"""
    # This is a signal to cycle modes - daemon would need to listen
    # For now, just return success
    return jsonify({
        'success': True,
        'message': 'Display mode cycled'
    })


@app.route('/api/system/metrics')
def get_metrics():
    """Get system quality metrics"""
    sys.path.insert(0, str(Path(__file__).parent.parent / "ember_integration"))
    from system_monitor import SystemMonitor

    monitor = SystemMonitor()

    return jsonify({
        'violations': monitor.get_violation_stats(),
        'learning': monitor.get_learning_stats(),
        'outcomes': monitor.get_outcome_stats(),
        'quality_score': monitor.get_quality_score(),
        'system_info': monitor.get_system_info()
    })


if __name__ == '__main__':
    print("=" * 50)
    print("🔥 Ember Web Controller API 🔥")
    print("=" * 50)
    print()
    print("Starting server on http://localhost:5001")
    print("Open this URL in your browser to use the controller")
    print()

    app.run(host='0.0.0.0', port=5001, debug=False)
