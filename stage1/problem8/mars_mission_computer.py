"""Mars mission computer that reports sensor data and system status."""

import json
import os
import platform
import random
import time

try:
    import psutil
except ImportError:
    psutil = None


class DummySensor:
    """A dummy sensor that produces randomized Mars base env values."""

    def __init__(self):
        self.env_values = {
            'mars_base_internal_temperature': 0,
            'mars_base_external_temperature': 0,
            'mars_base_internal_humidity': 0,
            'mars_base_external_illuminance': 0,
            'mars_base_internal_co2': 0,
            'mars_base_internal_oxygen': 0,
        }

    def set_env(self):
        """Fill env_values with random values within their valid range."""
        self.env_values['mars_base_internal_temperature'] = (
            random.randint(18, 30))
        self.env_values['mars_base_external_temperature'] = (
            random.randint(0, 21))
        self.env_values['mars_base_internal_humidity'] = (
            random.randint(50, 60))
        self.env_values['mars_base_external_illuminance'] = (
            random.randint(500, 715))
        self.env_values['mars_base_internal_co2'] = (
            round(random.uniform(0.02, 0.1), 4))
        self.env_values['mars_base_internal_oxygen'] = (
            round(random.uniform(4, 7), 2))

    def get_env(self):
        """Return the current env_values dictionary."""
        return self.env_values


class MissionComputer:
    """Collects sensor data and system status, reporting both as JSON."""

    def __init__(self):
        self.env_values = {
            'mars_base_internal_temperature': 0,
            'mars_base_external_temperature': 0,
            'mars_base_internal_humidity': 0,
            'mars_base_external_illuminance': 0,
            'mars_base_internal_co2': 0,
            'mars_base_internal_oxygen': 0,
        }

    def get_sensor_data(self):
        """Read ds's values, print them as JSON, and repeat every 5s."""
        try:
            while True:
                ds.set_env()
                self.env_values = ds.get_env()
                print(json.dumps(self.env_values, indent=4))
                time.sleep(5)
        except KeyboardInterrupt:
            print('System stopped….')

    def get_mission_computer_info(self):
        """Print and return OS, CPU, and memory info as JSON."""
        info = {}
        try:
            info['os'] = platform.system()
            info['os_version'] = platform.version()
            info['cpu_type'] = platform.processor() or platform.machine()
            info['cpu_cores'] = os.cpu_count()
            if psutil is not None:
                info['memory_size'] = psutil.virtual_memory().total
            else:
                info['memory_size'] = 'unavailable (psutil not installed)'
        except Exception as error:
            info['error'] = f'Failed to retrieve mission computer info: {error}'
        print(json.dumps(info, indent=4, ensure_ascii=False))
        return info

    def get_mission_computer_load(self):
        """Print and return real-time CPU and memory load as JSON."""
        load = {}
        try:
            if psutil is not None:
                load['cpu_usage_percent'] = psutil.cpu_percent(interval=1)
                load['memory_usage_percent'] = psutil.virtual_memory().percent
            else:
                load['error'] = 'unavailable (psutil not installed)'
        except Exception as error:
            load['error'] = f'Failed to retrieve mission computer load: {error}'
        print(json.dumps(load, indent=4, ensure_ascii=False))
        return load


ds = DummySensor()

runComputer = MissionComputer()
runComputer.get_mission_computer_info()
runComputer.get_mission_computer_load()
