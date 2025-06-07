"""
全局信号量
"""

import asyncio

# 用于论文模块
semaphore1024 = asyncio.Semaphore(1024)
# 用于文件解析
semaphore1 = asyncio.Semaphore(1)
