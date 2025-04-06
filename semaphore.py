"""
全局信号量
"""

import asyncio

# 用于论文模块
semaphore1024 = asyncio.Semaphore(1024)
