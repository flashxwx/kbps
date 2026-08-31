import threading, os, time, math
from queue import Queue
from enum import Enum
from typing_extensions import deprecated

from sortedcontainers import SortedDict, SortedValuesView

from slay import Request, Info, Connection, Socket

import database
from database import slay_ranking

from slayone.stats import GameRoomInfo
from slayone.ranking_info import RankingInfoDict

match_ranking_for_settlement_queue: Queue[tuple[SortedDict | dict[int, GameRoomInfo.PlayerInfo], RankingInfoDict, str]] = Queue()
""" (all_real_players_info, all_real_ranking_info, server_name) """

__dm_player_update_buffer: dict[int, slay_ranking.DMPlayer] = None
__clan_update_buffer: dict[str, slay_ranking.Clan] = None

ELO_K_VALUE_FOR_NORMAL = 16
ELO_K_VALUE_FOR_NEWBIE = 32
ELO_SCORE_DECIMAL_PRECISION = 2
LOWEST_ELO_SCORE = 900

class VersusResult(Enum):
    LOSE = 0.0
    TIE = 0.5
    WIN = 1.0

if os.environ.get("TEST_MODE"):
    slayone_scan_fastest_connection = Connection(Socket.ASIA, "rank")

def process_match_ranking_settlement():
    global slayone_scan_fastest_connection

    from slayone.scan import connections as slayone_scan_connections

    if os.environ.get("TEST_MODE"):
        slayone_scan_fastest_connection.open(new_thread=True)
    else:
        slayone_scan_fastest_connection = slayone_scan_connections.list[2]

    global __dm_player_update_buffer, __clan_update_buffer

    slay_ranking_database = database.SlayRanking()

    while True:
        __dm_player_update_buffer = dict()
        __clan_update_buffer = dict()

        result = match_ranking_for_settlement_queue.get()

        if result == None:
            slay_ranking_database.connection.close()
            if os.environ.get("TEST_MODE"):
                slayone_scan_fastest_connection.close()
            return

        all_real_players_info, all_real_ranking_info, server_name = result

        # if target_in_game_id > 0:
        #     target_info = players_info[target_in_game_id]
        #     if target_info.duration_info.settle() < 300 or target_info.id < 1 or len(players_info) == 1:
        #         continue

        #     settle_match_ranking_for_one_target(slay_ranking_database, target_info, players_info.values(), ranking_info, server_name)

        # elif target_in_game_id == 0:
        real_players_info_values = all_real_players_info.values()
        players_info_pointer = 1
        # players_info_pointer_end = len(all_real_players_info) - 1
        for target_info in all_real_players_info.values():
            # if players_info_pointer > players_info_pointer_end: # bot kills gotta be settled even there's only one real player # passed enemylist should be empty
            #     break

            settle_match_ranking_for_one_target(
                slay_ranking_database, target_info, real_players_info_values[players_info_pointer:], all_real_ranking_info, server_name
            )

            players_info_pointer += 1

        for player_id, dm_player in __dm_player_update_buffer.items():
            if len(__dm_player_update_buffer) == 1:
                dm_player.id = next(iter(__dm_player_update_buffer.keys()))
                slay_ranking_database.save_dm_player_with_no_rank(server_name, dm_player)
                break

            if dm_player.clan_tag:
                settle_match_ranking_for_a_clan(
                    slayone_scan_fastest_connection, slay_ranking_database, server_name, dm_player.clan_tag,
                    calculate_score_change_for_clan(dm_player.elo, dm_player.elo_after, dm_player.match_played_count), f"{dm_player.nickname}(ID:{player_id})"
                )

            dm_player.match_played_count += 1

            target_elo_change = round(dm_player.elo_after - dm_player.elo, 2)
            change_sign = "-" if target_elo_change < 0 else "+"
            dm_player.add_to_log_buffer(
                f"\n{change_sign} ELO Summary: {dm_player.elo} {change_sign} {abs(target_elo_change)} = {dm_player.elo_after}```"
            )
            dm_player.flush_log_buffer()

            dm_player.elo = dm_player.elo_after

            if dm_player.id > 0:
                slay_ranking_database.save_dm_player(server_name, dm_player)
            else:
                dm_player.id = player_id
                slay_ranking_database.save_dm_player(server_name, dm_player)

        if len(__clan_update_buffer) == 0:
            # if os.environ.get("TEST_MODE"):
            #     slay_ranking_database.connection.close()
            #     slayone_scan_fastest_connection.close()
            #     return
            continue
        else:
            for clan in __clan_update_buffer.values():
                clan_elo_change = round(clan.elo_after - clan.elo, 2)
                change_sign = "-" if clan_elo_change < 0 else "+"
                clan.add_to_log_buffer(f"\n{change_sign} ELO Summary: {clan.elo} {change_sign} {abs(clan_elo_change)} = {clan.elo_after}```")
                clan.flush_log_buffer()

                clan.elo = clan.elo_after

                if clan.got_from_database:
                    slay_ranking_database.save_clan(server_name, clan)
                else:
                    slay_ranking_database.save_clan(server_name, clan)

        # if os.environ.get("TEST_MODE"):
        #     slay_ranking_database.connection.close()
        #     slayone_scan_fastest_connection.close()
        #     return

def settle_match_ranking_for_one_target(
    slay_ranking_database: database.SlayRanking,
    target_info: GameRoomInfo.PlayerInfo,
    enemy_players_info_values: SortedValuesView | list[GameRoomInfo.PlayerInfo],
    all_real_ranking_info: RankingInfoDict,
    server_name: str,
):
    now = int(time.time())
    target_player_id = target_info.id

    cached_dm_player = __dm_player_update_buffer.get(target_player_id)
    if cached_dm_player:
        target_dm_player = cached_dm_player
    else:
        target_dm_player = slay_ranking_database.fetch_dm_player(server_name, target_player_id, do_season_check=True)
        if target_dm_player == None:
            target_dm_player = slay_ranking.DMPlayer( # why set id as 0 here? meaning it needs to be insert later, instead of update in database # it doesnt matter now
                0, slay_ranking_database.current_season_id, target_info.nickname, target_info.clan_tag,
                target_info.kills, target_info.bot_kills
            )
            __dm_player_update_buffer[target_player_id] = target_dm_player
        else:
            target_dm_player.nickname = target_info.nickname
            target_dm_player.clan_tag = target_info.clan_tag
            target_dm_player.kills += target_info.kills
            target_dm_player.bot_kills += target_info.bot_kills
            target_dm_player.elo_after = target_dm_player.elo
            __dm_player_update_buffer[target_player_id] = target_dm_player

        target_dm_player.add_to_log_buffer(
            f"<t:{now}:F> in **{server_name}**```diff\n"
            +f"Player: {target_dm_player.nickname}(ID: {target_info.id} | "
            +(f"Clan: {target_info.clan_tag} | " if target_info.clan_tag else "")
            +f"ELO: {target_dm_player.elo} | Kills: {target_info.kills} | Bot Kills: {target_info.bot_kills} | MP: {target_dm_player.match_played_count})\n"
        )

    if len(enemy_players_info_values) == 0:
        return

    target_score = target_info.kills
    target_rank = all_real_ranking_info.get_rank_by_score(target_score)

    for enemy_player_info in enemy_players_info_values:
        enemy_player_id = enemy_player_info.id

        if enemy_player_id == target_player_id:
            continue

        cached_dm_player = __dm_player_update_buffer.get(enemy_player_id)
        if cached_dm_player:
            enemy_dm_player = cached_dm_player
        else:
            enemy_dm_player = slay_ranking_database.fetch_dm_player(server_name, enemy_player_id, do_season_check=True)
            if enemy_dm_player == None:
                enemy_dm_player = slay_ranking.DMPlayer( # why set id as 0 here? meaning it needs to be insert later, instead of update in database
                    0, slay_ranking_database.current_season_id, enemy_player_info.nickname, enemy_player_info.clan_tag,
                    enemy_player_info.kills, enemy_player_info.bot_kills
                )
                __dm_player_update_buffer[enemy_player_id] = enemy_dm_player
            else:
                enemy_dm_player.nickname = enemy_player_info.nickname
                enemy_dm_player.clan_tag = enemy_player_info.clan_tag
                enemy_dm_player.kills += enemy_player_info.kills
                enemy_dm_player.bot_kills += enemy_player_info.bot_kills
                enemy_dm_player.elo_after = enemy_dm_player.elo
                __dm_player_update_buffer[enemy_player_id] = enemy_dm_player

            enemy_dm_player.add_to_log_buffer(
                f"<t:{now}:F> in **{server_name}**```diff\n"
                +f"Player: {enemy_dm_player.nickname}(ID: {enemy_player_info.id} | "
                +(f"Clan: {enemy_player_info.clan_tag} | " if enemy_player_info.clan_tag else "")
                +f"ELO: {enemy_dm_player.elo} | Kills: {enemy_player_info.kills} | MP: {enemy_dm_player.match_played_count})\n"
            )

        enemy_rank = all_real_ranking_info.get_rank_by_score(enemy_player_info.kills)

        versus_result = VersusResult.WIN if target_rank < enemy_rank else VersusResult.LOSE if target_rank > enemy_rank else VersusResult.TIE

        min_gaming_duration = min(target_info.duration_info.settle(), enemy_player_info.duration_info.settle())
        min_gaming_duration_m, min_gaming_duration_s = divmod(int(min_gaming_duration), 60)

        target_dm_player.elo_after, enemy_dm_player.elo_after, target_elo_change, enemy_elo_change = calculate_elo_score(
            target_dm_player.elo_after, enemy_dm_player.elo_after, versus_result,
            target_dm_player.match_played_count, enemy_dm_player.match_played_count,
            get_impact_based_on_rankings(target_rank, enemy_rank) * (min_gaming_duration / 600)
        )

        change_sign = "-" if target_elo_change < 0 else "+"
        target_dm_player.add_to_log_buffer(
            f"{change_sign} "
            f"{"WON against" if versus_result == VersusResult.WIN else "LOST to" if versus_result == VersusResult.LOSE else "TIED with"} "
            f"{enemy_dm_player.nickname}(ID: {enemy_player_id} | ELO: {enemy_dm_player.elo} | Kills: {enemy_player_info.kills} | MP: {enemy_dm_player.match_played_count}) : {target_elo_change} "
            f"(Duration: {min_gaming_duration_m}m,{min_gaming_duration_s}s)"
        )

        change_sign = "-" if enemy_elo_change < 0 else "+"
        enemy_dm_player.add_to_log_buffer(
            f"{change_sign} "
            f"{"LOST to" if versus_result == VersusResult.WIN else "WON against" if versus_result == VersusResult.LOSE else "TIED with"} "
            f"{target_dm_player.nickname}(ID: {target_player_id} | ELO: {target_dm_player.elo} | Kills: {target_info.kills} | MP: {target_dm_player.match_played_count}] : {enemy_elo_change} "
            f"(Duration: {min_gaming_duration_m}m,{min_gaming_duration_s}s)"
        )

def settle_match_ranking_for_a_clan(
    slayone_scan_fastest_connection: Connection, slay_ranking_database: database.SlayRanking, server_name: str,
    tag: str, change: float, p_str: str
):
    now = int(time.time())

    if change == 0:
        return

    cached_clan =__clan_update_buffer.get(tag)
    if cached_clan:
        clan = cached_clan
    else:
        try:
            clan_info: Info.Clan = slayone_scan_fastest_connection.request_from_outside(Request.ClanInfo(tag), "on_clan_info")
        except Exception as e:
            print(e)
            slayone_scan_fastest_connection.log("ERROR", f"Coundn't get the info of [{tag}] clan.")
            return

        try:
            clan_member_list: list[Info.ClanMember] = slayone_scan_fastest_connection.request_from_outside(Request.ClanMemberList(tag), "on_clan_member_list")
        except Exception as e:
            print(e)
            slayone_scan_fastest_connection.log("ERROR", f"Couldn't get the member list of [{tag}] clan.")
            return

        clan = slay_ranking_database.fetch_clan(server_name, tag)
        if clan:
            clan.member_count = len(clan_member_list)
            clan.elo_after = clan.elo
            clan.name = clan_info.name
            __clan_update_buffer[tag] = clan
        else:
            clan = slay_ranking.Clan(tag, slay_ranking_database.current_season_id, clan_info.name, member_count=len(clan_member_list))
            __clan_update_buffer[tag] = clan

        clan.add_to_log_buffer(
            f"<t:{now}:F> in **{server_name}**```diff\n"
            f"[{clan.tag}] {clan.name} [ELO:{clan.elo}][ELO_ADDEND:{clan.elo_addend}][ELO_SUBTRAHEND:{clan.elo_subtrahend}]\n"
        )
    
    if change > 0:
        clan.elo_addend += change
        clan.elo_addend = round(clan.elo_addend, ELO_SCORE_DECIMAL_PRECISION)
        clan.add_to_log_buffer(f"+ {p_str} contributed {change} elo score to clan")
    else:
        change = abs(change)
        clan.elo_subtrahend += change
        clan.elo_subtrahend = round(clan.elo_subtrahend, ELO_SCORE_DECIMAL_PRECISION)
        clan.add_to_log_buffer(f"- {p_str} lost {change} elo score from clan")

    clan.elo_after = round(1000 + math.sqrt(clan.elo_addend) - math.sqrt(clan.elo_subtrahend / (1 + math.log10(clan.member_count))), ELO_SCORE_DECIMAL_PRECISION)

def calculate_elo_score(
    a_score: float, b_score: float, versus_result: VersusResult,
    a_match_played_count: int = 11, b_match_played_count: int = 11,
    effect_of_change: float = 1
):
    a_score = round(a_score, ELO_SCORE_DECIMAL_PRECISION)
    b_score = round(b_score, ELO_SCORE_DECIMAL_PRECISION)

    a_k_value = max(ELO_K_VALUE_FOR_NORMAL, ELO_K_VALUE_FOR_NEWBIE / (1 + (a_match_played_count / 10)))
    b_k_value = max(ELO_K_VALUE_FOR_NORMAL, ELO_K_VALUE_FOR_NEWBIE / (1 + (b_match_played_count / 10)))

    a_expectation = 1 / (1 + (10 ** ((b_score - a_score) / 400)))
    b_expectation = 1 / (1 + (10 ** ((a_score - b_score) / 400)))

    a_change = a_k_value * (versus_result.value - a_expectation) * effect_of_change
    b_change = b_k_value * (1 - versus_result.value - b_expectation) * effect_of_change

    new_a_score = a_score + a_change
    new_b_score = b_score + b_change

    if new_a_score < LOWEST_ELO_SCORE:
        new_a_score = LOWEST_ELO_SCORE

    if new_b_score < LOWEST_ELO_SCORE:
        new_b_score = LOWEST_ELO_SCORE

    return (
        round(new_a_score, ELO_SCORE_DECIMAL_PRECISION),
        round(new_b_score, ELO_SCORE_DECIMAL_PRECISION),
        round(a_change, ELO_SCORE_DECIMAL_PRECISION),
        round(b_change, ELO_SCORE_DECIMAL_PRECISION)
    )

def calculate_score_change_for_clan(player_score_before: float, player_score_after: float, match_played_count: int):
    if match_played_count < 10:
        return 0

    rank_weight = ((player_score_before - 1000) // 100) + 1

    return round(rank_weight * (player_score_after - player_score_before), ELO_SCORE_DECIMAL_PRECISION)

def get_info_of_ranking_weights(player_count: int):
    weights = []
    sum_of_weights = 0

    for n in range(player_count, 0, -1):
        weights.append(n)
        sum_of_weights += n

    return weights, sum_of_weights

def get_impact_based_on_rankings(a_rank: int, b_rank: int):
    return 1 / (abs(a_rank - b_rank) + 1)

def start_processing_match_ranking_settlement():
    thread = threading.Thread(target=process_match_ranking_settlement)
    thread.start()

    return thread

def stop_processing_match_ranking_settlement():
    match_ranking_for_settlement_queue.put(None)

def _test():
    from sortedcontainers import SortedDict

    global __dm_player_update_buffer, __clan_update_buffer

    pt = start_processing_match_ranking_settlement()

    __clan_update_buffer = dict()

    players_info, ranking_info = (
        SortedDict({
            10: GameRoomInfo.PlayerInfo(10, "a", "BNQ", GameRoomInfo.DurationInfo(None, 600), 0, 2),
            11: GameRoomInfo.PlayerInfo(11, "b", "", GameRoomInfo.DurationInfo(None, 600), 0, 3),
            12: GameRoomInfo.PlayerInfo(12, "c", "GODLY", GameRoomInfo.DurationInfo(None, 600), 5, 0)
        }),
        RankingInfoDict(lambda key: -key, {5: {10}, 1: {11}, 0: {12}})
    )

    try:
        match_ranking_for_settlement_queue.put((players_info, ranking_info, "ASIA"))
        pt.join()
    except Exception as e:
        print(e)
    finally:
        slayone_scan_fastest_connection.close()
        stop_processing_match_ranking_settlement()