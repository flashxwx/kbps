# Match Watcher Logic: Cost 1 connection per match

import time, copy, logging, os
from itertools import islice

from sortedcontainers import SortedDict

from slay import Connection, Socket, Info, Request

from slayone.stats import (
    real_player_count_queue, game_rooms_info_of_each_server, game_rooms_info_lock, GameRoomInfo
)

from slayone.ranking import RankingInfoDict, match_ranking_for_settlement_queue
from database import Replay, replay_queue

watcher_switch = True # Switch of watcher feature
watching_game_room_id_set_of_each_server = [set(), set(), set()]
watcher_connection_set: set["WatcherConnection"] = set()

valid_attack_duration = 5

class WatcherConnection(Connection):
    def __init__(self, socket, game_id: int):
        self.settled_all = False
        self.game_start_timestamp = 0
        self.last_game_end_timestamp = 0
        self.game_id = game_id
        self.has_just_joined = True
        self.game_room_info: GameRoomInfo = None

        super().__init__(socket, "watcher", sequence=game_id, enable_replay_cache=True)

        if os.environ.get("TEST_MODE"):
            self.logging_level = logging.INFO
        else:
            self.logging_level = logging.ERROR

    def save_replay(self, is_current: bool = True):
        if is_current:
            replay_json = self.json_from_replay("current")
            mins, secs = divmod(int(time.time()) - self.game_start_timestamp, 60)
        else:
            replay_json = self.json_from_replay("last")
            mins, secs = divmod((self.last_game_end_timestamp - self.game_start_timestamp), 60)

        timestamp = self.game_start_timestamp
        server_index = self.socket.index
        mode_index = self.game_room_info.mode.id

        info = "Players who played: " + ", ".join(islice(self.game_room_info.all_player_nicknames, 75))

        if len(self.game_room_info.all_player_nicknames) > 75:
            info += ", ..."

        replay_queue.put(Replay(
            f"{server_index}-{mode_index}-{self.game_id}-{timestamp}",
            server_index,
            mode_index,
            timestamp,
            len(replay_json.encode("utf-8")),
            f"{self.game_room_info.map_name}, Starts At <t:{timestamp}:F>, {mins} minutes {secs} seconds",
            info,
            replay_json
        ))

def watch_unwatched_game_rooms(socket: Socket, game_profile_list: list[Info.GameProfile]):
    watching_game_room_id_set = watching_game_room_id_set_of_each_server[socket.index]
    
    for game_profile in game_profile_list:
        if game_profile.id not in watching_game_room_id_set:
            create_watcher(socket, game_profile.id, game_profile.map_name, game_profile.max_player_amount)

def create_watcher(socket: Socket, game_id: int, map_name: str, max_players: int): # Watcher means the connection that watch a game
    watching_game_room_id_set = watching_game_room_id_set_of_each_server[socket.index]

    if game_id in watching_game_room_id_set:
        return

    connection = WatcherConnection(socket, game_id)
    # connection.logging_level = logging.WARNING

    connection.map_name = map_name
    connection.max_players = max_players

    connection.on_open = on_open
    connection.on_close = on_close

    connection.on_game_init = on_game_init
    connection.on_player_join = on_player_join
    connection.on_player_leave = on_player_leave
    connection.on_player_respawn = on_player_respawn

    connection.on_hp_update = on_hp_update

    connection.on_game_round_end = on_game_round_end
    connection.on_game_settlement_end = on_game_settlement_end
    
    watching_game_room_id_set.add(game_id)

    watcher_connection_set.add(connection)
    connection.start(non_blocking=True)

def on_open(connection: WatcherConnection):
    connection.setup_response_event_timeout_func("on_game_init", fail_to_join_game_room)
    connection.send(Request.JoinGameRoom(connection.game_id))

def fail_to_join_game_room(connection: WatcherConnection):
    connection.log("INFO", f"Game room ({connection.game_id}) not found, closing connection.")
    connection.close()

def on_game_init(connection: WatcherConnection, info: Info.GameInitial):
    now = time.time()

    connection.settled_all = False

    if not connection.has_just_joined:
        if (time.time() - connection.game_start_timestamp) > 300:  
            connection.save_replay(is_current=False)

        game_room_info = connection.game_room_info

        game_room_info.map_name = map_name.title() if (map_name := info.game_data.map_data.get("name")) else "Unknown Map"
        if new_max_players := info.game_data.map_data.get("maxPlayers"):
            game_room_info.max_players = new_max_players

        game_room_info.all_player_nicknames.clear()
        all_real_players_info = connection.game_room_info.all_real_players_info = SortedDict()
        all_real_ranking_info = game_room_info.all_real_ranking_info = RankingInfoDict(lambda key: -key)

        for player_info in connection.game_room_info.current_players_info.values():
            player_info.duration_info.settled_duration = 0.0
            player_info.duration_info.timestamp_for_next_duration_settlement = now
            player_info.kills = 0
            player_info.bot_kills = 0
            player_info.last_injury_info = None

            if player_info.id > 0:
                all_real_players_info[player_info.id] = player_info
                all_real_ranking_info.set_score(player_info.id, 0)

            game_room_info.all_player_nicknames.add(player_info.nickname)

        game_room_info.current_ranking_info.set_all_to_zero_score()
        connection.game_start_timestamp = int(now)

        return

    all_real_players_info = SortedDict()
    all_real_ranking_info = RankingInfoDict(lambda key: -key)
    current_players_info: dict[int, GameRoomInfo.PlayerInfo] = dict()
    current_ranking_info = RankingInfoDict(lambda key: -key)
    all_player_nicknames = set()

    connection.game_start_timestamp = int(now)
    connection.game_room_info = GameRoomInfo(
        info.game_data.mode,
        connection.map_name,
        info.game_data.max_round_ticks / 20,
        connection.max_players,
        all_real_players_info,
        current_players_info,
        all_real_ranking_info,
        current_ranking_info,
        all_player_nicknames
    )

    if info.game_data.mode != Info.GameMode.DEATHMATCH:
        connection.is_team_mode = True

    for player in info.players:
        if player.nickname_color == Info.NicknameColor.BOT:
            continue

        player_info = GameRoomInfo.PlayerInfo(player.id, player.nickname, player.clan_tag, GameRoomInfo.DurationInfo(now))

        if player.id > 0:
            all_real_players_info[player.id] = player_info
            all_real_ranking_info.set_score(player.id, 0)

        current_players_info[player.in_game_id] = player_info
        current_ranking_info.set_score(player.in_game_id, 0)
        all_player_nicknames.add(player.nickname)

    current_player_count = len(current_players_info)

    if current_player_count == 0:
        connection.close()
        return
    elif current_player_count == 1:
        next(iter(current_players_info.values())).duration_info.settle(now)

    real_player_count_queue.put((connection.socket.index, current_player_count))

    with game_rooms_info_lock:
        game_rooms_info_of_each_server[connection.socket.index][connection.game_id] = connection.game_room_info

    connection.has_just_joined = False

def on_player_join(connection: WatcherConnection, info: Info.NewPlayer):
    if info.nickname_color_id == Info.NicknameColor.BOT.value:
        return

    now = time.time()

    current_players_info = connection.game_room_info.current_players_info
    if len(current_players_info) == 1:
        next(iter(current_players_info.values())).duration_info.timestamp_for_next_duration_settlement = now

    player_info = None

    if info.uid > 0:
        player_info = connection.game_room_info.all_real_players_info.get(info.uid)
        if player_info:
            player_info.nickname = info.nickname
            player_info.clan_tag = info.clan_tag
            player_info.duration_info.timestamp_for_next_duration_settlement = time.time()

        if not player_info:
            player_info = GameRoomInfo.PlayerInfo(info.uid, info.nickname, info.clan_tag, GameRoomInfo.DurationInfo(now))
            connection.game_room_info.all_real_players_info[info.uid] = player_info
            connection.game_room_info.all_real_ranking_info.set_score(info.uid, 0)

    if not player_info:
        player_info = GameRoomInfo.PlayerInfo(info.uid, info.nickname, info.clan_tag, GameRoomInfo.DurationInfo(now))

    current_players_info[info.in_game_id] = player_info
    connection.game_room_info.current_ranking_info.set_score(info.in_game_id, player_info.kills)
    connection.game_room_info.all_player_nicknames.add(info.nickname)

    real_player_count_queue.put((connection.socket.index, 1))

def on_player_leave(connection: WatcherConnection, in_game_id: int):
    current_players_info = connection.game_room_info.current_players_info
    player_info = current_players_info.get(in_game_id)

    if player_info:
        player_info = current_players_info.pop(in_game_id)
        player_info.duration_info.settle()

        connection.game_room_info.current_ranking_info.remove_id(in_game_id, player_info.kills)

        real_player_count_queue.put((connection.socket.index, -1))

        player_count = len(current_players_info)
        if player_count == 0:
            connection.close()
        elif player_count == 1:
            next(iter(current_players_info.values())).duration_info.settle()

def on_hp_update(connection: WatcherConnection, info: Info.HP):
    current_players_info = connection.game_room_info.current_players_info
    current_ranking_info = connection.game_room_info.current_ranking_info
    all_real_ranking_info = connection.game_room_info.all_real_ranking_info

    attacker_in_game_id = info.attacker_in_game_id
    victim_in_game_id = info.victim_in_game_id

    if info.hp != 0.0:
        if (
            (attacker_in_game_id != victim_in_game_id)
            and (victim_player_info := current_players_info.get(victim_in_game_id))
            and (current_players_info.get(attacker_in_game_id))
        ):
            victim_player_info.last_injury_info = GameRoomInfo.LastInjuryInfo(attacker_in_game_id, time.time())

        return

    if attacker_player_info := current_players_info.get(attacker_in_game_id):
        if attacker_in_game_id == victim_in_game_id:
            if (
                (last_injury_info := attacker_player_info.last_injury_info)
                and ((time.time() - last_injury_info.at) < valid_attack_duration)
                and (last_attacker_player_info := current_players_info.get(last_injury_info.by))
            ):
                new_kills = last_attacker_player_info.kills + 1
                current_ranking_info.update_score(last_injury_info.by, last_attacker_player_info.kills, new_kills)
                if last_attacker_player_info.id > 0:
                    all_real_ranking_info.update_score(last_attacker_player_info.id, last_attacker_player_info.kills, new_kills)
                last_attacker_player_info.kills = new_kills

            attacker_player_info.duration_info.settle()

        elif victim_player_info := current_players_info.get(victim_in_game_id):
            new_kills = attacker_player_info.kills + 1
            current_ranking_info.update_score(attacker_in_game_id, attacker_player_info.kills, new_kills)
            if attacker_player_info.id > 0:
                all_real_ranking_info.update_score(attacker_player_info.id, attacker_player_info.kills, new_kills)
            attacker_player_info.kills = new_kills

            victim_player_info.duration_info.settle()
        else:
            attacker_player_info.bot_kills += 1

    elif victim_player_info := current_players_info.get(victim_in_game_id):
        if (
            (last_injury_info := victim_player_info.last_injury_info)
            and ((time.time() - last_injury_info.at) < valid_attack_duration)
            and (last_attacker_player_info := current_players_info.get(last_injury_info.by))
        ):
            new_kills = last_attacker_player_info.kills + 1
            current_ranking_info.update_score(last_injury_info.by, last_attacker_player_info.kills, new_kills)
            if last_attacker_player_info.id > 0:
                all_real_ranking_info.update_score(last_attacker_player_info.id, last_attacker_player_info.kills, new_kills)
            last_attacker_player_info.kills = new_kills

        victim_player_info.duration_info.settle()

def on_player_respawn(connection: WatcherConnection, info: Info.PlayerRespawn):
    if player_info := connection.game_room_info.current_players_info.get(info.in_game_id):
        player_info.duration_info.timestamp_for_next_duration_settlement = time.time()

def on_game_round_end(connection: WatcherConnection):
    if connection.game_room_info.mode == Info.GameMode.DEATHMATCH:
        match_ranking_for_settlement_queue.put(
            copy.deepcopy((
                connection.game_room_info.all_real_players_info,
                connection.game_room_info.all_real_ranking_info,
                connection.socket.name
            ))
        )

        connection.settled_all = True

def on_game_settlement_end(connection: WatcherConnection):
    now = time.time()

    connection.last_game_end_timestamp = int(now)

def on_close(connection: WatcherConnection, code: int, message: str):
    now = time.time()
    game_duration = now - connection.game_start_timestamp

    watching_game_room_id_set_of_each_server[connection.socket.index].remove(connection.game_id)

    watcher_connection_set.remove(connection)

    if connection.has_just_joined:
        return

    if (
        connection.game_room_info.mode == Info.GameMode.DEATHMATCH
        and (not connection.settled_all)
    ):
        match_ranking_for_settlement_queue.put(
            copy.deepcopy((
                connection.game_room_info.all_real_players_info,
                connection.game_room_info.all_real_ranking_info,
                connection.socket.name
            ))
        )

    if True or os.environ.get("TEST_MODE"):
        with game_rooms_info_lock:
            del game_rooms_info_of_each_server[connection.socket.index][connection.game_id]

        real_player_count_queue.put((connection.socket.index, -len(connection.game_room_info.current_players_info)))

        if game_duration > 300:
            connection.save_replay()
    else:
        try: # bad practice, but i couldn't find the bug # I might found the bug, haven't tested by removing this bad practice # bug at connection.close in on_game_init(), didnt add return
            with game_rooms_info_lock:
                del game_rooms_info_of_each_server[connection.socket.index][connection.game_id]

            real_player_count_queue.put((connection.socket.index, -len(connection.game_room_info.current_players_info)))

            watching_game_room_id_set_of_each_server[connection.socket.index].remove(connection.game_id)

            watcher_connection_set.remove(connection)

            if game_duration > 300:
                connection.save_replay()
        except:
            ...