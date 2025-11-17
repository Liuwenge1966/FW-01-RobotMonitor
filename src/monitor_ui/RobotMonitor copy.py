import sys
import os
import json
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QListWidgetItem, QAction, QMenu
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QPalette

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.monitor_ui.main_window import Ui_MainWindow
from src.protocols.MQTTHandler import MQTTHandler
from src.protocols.MQTT_Topics import get_control_topic, get_status_topic, create_control_command, GEAR_MAP


class RobotMonitor(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        # 初始化MQTT处理器
        self.mqtt_handler = MQTTHandler()
        
        # 当前机器人ID
        self.current_robot_id = self.lineEdit_RobotID.text()
        
        # 当前控制命令
        self.current_control_cmd = create_control_command(
            robot_id=self.current_robot_id,
            gear=6,  # 默认4T4D档
            speed=0.0,
            steer=0.0,
            side_slip=0.0
        )
        
        # 定时发布控制命令的标识
        self.is_sending_commands = False
        
        # 当前主题
        self.current_theme = "default"
        
        # 创建主题菜单
        self.create_theme_menu()
        
        # 连接信号和槽
        self.setup_connections()
        
        # 更新界面状态
        self.update_connection_status()
        
    def create_theme_menu(self):
        """创建主题菜单"""
        # 创建视图菜单
        view_menu = self.menuBar().addMenu("视图")
        
        # 创建主题子菜单
        theme_menu = view_menu.addMenu("主题")
        
        # 默认主题动作
        default_theme_action = QAction("默认", self)
        default_theme_action.triggered.connect(lambda: self.set_theme("default"))
        theme_menu.addAction(default_theme_action)
        
        # 科幻主题动作
        sci_fi_theme_action = QAction("科幻", self)
        sci_fi_theme_action.triggered.connect(lambda: self.set_theme("sci-fi"))
        theme_menu.addAction(sci_fi_theme_action)
        
    def set_theme(self, theme):
        """设置界面主题"""
        self.current_theme = theme
        
        if theme == "sci-fi":
            self.apply_sci_fi_theme()
        else:
            self.apply_default_theme()
            
    def apply_sci_fi_theme(self):
        """应用科幻主题"""
        # 设置整体样式表
        sci_fi_style = """
        QMainWindow {
            background-color: #0d1b2a;
            color: #e0e1dd;
        }
        
        QWidget {
            background-color: #0d1b2a;
            color: #e0e1dd;
            font-family: "Courier New", monospace;
        }
        
        QGroupBox {
            border: 2px solid #415a77;
            border-radius: 8px;
            margin-top: 1ex;
            font-weight: bold;
            color: #778da9;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        
        QPushButton {
            background-color: #1b263b;
            border: 2px solid #415a77;
            border-radius: 10px;
            padding: 8px;
            color: #e0e1dd;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #415a77;
            border: 2px solid #778da9;
        }
        
        QPushButton:pressed {
            background-color: #778da9;
            border: 2px solid #e0e1dd;
        }
        
        QPushButton:disabled {
            background-color: #1b263b;
            border: 2px solid #2d3748;
            color: #778da9;
        }
        
        QLabel {
            color: #e0e1dd;
        }
        
        QLineEdit {
            background-color: #1b263b;
            border: 2px solid #415a77;
            border-radius: 5px;
            padding: 5px;
            color: #e0e1dd;
        }
        
        QListWidget {
            background-color: #1b263b;
            border: 2px solid #415a77;
            border-radius: 5px;
            color: #e0e1dd;
        }
        
        QListWidget::item {
            padding: 3px;
        }
        
        QListWidget::item:selected {
            background-color: #415a77;
        }
        
        QRadioButton {
            color: #e0e1dd;
        }
        
        QMenuBar {
            background-color: #1b263b;
            color: #e0e1dd;
            border-bottom: 1px solid #415a77;
        }
        
        QMenuBar::item {
            background: transparent;
            padding: 5px 10px;
        }
        
        QMenuBar::item:selected {
            background: #415a77;
        }
        
        QMenuBar::item:pressed {
            background: #778da9;
        }
        
        QMenu {
            background-color: #1b263b;
            color: #e0e1dd;
            border: 1px solid #415a77;
        }
        
        QMenu::item {
            padding: 5px 20px;
        }
        
        QMenu::item:selected {
            background-color: #415a77;
        }
        
        QStatusBar {
            background-color: #1b263b;
            color: #e0e1dd;
            border-top: 1px solid #415a77;
        }
        """
        
        self.setStyleSheet(sci_fi_style)
        
        # 设置字体
        font = QFont("Courier New", 9)
        QApplication.setFont(font)
        
        # 更新状态标签样式
        self.lb_ConnectStatus.setStyleSheet("color: #4CAF50; font-weight: bold;")
        
    def apply_default_theme(self):
        """应用默认主题"""
        # 清除样式表
        self.setStyleSheet("")
        
        # 恢复默认字体
        font = QFont()
        QApplication.setFont(font)
        
        # 更新连接状态显示
        self.update_connection_status()
        
    def setup_connections(self):
        """连接信号和槽"""
        # MQTT连接相关
        self.btn_MQTT_Connect.clicked.connect(self.connect_mqtt)
        self.btn_MQTT_Disconnect.clicked.connect(self.disconnect_mqtt)
        
        # 退出按钮
        self.btnExit.clicked.connect(self.close_application)
        
        # 控制按钮
        self.btn_GoForward.clicked.connect(lambda: self.set_movement(speed=0.1, steer=0.0))
        self.btn_GoBack.clicked.connect(lambda: self.set_movement(speed=-0.1, steer=0.0))
        self.btn_TurnLeft.clicked.connect(lambda: self.set_movement(speed=0.0, steer=90))
        self.btn_TurnRight.clicked.connect(lambda: self.set_movement(speed=0.0, steer=-90))
        self.btn_Stop.clicked.connect(lambda: self.set_movement(speed=0.0, steer=0.0))
        self.btn_HeadLeft.clicked.connect(lambda: self.set_movement(speed=0.1, steer=25))
        self.btn_HeadRight.clicked.connect(lambda: self.set_movement(speed=0.1, steer=-25))
        self.btn_BackLeft.clicked.connect(lambda: self.set_movement(speed=-0.1, steer=-25))
        self.btn_BackRight.clicked.connect(lambda: self.set_movement(speed=-0.1, steer=25))
        
        # 档位选择
        self.Radio_Gear_4T4D.toggled.connect(self.update_gear_selection)
        self.Radio_Gear_Side.toggled.connect(self.update_gear_selection)
        
        # 停止发送命令
        self.btn_StopCmd.clicked.connect(self.stop_sending_commands)
        
        # 机器人ID更改
        self.lineEdit_RobotID.textChanged.connect(self.robot_id_changed)
        
    def connect_mqtt(self):
        """连接MQTT服务器"""
        try:
            broker_address = self.lineEdit_MQTTServer.text()
            broker_port = int(self.lineEdit_MQTTPort.text())
            
            # 设置MQTT代理信息
            self.mqtt_handler.set_broker(broker_address, broker_port)
            
            # 连接MQTT服务器
            if self.mqtt_handler.connect():
                # 订阅状态主题
                status_topic = get_status_topic(self.current_robot_id)
                self.mqtt_handler.subscribe(status_topic, self.on_status_message, "json")
                
                # 更新界面状态
                self.lb_ConnectStatus.setText("已连接")
                if self.current_theme == "sci-fi":
                    self.lb_ConnectStatus.setStyleSheet("color: #4CAF50; font-weight: bold;")
                else:
                    self.lb_ConnectStatus.setStyleSheet("color: green")
                
                QMessageBox.information(self, "连接成功", "MQTT服务器连接成功！")
            else:
                QMessageBox.critical(self, "连接失败", "无法连接到MQTT服务器！")
                
        except Exception as e:
            QMessageBox.critical(self, "连接错误", f"连接MQTT服务器时发生错误：{str(e)}")
    
    def disconnect_mqtt(self):
        """断开MQTT连接"""
        try:
            if self.mqtt_handler.disconnect():
                self.lb_ConnectStatus.setText("未连接")
                if self.current_theme == "sci-fi":
                    self.lb_ConnectStatus.setStyleSheet("color: #F44336; font-weight: bold;")
                else:
                    self.lb_ConnectStatus.setStyleSheet("color: red")
                QMessageBox.information(self, "断开连接", "已成功断开MQTT连接！")
            else:
                QMessageBox.warning(self, "断开失败", "断开MQTT连接时出现问题！")
        except Exception as e:
            QMessageBox.critical(self, "断开错误", f"断开MQTT连接时发生错误：{str(e)}")
    
    def on_status_message(self, topic, data):
        """处理来自机器人的状态消息"""
        try:
            # 在接收消息列表中显示原始数据
            item = QListWidgetItem(json.dumps(data, ensure_ascii=False))
            self.lvRevMsg.addItem(item)
            self.lvRevMsg.scrollToBottom()
            
            # 更新各个状态显示标签
            self.lb_Gear.setText(f"当前档位：{GEAR_MAP.get(data.get('Gear', 0), '未知')}")
            self.lb_Speed.setText(f"当前车体线速度(m/s)：{data.get('Speed', 0.0):.2f}")
            self.lb_Steer.setText(f"当前车体转向角(°)：{data.get('Steering_deg', 0.0):.2f}")
            self.lb_SideSlip.setText(f"当前车体侧偏角(°)：{data.get('SideSlip', 0.0):.2f}")
            self.lb_Angular_Velocity.setText(f"当前车体角速度(度/s)：{data.get('angular_velocity', 0.0):.2f}")
            self.lb_battery_voltage.setText(f"当前电池电压(V)：{data.get('battery_voltage', 0.0):.2f}")
            self.lb_battery_current.setText(f"当前电池电流(a)：{data.get('battery_current', 0.0):.2f}")
            self.lb_battery_remaining_capacity.setText(f"当前电池剩余容量(Ah)：{data.get('battery_remaining_capacity', 0.0):.2f}")
            self.lb_battery_max_temperature.setText(f"当前电池最高温度(C°)：{data.get('battery_max_temperature', 0.0):.1f}")
            self.lb_battery_min_temperature.setText(f"当前电池最低温度(C°)：{data.get('battery_min_temperature', 0.0):.1f}")
            self.lb_battery_soc_percent.setText(f"当前剩余电量比(%)：{data.get('battery_soc_percent', 0.0):.1f}")
            
            charging_status = "正在充电" if data.get('battery_is_charging', False) else "未充电"
            self.lb_battery_is_charging.setText(f"充电标志：{charging_status}")
            
        except Exception as e:
            print(f"处理状态消息时出错：{str(e)}")
    
    def send_control_command(self):
        """发送控制命令"""
        if not self.mqtt_handler.is_connected:
            QMessageBox.warning(self, "未连接", "请先连接MQTT服务器！")
            return False
            
        try:
            control_topic = get_control_topic(self.current_robot_id)
            success = self.mqtt_handler.publish_once(control_topic, self.current_control_cmd)
            
            if success:
                # 在发送消息列表中显示已发送的命令
                item = QListWidgetItem(json.dumps(self.current_control_cmd, ensure_ascii=False))
                self.lvSendMsg.addItem(item)
                self.lvSendMsg.scrollToBottom()
                return True
            else:
                QMessageBox.warning(self, "发送失败", "控制命令发送失败！")
                return False
                
        except Exception as e:
            QMessageBox.critical(self, "发送错误", f"发送控制命令时发生错误：{str(e)}")
            return False
    
    def start_sending_commands(self):
        """开始定时发送控制命令"""
        if not self.mqtt_handler.is_connected:
            QMessageBox.warning(self, "未连接", "请先连接MQTT服务器！")
            return
            
        control_topic = get_control_topic(self.current_robot_id)
        if not self.mqtt_handler.start_publishing(control_topic, self.current_control_cmd, 0.1):  # 100ms间隔
            QMessageBox.warning(self, "发送失败", "无法启动命令发送！")
            return
            
        self.is_sending_commands = True
        self.btn_StopCmd.setEnabled(True)
    
    def stop_sending_commands(self):
        """发送停车MQTT控制命令,但不停止MQTT连接 """
        self.set_movement(0.0, 0.0)
    
    def set_movement(self, speed, steer):
        """设置移动参数并发送命令"""
        # 更新控制命令
        self.current_control_cmd["Speed"] = speed
        self.current_control_cmd["Steer"] = steer
        
        # 如果正在连续发送，则更新发送数据；否则直接发送一次
        if self.is_sending_commands:
            control_topic = get_control_topic(self.current_robot_id)
            self.mqtt_handler.update_publish_data(control_topic, self.current_control_cmd)
        else:
            self.send_control_command()
            # 对于非停止命令，开始连续发送
            #if speed != 0.0 or steer != 0.0:
            #    self.start_sending_commands()
    
    def update_gear_selection(self):
        """更新档位选择"""
        if self.Radio_Gear_4T4D.isChecked():
            self.current_control_cmd["Gear"] = 6  # 4T4D档
        elif self.Radio_Gear_Side.isChecked():
            self.current_control_cmd["Gear"] = 7  # 横移档
    
    def robot_id_changed(self, robot_id):
        """机器人ID更改处理"""
        self.current_robot_id = robot_id
        self.current_control_cmd["robot_id"] = robot_id
    
    def update_connection_status(self):
        """更新连接状态显示"""
        if self.mqtt_handler.is_connected:
            self.lb_ConnectStatus.setText("已连接")
            if self.current_theme == "sci-fi":
                self.lb_ConnectStatus.setStyleSheet("color: #4CAF50; font-weight: bold;")
            else:
                self.lb_ConnectStatus.setStyleSheet("color: green")
        else:
            self.lb_ConnectStatus.setText("未连接")
            if self.current_theme == "sci-fi":
                self.lb_ConnectStatus.setStyleSheet("color: #F44336; font-weight: bold;")
            else:
                self.lb_ConnectStatus.setStyleSheet("color: red")
    
    def close_application(self):
        """关闭应用程序"""
        try:
            # 停止发送命令
            if self.is_sending_commands:
                self.stop_sending_commands()
            
            # 断开MQTT连接
            if self.mqtt_handler.is_connected:
                self.mqtt_handler.disconnect()
            
            # 关闭窗口
            self.close()
            
        except Exception as e:
            print(f"关闭应用程序时出错：{str(e)}")
            self.close()


def main():
    app = QApplication(sys.argv)
    window = RobotMonitor()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()