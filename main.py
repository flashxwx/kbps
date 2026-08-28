import os, sys, threading

os.environ["TEST_MODE"] = ''

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
from dc.ui.slay_peak_chart import chart_thread_pool

class State:
    need_restart = False

def main():
    import main_state

    database.start_processing_replay_saving()

    slayone.ranking.start_processing_match_ranking_settlement()
    slayone.stats.start_all_stats_threads()
    slayone.resource.monitor.start_monitoring()

    slayone.scan.connections.start(non_blocking=True, reopen_attempts=6, reopen_interval=600)

    dc.run_bot(os.environ.get("DISCORD_BOT_TOKEN"))
    slay_replay_database.connection.close()
    slay_ranking_database.connection.close()
    user_database.connection.close()
    chart_thread_pool.shutdown()
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

if __name__ == "__main__":
    main()