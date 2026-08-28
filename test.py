import os, sys, threading

os.environ["TEST_MODE"] = "true"

import dotenv
dotenv.load_dotenv()

import slay

slay.Connection.setup_log_file("slay.log")

import database
database.init_all_databases()

import dc
import slayone.stats, slayone.scan, slayone.watcher, slayone.ranking
import slayone.resource.monitor

from dc.slay_radio import broadcast_messages_process_event
from dc.ui.slay_replay import slay_replay_database
from dc.ui.slay_ranking import slay_ranking_database, user_database

def test_main():
    import main_state

    database.start_processing_replay_saving()

    slayone.ranking.start_processing_match_ranking_settlement()
    slayone.stats.start_all_stats_threads()
    slayone.resource.monitor.start_monitoring()

    slayone.scan.connections.start(non_blocking=True, reopen_attempts=6, reopen_interval=600)

    dc.run_bot(os.environ.get("DISCORD_BOT_FOR_TESTING_TOKEN"))
    slay_replay_database.connection.close()
    slay_ranking_database.connection.close()
    user_database.connection.close()
    slayone.resource.monitor.stop_monitoring()

    broadcast_messages_process_event.set()

    slayone.scan.connections.close()

    for connection in slayone.watcher.watcher_connection_set.copy():
        connection.close()

    slayone.stats.stop_all_stats_threads()
    slayone.ranking.stop_processing_match_ranking_settlement()
    database.stop_processing_replay_saving()

    if main_state.need_restart:
        main_thread = threading.main_thread()

        for thread in threading.enumerate():
            if thread == main_thread:
                continue

            thread.join()

        os.execv(sys.executable, [sys.executable] + sys.argv)

def test_dc():
    import main_state
    # database.SlayReplay().prune_space(5_000_000)

    game_room_info_example = slayone.stats.GameRoomInfo(slayone.stats.Info.GameMode.TEAM_DEATHMATCH, "map name abc", 10, 10, {}, {}, None, {}, set())
    d = slayone.stats.game_rooms_info_of_each_server[2]
    d1 = slayone.stats.game_rooms_info_of_each_server[1]
    d0 = slayone.stats.game_rooms_info_of_each_server[0]

    d[1] = game_room_info_example
    d[2] = slayone.stats.GameRoomInfo(slayone.stats.Info.GameMode.DEATHMATCH, "map name abc2", 10, 10, {}, {}, None, {}, set())
    d[3] = slayone.stats.GameRoomInfo(slayone.stats.Info.GameMode.CAPTURE_THE_FLAG, "map name abc3", 10, 10, {}, {}, None, {}, set())

    d0[1] = game_room_info_example
    d0[2] = slayone.stats.GameRoomInfo(slayone.stats.Info.GameMode.DEATHMATCH, "map name abc2", 10, 10, {}, {}, None, {}, set())
    d0[3] = slayone.stats.GameRoomInfo(slayone.stats.Info.GameMode.CAPTURE_THE_FLAG, "map name abc3", 10, 10, {}, {}, None, {}, set())

    d1[1] = game_room_info_example
    d1[2] = slayone.stats.GameRoomInfo(slayone.stats.Info.GameMode.DEATHMATCH, "map name abc2", 10, 10, {}, {}, None, {}, set())
    d1[3] = slayone.stats.GameRoomInfo(slayone.stats.Info.GameMode.CAPTURE_THE_FLAG, "map name abc3", 10, 10, {}, {}, None, {}, set())
    # d[4] = slayone.stats.GameRoomInfo(slayone.stats.Info.GameMode.INFECTION, "map name abc4", 10, 10, {}, {}, None, {}, set())

    dc.run_bot(os.environ.get("DISCORD_BOT_FOR_TESTING_TOKEN"))
    slay_replay_database.connection.close()
    slay_ranking_database.connection.close()
    user_database.connection.close()

    broadcast_messages_process_event.set()

    if main_state.need_restart:
        main_thread = threading.main_thread()

        for thread in threading.enumerate():
            if thread == main_thread:
                continue

            thread.join()

        os.execv(sys.executable, [sys.executable] + sys.argv)

def test_module():
    import slayone.ranking

    slayone.ranking._test()

globals()[f"test_{"" if len(sys.argv) < 2 else sys.argv[1]}"]()