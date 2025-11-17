# -*- coding: utf-8 -*-
"""
Edge_GetRobotStatus.py - 机器人状态采集与MQTT发布模块

该模块负责从CAN总线读取机器人状态数据，解析后通过MQTT协议发布到云端。
主要功能包括：
1. 连接CAN总线并监听机器人状态消息
2. 解析CAN消息为结构化数据
3. 通过MQTT将状态信息发布到指定主题
4. 处理连接异常和重连机制
"""

import json
import time
import logging
from typing import Dict, Any
import paho.mqtt.client as mqtt
import can
import sys
import os

# Add the parent directory to the path so we can import the config module
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# 协议模块
from src.protocols.CANBusHandler import CANBusHandler
from src.protocols.MQTTHandler import MQTTHandler

# CAN消息解析模块
from src.protocols.CAN_RevMsgDecoder import CtrlFbDecoder,SteeringCtrlFbDecoder,BmsFbDecoder, BmsFlagFbDecoder

# MQTT消息定义 
from src.protocols.MQTT_Topics import (
    get_status_topic,
    status_from_robot
)

# 常量定义
from src.config.settings import (
    MQTT_SERVER, 
    MQTT_PORT, 
    MQTT_CLIENT_ID, 
    MQTT_PUBLISH_TOPIC, 
    MQTT_SUBSCRIBE_TOPIC,
    CAN_BUS_TYPE,
    CAN_CHANNEL,
    CAN_BITRATE
)

# 配置日志
import logging.handlers
import os

# 创建logs目录（如果不存在）
log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
os.makedirs(log_dir, exist_ok=True)

# 配置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 创建logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# 创建文件处理器，支持日志轮转
log_file = os.path.join(log_dir, 'robot_monitor.log')
file_handler = logging.handlers.RotatingFileHandler(
    log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# 添加处理器到logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# 机器人状态采集器
class EdgeGetRobotStatus:
    """
    边缘控制器 - 机器人状态采集模块
    """

    def __init__(self, robot_id: str = "01"):
        """
        初始化机器人状态采集器
        :param robot_id: 机器人ID，默认为"01"
        """
        self.robot_id = robot_id
        self.status_topic = get_status_topic(robot_id)
        
        # CAN总线相关
        self.can_handler = None
        #self.can_protocol = CANProtocol()
        
        # MQTT相关
        self.mqtt_client = None
        self.mqtt_broker = MQTT_SERVER
        self.mqtt_port = MQTT_PORT
        self.mqtt_connected = False
        
        # 初始化状态数据
        self.current_status = status_from_robot.copy()
        self.current_status['robot_id'] = robot_id

        self.running = False

    def setup_can_bus(self, bus_type: str = 'candle', channel: int = 0, bitrate: int = 500000) -> bool:
        """
        设置并连接CAN总线

        :param bus_type: CAN总线类型
        :param channel: CAN通道号
        :param bitrate: 波特率
        :return: 连接是否成功
        """
        try:
            self.can_handler = CANBusHandler(bus_type=bus_type, channel=channel, bitrate=bitrate)

            # 注册CAN消息处理回调
            self.can_handler.register_event_handler(self._on_can_message_received)
            
            # 尝试连接
            success = self.can_handler.connect()
            if success:
                logger.info("CAN总线连接成功")
            else:
                logger.error("CAN总线连接失败")
            return success
        except ImportError:
            logger.error("无法导入CANBusHandler模块")
            return False
        except Exception as e:
            logger.error(f"设置CAN总线时出错: {e}")
            return False

    def setup_mqtt(self, broker: str = "localhost", port: int = 1883, username: str = None, password: str = None) -> bool:
        """
        设置MQTT客户端连接参数
        
        :param broker: MQTT代理地址
        :param port: MQTT代理端口
        :param username: 用户名（可选）
        :param password: 密码（可选）
        :return: 设置是否成功
        """
        try:
            self.mqtt_broker = broker
            self.mqtt_port = port
            
            # 创建MQTT客户端
            self.mqtt_client = MQTTHandler(broker, port,"Robot_"+self.robot_id)
            logger.info(f"MQTT客户端设置完成: {broker}:{port}:Robot_{self.robot_id}")
            return True
        except Exception as e:
            logger.error(f"设置MQTT客户端时出错: {e}")
            return False

    def connect_mqtt(self) -> bool:
        """
        连接到MQTT代理
        :return: 连接是否成功
        """
        try:
            if self.mqtt_client is None:
                logger.error("MQTT客户端未初始化，请先调用setup_mqtt()")
                return False
            
            if not self.mqtt_client.connect():
                logger.info("连接到MQTT代理失败"+self.mqtt_client.strConnStatus)
                return False
            
            # 启动MQTT循环
            self.mqtt_client.start_publishing(self.status_topic, self.current_status,0.5)
            logger.info("connect_mqtt：MQTT客户端启动成功")
            return True

        except Exception as e:
            logger.error(f"connect_mqtt：连接MQTT代理时出错: {e}")
            return False

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """
        MQTT连接回调函数
        """
        if rc == 0:
            self.mqtt_connected = True
            logger.info("成功连接到MQTT代理")
        else:
            self.mqtt_connected = False
            logger.error(f"无法连接到MQTT代理，返回码: {rc}")

    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """
        MQTT断开连接回调函数
        """
        self.mqtt_connected = False
        logger.warning("与MQTT代理断开连接")

    # CAN消息处理
    def _on_can_message_received(self, message):
        """
        CAN消息接收回调函数
        
        :param message: 接收到的CAN消息
        """
        try:
            # 解析CAN消息，并更新本地缓存
            self.handle_canmsg_to_mqttmsg(message)

            # 更新状态数据，提交发送
            self.mqtt_client.update_publish_data(self.status_topic, self.current_status)
        except Exception as e:
            logger.error(f"处理CAN消息时出错: {e}")

    def handle_canmsg_to_mqttmsg(self, msg: can.Message):
        # 在UI中处理接收到的CAN消息
        if msg.arbitration_id == 0x18C4D2EF:  # steering_ctrl_fb
            ddd = SteeringCtrlFbDecoder().parse_steering_ctrl_fb(msg)
            # 刷新接收到的CAN消息json
            self.current_status.update({
                "Gear": ddd["gear"],
                "Speed": ddd["speed_mps"],
                "Steering_deg": ddd["steering_deg"],
                "SideSlip": ddd["side_slip_angle_deg"]
            })

        elif msg.arbitration_id == 0x18C4D1EF: # ctrl_fb
            ddd = CtrlFbDecoder().parse_ctrl_cmd(msg)
            # 更新接收到的CAN消息json
            self.current_status.update({
                "Gear": ddd["gear"],
                "Speed": ddd["linear_velocity_mps"],
                "angular_velocity": ddd["angular_velocity_dps"],
                "SideSlip": ddd["side_slip_angle_deg"]
            })

        elif msg.arbitration_id == 0x18C4E1EF: # bms_fb
            ddd = BmsFbDecoder().parse_bms_fb(msg)
            # 刷新接收到的CAN消息json
            self.current_status.update({
                "battery_voltage": ddd["voltage_v"],
                "battery_current": ddd["current_a"],
                "battery_remaining_capacity": ddd["remaining_capacity_ah"]
            })

        elif msg.arbitration_id == 0x18C4E2EF: # bms_flag_fb
            ddd = BmsFlagFbDecoder().parse_bms_flag_fb(msg)
            # 刷新接收到的CAN消息json
            self.current_status.update({
                "battery_soc_percent": ddd["soc_percent"],
                "battery_max_temperature": ddd["max_temp_c"],
                "battery_min_temperature": ddd["min_temp_c"],
                "battery_is_charging": ddd["is_charging"]
            })
           
    def publish_status(self) -> bool:
        """
        将当前机器人状态发布到MQTT主题
        
        :return: 发布是否成功
        """
        if not self.mqtt_connected:
            logger.warning("MQTT未连接，无法发布状态")
            return False
            
        try:
            # 将状态数据转换为JSON格式
            payload = json.dumps(self.current_status)
            
            # 发布到MQTT主题
            result = self.mqtt_client.publish(self.status_topic, payload, qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"状态已发布到 {self.status_topic}")
                return True
            else:
                logger.error(f"发布状态失败，错误码: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"发布状态时出错: {e}")
            return False

    def start(self) -> bool:
        """
        启动状态采集服务
        
        :return: 启动是否成功
        """
        try:
            # 检查必要组件是否已设置
            if self.can_handler is None:
                logger.error("CAN总线未设置或连接错位，请先调用setup_can_bus()")
                return False
            logger.info("CAN总线已连接")
                
            if self.mqtt_client is None:
                logger.error("MQTT客户端未设置，请先调用setup_mqtt()")
                return False
            
            # 连接MQTT（如果尚未连接）
            if not self.mqtt_connected:
                if not self.connect_mqtt():
                    logger.error("无法连接到MQTT代理")
                    return False
                # 启动MQTT 消息发布循环
                self.mqtt_client.start_publishing(self.status_topic, self.current_status, 0.5)
                logger.info("已连接到MQTT代理")
            
            # 标记为运行状态
            self.running = True
            logger.info("机器人状态采集服务已启动")
            return True
        except Exception as e:
            logger.error(f"启动服务时出错: {e}")
            return False

    def stop(self):
        """
        停止状态采集服务
        """
        try:
            self.running = False
            
            # 断开MQTT连接
            if self.mqtt_client:
                self.mqtt_client.disconnect()
            
            # 断开CAN总线连接
            if self.can_handler:
                self.can_handler.disconnect()
                
            logger.info("机器人状态采集服务已停止")
        except Exception as e:
            logger.error(f"停止服务时出错: {e}")

    def run_once(self):
        """
        执行一次状态采集和发布（用于测试）
        """
        try:
            # 这里可以添加手动触发状态更新的逻辑
            # 在实际应用中，状态更新由CAN消息事件驱动
            pass
        except Exception as e:
            logger.error(f"执行单次采集时出错: {e}")


def main():
    """
    主函数 - 示例用法
    """
    # 创建机器人状态采集器实例
    status_collector = EdgeGetRobotStatus(robot_id="01")
    
    # 设置CAN总线
    if not status_collector.setup_can_bus(bus_type=CAN_BUS_TYPE, channel=CAN_CHANNEL, bitrate=CAN_BITRATE):
        logger.error("无法设置CAN总线，程序退出。")
        return
    
    # 设置MQTT
    if not status_collector.setup_mqtt(broker=MQTT_SERVER, port=MQTT_PORT):
        logger.error("无法设置MQTT客户端，程序退出。")
        return
    
    # 启动服务
    if not status_collector.start():
        logger.error("无法启动服务，程序退出。")
        return
    
    try:
        # 保持运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到退出信号")
    finally:
        # 清理资源
        status_collector.stop()


if __name__ == "__main__":
    main()

