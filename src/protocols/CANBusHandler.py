"""
CANBusHandler.py

CANBusHandler是一个基于 Python 的 CAN 总线通信处理类，封装了 CAN 总线的连接、消息收发、事件处理等核心功能。该类采用多线程设计，支持异步消息监听和周期消息发送，适用于机器人控制、汽车电子、工业自动化等需要 CAN 总线通信的应用场景。
核心功能
1. CAN 总线连接管理
    自动连接：支持多种 CAN 总线接口类型（如 candle、socketcan 等）
    参数配置：可配置通道号、波特率等连接参数
    状态监控：实时监控连接状态，提供连接状态信息
2. 消息接收处理
    同步接收：提供带超时机制的同步消息接收方法
    异步监听：支持后台线程持续监听 CAN 总线消息
    事件驱动：采用事件处理器模式，可注册多个消息处理函数
    线程安全：消息监听在独立线程中运行，不影响主程序执行
3. 消息发送功能
    单次发送：支持单条 CAN 消息的发送
    周期发送：支持在后台线程中周期性地发送指定消息
    动态更新：可在运行中更新发送数据和发送间隔
    错误处理：完善的异常捕获和错误提示机制
4. 多线程支持
    监听线程：独立的守护线程处理消息接收
    发送线程：独立的守护线程处理周期消息发送
    资源管理：提供线程启动、停止和资源释放功能

主要方法说明
    连接管理
        connect(): 建立 CAN 总线连接
        disconnect(): 断开 CAN 总线连接并释放资源
    消息接收
        receive_message(): 同步接收 CAN 消息
        register_event_handler(): 注册消息事件处理函数
        listen_for_messages(): 启动异步消息监听
        stop_listening(): 停止消息监听
    消息发送
        send_message(): 发送单条 CAN 消息
        start_sending(): 启动周期消息发送
        stop_sending(): 停止周期消息发送
        update_send_data(): 更新发送数据内容
        update_send_interval(): 更新发送时间间隔
"""
import can
import threading
import subprocess
import time
from typing import Callable, Optional

class CANBusHandler:
    def __init__(self, bus_type: str = 'candle', channel: int = 0, bitrate: int = 500000):
        """
        Initializes the CANBusHandler class with connection parameters.
        
        :param bus_type: Type of CAN bus interface (e.g., 'candle', 'socketcan')
        :param channel: The channel number for CAN bus connection
        :param bitrate: The bitrate for CAN communication
        """
        self.bus = None
        self.bus_type = bus_type
        self.channel = channel
        self.bitrate = bitrate
        
        # 状态标志
        self.is_connected = False
        self.listening = False
        self.sending = False
        
        # 消息处理相关
        self.event_handlers = []
        self.strConnStatus = "CAN bus disconnected."
        self.listener_thread = None
        
        # 发送相关
        self.sender_thread = None
        self.sender_data = None
        self.sender_id = None
        self.sender_interval = 0.02

    # CAN接口启动（树莓派、linux）
    def bring_interface_up(self) -> bool:
        """启动CAN接口"""
        try:
            # 先关闭接口
            subprocess.run(['sudo', 'ip', 'link', 'set', self.channel, 'down'], check=True)
            time.sleep(0.5)
            
            # 设置比特率并启动
            subprocess.run([
                'sudo', 'ip', 'link', 'set', self.channel, 'up', 
                'type', 'can', 'bitrate', str(self.bitrate)
            ], check=True)
            
            time.sleep(1)  # 等待接口完全启动
            print(f"CAN接口 {self.channel} 已启动")
            return True

    def connect(self) -> bool:
        """
        Establishes the CAN bus connection.
        
        :return: True if connection is successful, False otherwise
        """
        if self.bus_type == 'socketcan':
            self.bring_interface_up()
        elif self.bus_type == 'candle':
            pass

        try:
            if self.is_connected:
                print("Already connected to CAN bus.")
                return True
                
            self.bus = can.interface.Bus(bustype=self.bus_type, channel=self.channel, bitrate=self.bitrate)
            self.is_connected = True
            self.strConnStatus = f"Connected to CAN bus {self.bus_type} on channel {self.channel} with bitrate {self.bitrate} bps."
            print("CAN bus connection successful.")
            # Start listening for messages
            self.listen_for_messages()
            return True
        except Exception as e:
            print(f"Error connecting to CAN bus: {e}")
            self.strConnStatus = f"Error connecting to CAN bus: {e}"
            self.is_connected = False
            return False

    def disconnect(self):
        """
        Disconnects from the CAN bus.
        """
        if not self.is_connected:
            print("没有连接CAN总线.")
            return
            
        # 停止所有活动
        self.stop_listening()
        self.stop_sending()
        
        if self.bus:
            self.bus.shutdown()
            self.bus = None
            
        self.is_connected = False
        self.strConnStatus = "CAN bus disconnected."
        print("CAN总线已断开.")

    def receive_message(self, timeout: float = 1.0) -> Optional[can.Message]:
        """
        Receives a message from the CAN bus with a timeout.
        
        :param timeout: The time in seconds to wait for a message before returning None
        :return: The received CAN message, or None if no message is received
        """
        if not self.is_connected:
            print("Not connected to CAN bus.")
            return None
            
        try:
            msg = self.bus.recv(timeout)
            return msg
        except can.CanError as e:
            print(f"Error receiving message: {e}")
            return None

    def register_event_handler(self, handler: Callable[[can.Message], None]):
        """
        Registers a handler function that will be called when a CAN message is received.
        
        :param handler: The event handler function that takes a can.Message as argument
        """
        self.event_handlers.append(handler)

    def listen_for_messages(self):
        """
        启动一个后台线程来监听CAN总线消息并在接收到消息时触发事件处理器。
        
        该方法会创建并启动一个守护线程，该线程会持续轮询CAN总线以接收消息，
        并在接收到消息后调用所有已注册的事件处理器。
        """
        if not self.is_connected:
            print("Not connected to CAN bus.")
            return
            
        if self.listening:
            print("Already listening for messages.")
            return

        def listener():
            """
            监听CAN总线消息的内部函数
            
            该函数作为独立线程运行，持续从CAN总线接收消息，并将接收到的消息传递给所有已注册的事件处理器进行处理。
            当listening或is_connected标志变为False时，监听循环会终止。
            """
            self.listening = True
            print("Listening for CAN messages...")
            while self.listening and self.is_connected:
                msg = self.receive_message(timeout=0.1)  # 100ms timeout
                if msg:
                    for handler in self.event_handlers:
                        try:
                            handler(msg)
                        except Exception as e:
                            print(f"Error in message handler: {e}")

        # Start the listener thread
        self.listener_thread = threading.Thread(target=listener, daemon=True)
        self.listener_thread.start()

    def stop_listening(self):
        """
        Stops the CAN bus message listener thread.
        """
        if not self.listening:
            return
            
        self.listening = False
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=2) 
        print("Stopped listening for CAN messages.")

    def send_message(self, msg_id: int, data: bytearray, is_extended: bool=True) -> bool:
        """
        Sends a message over the CAN bus.
        
        :param msg_id: CAN message ID
        :param data: Data to be sent in the message
        :param is_extended: Whether to use extended ID format
        :return: True if the message was sent successfully, False otherwise
        """
        if not self.is_connected:
            print("CANHandler.Send_message: Not connected to CAN bus.")
            return False
            
        try:
            msg = can.Message(arbitration_id=msg_id, is_extended_id=is_extended, data=data)
            self.bus.send(msg, timeout=0.02)
            #print(f"send_message: Message sent with ID 0x{msg_id:X}.")
            return True
        except can.CanError as e:
            print(f"CANHandler.Send_message: send_message: Error sending message: {e}")
            return False

    def start_sending(self, msg_id: int, data: bytearray, interval: float = 0.02, is_extended: bool = True) -> bool:
        """
        Starts continuously sending a message at a regular interval in a separate thread.
        
        :param msg_id: CAN message ID
        :param data: Data to be sent in the message
        :param interval: The time interval (in seconds) between each message
        :param is_extended: Whether to use extended ID format
        :return: True if sending started successfully, False otherwise
        """
        if not self.is_connected:
            print("Not connected to CAN bus.")
            return False
            
        if self.sending:
            print("Already sending messages. Stop current sending first.")
            return False

        def sender():
            self.sending = True
            self.sender_data = data.copy()
            self.sender_id = msg_id
            self.sender_interval = interval
            self.sender_extended = is_extended
            
            while self.sending and self.is_connected:
                # 使用当前存储的数据发送消息
                success = self.send_message(self.sender_id, self.sender_data, self.sender_extended)
                if not success:
                    print("Failed to send message in continuous sender.")
                
                # 等待指定间隔或停止信号
                time.sleep(self.sender_interval)

        # Start the sender thread
        self.sender_thread = threading.Thread(target=sender, daemon=True)
        self.sender_thread.start()
        print(f"Started sending messages with ID 0x{msg_id:X} every {interval} seconds.")
        return True

    def stop_sending(self):
        """
        Stops the continuous message sending thread.
        """
        if not self.sending:
            return
            
        self.sending = False
        if self.sender_thread and self.sender_thread.is_alive():
            self.sender_thread.join(timeout=2)
        print("Stopped sending messages.")

    def update_send_data(self, new_data: bytearray):
        """
        Updates the data to be sent in continuous sending mode.
        
        :param new_data: New data to be sent
        """
        if self.sending:
            self.sender_data = new_data.copy()
        else:
            print("Not currently sending messages.")

    def update_send_interval(self, new_interval: float):
        """
        Updates the interval between messages in continuous sending mode.
        
        :param new_interval: New interval in seconds
        """
        if self.sending:
            self.sender_interval = new_interval
        else:
            print("Not currently sending messages.")