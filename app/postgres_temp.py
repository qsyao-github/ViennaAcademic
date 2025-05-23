import psycopg

conn = psycopg.connect(
    conninfo="postgresql://vienna_academic:vienna_academic@postgres:5432/userdb"
)
cursor = conn.cursor()


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
        cursor.execute(f"SELECT * FROM checkpoints WHERE thread_id = {thread_id};")
        print(cursor.fetchall())
    else:
        cursor.execute("SELECT thread_id FROM checkpoints;")
        print(cursor.fetchall())


""" delete_utils("123")
inspect_utils() """

conn.close()
