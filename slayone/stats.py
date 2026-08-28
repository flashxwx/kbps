# Match Scan and Match Watch have to use Queue to send the info that stats need.

import threading, time

from queue import Queue
from dataclasses import dataclass

from utils import sleep_with_event, sleep_until_with_event

import database
from slay import Info
from sortedcontainers import SortedDict

from slayone.ranking_info import RankingInfoDict

stats_thread_close_event = threading.Event()

real_player_count_of_each_server = [0, 0, 0]
real_player_count_queue = Queue() # (server_index, addend)
real_player_count_last_time = [0, 0, 0]

real_player_count_peak_of_each_server = [0, 0, 0]
real_player_count_peak_lock = threading.Lock()

solo_ranked_search_count_of_each_server = [0, 0, 0]
# solo_ranked_search_count_queue = Queue() # (server_index, mode, number)

@dataclass(slots=True)
class GameRoomInfo:
    mode: Info.GameMode
    map_name: str
    round_time: float
    max_players: int
    all_real_players_info: SortedDict | dict[int, "GameRoomInfo.PlayerInfo"]
    current_players_info: dict[int, "GameRoomInfo.PlayerInfo"]
    all_real_ranking_info: RankingInfoDict
    current_ranking_info: RankingInfoDict
    """ { score: {in_game_id, ...}} """
    all_player_nicknames: set[str]

    @dataclass(slots=True)
    class PlayerInfo:
        id: int
        nickname: str
        clan_tag: str = ""
        duration_info: "GameRoomInfo.DurationInfo" = None
        kills: int = 0
        bot_kills: int = 0
        last_injury_info: "GameRoomInfo.LastInjuryInfo" = None

    @dataclass(slots=True)
    class LastInjuryInfo:
        by: int
        at: float

    @dataclass(slots=True)
    class DurationInfo:
        timestamp_for_next_duration_settlement: float | None
        settled_duration: float = 0.0

        def settle(self, now: float = None):
            if self.timestamp_for_next_duration_settlement != None:
                self.settled_duration += (now if now else time.time()) - self.timestamp_for_next_duration_settlement
                self.timestamp_for_next_duration_settlement = None

            return self.settled_duration

    def current_top_players(self, number: int):
        for in_game_id_set in self.current_ranking_info.values():
            for in_game_id in in_game_id_set:
                if number == 0:
                    return

                yield self.current_players_info[in_game_id]

                number -= 1

game_rooms_info_of_each_server: tuple[SortedDict | dict[int, GameRoomInfo]] = (SortedDict(), SortedDict(), SortedDict())
game_rooms_info_lock = threading.Lock() # This is only needed when adding or removing game room info. # actually no need, check https://docs.python.org/3/library/threadsafety.html, i am lazy to make change on this
# game_rooms_info_bin = ({}, {}, {})
# game_rooms_info_bin_lock = threading.Lock() # This is only needed when adding or removing game room info.

def real_player_count_loop():
    from dc import slay_radio

    global real_player_count_last_time

    while True:
        data = real_player_count_queue.get()
        if data == None:
            return

        server_index = data[0]

        old_real_player_count = real_player_count_of_each_server[server_index]
        new_real_player_count = old_real_player_count + data[1]

        if new_real_player_count < 0: # bad practice, but sometimes it goes to negative number, and I couldn't find out the reason
            new_real_player_count = 0

        real_player_count_of_each_server[server_index] = new_real_player_count

        real_player_count_last_time[server_index] = time.time()

        if new_real_player_count > old_real_player_count:
            if new_real_player_count == 1:
                slay_radio.add_broadcast_message(
                    f"there was {new_real_player_count} person playing in **{slay_radio.server_texts[server_index]}**",
                    f"player_count_increment-{server_index}"
                )
            else:
                slay_radio.add_broadcast_message(
                    f"there were {new_real_player_count} people playing in **{slay_radio.server_texts[server_index]}**",
                    f"player_count_increment-{server_index}"
                )

        if new_real_player_count > real_player_count_peak_of_each_server[server_index]:
            with real_player_count_peak_lock:
                real_player_count_peak_of_each_server[server_index] = new_real_player_count
        
        # print("real player count:", real_player_count_of_each_server)
        # print("peaks:", real_player_count_peak_of_each_server)

def real_player_count_peak_export_loop():
    global real_player_count_peak_of_each_server

    current_timestamp = time.time()

    next_hour_timestamp = current_timestamp - (current_timestamp % 3600) + 3600

    is_full = sleep_until_with_event(stats_thread_close_event, next_hour_timestamp)

    if not is_full:
        return

    with real_player_count_peak_lock:
        real_player_count_peak_of_each_server = [0, 0, 0]

    while True:
        current_hour_timestamp = next_hour_timestamp
        next_hour_timestamp += 3600

        is_full = sleep_until_with_event(stats_thread_close_event, next_hour_timestamp)
        if not is_full:
            return

        with real_player_count_peak_lock:
            copy_of_real_player_count_peak_of_each_server = real_player_count_peak_of_each_server.copy()
            real_player_count_peak_of_each_server = [0, 0, 0]

        slay_peaks_database = database.SlayPeaks()

        slay_peaks_database.insert_peak("EU", current_hour_timestamp, copy_of_real_player_count_peak_of_each_server[0])
        slay_peaks_database.insert_peak("AM", current_hour_timestamp, copy_of_real_player_count_peak_of_each_server[1])
        slay_peaks_database.insert_peak("ASIA", current_hour_timestamp, copy_of_real_player_count_peak_of_each_server[2])

        slay_peaks_database.connection.close()

# def solo_ranked_search_count_loop():
#     while True:
#         data = solo_ranked_search_count_queue.get()
#         if data == None:
#             return

#         mode = data[1]
#         if mode == 0:
#             solo_ranked_search_count_of_each_server[data[0]] = data[2]
#         elif mode == 1:
#             solo_ranked_search_count_of_each_server[data[0]] += data[2]

def return_all_broadcast_message() -> str:
    from dc import slay_radio

    message = "Currently, "

    for server_index, count in enumerate(solo_ranked_search_count_of_each_server):
        if len(message) > 11:
            message += "\n and "

        if count == 1:
            message += f"there is 1 person searching for 1v1 ranked match in {slay_radio.server_texts[server_index]}"
        else:
            message += f"there are {count} people searching for 1v1 ranked match in {slay_radio.server_texts[server_index]}"
        

    for server_index, count in enumerate(real_player_count_of_each_server):
        if len(message) > 11:
            message += "\n and "

        if count == 1:
            message += f"there is 1 person playing in {slay_radio.server_texts[server_index]}"
        else:
            message += f"there are {count} people playing in {slay_radio.server_texts[server_index]}"

    if len(message) > 11:
        return message
    else:
        return ""

def start_all_stats_threads():
    threading.Thread(target=real_player_count_loop).start()
    threading.Thread(target=real_player_count_peak_export_loop).start()
    # threading.Thread(target=solo_ranked_search_count_loop).start()

def stop_all_stats_threads():
    stats_thread_close_event.set()

    real_player_count_queue.put(None)
    # solo_ranked_search_count_queue.put(None)

# def update_duration_info(info: list[float], now: float):
#     new_duration = now - info[0]

#     if len(info) == 1:
#         info.append(new_duration)
#     else:
#         info[1] = new_duration