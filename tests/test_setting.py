# -*- coding: utf-8 -*-
"""
Example program demonstrating how to use the settings configuration file.
"""

import sys
import os

# Add the parent directory to the path so we can import the config module
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.settings import (
    MQTT_SERVER,
    MQTT_PORT,
    MQTT_CLIENT_ID,
    MQTT_PUBLISH_TOPIC,
    MQTT_SUBSCRIBE_TOPIC,
    CAN_BUS_TYPE,
    CAN_CHANNEL,
    CAN_BITRATE
)


def display_mqtt_config():
    """
    Display the MQTT configuration settings.
    """
    print("MQTT Configuration:")
    print(f"  Server: {MQTT_SERVER}")
    print(f"  Port: {MQTT_PORT}")
    print(f"  Client ID: {MQTT_CLIENT_ID}")
    print(f"  Publish Topic: {MQTT_PUBLISH_TOPIC}")
    print(f"  Subscribe Topic: {MQTT_SUBSCRIBE_TOPIC}")
    print()


def display_can_config():
    """
    Display the CAN bus configuration settings.
    """
    print("CAN Bus Configuration:")
    print(f"  Bus Type: {CAN_BUS_TYPE}")
    print(f"  Channel: {CAN_CHANNEL}")
    print(f"  Bitrate: {CAN_BITRATE} bps")
    print()


def main():
    """
    Main function to demonstrate usage of configuration settings.
    """
    print("ROBOT_Monitor Configuration Usage Example")
    print("=" * 40)
    
    display_mqtt_config()
    display_can_config()
    
    # Example of using configuration in a practical context
    print("Example Usage:")
    print(f"Connecting to MQTT broker at {MQTT_SERVER}:{MQTT_PORT}")
    print(f"Subscribing to topic: {MQTT_SUBSCRIBE_TOPIC}")
    print(f"Initializing CAN bus with {CAN_BUS_TYPE} interface on channel {CAN_CHANNEL}")


if __name__ == "__main__":
    main()