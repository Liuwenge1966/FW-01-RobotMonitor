import can

class CtrlCmdPacker:
    """
    一个用于生成ctrl_cmd CAN消息的类，根据给定的目标档位、线速度、角速度和侧偏角生成8字节的消息数据。
    
    该类维护一个内部计数器（Alive Rolling Counter），每生成一帧消息时递增（模16）。
    消息ID固定为0x18C4D1D0，扩展帧。
    
    示例用法:
        packer = CtrlCmdPacker()
        data = packer.generate_message(gear=1, speed=0.0, angular_velocity=0.0, side_bias_angle=0.0)
        # data 是一个bytearray，可以用于创建can.Message并发送
    """
    
    def __init__(self):
        """
        初始化CtrlCmdPacker实例。
        """
        self.counter = 0  # Alive Rolling Counter，初始为0

    def generate_message(self, gear: int, speed: float, angular_velocity: float, side_bias_angle: float) ->can.Message:
        """
        根据输入参数生成CAN消息。
        
        参数:
            gear: 目标档位 (int)，有效值: 0=disable, 1=驻车档, 2=空挡, 4=FR-档, 6=4T4D-档, 7=横移-档
            speed: 目标车体线速度 (float)，单位 m/s，正负表示方向
            angular_velocity: 目标车体角速度 (float)，单位 °/s，正负表示旋转方向
            side_bias_angle: 目标车体侧偏角 (float)，单位 °
        
        返回:
            bytearray: 8字节的消息数据，可用于can.Message的data字段
        """
        # 转换为原始ticks值
        speed_raw = int(speed / 0.001)
        angular_raw = int(angular_velocity / 0.01)
        bias_raw = int(side_bias_angle / 0.01)
        gear_raw = gear & 0x0F
        counter = self.counter & 0x0F

        # 初始化8字节数据
        data = bytearray(8)

        # 填充数据按照位布局
        data[0] = (gear_raw & 0x0F) | ((speed_raw << 4) & 0xF0)
        data[1] = (speed_raw >> 4) & 0xFF
        data[2] = ((speed_raw >> 12) & 0x0F) | ((angular_raw << 4) & 0xF0)
        data[3] = (angular_raw >> 4) & 0xFF
        data[4] = ((angular_raw >> 12) & 0x0F) | ((bias_raw << 4) & 0xF0)
        data[5] = (bias_raw >> 4) & 0xFF
        data[6] = ((bias_raw >> 12) & 0x0F) | (counter << 4)

        # 计算BCC: 前7字节异或
        bcc = 0
        for b in data[:7]:
            bcc ^= b
        data[7] = bcc

        # 更新计数器
        self.counter = (self.counter + 1) % 16

        return can.Message(
            arbitration_id=0x18C4D1D0,
            is_extended_id=True,
            data=data
        )

class SteeringCtrlCmdPacker:
    """
    一个用于生成ctrl_cmd CAN消息的类，根据给定的目标档位、线速度、角速度和侧偏角生成8字节的消息数据。
    
    该类维护一个内部计数器（Alive Rolling Counter），每生成一帧消息时递增（模16）。
    消息ID固定为0x18C4D2D0，扩展帧。
    
    示例用法:
        packer = CtrlCmdPacker()
        data = packer.generate_message(gear=1, speed=0.0, angular_velocity=0.0, side_bias_angle=0.0)
        # data 是一个bytearray，可以用于创建can.Message并发送
    """
    
    def __init__(self):
        """
        初始化CtrlCmdPacker实例。
        """
        self.counter = 0  # Alive Rolling Counter，初始为0

    def generate_message(self, gear: int, speed: float, steer: float, side_bias_angle: float) ->can.Message:
        """
        根据输入参数生成CAN消息。
        
        参数:
            gear: 目标档位 (int)，有效值: 0=disable, 1=驻车档, 2=空挡, 4=FR-档, 6=4T4D-档, 7=横移-档
            speed: 目标车体线速度 (float)，单位 m/s，正负表示方向
            angular_velocity: 目标车体角速度 (float)，单位 °/s，正负表示旋转方向
            side_bias_angle: 目标车体侧偏角 (float)，单位 °
        
        返回:
            bytearray: 8字节的消息数据，可用于can.Message的data字段
        """
        # 转换为原始ticks值
        speed_raw = int(speed / 0.001)
        steer_raw = int(steer / 0.01)
        bias_raw = int(side_bias_angle / 0.01)
        gear_raw = gear & 0x0F
        counter = self.counter & 0x0F

        # 初始化8字节数据
        data = bytearray(8)

        # 填充数据按照位布局
        data[0] = (gear_raw & 0x0F) | ((speed_raw << 4) & 0xF0)
        data[1] = (speed_raw >> 4) & 0xFF
        data[2] = ((speed_raw >> 12) & 0x0F) | ((steer_raw << 4) & 0xF0)
        data[3] = (steer_raw >> 4) & 0xFF
        data[4] = ((steer_raw >> 12) & 0x0F) | ((bias_raw << 4) & 0xF0)
        data[5] = (bias_raw >> 4) & 0xFF
        data[6] = ((bias_raw >> 12) & 0x0F) | (counter << 4)

        # 计算BCC: 前7字节异或
        bcc = 0
        for b in data[:7]:
            bcc ^= b
        data[7] = bcc

        # 更新计数器
        self.counter = (self.counter + 1) % 16

        return can.Message(
            arbitration_id=0x18C4D2D0,
            is_extended_id=True,
            data=data
        )


class SteeringCtrlCmdPacker01:
    """
    一个用于生成steering_ctrl_cmd CAN消息的类，根据给定的目标档位、车体速度、转向角和侧偏角生成8字节的消息数据。
    
    该类维护一个内部计数器（Alive Rolling Counter），每生成一帧消息时递增（模16）。
    消息ID固定为0x18C4D2D0，扩展帧。
    
    示例用法:
        packer = SteeringCtrlCmdPacker()
        data = packer.generate_message(gear=1, speed=0.0, steer=0.0, yaw=0.0)
        # data 是一个bytearray，可以用于创建can.Message并发送
    """
    
    def __init__(self):
        """
        初始化SteeringCtrlCmdPacker实例。
        """
        self.counter = 0  # Alive Rolling Counter，初始为0

    def generate_message(self, gear: int, speed: float, steer: float, yaw: float) -> can.Message:
        """
        根据输入参数生成CAN消息。
        
        参数:
            gear: 目标档位 (int)，有效值: 0=disable, 1=驻车档, 2=空挡, 3=FR-档, 5=4T4D-档, 7=横移-档
            speed: 目标车体速度 (float)，单位 m/s，正负表示方向
            steer: 目标车体转向角 (float)，单位 °，正负表示方向
            yaw: 目标车体侧偏角 (float)，单位 °
        
        返回:
            bytearray: 8字节的消息数据，可用于can.Message的data字段
        """
        # 转换为原始ticks值
        speed_raw = int(speed / 0.001)
        steer_raw = int(steer / 0.01)
        yaw_raw = int(yaw / 0.01)
        gear_raw = gear & 0x0F
        counter = self.counter & 0x0F

        # 初始化8字节数据
        data = bytearray(8)

        # 填充数据按照位布局
        data[0] = (gear_raw & 0x0F) | ((speed_raw << 4) & 0xF0)
        data[1] = (speed_raw >> 4) & 0xFF
        data[2] = ((speed_raw >> 12) & 0x0F) | ((steer_raw << 4) & 0xF0)
        data[3] = (steer_raw >> 4) & 0xFF
        data[4] = ((steer_raw >> 12) & 0x0F) | ((yaw_raw << 4) & 0xF0)
        data[5] = (yaw_raw >> 4) & 0xFF
        data[6] = ((yaw_raw >> 12) & 0x0F) | (counter << 4)

        # 计算BCC: 前7字节异或
        bcc = 0
        for b in data[:7]:
            bcc ^= b
        data[7] = bcc

        # 更新计数器
        self.counter = (self.counter + 1) % 16
        
        return can.Message(
            arbitration_id=0x18C4D2D0,
            is_extended_id=True,
            data=data
        )