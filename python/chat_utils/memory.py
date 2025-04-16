import aiosqlite
import asyncio
import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
checkpoint_connection = aiosqlite.connect("checkpoints.db")


async def remove_thread_data(thread_id: str) -> None:
    """删除指定 thread_id 的所有检查点和写入记录"""
    await checkpoint_connection.execute(
        "DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,)
    )
    await checkpoint_connection.execute(
        "DELETE FROM writes WHERE thread_id = ?", (thread_id,)
    )
    await checkpoint_connection.commit()


async def shutdown_sqlite_connection():
    global checkpoint_connection
    if checkpoint_connection.is_alive():
        async with checkpoint_connection.executescript(
            "DELETE FROM checkpoints;DELETE FROM writes;VACUUM;"
        ):
            await checkpoint_connection.commit()
        await checkpoint_connection.close()
    print("sqlite connection closed")
