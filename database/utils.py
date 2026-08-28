import sqlite3
from contextlib import contextmanager

@contextmanager
def open_cursor(connection: sqlite3.Connection, need_commit: bool = False):
    cursor = connection.cursor()

    try:
        yield cursor
        if need_commit:
            connection.commit()

    except Exception as e:
        connection.rollback()
        raise e

    finally:
        cursor.close()

def add_column_if_not_exists(
    database_path: str,
    table_name: str, 
    column_name: str,
    column_type: str,
    column_default_value: str = ""
):
    connection = sqlite3.connect(database_path)

    try:
        with open_cursor(connection, need_commit=True) as cursor:
            cursor = connection.cursor()

            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [info[1] for info in cursor.fetchall()]
            
            if column_name not in columns:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} {"DEFAULT "+column_default_value if column_default_value else ""}")

    except:
        connection.close()

def drop_index_if_exists(connection, index_name):
    cursor = connection.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,)
    )
    if cursor.fetchone():
        cursor.execute(f"DROP INDEX {index_name}")

    connection.commit()