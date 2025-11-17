import json
import time
import threading
import paho.mqtt.client as mqtt

class MQTTHandler:
    def __init__(self, broker_address="localhost", broker_port=1883, client_id="Robot00"):
        """
        初始化MQTT处理器
        
        :param broker_address: MQTT代理地址
        :param broker_port: MQTT代理端口
        :param client_id: 客户端ID
        """
        self.broker_address = broker_address
        self.broker_port = broker_port
        
        # MQTT客户端设置
        self.client = mqtt.Client(client_id=client_id)
        self.client.username_pw_set(client_id, "password")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # 连接状态
        self.is_connected = False
        self.strConnStatus = "MQTT broker disconnected."
        
        # 发布相关
        self.publish_topics = {}  # 格式: {topic: {"interval": seconds, "data": message_data}}
        self.publish_threads = {}  # 存储发布线程
        self.stop_events = {}     # 存储停止事件
        self.publish_locks = {}   # 存储每个主题的锁
        
        # 订阅相关
        self.subscribed_topics = set()
        self.callbacks = {
            "text": {},    # 格式: {topic: callback_function}
            "json": {},    # 格式: {topic: callback_function}
            "binary": {}   # 格式: {topic: callback_function}
        }
        
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调函数"""
        if rc == 0:
            self.is_connected = True
            print(f"_on_connect：MQTT连接成功 - {self.broker_address}:{self.broker_port}")
            
            # 重新订阅之前的主题
            for topic in self.subscribed_topics:
                self.client.subscribe(topic)
        else:
            print(f"_on_connect：MQTT连接失败，错误代码: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调函数"""
        self.is_connected = False
        print("_on_disconnect：MQTT连接已断开")
    
    def _on_message(self, client, userdata, msg):
        """消息接收回调函数"""
        topic = msg.topic
        try:
            # 尝试解析为JSON
            payload = msg.payload.decode('utf-8')
            try:
                json_data = json.loads(payload)
                if topic in self.callbacks["json"]:
                    self.callbacks["json"][topic](topic, json_data)
            except json.JSONDecodeError:
                # 处理普通文本
                if topic in self.callbacks["text"]:
                    self.callbacks["text"][topic](topic, payload)
        except UnicodeDecodeError:
            # 处理二进制数据
            if topic in self.callbacks["binary"]:
                self.callbacks["binary"][topic](topic, msg.payload)
    
    def connect(self) -> bool:
        """连接到MQTT代理"""
        try:
            self.client.connect(self.broker_address, self.broker_port, 60)
            time.sleep(1)
            print(f"self.client.connect:连接成功")
            self.client.loop_start()
            time.sleep(1)
            print(f"self.client.loop_start:启动成功")
            return True
        except Exception as e:
            print(f"self.client.loop_start:MQTT连接错误 {e}")
            return False
    
    def disconnect(self) -> bool:
        """断开MQTT连接"""
        # 停止所有发布
        for topic in list(self.publish_threads.keys()):
            self.stop_publishing(topic)
        
        # 取消所有订阅
        for topic in list(self.subscribed_topics):
            self.unsubscribe(topic)
        
        self.client.loop_stop()
        self.client.disconnect()
        self.is_connected = False
        return True
    
    # ====== 发布相关方法 ======
    def publish_once(self, topic: str, message) -> bool:
        """
        单次发布消息
        
        :param topic: 发布主题
        :param message: 要发布的消息（可以是字符串、字典或字节）
        :return: 是否发布成功
        """
        if not self.is_connected:
            print("MQTT未连接，请先连接")
            return False
        
        try:
            if isinstance(message, (dict, list)):
                message = json.dumps(message)
            self.client.publish(topic, message)
            return True
        except Exception as e:
            print(f"发布消息失败: {e}")
            return False
    
    def start_publishing(self, topic: str, message, interval: float = 1.0) -> bool:
        """
        开始定期发布消息
        
        :param topic: 发布主题
        :param message: 要发布的消息（可以是字符串、字典或字节）
        :param interval: 发布间隔（秒）
        :return: 是否成功启动发布
        """
        if not self.is_connected:
            print("start_publishing：MQTT未连接，请先连接")
            return False
            
        if topic in self.publish_threads and self.publish_threads[topic].is_alive():
            print(f"start_publishing：主题 {topic} 已经在发布中")
            return False
        
        self.publish_topics[topic] = {
            "interval": interval,
            "data": message
        }
        self.publish_locks[topic] = threading.Lock()
        self.stop_events[topic] = threading.Event()
        
        self.publish_threads[topic] = threading.Thread(
            target=self._publish_loop,
            args=(topic,),
            daemon=True
        )
        self.publish_threads[topic].start()
        print(f"start_publishing：已开始发布主题: {topic}")
        return True
    
    def stop_publishing(self, topic: str) -> bool:
        """
        停止特定主题的发布
        
        :param topic: 要停止发布的主题
        :return: 是否成功停止
        """
        if topic not in self.publish_threads:
            print(f"主题 {topic} 没有在发布")
            return False
            
        self.stop_events[topic].set()
        if self.publish_threads[topic].is_alive():
            self.publish_threads[topic].join()
        
        # 清理相关资源
        del self.publish_threads[topic]
        del self.stop_events[topic]
        del self.publish_locks[topic]
        del self.publish_topics[topic]
        
        print(f"stop_publishing：已停止发布主题: {topic}")
        return True
    
    def update_publish_data(self, topic: str, new_data):
        """
        更新要发布的消息数据
        
        :param topic: 要更新的主题
        :param new_data: 新的消息数据
        """
        if topic in self.publish_topics:
            with self.publish_locks[topic]:
                self.publish_topics[topic]["data"] = new_data
    
    def _publish_loop(self, topic: str):
        """发布消息的循环"""
        while not self.stop_events[topic].is_set():
            with self.publish_locks[topic]:
                message = self.publish_topics[topic]["data"]
                if isinstance(message, (dict, list)):
                    message = json.dumps(message)
            
            if self.is_connected:
                try:
                    self.client.publish(topic, message)
                except Exception as e:
                    print(f"发布消息失败: {e}")
            
            # 等待指定间隔或停止信号
            if self.stop_events[topic].wait(self.publish_topics[topic]["interval"]):
                break
    
    # ====== 订阅相关方法 ======
    def subscribe(self, topic: str, callback=None, message_type="text") -> bool:
        """
        订阅主题
        
        :param topic: 要订阅的主题
        :param callback: 消息处理回调函数
        :param message_type: 消息类型 ("text", "json", "binary")
        :return: 是否成功订阅
        """
        if not self.is_connected:
            print("MQTT未连接，请先连接")
            return False
            
        try:
            self.client.subscribe(topic)
            self.subscribed_topics.add(topic)
            
            if callback:
                if message_type in self.callbacks:
                    self.callbacks[message_type][topic] = callback
                
            print(f"已订阅主题: {topic}")
            return True
        except Exception as e:
            print(f"订阅主题失败: {e}")
            return False
    
    def unsubscribe(self, topic: str) -> bool:
        """
        取消订阅主题
        
        :param topic: 要取消订阅的主题
        :return: 是否成功取消订阅
        """
        if topic not in self.subscribed_topics:
            print(f"主题 {topic} 未订阅")
            return False
            
        self.client.unsubscribe(topic)
        self.subscribed_topics.remove(topic)
        
        # 清理相关回调
        for callback_type in self.callbacks:
            if topic in self.callbacks[callback_type]:
                del self.callbacks[callback_type][topic]
        
        print(f"已取消订阅主题: {topic}")
        return True
    
    def set_message_callback(self, topic: str, callback, message_type="text"):
        """
        设置特定主题的消息处理回调函数
        
        :param topic: 主题
        :param callback: 回调函数
        :param message_type: 消息类型 ("text", "json", "binary")
        """
        if message_type in self.callbacks:
            self.callbacks[message_type][topic] = callback
    
    # ====== 配置方法 ======
    def set_broker(self, address: str, port: int = 1883):
        """
        设置MQTT代理地址和端口
        
        :param address: 代理地址
        :param port: 代理端口
        """
        was_connected = self.is_connected
        if was_connected:
            self.disconnect()
            
        self.broker_address = address
        self.broker_port = port
        
        if was_connected:
            self.connect()