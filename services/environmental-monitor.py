#!/usr/bin/env python3
"""
Environmental Monitoring Service
Physical world sensing for agentic cluster context

Responsibilities:
- Read temperature/humidity (DHT22)
- Detect motion (PIR sensor)
- Measure light levels (photoresistor)
- Store readings in cluster memory
- Correlate with node performance
- Control status LEDs
"""

import sys
import time
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# GPIO library - will fail gracefully if not on appropriate hardware
try:
    import gpiod
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("Warning: gpiod not available, running in simulation mode")

# Add cluster deployment to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'cluster-deployment'))
from toon_config import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/var/log/environmental-monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DHT22Sensor:
    """Temperature and humidity sensor"""

    def __init__(self, pin: int):
        self.pin = pin
        self.last_reading: Optional[Dict] = None

    def read(self) -> Optional[Dict]:
        """Read temperature and humidity"""
        try:
            if not GPIO_AVAILABLE:
                # Simulation mode
                import random
                return {
                    'temperature_c': round(20 + random.uniform(-5, 10), 1),
                    'temperature_f': round(68 + random.uniform(-9, 18), 1),
                    'humidity_percent': round(40 + random.uniform(-20, 40), 1),
                    'timestamp': datetime.now().isoformat(),
                    'simulated': True
                }

            # Real sensor reading would go here
            # Using Adafruit_DHT or similar library
            # import Adafruit_DHT
            # humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, self.pin)

            # For now, return simulated data
            import random
            return {
                'temperature_c': round(20 + random.uniform(-5, 10), 1),
                'temperature_f': round(68 + random.uniform(-9, 18), 1),
                'humidity_percent': round(40 + random.uniform(-20, 40), 1),
                'timestamp': datetime.now().isoformat(),
                'simulated': True
            }

        except Exception as e:
            logger.error(f"Failed to read DHT22: {e}")
            return None


class PIRSensor:
    """Motion detection sensor"""

    def __init__(self, pin: int):
        self.pin = pin
        self.motion_detected = False
        self.last_motion: Optional[datetime] = None

        if GPIO_AVAILABLE:
            # Initialize GPIO for PIR
            pass

    def read(self) -> Dict:
        """Check if motion detected"""
        try:
            if not GPIO_AVAILABLE:
                # Simulation mode - occasional motion
                import random
                motion = random.random() < 0.1  # 10% chance

                if motion:
                    self.motion_detected = True
                    self.last_motion = datetime.now()

                return {
                    'motion_detected': motion,
                    'last_motion': self.last_motion.isoformat() if self.last_motion else None,
                    'timestamp': datetime.now().isoformat(),
                    'simulated': True
                }

            # Real sensor reading would go here
            # Read GPIO pin value
            # motion = GPIO.input(self.pin)

            # Simulated for now
            import random
            motion = random.random() < 0.1

            return {
                'motion_detected': motion,
                'last_motion': self.last_motion.isoformat() if self.last_motion else None,
                'timestamp': datetime.now().isoformat(),
                'simulated': True
            }

        except Exception as e:
            logger.error(f"Failed to read PIR: {e}")
            return {'motion_detected': False, 'error': str(e)}


class PhotoresistorSensor:
    """Light level sensor"""

    def __init__(self, pin: int):
        self.pin = pin

    def read(self) -> Optional[Dict]:
        """Read light level"""
        try:
            if not GPIO_AVAILABLE:
                # Simulation mode - varies by hour
                hour = datetime.now().hour
                if 6 <= hour <= 18:  # Daytime
                    import random
                    light_level = random.randint(600, 1000)
                else:  # Nighttime
                    import random
                    light_level = random.randint(0, 200)

                return {
                    'light_level': light_level,
                    'brightness': self._categorize_brightness(light_level),
                    'timestamp': datetime.now().isoformat(),
                    'simulated': True
                }

            # Real sensor reading would use ADC
            # For now, simulated
            hour = datetime.now().hour
            import random
            light_level = random.randint(600, 1000) if 6 <= hour <= 18 else random.randint(0, 200)

            return {
                'light_level': light_level,
                'brightness': self._categorize_brightness(light_level),
                'timestamp': datetime.now().isoformat(),
                'simulated': True
            }

        except Exception as e:
            logger.error(f"Failed to read photoresistor: {e}")
            return None

    def _categorize_brightness(self, level: int) -> str:
        """Categorize light level"""
        if level > 800:
            return 'bright'
        elif level > 400:
            return 'moderate'
        elif level > 100:
            return 'dim'
        else:
            return 'dark'


class StatusLEDs:
    """Control status LEDs for visual feedback"""

    def __init__(self):
        self.leds = {
            'green': 17,   # All systems normal
            'yellow': 27,  # Warning
            'red': 22      # Critical
        }

        if GPIO_AVAILABLE:
            # Initialize GPIO for LEDs
            pass

    def set(self, color: str, state: bool):
        """Set LED state"""
        if color not in self.leds:
            return

        try:
            if GPIO_AVAILABLE:
                # Set GPIO pin
                # GPIO.output(self.leds[color], state)
                pass

            logger.debug(f"LED {color}: {'ON' if state else 'OFF'}")
        except Exception as e:
            logger.error(f"Failed to set LED {color}: {e}")

    def cluster_status(self, online_nodes: int, total_nodes: int):
        """Update LEDs based on cluster status"""
        if online_nodes == total_nodes:
            self.set('green', True)
            self.set('yellow', False)
            self.set('red', False)
        elif online_nodes >= total_nodes * 0.5:
            self.set('green', False)
            self.set('yellow', True)
            self.set('red', False)
        else:
            self.set('green', False)
            self.set('yellow', False)
            self.set('red', True)


class EnvironmentalMonitor:
    """Main environmental monitoring service"""

    def __init__(self, config_path: str = None):
        """Initialize monitor with configuration"""
        config_path = config_path or str(Path.home() / '.claude' / 'node-config')
        self.config = load_config(config_path)

        self.node_id = self.config.get('node_id', 'bpi-sentinel')

        # Get sensor configuration
        env_config = self.config.get('services', {}).get('environmental_monitor', {})
        self.logging_interval = env_config.get('logging_interval_seconds', 60)

        # Initialize sensors
        self.sensors = {
            'temperature': DHT22Sensor(pin=7),
            'motion': PIRSensor(pin=11),
            'light': PhotoresistorSensor(pin=13)
        }

        self.leds = StatusLEDs()

        # Database
        agentic_root = Path.home() / 'agentic-system'
        self.shared_memory_db = agentic_root / 'databases' / 'cluster' / 'shared_memories.db'

        logger.info(f"Environmental Monitor initialized: {self.node_id}")
        logger.info(f"GPIO Available: {GPIO_AVAILABLE}")

    def read_all_sensors(self) -> Dict:
        """Read all sensors"""
        readings = {
            'timestamp': datetime.now().isoformat(),
            'node_id': self.node_id,
            'sensors': {}
        }

        # Temperature/humidity
        temp_data = self.sensors['temperature'].read()
        if temp_data:
            readings['sensors']['temperature'] = temp_data

        # Motion
        motion_data = self.sensors['motion'].read()
        if motion_data:
            readings['sensors']['motion'] = motion_data

        # Light
        light_data = self.sensors['light'].read()
        if light_data:
            readings['sensors']['light'] = light_data

        return readings

    def store_readings(self, readings: Dict):
        """Store sensor readings in cluster memory"""
        try:
            conn = sqlite3.connect(str(self.shared_memory_db))
            cursor = conn.cursor()

            # Store as environmental observation
            cursor.execute("""
                INSERT INTO entities (name, entity_type, observations, node_id, created_at, updated_at)
                VALUES (?, 'environmental_data', ?, ?, datetime('now'), datetime('now'))
            """, (
                f"env_reading_{int(time.time())}",
                json.dumps([json.dumps(readings)]),
                self.node_id
            ))

            conn.commit()
            conn.close()

            logger.debug(f"Stored readings: {len(readings['sensors'])} sensors")
        except Exception as e:
            logger.error(f"Failed to store readings: {e}")

    def correlate_with_performance(self, readings: Dict):
        """Correlate environmental data with node performance"""
        # Future: Query node performance metrics and correlate
        # For example: "macpro51 thermal throttles when temp > 25°C"

        temp_data = readings['sensors'].get('temperature', {})
        if temp_data and not temp_data.get('simulated'):
            temp_c = temp_data.get('temperature_c', 0)

            if temp_c > 28:
                logger.warning(f"High ambient temperature detected: {temp_c}°C")
                logger.warning("Node performance may be degraded")

    def update_status_leds(self):
        """Update status LEDs based on cluster health"""
        try:
            # Query node registry for cluster status
            conn = sqlite3.connect(str(self.shared_memory_db.parent / 'node_registry.db'))
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM nodes")
            total_nodes = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM nodes WHERE status = 'online'")
            online_nodes = cursor.fetchone()[0]

            conn.close()

            # Update LEDs
            self.leds.cluster_status(online_nodes, total_nodes)

        except Exception as e:
            logger.debug(f"Failed to update status LEDs: {e}")

    def run_monitoring_cycle(self):
        """Run one complete monitoring cycle"""
        logger.info("Reading environmental sensors...")

        # Read sensors
        readings = self.read_all_sensors()

        # Log summary
        temp = readings['sensors'].get('temperature', {})
        motion = readings['sensors'].get('motion', {})
        light = readings['sensors'].get('light', {})

        summary = []
        if temp:
            summary.append(f"Temp: {temp.get('temperature_c')}°C")
        if motion:
            summary.append(f"Motion: {'Yes' if motion.get('motion_detected') else 'No'}")
        if light:
            summary.append(f"Light: {light.get('brightness')}")

        logger.info(" | ".join(summary))

        # Store in cluster memory
        self.store_readings(readings)

        # Correlate with performance
        self.correlate_with_performance(readings)

        # Update status LEDs
        self.update_status_leds()

    def run(self):
        """Main monitoring loop"""
        logger.info(f"🌡️  Environmental Monitor starting (interval: {self.logging_interval}s)")

        if not GPIO_AVAILABLE:
            logger.warning("Running in SIMULATION mode - no real sensors")

        try:
            while True:
                try:
                    self.run_monitoring_cycle()
                except Exception as e:
                    logger.error(f"Error in monitoring cycle: {e}", exc_info=True)

                time.sleep(self.logging_interval)

        except KeyboardInterrupt:
            logger.info("Environmental monitor shutting down gracefully...")
            # Turn off all LEDs
            self.leds.set('green', False)
            self.leds.set('yellow', False)
            self.leds.set('red', False)
        except Exception as e:
            logger.error(f"Fatal error in monitor: {e}", exc_info=True)
            raise


def main():
    """Entry point"""
    monitor = EnvironmentalMonitor()
    monitor.run()


if __name__ == '__main__':
    main()
