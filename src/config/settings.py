# -*- coding: utf-8 -*-
"""
System configuration settings for ROBOT_Monitor application.
Contains MQTT and CAN bus configuration parameters.
"""

# MQTT Configuration
MQTT_SERVER = "192.168.12.117"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "mqttx_d49724d2"
MQTT_PUBLISH_TOPIC = "Robot01_Status"
MQTT_SUBSCRIBE_TOPIC = "Robot01_CtrlCmd"

# CAN Bus Configuration
CAN_BUS_TYPE = "candle"
CAN_CHANNEL = 0
CAN_BITRATE = 500000

