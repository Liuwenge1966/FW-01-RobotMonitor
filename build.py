#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os


def create_directory_structure():
    """
    自动构建ROBOT_Monitor项目的目录结构
    """
    # 定义项目根目录
    project_root = "."

    # 定义需要创建的目录结构
    directories = [
        "docs",
        "src",
        "src/config",
        "src/edge_controller",
        "src/monitor_ui",
        "src/protocols",
        "tests",
        "scripts",
        "logs"
    ]

    # 定义需要创建的文件
    files = [
        # 文档文件
        "docs/architecture.md",
        "docs/protocol.md",
        "README.md",

        # 配置模块文件
        "src/config/__init__.py",
        "src/config/settings.py",

        # 边缘控制器文件
        "src/edge_controller/__init__.py",
        "src/edge_controller/get_robot_status.py",
        "src/edge_controller/ctrl_robot.py",

        # 远程监控UI文件
        "src/monitor_ui/__init__.py",
        "src/monitor_ui/main_window.py",
        "src/monitor_ui/ui_design.py",
        "src/monitor_ui/mqtt_handler.py",

        # 通信协议文件
        "src/protocols/__init__.py",
        "src/protocols/can_protocol.py",
        "src/protocols/mqtt_topics.py",

        # 测试文件
        "tests/test_can_protocol.py",
        "tests/test_mqtt_conn.py",

        # 脚本文件
        "scripts/start_ui.sh",
        "scripts/start_edge.sh",
        "scripts/can_setup.sh",

        # 依赖文件
        "requirements.txt"
    ]

    # 创建目录
    print("正在创建目录结构...")
    for directory in directories:
        dir_path = os.path.join(project_root, directory)
        os.makedirs(dir_path, exist_ok=True)
        print(f"创建目录: {dir_path}")

    # 创建文件
    print("\n正在创建文件...")
    for file in files:
        file_path = os.path.join(project_root, file)
        
        # 如果文件已经存在，则跳过
        if os.path.exists(file_path):
            print(f"文件已存在: {file_path}")
            continue
            
        # 创建空文件
        with open(file_path, 'w', encoding='utf-8') as f:
            # 为Python的__init__.py文件添加注释
            if file.endswith('__init__.py'):
                f.write('# -*- coding: utf-8 -*-\n')
                f.write('"""Package initialization file."""\n')
            
            # 为Python源文件添加基本模板
            elif file.endswith('.py') and file != 'build.py':
                f.write('# -*- coding: utf-8 -*-\n')
                f.write('"""\n')
                filename = os.path.basename(file)
                f.write(f'{filename} - TODO: Add module description\n')
                f.write('"""\n\n')
                
            # 为shell脚本添加基本模板
            elif file.endswith('.sh'):
                f.write('#!/bin/bash\n\n')
                filename = os.path.basename(file).replace('.sh', '')
                f.write(f'# {filename} - TODO: Add script description\n\n')
                
            # 为markdown文件添加标题
            elif file.endswith('.md'):
                filename = os.path.basename(file).replace('.md', '')
                f.write(f'# {filename}\n\n')
                f.write('TODO: Add content\n\n')
                
            # 为requirements.txt添加注释
            elif file == 'requirements.txt':
                f.write('# Project dependencies\n')
                f.write('# TODO: Add required packages\n\n')
                
            # 为README.md添加项目描述
            elif file == 'README.md':
                f.write('# ROBOT_Monitor\n\n')
                f.write('机器人远程监控系统\n\n')
                f.write('## 项目结构\n\n')
                f.write('```\n')
                f.write('ROBOT_Monitor/\n')
                f.write('├── docs/                      # 文档目录\n')
                f.write('│   ├── architecture.md       # 系统架构说明\n')
                f.write('│   └── protocol.md           # 详细通信协议\n')
                f.write('├── src/                      # 源代码目录\n')
                f.write('│   ├── config/               # 配置文件模块\n')
                f.write('│   ├── edge_controller/      # 边缘控制器程序包\n')
                f.write('│   ├── monitor_ui/           # 远程监控UI程序包\n')
                f.write('│   └── protocols/            # 通信协议解析包\n')
                f.write('├── tests/                    # 测试目录\n')
                f.write('├── scripts/                  # 实用脚本目录\n')
                f.write('├── logs/                     # 日志目录\n')
                f.write('├── requirements.txt          # Python项目依赖列表\n')
                f.write('└── README.md                 # 项目总说明文档\n')
                f.write('```\n')
        
        print(f"创建文件: {file_path}")

    print("\n目录结构创建完成！")


if __name__ == "__main__":
    create_directory_structure()