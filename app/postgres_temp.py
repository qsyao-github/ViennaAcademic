import psycopg

conn = psycopg.connect(
    conninfo="postgresql://vienna_academic:vienna_academic@postgres:5432/vadb"
)
cursor = conn.cursor()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(16) UNIQUE NOT NULL,
        password_hash CHAR(60) NOT NULL
    );
"""
)


def delete_utils(thread_id=""):
    if thread_id:
        cursor.execute(
            "DELETE FROM checkpoints WHERE thread_id = %s",
            (str(thread_id),),
        )
        cursor.execute(
            "DELETE FROM checkpoint_blobs WHERE thread_id = %s",
            (str(thread_id),),
        )
        cursor.execute(
            "DELETE FROM checkpoint_writes WHERE thread_id = %s",
            (str(thread_id),),
        )
    else:
        cursor.execute("DELETE FROM checkpoints;")
        cursor.execute("DELETE FROM checkpoint_blobs;")
        cursor.execute("DELETE FROM checkpoint_writes;")
    conn.commit()


def inspect_utils(thread_id=""):
    if thread_id:
        cursor.execute("SELECT * FROM checkpoints WHERE thread_id = %s;", (thread_id,))
        print(cursor.fetchall())
    else:
        cursor.execute("SELECT thread_id FROM checkpoints;")
        print(cursor.fetchall())


inspect_utils("test")
delete_utils()
conn.close()
