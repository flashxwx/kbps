import math, os
from itertools import islice

from dc import ui

from slayone.stats import real_player_count_of_each_server, game_rooms_info_of_each_server, solo_ranked_search_count_of_each_server
from slayone.scan import last_scan_activity_time_of_each_server


maximum_match_display_of_each_server = 1

mode_emojis_in_dc = [None, "⚔️", "🎏", None, "💀️", "🦠"]

async def build_slay_current_activity_ui(current_page: int = 1):
    total_pages = 0

    container = ui.Container()

    container.add_item(
        ui.TextDisplay(
            f"## EU SERVER ({real_player_count_of_each_server[0]} players)\n"
            f"> {solo_ranked_search_count_of_each_server[0]} player(s) searching for 1v1 ranked match."
        )
    )

    new_total_pages = __render_match_display(container, current_page, 0)
    if new_total_pages > total_pages:
        total_pages = new_total_pages

    container.add_item(ui.TextDisplay(f"-# Last scan eu lobby was at <t:{int(last_scan_activity_time_of_each_server[0])}:f> · Scan every 60 seconds"))
    container.add_item(ui.Separator())

    container.add_item(
        ui.TextDisplay(
            f"## AM SERVER ({real_player_count_of_each_server[1]} players)\n"
            f"> {solo_ranked_search_count_of_each_server[1]} player(s) searching for 1v1 ranked match."
        )
    )

    new_total_pages = __render_match_display(container, current_page, 1)
    if new_total_pages > total_pages:
        total_pages = new_total_pages

    container.add_item(ui.TextDisplay(f"-# Last scan am lobby was at <t:{int(last_scan_activity_time_of_each_server[1])}:f> · Scan every 60 seconds"))
    container.add_item(ui.Separator())

    container.add_item(
        ui.TextDisplay(
            f"## ASIA SERVER ({real_player_count_of_each_server[2]} players)\n"
            f"> {solo_ranked_search_count_of_each_server[2]} player(s) searching for 1v1 ranked match."
        )
    )

    new_total_pages = __render_match_display(container, current_page, 2)
    if new_total_pages > total_pages:
        total_pages = new_total_pages

    container.add_item(ui.TextDisplay(f"-# Last scan asia lobby was at <t:{int(last_scan_activity_time_of_each_server[2])}:f> · Scan every 60 seconds"))

    container.add_item(ui.Separator(visible=False))
    container.add_item(ui.TextDisplay("-# Only count real players, doesn't count bots in. All matches showing here are being watched in real time."))

    if os.environ.get("TEST_MODE") == "true":
        r = ui.MyLayoutView().add_item(container).add_item(
            ui.make_page_panel_container(ui.PagePanelInfo(build_slay_current_activity_ui, total_pages=total_pages, current_page=current_page))
        )

        # print(r.total_children_count)
        return r

    return ui.MyLayoutView().add_item(container).add_item(
        ui.make_page_panel_container(ui.PagePanelInfo(build_slay_current_activity_ui, total_pages=total_pages, current_page=current_page))
    )

def __render_match_display(container: ui.Container, current_page: int, server_index: int) -> int:
    game_rooms_info = game_rooms_info_of_each_server[server_index]

    end_at = maximum_match_display_of_each_server * current_page

    for game_room_id, game_room_info in game_rooms_info.items()[end_at-maximum_match_display_of_each_server:end_at]:
        container.add_item(
            ui.TextDisplay(
                f"### {mode_emojis_in_dc[game_room_info.mode.id]} {game_room_info.mode.text}, {game_room_info.map_name.title()} ({len(game_room_info.current_players_info)} of {game_room_info.max_players} players)"
            )
        )

        container.add_item(
            ui.Section(
                "**Players:** " + ", ".join(f"{player_info.nickname}(K:{player_info.kills})" for player_info in game_room_info.current_top_players(10)),
                accessory=ui.Button(label="Join", url=f"https://slay.one/?server={server_index}&game={game_room_id}")
            )
        )

    return math.ceil(len(game_rooms_info) / maximum_match_display_of_each_server)