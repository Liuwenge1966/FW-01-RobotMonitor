#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器人控制器模块 - Edge端
该模块负责订阅MQTT控制命令消息，将其转换为CAN协议控制指令发送给机器人，
同时从CAN总线读取机器人状态数据，解析后通过MQTT协议发布到云端。
"""

import json
import signal
import sys
import time
import threading
import logging
import os
from typing import Dict, Any

# 将项目根目录添加到Python路径中
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# 配置日志
# 确保logs目录存在
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "edge_robot_controller.log")),
        logging.StreamHandler(sys.stdout)
    ]
)

# 导入配置
from src.config.settings import MQTT_SERVER, MQTT_PORT, MQTT_CLIENT_ID, CAN_BUS_TYPE, CAN_CHANNEL, CAN_BITRATE

# 导入协议处理类
from src.protocols.MQTTHandler import MQTTHandler
from src.protocols.CANBusHandler import CANBusHandler
from src.protocols.CAN_SendMsgEncoder import CtrlCmdPacker
from src.protocols.MQTT_Topics import get_control_topic, get_status_topic, create_control_command

# CAN消息解析模块
from src.protocols.CAN_RevMsgDecoder import CtrlFbDecoder, SteeringCtrlFbDecoder, BmsFbDecoder, BmsFlagFbDecoder

class EdgeRobotController:
    """
    Edge端机器人控制器类
    负责接收MQTT控制命令并转换为CAN消息发送给机器人，
    同时从CAN总线读取机器人状态数据并通过MQTT发布
    """
    # CAN消息的循环计数
    loop_count = 0
    
    # 添加CAN发送线程引用，用于检查是否在运行
    thread_sendcom = None  
    # 添加停止CAN发送事件标志
    stop_event = threading.Event()  

    def __init__(self, robot_id: str = "01"):
        """
        初始化Edge端机器人控制器
        
        :param robot_id: 机器人ID
        """
        self.robot_id = robot_id
        self.control_topic = get_control_topic(robot_id)
        self.status_topic = get_status_topic(robot_id)
        
        # 初始化日志记录器
        self.logger = logging.getLogger(f"EdgeRobotController-{robot_id}")
        
        # 初始化MQTT和CAN处理器
        self.mqtt_handler = MQTTHandler(MQTT_SERVER, MQTT_PORT, f"Robot_{robot_id}")
        self.can_handler = CANBusHandler(CAN_BUS_TYPE, CAN_CHANNEL, CAN_BITRATE)
        
        # 初始化CAN消息编码器
        self.ctrl_cmd_packer = CtrlCmdPacker()
        
        # 收到的最新控制命令
        self.latest_control_command = create_control_command()
        # 初始化向机器人发送的CAN消息
        self.latest_msg_to_can = self.ctrl_cmd_packer.generate_message(0, 0.0, 0.0, 0.0)
        
        # 初始化状态数据
        self.current_status = {
            "robot_id": robot_id,
            "Gear": 0,
            "Speed": 0.0,
            "Steering_deg": 0.0,
            "SideSlip": 0.0,
            "linear_velocity": 0.0,
            "angular_velocity": 0.0,
            "battery_voltage": 0.0,
            "battery_current": 0.0,
            "battery_remaining_capacity": 0.0,
            "battery_max_temperature": 0.0,
            "battery_min_temperature": 0.0,
            "battery_soc_percent": 0.0,
            "battery_is_charging": False
        }
        
        # 运行状态标志
        self.running = True
        
        # 注册信号处理器以优雅地关闭程序
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """
        信号处理器，用于优雅地关闭程序
        """
        self.logger.info(f"接收到信号 {signum}，正在关闭程序...")
        self.running = False
        self.stop()
        sys.exit(0)
    
    def _on_control_message(self, topic: str, payload: Dict[str, Any]):
        """
        MQTT控制消息回调函数
        :param topic: 消息主题
        :param payload: 消息内容
        """
        try:
            self.logger.info(f"收到控制命令: {payload}")
            # 更新最新的控制命令
            self.latest_control_command = payload
            # 立即生成并发送一次CAN消息
            self._send_can_control_message()
            
        except Exception as e:
            self.logger.error(f"处理控制命令时出错: {e}")
    
    def _send_can_control_message(self):
        """
        将最新的控制命令转换为CAN消息并发送
        """
        try:
            # 从控制命令中提取参数
            robot_id = self.latest_control_command.get("robot_id", "00")
            gear = self.latest_control_command.get("Gear", 0)
            speed = self.latest_control_command.get("Speed", 0.0)
            steer = self.latest_control_command.get("Steer", 0.0)
            side_slip = self.latest_control_command.get("SideSlip", 0.0)
            if self.robot_id != robot_id:  # 检查机器人ID是否匹配
                self.logger.warning(f"机器人ID不匹配，当前机器人ID: {self.robot_id}, 控制命令机器人ID: {robot_id}。指令忽略。")
                return
            
            # 生成CAN消息
            self.latest_msg_to_can = self.ctrl_cmd_packer.generate_message(gear, speed, steer, side_slip)
            
            # 如果发送线程未运行，则启动它
            if not self.thread_sendcom or not self.thread_sendcom.is_alive():
                self.SendCtrlCmd_Loop()
        except Exception as e:
            self.logger.error(f"发送CAN控制命令时出错: {e}")
   
    def SendCtrlCmd_Loop(self, interval: float = 0.02):
        # 检查是否已有线程在运行
        if self.thread_sendcom and self.thread_sendcom.is_alive():
            self.logger.debug("发送线程已在运行，使用现有线程")
            return

        # 启动一个新线程运行循环，避免阻塞主线程
        def run_loop():
            while True:
                
                if self.stop_event.is_set():
                    self.logger.info("run_loop: 指令发送进程已停止")
                    break

                # 从控制命令中提取参数
                robot_id = self.latest_control_command.get("robot_id", "00")
                gear = self.latest_control_command.get("Gear", 0)
                speed = self.latest_control_command.get("Speed", 0.0)
                steer = self.latest_control_command.get("Steer", 0.0)
                side_slip = self.latest_control_command.get("SideSlip", 0.0)
                if self.robot_id != robot_id:  # 检查机器人ID是否匹配
                    self.logger.warning(f"机器人ID不匹配，当前机器人ID: {self.robot_id}, 控制命令机器人ID: {robot_id}。指令忽略。")
                    return
        
                # 生成CAN消息
                ddd = self.ctrl_cmd_packer.generate_message(gear, speed, steer, side_slip)
                # self.logger.info(f"run_loop: 指令发送进程is running + {ddd.arbitration_id}")
                # # 发送ctrl_cmd 命令, 档位、车体速度、转向角速度、侧偏角
                if self.can_handler.send_message(ddd.arbitration_id, ddd.data):
                    #self.logger.info("run_loop: Ctrl cmd 已发送")
                    pass
                else:
                    #self.logger.info("run_loop: Ctrl cmd 发送失败")
                    pass
                time.sleep(0.02)
            # 注意：这里不清除stop_event，这样可以真正停止线程
            self.thread_sendcom = None  # 重置线程引用

        # 清空停止标志（如果之前设置过）
        self.stop_event.clear()
        # 启动线程
        self.thread_sendcom = threading.Thread(target=run_loop, daemon=True)
        self.thread_sendcom.start()
        self.logger.info("已启动CAN控制命令循环发送线程")
  
    def SendCmd_Stop(self):
        # 设置停止发送CAN指令标志，关闭线程
        self.stop_event.set()
        if self.thread_sendcom and self.thread_sendcom.is_alive():
            self.thread_sendcom.join(timeout=1.0)  # 等待线程结束，最多等待1秒
        self.thread_sendcom = None
        self.logger.info("已停止CAN控制命令发送")
        # 不再清除stop_event，保持设置状态
    # def SendCmd_Stop(self):
    #     # 设置停止发送CAN指令标志，关闭线程
    #     self.stop_event.set()
    #     if self.thread_sendcom and self.thread_sendcom.is_alive():
    #         self.thread_sendcom.join(timeout=1.0)  # 等待线程结束，最多等待1秒
    #     self.thread_sendcom = None
    #     self.logger.info("已停止CAN控制命令发送")
    #     self.stop_event.clear()

    def _on_can_message_received(self, message):
        """
        CAN消息接收回调函数
        
        :param message: 接收到的CAN消息
        """
        try:
            # 解析CAN消息，并更新本地缓存
            self.handle_canmsg_to_mqttmsg(message)

            # 更新状态数据，提交发送
            self.mqtt_handler.update_publish_data(self.status_topic, self.current_status)
        except Exception as e:
            self.logger.error(f"处理CAN消息时出错: {e}")
    
    def handle_canmsg_to_mqttmsg(self, msg):
        """
        处理接收到的CAN消息并转换为MQTT状态数据
        
        :param msg: CAN消息
        """
        try:
            if msg.arbitration_id == 0x18C4D2EF:  # steering_ctrl_fb
                ddd = SteeringCtrlFbDecoder().parse_steering_ctrl_fb(msg)
                # 刷新接收到的CAN消息json
                self.current_status.update({
                    "Gear": ddd["gear"],
                    "Speed": ddd["speed_mps"],
                    "Steering_deg": ddd["steering_deg"],
                    "SideSlip": ddd["side_slip_angle_deg"]
                })

            elif msg.arbitration_id == 0x18C4D1EF:  # ctrl_fb
                ddd = CtrlFbDecoder().parse_ctrl_cmd(msg)
                # 更新接收到的CAN消息json
                self.current_status.update({
                    "Gear": ddd["gear"],
                    "Speed": ddd["linear_velocity_mps"],
                    "angular_velocity": ddd["angular_velocity_dps"],
                    "SideSlip": ddd["side_slip_angle_deg"]
                })

            elif msg.arbitration_id == 0x18C4E1EF:  # bms_fb
                ddd = BmsFbDecoder().parse_bms_fb(msg)
                # 刷新接收到的CAN消息json
                self.current_status.update({
                    "battery_voltage": ddd["voltage_v"],
                    "battery_current": ddd["current_a"],
                    "battery_remaining_capacity": ddd["remaining_capacity_ah"]
                })

            elif msg.arbitration_id == 0x18C4E2EF:  # bms_flag_fb
                ddd = BmsFlagFbDecoder().parse_bms_flag_fb(msg)
                # 刷新接收到的CAN消息json
                self.current_status.update({
                    "battery_soc_percent": ddd["soc_percent"],
                    "battery_max_temperature": ddd["max_temp_c"],
                    "battery_min_temperature": ddd["min_temp_c"],
                    "battery_is_charging": ddd["is_charging"]
                })
        except Exception as e:
            self.logger.error(f"解析CAN消息时出错: {e}")
    
    def start(self):
        """
        启动Edge端机器人控制器
        """
        self.logger.info("正在启动Edge端机器人控制器...")
        
        # 连接MQTT
        self.logger.info("正在连接MQTT服务器...")
        if not self.mqtt_handler.connect():
            self.logger.error("MQTT连接失败")
            self.stop()
            return False
        
        time.sleep(1)
        
        # 订阅控制命令主题
        self.logger.info(f"正在订阅控制命令主题: {self.control_topic}")
        if not self.mqtt_handler.subscribe(self.control_topic, self._on_control_message, "json"):
            self.logger.error("订阅控制命令主题失败")
            self.stop()
            return False

        # 连接CAN
        self.logger.info("正在连接CAN总线...")
        if not self.can_handler.connect():
            self.logger.error("CAN总线连接失败")
            self.stop()
            return False
        
        # 注册CAN消息处理回调
        self.can_handler.register_event_handler(self._on_can_message_received)
        
        time.sleep(1)
        # 启动循环发送CAN消息
        self.SendCtrlCmd_Loop()

        time.sleep(1)
        # 启动状态数据MQTT发布
        self.logger.info(f"正在启动状态数据发布到主题: {self.status_topic}")
        if not self.mqtt_handler.start_publishing(self.status_topic, self.current_status, 0.5):
            self.logger.error("启动状态数据发布失败")
            self.stop()
            return False

        self.logger.info("Edge端机器人控制器启动成功")
        
        # 主循环
        try:
            while self.running:
                # 每100ms检查一次
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.logger.info("接收到中断信号")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """
        停止Edge端机器人控制器
        """
        self.logger.info("正在停止Edge端机器人控制器...")
        
        # 断开MQTT连接
        if self.mqtt_handler.is_connected:
            self.logger.info("正在断开MQTT连接...")
            self.mqtt_handler.disconnect()
        
        # 停止发送CAN命令
        self.SendCmd_Stop()
        
        # 断开CAN连接
        if self.can_handler.is_connected:
            self.logger.info("正在断开CAN连接...")
            self.can_handler.disconnect()
        
        self.logger.info("Edge端机器人控制器已停止")

def main():
    """
    主函数
    """
    # 创建Edge端机器人控制器实例（假设机器人ID为01）
    controller = EdgeRobotController(robot_id="01")
    
    # 启动控制器
    controller.start()

if __name__ == "__main__":
    main()