# ROBOT_Monitor - 机器人远程监控系统

这是一个基于MQTT协议的机器人远程监控系统，采用了云-边-端协同的设计架构。该系统实现了对机器人状态的远程监视和运动控制指令的下发。

## 系统架构概述

系统由以下几个核心组件构成：

1. **远程监控UI** (`src/monitor_ui`) - 用户交互界面，运行在远程PC上
2. **MQTT代理** - 消息中枢，负责所有通信数据的路由
3. **边缘控制器** (`src/edge_controller`) - 部署在边缘设备上，负责协议转换
4. **机器人底层控制系统** - 直接与机器人硬件交互的执行单元
5. **通信网络** - 连接上述所有组件的网络基础设施

### 数据流向

- **上行链路(状态监控)**: 机器人状态数据 → 边缘控制器 → MQTT代理 → 远程监控UI
- **下行链路(控制指令)**: 远程监控UI → MQTT代理 → 边缘控制器 → 机器人执行机构

## 项目结构
ROBOT_Monitor/ ├── src/ # 源代码目录 │ ├── config/ # 系统配置文件 │ ├── edge_controller/ # 边缘控制器模块 │ ├── monitor_ui/ # 远程监控用户界面 │ └── protocols/ # 通信协议处理模块 ├── scripts/ # 系统脚本 ├── tests/ # 测试文件 ├── docs/ # 文档资料 ├── logs/ # 日志文件 ├── main.py # 程序入口 ├── build.py # 项目构建脚本 └── requirements.txt # 依赖包列表


## 核心组件详解

### 1. 远程监控程序 (`src/monitor_ui`)

**角色定位**: 系统的人机交互界面，提供可视化监控和控制功能。

**主要特性**:
- 图形用户界面，基于PyQt5开发
- 实时显示机器人状态信息（电池电量、温度等）
- 提供控制面板，可发送控制指令
- 支持多种主题（默认主题和科幻主题）
- 集成MQTT客户端，实现与MQTT代理的通信

**主要文件**:
- [RobotMonitor.py](file://e:\CANable%20USB-CAN\MyTest\ROBOT_Monitor\src\monitor_ui\RobotMonitor.py): 主程序文件，包含主要的UI逻辑和MQTT通信处理
- [main_window.py](file://e:\CANable%20USB-CAN\MyTest\ROBOT_Monitor\src\monitor_ui\main_window.py): UI界面定义文件，由Qt Designer生成
- [main_window.ui](file://e:\CANable%20USB-CAN\MyTest\ROBOT_Monitor\src\monitor_ui\main_window.ui): Qt Designer界面设计文件

### 2. MQTT代理

**角色定位**: 系统的消息路由中心，采用发布-订阅模式。

**主要功能**:
- 主题管理（`ROBOT/{robot_id}/Status` 和 `ROBOT/{robot_id}/Control`）
- 消息路由分发
- 客户端连接管理

### 3. 边缘控制器 (`src/edge_controller`)

**角色定位**: 协议转换器和实时控制处理器。

**主要文件**:
- [EdgeRobotController.py](file://e:\CANable%20USB-CAN\MyTest\ROBOT_Monitor\src\edge_controller\EdgeRobotController.py): 综合控制器，负责双向通信（MQTT ↔ CAN）

**主要功能**:
- 订阅MQTT控制命令主题
- 将控制指令转换为CAN消息
- 通过CAN总线发送控制指令给机器人
- 通过CAN总线从机器人读取状态数据
- 解析CAN消息为结构化数据
- 通过MQTT将状态信息发布到指定主题

### 4. 通信协议处理模块 (`src/protocols`)

**主要组件**:
- [MQTTHandler.py](file://e:\CANable%20USB-CAN\MyTest\ROBOT_Monitor\src\protocols\MQTTHandler.py) - MQTT通信处理封装
- [CANBusHandler.py](file://e:\CANable%20USB-CAN\MyTest\ROBOT_Monitor\src\protocols\CANBusHandler.py) - CAN总线通信处理封装
- [MQTT_Topics.py](file://e:\CANable%20USB-CAN\MyTest\ROBOT_Monitor\src\protocols\MQTT_Topics.py) - MQTT主题和数据结构定义
- [CAN_RevMsgDecoder.py](file://e:\CANable%20USB-CAN\MyTest\ROBOT_Monitor\src\protocols\CAN_RevMsgDecoder.py) - CAN接收消息解析器
- [CAN_SendMsgEncoder.py](file://e:\CANable%20USB-CAN\MyTest\ROBOT_Monitor\src\protocols\CAN_SendMsgEncoder.py) - CAN发送消息编码器

## 配置说明

系统配置文件位于 `src/config/settings.py`，主要包括：

- MQTT服务器地址和端口
- CAN总线类型、通道和波特率

默认配置如下：
```python
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

安装与运行
安装依赖：
pip install -r requirements.txt

修改配置文件 src/config/settings.py 中的MQTT和CAN参数

运行监控界面：
python main.py

在边缘设备上运行边缘控制器：
python src/edge_controller/EdgeRobotController.py

系统优势
解耦设计: 通过MQTT发布-订阅模式，实现各组件间的松耦合
实时性: 边缘控制器负责实时性要求高的CAN通信
可扩展性: 易于添加更多监控终端或机器人节点
标准化: 使用JSON作为数据交换格式，便于集成和调试
双向通信: 支持状态监控和控制指令下发的双向通信
用户友好: 提供图形化界面和多种主题选择