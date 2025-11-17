import can
import time
from datetime import datetime
from typing import Dict

# Steering Ctrl 转向控制反馈报文解析器
class SteeringCtrlFbDecoder:
    """
    用于解码MSG_ID=0x18C4D2EF的转向控制反馈报文
    根据协议文档，报文包含以下字段：
    - 当前档位 (4 bits)
    - 当前车体速度 (16 bits)
    - 当前车体转向角 (16 bits)
    - 当前车体侧偏角 (16 bits)
    - Alive Rolling Counter (4 bits)
    - Check BCC (8 bits)
    """
    # =============== 信号定义区 ===============
    TARGET_ID = 0x18C4D2EF
    GEAR_MAP = {
        0: "0",  #"DISABLE",
        1: "1",  #"驻车档",
        2: "2",  #"空挡",
        4: "4",  #"FR-档(未启用)",
        6: "6",  #"4T4D-档",
        7: "7"   #"横移-档"
    }

    last_counter = -1
    frame_count = 0

    def parse_steering_ctrl_fb(self, msg: can.Message) -> Dict:
        """
        解析转向控制反馈 CAN 帧消息，提取并解析其中的档位、车速、转向角等信号，
        并进行物理值转换与校验检查（如心跳计数器和BCC校验），最后将结果打印输出并返回结构化数据。

        参数:
            msg (can.Message): 来自CAN总线的原始消息对象，包含时间戳和数据字段。

        返回:
            Dict: 包含解析后的各项信息的字典，包括时间戳、档位、速度、角度、心跳状态及校验结果。
        """
        global last_counter, frame_count
        self.frame_count += 1
        data = msg.data

        # 提取指定起始位置和长度的数据位，并支持有符号/无符号处理
        def get_bits(start: int, length: int, signed: bool = False) -> int:
            """
            从数据中提取指定位置和长度的位数据
            
            参数:
                start: 起始位位置（从0开始计数）
                length: 要提取的位长度
                signed: 是否作为有符号数处理，默认为False
                
            返回值:
                提取的位数据转换成的整数值
            """
            # 计算起始字节位置和字节内位偏移
            byte_start = start // 8
            bit_start = start % 8
            value = 0
            
            # 逐位提取指定长度的数据
            for i in range(length):
                # 计算当前位所在的字节索引和位索引
                byte_idx = (bit_start + i) // 8
                bit_idx = (bit_start + i) % 8
                # 提取指定位并将其放置到结果值的相应位置
                value |= ((data[byte_start + byte_idx] >> bit_idx) & 1) << i
                
            # 如果是有符号数且最高位为1，则进行符号扩展
            if signed and (value & (1 << (length - 1))):
                value -= (1 << length)
            return value

        # =============== 解析 6 个信号 ===============
        gear_raw = get_bits(0, 4)
        speed_raw = get_bits(4, 16, signed=True)
        steer_raw = get_bits(20, 16, signed=True)
        roll_raw = get_bits(36, 16, signed=True)
        counter = get_bits(52, 4)
        bcc_received = get_bits(56, 8)

        # 计算接收数据的 BCC 校验码（前7字节异或）
        bcc_calc = 0
        for b in data[:7]:
            bcc_calc ^= b
        bcc_valid = (bcc_calc == bcc_received)

        # 心跳检测逻辑：验证当前帧计数是否符合预期递增规律
        counter_ok = True
        if self.last_counter >= 0:
            expected = (self.last_counter + 1) & 0xF
            if counter != expected:
                counter_ok = False
        self.last_counter = counter

        # 将原始数值转换为实际物理单位
        speed_mps = speed_raw * 0.001
        steer_deg = steer_raw * 0.01
        side_slip_angle_deg = roll_raw * 0.01
        gear_str = self.GEAR_MAP.get(gear_raw, f"未知({gear_raw})")

        return {
            "timestamp": msg.timestamp,
            "gear": gear_str,
            "speed_mps": speed_mps,
            "steering_deg": steer_deg,
            "side_slip_angle_deg": side_slip_angle_deg,
            "counter": counter,
            "bcc_valid": bcc_valid,
            "counter_ok": counter_ok
        }

# Ctrl指令反馈解析器
class CtrlFbDecoder:
    """
    用于解码MSG_ID=0x18C4D1EF的转向控制反馈报文
    根据协议文档，报文包含以下字段：
    - 当前档位 (4 bits)
    - 当前车体速度 (16 bits)
    - 当前车体转向角 (16 bits)
    - 当前车体侧偏角 (16 bits)
    - Alive Rolling Counter (4 bits)
    - Check BCC (8 bits)
    """
    # =============== 信号定义区 ===============
    TARGET_ID = 0x18C4D1D0
    
    GEAR_MAP = {
        0: "0",  #"DISABLE",
        1: "1",  #"驻车档",
        2: "2",  #"空挡",
        4: "4",  #"FR-档(未启用)",
        6: "6",  #"4T4D-档",
        7: "7"   #"横移-档"
    }

    last_counter = -1
    frame_count = 0

    def parse_ctrl_cmd(self, msg: can.Message) -> Dict:
        """
        解析指令控制命令 CAN 帧消息，提取并解析其中的档位、线速度、角速度等信号，
        并进行物理值转换与校验检查（如心跳计数器和BCC校验），最后将结果打印输出并返回结构化数据。

        参数:
            msg (can.Message): 来自CAN总线的原始消息对象，包含时间戳和数据字段。

        返回:
            Dict: 包含解析后的各项信息的字典，包括时间戳、档位、速度、角度、心跳状态及校验结果。
        """
        global last_counter, frame_count
        self.frame_count += 1
        data = msg.data

        # 提取指定起始位置和长度的数据位，并支持有符号/无符号处理
        def get_bits(start: int, length: int, signed: bool = False) -> int:
            """
            从数据中提取指定位置和长度的位数据
            
            参数:
                start: 起始位位置（从0开始计数）
                length: 要提取的位长度
                signed: 是否作为有符号数处理，默认为False
                
            返回值:
                提取的位数据转换成的整数值
            """
            # 计算起始字节位置和字节内位偏移
            byte_start = start // 8
            bit_start = start % 8
            value = 0
            
            # 逐位提取指定长度的数据
            for i in range(length):
                # 计算当前位所在的字节索引和位索引
                byte_idx = (bit_start + i) // 8
                bit_idx = (bit_start + i) % 8
                # 提取指定位并将其放置到结果值的相应位置
                value |= ((data[byte_start + byte_idx] >> bit_idx) & 1) << i
                
            # 如果是有符号数且最高位为1，则进行符号扩展
            if signed and (value & (1 << (length - 1))):
                value -= (1 << length)
            return value

        # =============== 解析 6 个信号 ===============
        gear_raw = get_bits(0, 4)
        linear_velocity_raw = get_bits(4, 16, signed=True)
        angular_velocity_raw = get_bits(20, 16, signed=True)
        side_slip_angle_raw = get_bits(36, 16, signed=True)
        counter = get_bits(52, 4)
        bcc_received = get_bits(56, 8)

        # 计算接收数据的 BCC 校验码（前7字节异或）
        bcc_calc = 0
        for b in data[:7]:
            bcc_calc ^= b
        bcc_valid = (bcc_calc == bcc_received)

        # 心跳检测逻辑：验证当前帧计数是否符合预期递增规律
        counter_ok = True
        if self.last_counter >= 0:
            expected = (self.last_counter + 1) & 0xF
            if counter != expected:
                counter_ok = False
        self.last_counter = counter

        # 将原始数值转换为实际物理单位
        linear_velocity_mps = linear_velocity_raw * 0.001
        angular_velocity_dps = angular_velocity_raw * 0.01
        side_slip_angle_deg = side_slip_angle_raw * 0.01
        gear_str = self.GEAR_MAP.get(gear_raw, f"未知({gear_raw})")

        return {
            "timestamp": msg.timestamp,
            "gear": gear_str,
            "linear_velocity_mps": linear_velocity_mps,
            "angular_velocity_dps": angular_velocity_dps,
            "side_slip_angle_deg": side_slip_angle_deg,
            "counter": counter,
            "bcc_valid": bcc_valid,
            "counter_ok": counter_ok
        }

# BMS反馈报文解析器
class BmsFbDecoder:
    """
    用于解码MSG_ID=0x18C4E1EF的BMS反馈报文
    根据协议文档，报文包含以下字段：
    - 当前电池电压 (16 bits)
    - 当前电池电流 (16 bits)
    - 当前电池剩余容量 (16 bits)
    - 心跳信号（循环计数器，Alive Rolling Counter） (4 bits)
    - 消息异或校验（Check BCC） (8 bits)
    """
    # =============== 信号定义区 ===============
    TARGET_ID = 0x18C4E1EF

    last_counter = -1
    frame_count = 0

    def parse_bms_fb(self, msg: can.Message) -> Dict:
        """
        解析BMS反馈 CAN 帧消息，提取并解析其中的电压、电流、剩余容量等信号，
        并进行物理值转换与校验检查（如心跳计数器和BCC校验），最后将结果打印输出并返回结构化数据。

        参数:
            msg (can.Message): 来自CAN总线的原始消息对象，包含时间戳和数据字段。

        返回:
            Dict: 包含解析后的各项信息的字典，包括时间戳、电压、电流、剩余容量、心跳状态及校验结果。
        """
        self.frame_count += 1
        data = msg.data

        # 提取指定起始位置和长度的数据位，并支持有符号/无符号处理
        def get_bits(start: int, length: int, signed: bool = False) -> int:
            """
            从数据中提取指定位置和长度的位数据
            
            参数:
                start: 起始位位置（从0开始计数）
                length: 要提取的位长度
                signed: 是否作为有符号数处理，默认为False
                
            返回值:
                提取的位数据转换成的整数值
            """
            # 计算起始字节位置和字节内位偏移
            byte_start = start // 8
            bit_start = start % 8
            value = 0
            
            # 逐位提取指定长度的数据
            for i in range(length):
                # 计算当前位所在的字节索引和位索引
                byte_idx = (bit_start + i) // 8
                bit_idx = (bit_start + i) % 8
                # 提取指定位并将其放置到结果值的相应位置
                value |= ((data[byte_start + byte_idx] >> bit_idx) & 1) << i
                
            # 如果是有符号数且最高位为1，则进行符号扩展
            if signed and (value & (1 << (length - 1))):
                value -= (1 << length)
            return value

        # =============== 解析信号 ===============
        voltage_raw = get_bits(0, 16, signed=False)
        current_raw = get_bits(16, 16, signed=True)
        remaining_capacity_raw = get_bits(32, 16, signed=False)
        counter = get_bits(52, 4)
        bcc_received = get_bits(56, 8)

        # 计算接收数据的 BCC 校验码（前7字节异或）
        bcc_calc = 0
        for b in data[:7]:
            bcc_calc ^= b
        bcc_valid = (bcc_calc == bcc_received)

        # 心跳检测逻辑：验证当前帧计数是否符合预期递增规律
        counter_ok = True
        if self.last_counter >= 0:
            expected = (self.last_counter + 1) & 0xF
            if counter != expected:
                counter_ok = False
        self.last_counter = counter

        # 将原始数值转换为实际物理单位
        voltage_v = voltage_raw * 0.01
        current_a = current_raw * 0.01
        remaining_capacity_ah = remaining_capacity_raw * 0.01

        # =============== 美观打印 ===============
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        status = "OK" if (bcc_valid and counter_ok) else "FAIL"

        return {
            "timestamp": msg.timestamp,
            "voltage_v": voltage_v,
            "current_a": current_a,
            "remaining_capacity_ah": remaining_capacity_ah,
            "counter": counter,
            "bcc_valid": bcc_valid,
            "counter_ok": counter_ok
        }



# BMS状态标志反馈报文解析器
class BmsFlagFbDecoder:
    """
    用于解码MSG_ID=0x18C4E2EF的BMS状态标志反馈报文
    根据协议文档，仅解析以下字段：
    - 当前剩余电量百分比 (8 bits)
    - 充电标志位 (1 bit)
    - 当前电池最高温度 (12 bits)
    - 当前电池最低温度 (12 bits)
    """
    # =============== 信号定义区 ===============
    TARGET_ID = 0x18C4E2EF

    last_counter = -1
    frame_count = 0

    def parse_bms_flag_fb(self, msg: can.Message) -> Dict:
        """
        解析BMS状态标志反馈 CAN 帧消息，提取指定的电池状态信息，
        并进行物理值转换与校验检查（如心跳计数器和BCC校验）。

        参数:
            msg (can.Message): 来自CAN总线的原始消息对象，包含时间戳和数据字段。

        返回:
            Dict: 包含解析后的指定信息的字典，包括SOC、充电状态、最高温度、最低温度、心跳状态及校验结果。
        """
        self.frame_count += 1
        data = msg.data

        # 提取指定起始位置和长度的数据位，并支持有符号/无符号处理
        def get_bits(start: int, length: int, signed: bool = False) -> int:
            """
            从数据中提取指定位置和长度的位数据
            
            参数:
                start: 起始位位置（从0开始计数）
                length: 要提取的位长度
                signed: 是否作为有符号数处理，默认为False
                
            返回值:
                提取的位数据转换成的整数值
            """
            # 计算起始字节位置和字节内位偏移
            byte_start = start // 8
            bit_start = start % 8
            value = 0
            
            # 逐位提取指定长度的数据
            for i in range(length):
                # 计算当前位所在的字节索引和位索引
                byte_idx = (bit_start + i) // 8
                bit_idx = (bit_start + i) % 8
                # 提取指定位并将其放置到结果值的相应位置
                value |= ((data[byte_start + byte_idx] >> bit_idx) & 1) << i
                
            # 如果是有符号数且最高位为1，则进行符号扩展
            if signed and (value & (1 << (length - 1))):
                value -= (1 << length)
            return value

        # =============== 解析指定信号 ===============
        # 当前剩余电量百分比 (byte[0], 0-7位)
        soc_raw = get_bits(0, 8, signed=False)
        
        # 充电标志位 (byte[2], 21位)
        charging_flag = get_bits(21, 1, signed=False)
        
        # 当前电池最高温度 (byte[1], 28-39位)
        max_temp_raw = get_bits(28, 12, signed=True)
        
        # 当前电池最低温度 (byte[1], 40-51位)
        min_temp_raw = get_bits(40, 12, signed=True)
        
        # 心跳信号（Alive Rolling Counter）(byte[6], 52-55位)
        counter = get_bits(52, 4)
        
        # BCC校验 (byte[7], 56-63位)
        bcc_received = get_bits(56, 8)

        # 计算接收数据的 BCC 校验码（前7字节异或）
        bcc_calc = 0
        for b in data[:7]:
            bcc_calc ^= b
        bcc_valid = (bcc_calc == bcc_received)

        # 心跳检测逻辑：验证当前帧计数是否符合预期递增规律
        counter_ok = True
        if self.last_counter >= 0:
            expected = (self.last_counter + 1) & 0xF
            if counter != expected:
                counter_ok = False
        self.last_counter = counter

        # 将原始数值转换为实际物理单位
        soc_percent = soc_raw  # 1%/bit，范围 0~100%
        is_charging = bool(charging_flag)  # 0: 放电状态，1: 充电状态
        max_temp_c = max_temp_raw * 0.1  # 0.1°C/bit
        min_temp_c = min_temp_raw * 0.1  # 0.1°C/bit

        return {
            "timestamp": msg.timestamp,
            "soc_percent": soc_percent,
            "is_charging": is_charging,
            "max_temp_c": max_temp_c,
            "min_temp_c": min_temp_c,
            "counter": counter,
            "bcc_valid": bcc_valid,
            "counter_ok": counter_ok
        }