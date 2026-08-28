# The unit of sizes here are all in bytes

import os, sqlite3, threading
from typing import NamedTuple
from collections import deque
from queue import Queue

from slay import Info

from database.utils import open_cursor

used_space_size = 0
max_used_space_size = 5_000_000_000

replay_queue: Queue["Replay"] = Queue()

class Replay(NamedTuple):
    """ id: [server_index]-[mode_index]-[game-id]-[timestamp] """

    id: int
    server_index: int
    mode_index: int
    timestamp: int
    size_in_bytes: int
    title: str
    info: str
    json: str

class ReplayMetadata(NamedTuple):
    id: int
    server_index: int
    mode_index: int
    timestamp: int
    size_in_bytes: int
    title: str
    info: str = ""

def init_slay_replay_global_value():
    global used_space_size

    with open("database/slay_replay_used_space_size.db.txt", "a+") as file:
        file.seek(0)
        used_space_size_str = file.read()

    if used_space_size_str:
        used_space_size = int(used_space_size_str)

class SlayReplay:
    def __init__(self):
        self.connection = sqlite3.Connection("database/slay_replay.sqlite.db")

    def update_used_space_size(self):
        with open("database/slay_replay_used_space_size.temp.txt", "w") as file:
            file.write(str(used_space_size))
            file.flush()
            os.fsync(file.fileno())

        os.replace("database/slay_replay_used_space_size.temp.txt", "database/slay_replay_used_space_size.db.txt")

    def insert_replay(self, replay: Replay):
        global used_space_size

        with open_cursor(self.connection, need_commit=True) as cursor:
            cursor.execute(
                "INSERT INTO REPLAY_METADATA (ID, SERVER_INDEX, MODE_INDEX, TIMESTAMP, SIZE, TITLE, INFO) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (replay.id, replay.server_index, replay.mode_index, replay.timestamp, replay.size_in_bytes, replay.title, replay.info)
            )

            cursor.execute("INSERT INTO REPLAY_JSONS (ID, JSON) VALUES (?,?)", (replay.id, replay.json))

            used_space_size += replay.size_in_bytes
            self.update_used_space_size()

    def fetch_replay_json_by_id(self, id: str):
        with open_cursor(self.connection) as cursor:
            data: str | None = cursor.execute("SELECT JSON FROM REPLAY_JSONS WHERE ID = ?", (id,)).fetchone()

        if data:
            return data[0]

    def fetch_replay_metadata_by_id(self, id: str):
        with open_cursor(self.connection) as cursor:
            data = cursor.execute("SELECT * FROM REPLAY_METADATA WHERE ID = ?", (id,)).fetchone()

        if data:
            return ReplayMetadata(*data)

    def fetch_replay_metadata_by_filter(self, server_query: str, mode_query: str, offset: int = 0, limit: int = 10):
        with open_cursor(self.connection) as cursor:
            total_rows = cursor.execute(f"SELECT COUNT(*) FROM REPLAY_METADATA WHERE ({server_query}) AND ({mode_query})").fetchone()[0]

            all_metadata = cursor.execute(
                "SELECT ID, SERVER_INDEX, MODE_INDEX, TIMESTAMP, SIZE, TITLE FROM REPLAY_METADATA "
                f"WHERE ({server_query}) AND ({mode_query}) "
                f"ORDER BY TIMESTAMP DESC LIMIT {limit} OFFSET {offset}"
            ).fetchall()

        return map(lambda x: ReplayMetadata(*x), all_metadata), total_rows

    def prune_space(self, size: int):
        global used_space_size

        while (size > 0) and (used_space_size > 0):
            with open_cursor(self.connection, need_commit=True) as cursor:
                replay_id, replay_size = cursor.execute("SELECT ID, SIZE FROM REPLAY_METADATA ORDER BY TIMESTAMP ASC LIMIT 1").fetchone()

                cursor.execute(f"DELETE FROM REPLAY_METADATA WHERE ID = '{replay_id}'")
                cursor.execute(f"DELETE FROM REPLAY_JSONS WHERE ID = '{replay_id}'")

                used_space_size = max(0, used_space_size - replay_size)
                self.update_used_space_size()

                size -= replay_size

def process_replay_saving():
    slay_replay_database = SlayReplay()

    while True:
        replay = replay_queue.get()
        if replay == -1:
            return

        new_used_space_size = used_space_size + replay.size_in_bytes

        slay_replay_database.prune_space(new_used_space_size - max_used_space_size)

        slay_replay_database.insert_replay(replay)

def start_processing_replay_saving():
    threading.Thread(target=process_replay_saving).start()

def stop_processing_replay_saving():
    replay_queue.put(-1)