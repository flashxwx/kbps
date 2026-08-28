""" Becareful of SQL Injection, never concat instruction string with data string from users. """

from database.slay_peaks import SlayPeaks
from database.users import Users
from database.slay_replay import SlayReplay, Replay, init_slay_replay_global_value, start_processing_replay_saving, stop_processing_replay_saving, replay_queue
from database.slay_ranking import SlayRanking, init_existed_season_name_in_history
from database.utils import drop_index_if_exists

def init_all_databases():
    init_slay_replay_global_value()
    init_existed_season_name_in_history()

    with open("database/slay_peaks.schema.sql", "r", encoding="utf-8") as file:
        slay_peaks_schema = file.read()

    with open("database/slay_replay.schema.sql", "r", encoding="utf-8") as file:
        slay_replay_schema = file.read()

    with open("database/slay_ranking.schema.sql", "r", encoding="utf-8") as file:
        slay_ranking_schema = file.read()

    with open("database/users.schema.sql", "r", encoding="utf-8") as file:
        users_schema = file.read()

    slay_peaks_database = SlayPeaks()
    slay_replay_database = SlayReplay()
    users_database = Users()
    slay_ranking_database = SlayRanking()

    try:
        slay_peaks_database.connection.executescript(slay_peaks_schema)
        slay_replay_database.connection.executescript(slay_replay_schema)
        users_database.connection.executescript(users_schema)
        slay_ranking_database.connection.executescript(slay_ranking_schema)
    except Exception as e:
        raise e
    finally:
        slay_peaks_database.connection.close()
        slay_replay_database.connection.close()
        users_database.connection.close()
        slay_ranking_database.connection.close()