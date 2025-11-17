import sys
import os

# 将src目录添加到Python路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from monitor_ui.RobotMonitor import main

if __name__ == "__main__":
    main()