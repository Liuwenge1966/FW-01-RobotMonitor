# -*- coding: utf-8 -*-
"""
MQTT消息主题和数据结构定义模块

该模块定义了机器人监控系统中使用的MQTT消息主题和数据结构，
包括控制命令和状态反馈两部分。

消息主题:
- 控制命令主题: ROBOT/{robot_id}/Control
- 状态反馈主题: ROBOT/{robot_id}/Status

数据结构:
- ctrlcmd_sendto_robot: 发送给机器人的控制命令
- status_from_robot: 从机器人接收的状态信息
"""

# MQTT主题定义
# 向机器人下发的控制命令主题
CONTROL_TOPIC = "ROBOT/{robot_id}/Control"

# 机器人向上位机发送的状态反馈主题
STATUS_TOPIC = "ROBOT/{robot_id}/Status"

# 向机器人下发的控制命令数据结构
ctrlcmd_sendto_robot = {
    "Robot_Id": "00",   # 机器人ID  "01"-"99"
    "Gear": 0,          # 档位: 整数类型，表示机器人的档位状态
    "Speed": 0.0,       # 车辆线速度: 浮点数类型，单位 m/s
    "Steer": 0.0,       # 车辆转向角: 浮点数类型，单位 弧度
    "SideSlip": 0.0     # 侧偏角: 浮点数类型，单位 弧度
}

# 机器人向上位机发的状态反馈数据结构
status_from_robot = {
    "robot_id": "00",                   # 机器人ID  "01"-"99"
    "Gear": 0,                          # 档位状态
    "Speed": 0.0,                       # 当前线速度 (m/s)
    "Steering_deg": 0.0,                # 当前转向角 (弧度)
    "SideSlip": 0.0,                    # 当前侧偏角 (弧度)
    "linear_velocity": 0.0,             # 线速度 (m/s)
    "angular_velocity": 0.0,            # 当前角速度(m/s)
    "battery_voltage": 0.0,             # 电池电压 (V)
    "battery_current": 0.0,             # 电池电流 (A)
    "battery_remaining_capacity": 0.0,  # 电池剩余容量 (Ah)
    "battery_max_temperature": 0.0,     # 电池最高温度 (°C)
    "battery_min_temperature": 0.0,     # 电池最低温度 (°C)
    "battery_soc_percent": 0.0,         # 电池剩余电量百分比 (%)
    "battery_is_charging": False        # 电池是否在充电 (布尔值)
}

# 档位映射表
GEAR_MAP = {
    "0": "DISABLE",
    "1": "驻车档",
    "2": "空挡",
    "4": "FR-档(未启用)",
    "6": "4T4D-档",
    "7": "横移-档"
}

def get_control_topic(robot_id: str) -> str:
    """
    获取指定机器人的控制命令主题
    
    :param robot_id: 机器人ID
    :return: 控制命令主题字符串
    """
    return CONTROL_TOPIC.format(robot_id=robot_id)

def get_status_topic(robot_id: str) -> str:
    """
    获取指定机器人的状态反馈主题
    
    :param robot_id: 机器人ID
    :return: 状态反馈主题字符串
    """
    return STATUS_TOPIC.format(robot_id=robot_id)

def create_control_command(robot_id: str = "00", gear: int = 0, speed: float = 0.0, steer: float = 0.0, side_slip: float = 0.0) -> dict:
    """
    创建一个控制命令对象
    :param robot_id: 机器人ID
    :param gear: 档位
    :param speed: 线速度 (m/s)
    :param steer: 转向角 (弧度)
    :param side_slip: 侧偏角 (弧度)
    :return: 控制命令字典
    """
    return {
        "robot_id": robot_id,
        "Gear": gear,
        "Speed": speed,
        "Steer": steer,
        "SideSlip": side_slip
    }

def create_status_feedback(robot_id: str = "00", gear: int = 0, speed: float = 0.0, steer: float = 0.0, side_slip: float = 0.0,
                          linear_velocity: float = 0.0, angular_velocity: float = 0.0, battery_voltage: float = 0.0, battery_current: float = 0.0,
                          battery_remaining_capacity: float = 0.0, battery_max_temperature: float = 0.0,
                          battery_min_temperature: float = 0.0, battery_soc_percent: float = 0.0,
                          battery_is_charging: bool = False) -> dict:
    """
    创建一个状态反馈对象
    :param robot_id: 机器人ID
    :param gear: 档位状态
    :param speed: 当前速度
    :param steer: 当前转向角
    :param side_slip: 当前侧偏角
    :param linear_velocity: 线速度
    :param angular_velocity: 角速度
    :param battery_voltage: 电池电压
    :param battery_current: 电池电流
    :param battery_remaining_capacity: 电池剩余容量
    :param battery_max_temperature: 电池最高温度
    :param battery_min_temperature: 电池最低温度
    :param battery_soc_percent: 电池剩余电量百分比
    :param battery_is_charging: 电池是否在充电
    :return: 状态反馈字典
    """
    return {
        "robot_id": robot_id,
        "Gear": gear,
        "Speed": speed,
        "Steer": steer,
        "SideSlip": side_slip,
        "linear_velocity": linear_velocity,
        "angular_velocity": angular_velocity,
        "battery_voltage": battery_voltage,
        "battery_current": battery_current,
        "battery_remaining_capacity": battery_remaining_capacity,
        "battery_max_temperature": battery_max_temperature,
        "battery_min_temperature": battery_min_temperature,
        "battery_soc_percent": battery_soc_percent,
        "battery_is_charging": battery_is_charging
    }