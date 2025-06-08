"""
全局信号量
"""

import asyncio

# 用于论文模块
semaphore100 = asyncio.Semaphore(100)
# 用于文件解析
semaphore1 = asyncio.Semaphore(1)
