#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器人控制模块 - Edge端
该模块负责订阅MQTT控制命令消息，将其转换为CAN协议控制指令，并持续发送给机器人
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
        logging.FileHandler(os.path.join(log_dir, "edge_ctrl_robot.log")),
        logging.StreamHandler(sys.stdout)
    ]
)

# 导入配置
from src.config.settings import MQTT_SERVER, MQTT_PORT, MQTT_CLIENT_ID, CAN_BUS_TYPE, CAN_CHANNEL, CAN_BITRATE

# 导入协议处理类
from src.protocols.MQTTHandler import MQTTHandler
from src.protocols.CANBusHandler import CANBusHandler
from src.protocols.CAN_SendMsgEncoder import CtrlCmdPacker
from src.protocols.MQTT_Topics import get_control_topic, create_control_command

class EdgeCtrlRobot:
    """
    Edge端机器人控制器类
    负责接收MQTT控制命令并转换为CAN消息发送给机器人
    """
    # CAN消息的循环计数
    loop_count = 0
    # 定义一个自定义信号，用于跨线程传递CAN消息
    # message_received = QtCore.pyqtSignal(object)
    
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
        
        # 初始化日志记录器
        self.logger = logging.getLogger(f"EdgeCtrlRobot-{robot_id}")
        
        # 初始化MQTT和CAN处理器
        self.mqtt_handler = MQTTHandler(MQTT_SERVER, MQTT_PORT, MQTT_CLIENT_ID)
        self.can_handler = CANBusHandler(CAN_BUS_TYPE, CAN_CHANNEL, CAN_BITRATE)
        
        # 初始化CAN消息编码器
        self.ctrl_cmd_packer = CtrlCmdPacker()
        
        # 最新控制命令
        self.latest_control_command = create_control_command()
        
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
            robot_id = self.latest_control_command.get("Robot_Id", "00")
            gear = self.latest_control_command.get("Gear", 0)
            speed = self.latest_control_command.get("Speed", 0.0)
            steer = self.latest_control_command.get("Steer", 0.0)
            side_slip = self.latest_control_command.get("SideSlip", 0.0)
            
            if self.robot_id != robot_id:  # 检查机器人ID是否匹配
                self.logger.warning(f"机器人ID不匹配，当前机器人ID: {self.robot_id}, 控制命令机器人ID: {robot_id}，机器人停止运动。")
                self.SendCmd_Stop()
                return

            if gear == 0:  # 档位为0时，停止发送CAN消息
                self.logger.info("档位为0，停止发送CAN消息")
                self.SendCmd_Stop()
                return

            # 启动循环发送CAN消息
            self.SendCtrlCmd_Loop(gear, speed, steer, side_slip)
                
        except Exception as e:
            self.logger.error(f"发送CAN控制命令时出错: {e}")
    
    
    # 实现循环发送CAN控制命令
    def SendCtrlCmd_Loop(self, gear: int, speed: float, angular_velocity: float, side_bias_angle: float, interval: float = 0.02):
        # 检查是否已有线程在运行
        if self.thread_sendcom and self.thread_sendcom.is_alive():
            self.logger.warning("发送线程已在运行，无法重复启动,先停止以前的")
            self.SendCmd_Stop()
            # return

        # 启动一个新线程运行循环，避免阻塞主线程
        def run_loop():
            while True:
                if self.stop_event.is_set():
                    self.logger.info("指令发送进程未停止，指令发送被中断")
                    break
                # 发送ctrl_cmd 命令, 档位、车体速度、转向角速度、侧偏角
                # 修复变量名错误，应该使用self.ctrl_cmd_packer而不是self.CtrlCmdEncoder
                ddd = self.ctrl_cmd_packer.generate_message(gear, speed, angular_velocity, side_bias_angle)
                # 发送 steer_ctrl_cmd 命令，档位、车体速度、转向角度、侧偏角  （不好用，不知为何）
                # ddd = self.SteeringCtrlCmdEncoder.generate_message(gear, speed, angular_velocity, side_bias_angle)
                if self.can_handler.send_message(ddd.arbitration_id, ddd.data):
                    self.logger.debug("Ctrl cmd 已发送")
                else:
                    self.logger.warning("Ctrl cmd 发送失败")
                time.sleep(0.02)
            self.stop_event.clear()  # 循环结束后重置标志，以便下次使用
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
        if self.thread_sendcom :
            self.thread_sendcom .join()  # 可选：等待线程结束，但由于daemon=True，可省略
            self.thread_sendcom  = None
        self.logger.info("已停止CAN控制命令发送")
    
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
        
        time.sleep(1)

        self.logger.info("Edge端机器人控制器启动成功")
        
        # 主循环
        try:
            while self.running:
                # 每100ms发送一次CAN控制命令（保持机器人接收到最新的控制指令）
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
        
        # 断开CAN连接
        if self.can_handler.is_connected:
            self.logger.info("正在断开CAN连接...")
            # 修复方法调用错误，应该使用self.SendCmd_Stop()
            self.SendCmd_Stop()
            self.can_handler.disconnect()
        
        self.logger.info("Edge端机器人控制器已停止")

def main():
    """
    主函数
    """
    # 创建Edge端机器人控制器实例（假设机器人ID为01）
    controller = EdgeCtrlRobot(robot_id="01")
    
    # 启动控制器
    controller.start()

if __name__ == "__main__":
    main()