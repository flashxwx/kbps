import threading, time, os, datetime as dt, subprocess, math
from typing import NamedTuple
from dataclasses import dataclass
from queue import Queue

from sortedcontainers import SortedSet

import sqlite3

from database.utils import open_cursor

ELO_COMPRESSION_FOR_SEASON_CHANGE = 0.5

@dataclass(slots=True)
class DMPlayer():
    id: int
    season_id: str
    nickname: str
    clan_tag: str = ""
    kills: int = 0
    bot_kills: int = 0
    elo: float = 1000
    logs: str = ""
    match_played_count: int = 0
    rowid: int = None
    elo_after: float = 1000
    log_buffer: str = ""

    def add_to_log_buffer(self, message: str):
        if len(self.log_buffer) > 0:
            self.log_buffer += "\n"

        self.log_buffer += message

    def flush_log_buffer(self):
        if len(self.logs) > 0:
            self.log_buffer += "\n"

        self.logs = self.log_buffer + self.logs

        if len(self.logs) > 2000:
            self.logs = self.logs[:2000]
            self.logs = self.logs[:self.logs.rindex("<")]

        self.log_buffer = ""

@dataclass(slots=True)
class Clan():
    tag: str
    season_id: str
    name: str
    elo_addend: float = 0
    elo_subtrahend: float = 0
    elo: float = 1000
    logs: str = ""
    rowid: int = None
    member_count: int = 0
    got_from_database: bool = False
    log_buffer: str = ""
    elo_after: float = 1000

    def add_to_log_buffer(self, message: str, nl: bool = True):
        if nl and len(self.log_buffer) > 0:
            self.log_buffer += "\n"

        self.log_buffer += message

    def flush_log_buffer(self):
        if len(self.logs) > 0:
            self.log_buffer += "\n"

        self.logs = self.log_buffer + self.logs

        if len(self.logs) > 2000:
            self.logs = self.logs[:2000]
            self.logs = self.logs[:self.logs.rindex("<")]

        self.log_buffer = ""

class SlayRanking:
    current_season_id = ""
    current_total_quarter = 0
    next_season_start_timestamp = 0

    existed_season_ids_in_history: SortedSet = SortedSet()
    """ arranged from oldest season to newest. Use reversed() to iterate from the newest. """

    season_check_lock = threading.Lock()

    def season_check():
        with SlayRanking.season_check_lock:
            if time.time() > SlayRanking.next_season_start_timestamp:
                current_datetime = dt.datetime.now(dt.timezone.utc)
                current_quarter = ((current_datetime.month - 1) // 3) + 1
                next_quarter = current_quarter + 1

                new_current_season_id = f"S{current_datetime.year}Q{current_quarter}"

                if new_current_season_id not in SlayRanking.existed_season_ids_in_history:
                    with open("database/slay_ranking_season_ids.db.txt", "a") as file:
                        file.write(new_current_season_id + "\n")

                    SlayRanking.existed_season_ids_in_history.add(new_current_season_id)

                SlayRanking.current_season_id = new_current_season_id
                SlayRanking.current_total_quarter = (current_datetime.year * 4) + current_quarter

                if next_quarter == 5:
                    SlayRanking.next_season_start_timestamp = dt.datetime(
                        year=current_datetime.year + 1,
                        month=1,
                        day=1,
                        tzinfo=dt.timezone.utc
                    ).timestamp()
                else:
                    SlayRanking.next_season_start_timestamp = dt.datetime(
                        year=current_datetime.year,
                        month=(next_quarter * 3) - 2,
                        day=1,
                        tzinfo=dt.timezone.utc
                    ).timestamp()

    def distance_between_current_season(target_season_id: str):
        if target_season_id == SlayRanking.current_season_id:
            return 0

        target_year_str, target_quarter_str = target_season_id[1:].split("Q")

        return SlayRanking.current_total_quarter - ((int(target_year_str) * 4) + int(target_quarter_str))

    def __init__(self):
        SlayRanking.season_check()

        self.connection = sqlite3.Connection("database/slay_ranking.sqlite.db")

    def save_dm_player_with_no_rank(self, server_name, dm_player: DMPlayer):
        SlayRanking.season_check()

        with open_cursor(self.connection, need_commit=True) as cursor:
            cursor.execute(
                f"INSERT INTO {server_name}_DEATHMATCH_RANKING "
                "(ID, SEASON_ID, NICKNAME, CLAN_TAG, BOT_KILLS) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(ID, SEASON_ID) DO UPDATE SET "
                "NICKNAME = excluded.NICKNAME, "
                "CLAN_TAG = excluded.CLAN_TAG, "
                "BOT_KILLS = excluded.BOT_KILLS",
                (
                    dm_player.id,
                    SlayRanking.current_season_id,
                    dm_player.nickname,
                    dm_player.clan_tag,
                    dm_player.bot_kills
                )
            )

    def search_dm_player(self, server_name: str, nickname: str, season_id: str):
        # if season_id == None:
        #     season_id = self.current_season_id
        query = (
            f"SELECT a.*, a.rowid FROM {server_name}_DEATHMATCH_RANKING a "
            "JOIN SEARCH_INDEX_FTS5 b ON b.REFERENCE_KEY = a.ID || '|' || a.SEASON_ID "
            f"WHERE b.SEARCH_TEXT MATCH ? AND b.REGION = \"{server_name}\" AND b.SEASON_ID = ? AND b.TABLE_TYPE = \"DEATHMATCH\" "
            "ORDER BY a.MATCH_PLAYED_COUNT DESC LIMIT 8"
        )

        with open_cursor(self.connection) as cursor:
            data = cursor.execute(query, (nickname, season_id)).fetchall()

        return list(map(lambda d: DMPlayer(*d), data))

    def save_dm_player(self, server_name: str, dm_player: DMPlayer):
        SlayRanking.season_check()

        with open_cursor(self.connection, need_commit=True) as cursor:
            cursor.execute(
                f"INSERT INTO {server_name}_DEATHMATCH_RANKING "
                "(ID, SEASON_ID, NICKNAME, CLAN_TAG, KILLS, BOT_KILLS, ELO, LOGS, MATCH_PLAYED_COUNT) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(ID, SEASON_ID) DO UPDATE SET "
                "NICKNAME = excluded.NICKNAME, "
                "CLAN_TAG = excluded.CLAN_TAG, "
                "KILLS = excluded.KILLS, "
                "BOT_KILLS = excluded.BOT_KILLS, "
                "ELO = excluded.ELO, "
                "LOGS = excluded.LOGS, "
                "MATCH_PLAYED_COUNT = excluded.MATCH_PLAYED_COUNT",
                (
                    dm_player.id, 
                    SlayRanking.current_season_id,
                    dm_player.nickname, 
                    dm_player.clan_tag,
                    dm_player.kills, 
                    dm_player.bot_kills, 
                    dm_player.elo,
                    dm_player.logs, 
                    dm_player.match_played_count
                )
            )

    def fetch_dm_player_ranks(self, server_name: str, id: int, season_id: str) -> tuple[int, int, int]:
        with open_cursor(self.connection) as cursor:
            return cursor.execute(
                "SELECT "
                f"(SELECT COUNT(*) + 1 FROM {server_name}_DEATHMATCH_RANKING WHERE SEASON_ID=? AND KILLS > a.KILLS),"
                f"(SELECT COUNT(*) + 1 FROM {server_name}_DEATHMATCH_RANKING WHERE SEASON_ID=? AND BOT_KILLS > a.BOT_KILLS),"
                f"(SELECT COUNT(*) + 1 FROM {server_name}_DEATHMATCH_RANKING WHERE SEASON_ID=? AND ELO > a.ELO) "
                f"FROM {server_name}_DEATHMATCH_RANKING a WHERE ID=? AND SEASON_ID=?",
                (season_id, season_id, season_id, id, season_id)
            ).fetchone()

    def fetch_dm_player(self, server_name: str, id: int, season_id: str = None, do_season_check: bool = False):
        with open_cursor(self.connection) as cursor:
            if season_id:
                data = cursor.execute(
                    "SELECT * "
                    f"FROM {server_name}_DEATHMATCH_RANKING WHERE ID = ? AND SEASON_ID = ?",
                    (id, season_id)
                ).fetchone()
            else:
                data = cursor.execute(
                    f"SELECT * FROM {server_name}_DEATHMATCH_RANKING WHERE ID = ? ORDER BY "
                    "CAST(SUBSTR(SEASON_ID, 2, 4) AS INTEGER) DESC, "
                    "CAST(SUBSTR(SEASON_ID, 7, 1) AS INTEGER) DESC LIMIT 1", (id,)
                ).fetchone()

        if data:
            dm_player = DMPlayer(*data)
        else:
            return

        if not do_season_check:
            return dm_player

        if distance := SlayRanking.distance_between_current_season(dm_player.season_id):
            org_season_id = dm_player.season_id

            dm_player.season_id = SlayRanking.current_season_id
            dm_player.kills = 0
            dm_player.bot_kills = 0

            org_elo = dm_player.elo
            elo_change = dm_player.elo - 1000

            if elo_change > 0:
                for _ in range(distance):
                    elo_change = elo_change * ELO_COMPRESSION_FOR_SEASON_CHANGE

                dm_player.elo = round(1000 + elo_change, 2)
            else:
                dm_player.elo = 1000
            
            dm_player.add_to_log_buffer(
                f"```diff\n- Season ELO Update: {org_elo}({org_season_id}) -> {dm_player.elo}({dm_player.season_id})```"
            )
            dm_player.flush_log_buffer()

        return dm_player

    def fetch_dm_players_by_ranking_page(self, server_name: str, column_name: str, season_id: str, page: int):
        with open_cursor(self.connection) as cursor:
            data = cursor.execute(
                f"SELECT 1 FROM {server_name}_DEATHMATCH_RANKING WHERE SEASON_ID = ? LIMIT 1 OFFSET 1000",
                (season_id,)
            ).fetchone()

            more_than_1000 = True if data else False

            if more_than_1000:
                max_page = 200
            else:
                data = cursor.execute(f"SELECT COUNT(*) FROM {server_name}_DEATHMATCH_RANKING WHERE SEASON_ID = ?", (season_id,)).fetchone()
                max_page = math.ceil(data[0] / 5)

                if max_page == 0:
                    return [], page, 0

            if page < 1:
                page = 1
            if page > max_page:
                page = max_page

            data = cursor.execute(
                f"SELECT ID, SEASON_ID, NICKNAME, CLAN_TAG, KILLS, BOT_KILLS, ELO "
                f"FROM {server_name}_DEATHMATCH_RANKING WHERE SEASON_ID = ? "
                f"ORDER BY {column_name} DESC LIMIT 5 OFFSET {(page-1)*5}",
                (season_id,)
            ).fetchall()

        return [DMPlayer(*datum) for datum in data], page, max_page

    def fetch_clan_ranks(self, server_name: str, tag: str, season_id: str) -> tuple[int]:
        with open_cursor(self.connection) as cursor:
            return cursor.execute(
                "SELECT "
                f"(SELECT COUNT(*) + 1 FROM {server_name}_CLAN_RANKING WHERE SEASON_ID=? AND ELO > a.ELO) "
                f"FROM {server_name}_CLAN_RANKING a WHERE TAG=? AND SEASON_ID=?",
                (season_id, tag, season_id)
            ).fetchone()

    def search_clan(self, server_name: str, tag: str, season_id: str = None):
        # if season_id == None:
        #     season_id = self.current_season_id

        query = (
            f"SELECT a.*, a._rowid_ FROM {server_name}_CLAN_RANKING a "
            "JOIN SEARCH_INDEX_FTS5 b ON b.REFERENCE_KEY = a.TAG || '|' || a.SEASON_ID "
            f"WHERE b.SEARCH_TEXT MATCH ? AND b.REGION = \"{server_name}\" AND b.SEASON_ID = ? AND b.TABLE_TYPE = \"CLAN\" "
            "ORDER BY a.ELO DESC LIMIT 8"
        )

        with open_cursor(self.connection) as cursor:
            data = cursor.execute(query, (tag, season_id)).fetchall()

        return list(map(lambda d: Clan(*d), data))

    def fetch_clan_by_ranking_page(self, server_name: str, season_id: str, page: int):
        with open_cursor(self.connection) as cursor:
            data = cursor.execute(
                f"SELECT 1 FROM {server_name}_CLAN_RANKING WHERE SEASON_ID = ? LIMIT 1 OFFSET 1000",
                (season_id,)
            ).fetchone()

            more_than_1000 = True if data else False

            if more_than_1000:
                max_page = 100
            else:
                data = cursor.execute(f"SELECT COUNT(*) FROM {server_name}_CLAN_RANKING WHERE SEASON_ID = ?", (season_id,)).fetchone()
                max_page = math.ceil(data[0] / 10)

                if max_page == 0:
                    return [], page, 0

            if page < 1:
                page = 1
            if page > max_page:
                page = max_page

            data = cursor.execute(
                f"SELECT TAG, SEASON_ID, NAME, ELO_ADDEND, ELO_SUBTRAHEND, ELO "
                f"FROM {server_name}_CLAN_RANKING WHERE SEASON_ID = ? "
                f"ORDER BY ELO DESC LIMIT 10 OFFSET {(page-1)*10}",
                (season_id,)
            ).fetchall()

        return [Clan(*datum) for datum in data], page, max_page

    def save_clan(self, server_name: str, clan: Clan):
        SlayRanking.season_check()

        with open_cursor(self.connection, need_commit=True) as cursor:
            cursor.execute(
                f"INSERT INTO {server_name}_CLAN_RANKING "
                f"(TAG, SEASON_ID, NAME, ELO_ADDEND, ELO_SUBTRAHEND, ELO, LOGS) "
                f"VALUES (?, ?, ?, ?, ?, ?, ?) "
                f"ON CONFLICT(TAG, SEASON_ID) DO UPDATE SET "
                f"NAME = excluded.NAME, "
                f"ELO_ADDEND = excluded.ELO_ADDEND, "
                f"ELO_SUBTRAHEND = excluded.ELO_SUBTRAHEND, "
                f"ELO = excluded.ELO, "
                f"LOGS = excluded.LOGS",
                (
                    clan.tag, 
                    SlayRanking.current_season_id, 
                    clan.name, 
                    clan.elo_addend, 
                    clan.elo_subtrahend, 
                    clan.elo, 
                    clan.logs
                )
            )

    def fetch_clan(self, server_name: str, tag: str, season_id: str=None, do_season_check: bool = False):
        with open_cursor(self.connection) as cursor:
            data = cursor.execute(
                "SELECT * "
                f"FROM {server_name}_CLAN_RANKING WHERE TAG = ? AND SEASON_ID = ?",
                (tag, season_id if season_id else SlayRanking.current_season_id)
            ).fetchone()

        if data:
            clan = Clan(*data, got_from_database=True)
        else:
            return

        if not do_season_check:
            return clan

        if distance := SlayRanking.distance_between_current_season(clan.season_id):
            org_season_id = clan.season_id

            clan.season_id = SlayRanking.current_season_id
            clan.elo_addend = 0
            clan.elo_subtrahend = 0

            org_elo = clan.elo
            elo_change = clan.elo - 1000

            if elo_change > 0:
                for _ in range(distance):
                    elo_change = elo_change * ELO_COMPRESSION_FOR_SEASON_CHANGE

                clan.elo = round(1000 + elo_change, 2)
            else:
                clan.elo = 1000
            
            clan.add_to_log_buffer(
                f"```diff\n- Season ELO Update: {org_elo}({org_season_id}) -> {clan.elo}({clan.season_id})```"
            )
            clan.flush_log_buffer()

        return clan

def init_existed_season_name_in_history():
    if len(SlayRanking.existed_season_ids_in_history) > 0:
        return

    with open("database/slay_ranking_season_ids.db.txt", "r", encoding="utf-8") as file:
        for line in file:
            SlayRanking.existed_season_ids_in_history.add(line[:-1])

def _test():
    init_existed_season_name_in_history()
    print(SlayRanking.existed_season_ids_in_history)