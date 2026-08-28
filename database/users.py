import sqlite3

from database.utils import open_cursor

class Users:
    def __init__(self):
        self.connection = sqlite3.Connection("database/users.sqlite.db")

    def is_favorite_player(self, discord_user_id: int, player_id: int):
        with open_cursor(self.connection) as cursor:
            return bool(cursor.execute(
                f"SELECT EXISTS(SELECT 1 FROM FAVORITE_PLAYERS WHERE DISCORD_USER_ID={discord_user_id} AND PLAYER_ID = ?)",
                (player_id,)
            ).fetchone()[0])

    def is_favorite_clan(self, discord_user_id: int, tag: str):
        with open_cursor(self.connection) as cursor:
            return bool(cursor.execute(
                f"SELECT EXISTS(SELECT 1 FROM FAVORITE_CLANS WHERE DISCORD_USER_ID={discord_user_id} AND CLAN_TAG = ?)",
                (tag,)
            ).fetchone()[0])

    def insert_favorite_player(self, discord_user_id: int, player_id: int, nickname: str):
        with open_cursor(self.connection, need_commit=True) as cursor:
            cursor.execute(f"INSERT INTO FAVORITE_PLAYERS VALUES ({discord_user_id}, ?, ?)", (player_id, nickname))

    def delete_favorite_player(self, discord_user_id: int, player_id: int):
        with open_cursor(self.connection, need_commit=True) as cursor:
            cursor.execute(f"DELETE FROM FAVORITE_PLAYERS WHERE DISCORD_USER_ID = {discord_user_id} AND PLAYER_ID = ?", (player_id,))

    def favorite_players(self, discord_user_id: int) -> list[tuple[int, str]]:
        with open_cursor(self.connection) as cursor:
            return cursor.execute(f"SELECT PLAYER_ID, NICKNAME FROM FAVORITE_PLAYERS WHERE DISCORD_USER_ID = {discord_user_id}").fetchall()

    def favorite_players_count(self, discord_user_id: int):
        with open_cursor(self.connection) as cursor:
            return cursor.execute(f"SELECT COUNT(*) FROM FAVORITE_PLAYERS WHERE DISCORD_USER_ID = {discord_user_id}").fetchone()[0]

    def insert_favorite_clan(self, discord_user_id: int, clan_tag: str):
        with open_cursor(self.connection, need_commit=True) as cursor:
            cursor.execute(f"INSERT INTO FAVORITE_CLANS VALUES ({discord_user_id}, ?)", (clan_tag,))

    def delete_favorite_clan(self, discord_user_id: int, clan_tag: str):
        with open_cursor(self.connection, need_commit=True) as cursor:
            cursor.execute(f"DELETE FROM FAVORITE_CLANS WHERE DISCORD_USER_ID = {discord_user_id} AND CLAN_TAG = ?", (clan_tag,))

    def favorite_clans(self, discord_user_id: int):
        with open_cursor(self.connection) as cursor:
            return cursor.execute(f"SELECT CLAN_TAG FROM FAVORITE_CLANS WHERE DISCORD_USER_ID = {discord_user_id}").fetchall()

    def favorite_clans_count(self, discord_user_id: int):
        with open_cursor(self.connection) as cursor:
            return cursor.execute(f"SELECT COUNT(*) FROM FAVORITE_CLANS WHERE DISCORD_USER_ID = {discord_user_id}").fetchone()[0]

    def insert_radio_receiver(self, discord_user_id: int):
        self.connection.executescript(
            "INSERT OR IGNORE INTO DMS_RADIO_RECEIVERS (DISCORD_USER_ID)"
            f" VALUES ({discord_user_id})"
        )
    
    def fetch_radio_receiver(self, discord_user_id: int):
        with open_cursor(self.connection) as cursor:
            cursor.execute(
                f"SELECT * FROM DMS_RADIO_RECEIVERS WHERE DISCORD_USER_ID = {discord_user_id}"
            )

            return cursor.fetchone()
    
    def delete_radio_receiver(self, discord_user_id: int):
        self.connection.executescript(
            "DELETE FROM DMS_RADIO_RECEIVERS"
            f" WHERE DISCORD_USER_ID = {discord_user_id}"
        )

    def radio_receivers(self, batch_size: int = 1000):
        with open_cursor(self.connection) as cursor:
            cursor.execute("SELECT DISCORD_USER_ID FROM DMS_RADIO_RECEIVERS")

            while True:
                infos = cursor.fetchmany(batch_size)

                if not infos:
                    break

                for info in infos:
                    yield info