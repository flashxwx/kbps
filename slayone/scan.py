# Match Scan Logic: Cost 1 connection per server

import os, time

from slay import Connections, Connection, Socket, Request, Info

from slayone.stats import solo_ranked_search_count_of_each_server
from slayone.watcher import watcher_switch, watch_unwatched_game_rooms

if os.environ.get("TEST_MODE"):
    connections = Connections((Socket.ASIA,), category="scan")
else:
    connections = Connections((Socket.EU, Socket.AM, Socket.ASIA), category="scan")

game_profile_list_of_each_server: list[list[Info.GameProfile]] = [[], [], []]
last_scan_activity_time_of_each_server = [0, 0, 0] # Record the time in every event callback that used for scan.

# need_deep_scan = False # Deep scan means it will visit each game room to get more info.
game_profile_list_for_deep_scan_of_each_server: list[list[Info.GameProfile]] = [[], [], []]

def lobby_scan_request_loop(connection: Connection):
    while True:
        # Wait a 10 seconds here avoiding server doesn't process the request, server can be tricky sometimes.

        ok = connection.wait(10)
        if not ok:
            return
        
        connection.send(Request.GameList())

        ok = connection.wait(50)
        if not ok:
            return

# __timeout_time = 10
# def __is_deep_scanning(server_index: int):
#     last_scan_activity_time = last_scan_activity_time_of_each_server[server_index]

#     return (time.time() - last_scan_activity_time) < __timeout_time

@connections.on_open
def _(connection: Connection):
    if not os.environ.get("TEST_MODE"):
        connection.send(Request.LogIn("kbpschat", os.environ.get("KBPS_SLAY_ACCOUNT_PASSWORD")))

    connection.create_thread(lobby_scan_request_loop, connection)

@connections.on_game_list
def _(connection: Connection, info: list[Info.GameProfile]):

    # if need_deep_scan and (not __is_deep_scanning(connection.socket.index)) and (len(info) != 0):
    #     game_profile_list_for_deep_scan_of_each_server[connection.socket.index] = info.copy()

    #     connection.send(Request.JoinGameRoom(info[-1].id))
    
    if watcher_switch:
        watch_unwatched_game_rooms(connection.socket, info)

    game_profile_list_of_each_server[connection.socket.index] = info

    last_scan_activity_time_of_each_server[connection.socket.index] = time.time()

# @connections.on_game_init
# def _(connection: Connection, info: Info.GameInitial):
#     connection.send(Request.LeaveGame())

#     last_scan_activity_time_of_each_server[connection.socket.index] = time.time()

#     game_profile = game_profile_list_for_deep_scan_of_each_server[connection.socket.index].pop()

#     real_player_count = 0

#     for player in info.players:
#         if player.nickname_color == Info.NicknameColor.BOT:
#             continue

#         real_player_count += 1

#     if watcher_switch and real_player_count != 0:
#         create_watcher(connection.socket, game_profile.id)

# @connections.on_game_stats
# def _(connection: Connection, info: Info.GameStats):
#     game_profile_list = game_profile_list_for_deep_scan_of_each_server[connection.socket.index]

#     if len(game_profile_list) != 0:
#         connection.wait(2) # Server will not respond if joinning too fast after leaving.
#         connection.send(Request.JoinGameRoom(game_profile_list[-1].id))
#         return

@connections.on_account_logging
def _(connection: Connection, info: Info.AccountLogging):
    from dc import slay_radio

    if info.ranked_search_count == 0:
        return

    solo_ranked_search_count_of_each_server[connection.socket.index] = info.ranked_search_count

    count = info.ranked_search_count

    if count == 1:
        slay_radio.add_broadcast_message(
            f"there was {count} person searching for 1v1 ranked match in {slay_radio.server_texts[connection.socket.index]}",
            f"solo_ranked_search_count_increment-{connection.socket.index}"
        )
    else:
        slay_radio.add_broadcast_message(
            f"there were {count} people playing in {slay_radio.server_texts[connection.socket.index]}",
            f"solo_ranked_search_count_increment-{connection.socket.index}"
    )

@connections.on_ranked_search_count
def _(connection: Connection, count: int):
    from dc import slay_radio

    old_ranked_search_count = solo_ranked_search_count_of_each_server[connection.socket.index]

    solo_ranked_search_count_of_each_server[connection.socket.index] = count

    if count > old_ranked_search_count:
        if count == 1:
            slay_radio.add_broadcast_message(
                f"there was {count} person searching for 1v1 ranked match in **{slay_radio.server_texts[connection.socket.index]}**",
                f"solo_ranked_search_count_increment-{connection.socket.index}"
            )
        else:
            slay_radio.add_broadcast_message(
                f"there were {count} people playing in **{slay_radio.server_texts[connection.socket.index]}**",
                f"solo_ranked_search_count_increment-{connection.socket.index}"
            )