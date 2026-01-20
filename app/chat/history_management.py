import aiosqlite

conn = None


async def get_sqlite_connection():
    """异步环境获取checkpoint数据库连接，自动初始化"""
    global conn
    if conn is None:
        conn = await aiosqlite.connect("checkpoints.db")
    return conn


async def close_sqlite_connection() -> None:
    """关闭数据库连接并清理资源"""
    global conn
    await conn.close()
    conn = None


async def get_thread_ids() -> frozenset[str]:
    """获取数据库中所有thread_id"""
    conn = await get_sqlite_connection()
    cursor = await conn.cursor()
    await cursor.execute("SELECT thread_id FROM checkpoints")
    results = await cursor.fetchall()
    return frozenset(row[0] for row in results)
