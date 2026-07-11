"""Mars mission computer dummy environment sensor."""

import random


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


ds = DummySensor()
ds.set_env()
print(ds.get_env())
