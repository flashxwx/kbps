import traceback, time, io
from typing import Optional, Literal

import discord
from discord import Interaction, Guild, User, app_commands
from discord.app_commands import CommandTree, AppCommandError, Choice, Range, choices

from dc import ui, bot, bot_logger, slay_radio
from dc.error import handle_interaction_error

command_tree = CommandTree(bot)
command_request_count_for_each_place: dict[Guild | User, int] = dict()

def stats_for_new_command_request(interaction: Interaction):
    place = interaction.guild
    if not place:
        place = interaction.user

    command_request_count_for_each_place[place] = command_request_count_for_each_place.get(place, 0) + 1

def get_stats_for_command_request():
    days_since_start_running = max((time.time() - bot.start_running_time) / 86400, 1)
    stats_message = f"days since start running: {days_since_start_running}\n"

    for place, count in command_request_count_for_each_place.items():
        if isinstance(place, Guild):
            stats_message += f"Server {place.name} ({place.id}) - avg:{count/days_since_start_running} total:{count}\n"
        else:
            stats_message += f"User {place.name} ({place.id}) - avg:{count/days_since_start_running} total: {count}\n"

    return stats_message

@command_tree.error
async def on_error(interaction: Interaction, error: AppCommandError):
    await handle_interaction_error(interaction, error)

@command_tree.command(name="clanrank")
# @app_commands.guilds(1120432082846486638, 1443569912017715214)
@choices(
    server=[
        Choice(name="eu", value="EU"),
        Choice(name="am", value="AM"),
        Choice(name="asia", value="ASIA")
    ]
)
async def show_clan_rank(
    interaction: Interaction,
    clan_tag: str = None,
    search_clan_tag: str = None,
    server: str = "EU",
    season: str = None,
    ephemeral: bool = True
):
    await interaction.response.defer(thinking=True, ephemeral=ephemeral)

    await interaction.edit_original_response(
        view=await ui.build_slay_clan_rank_ui(ui.SlayClanRankUIInfo(
            interaction.user.id,
            clan_tag,
            search_clan_tag,
            server,
            season,
            page_index=2 if clan_tag else 1 if search_clan_tag else 0
        ))
    )

    stats_for_new_command_request(interaction)

@command_tree.command(name="playerrank")
# @app_commands.guilds(1120432082846486638, 1443569912017715214)
@choices(
    server=[
        Choice(name="eu", value="EU"),
        Choice(name="am", value="AM"),
        Choice(name="asia", value="ASIA")
    ]
)
async def show_player_rank(
    interaction: Interaction,
    player_id: int = None,
    nickname: str = None,
    server: str = "EU",
    season: str = None,
    ephemeral: bool = True
):
    await interaction.response.defer(thinking=True, ephemeral=ephemeral)

    await interaction.edit_original_response(
        view=await ui.build_slay_player_rank_ui(
            ui.SlayPlayerRankUIInfo(
                interaction.user.id,
                player_id,
                nickname,
                server,
                season,
                page_index=2 if player_id else 1 if nickname else 0
            )
        )
    )

    stats_for_new_command_request(interaction)

@command_tree.command(name="ranking")
# @app_commands.guilds(1120432082846486638, 1443569912017715214)
@choices(
    server=[
        Choice(name="eu", value="EU"),
        Choice(name="am", value="AM"),
        Choice(name="asia", value="ASIA")
    ],
    type=[
        Choice(name="dm_player_elo", value=1),
        Choice(name="dm_clan_elo", value=2),
        Choice(name="dm_kills", value=3),
        Choice(name="dm_bot_kills", value=4),
    ]
)
async def show_ranking(
    interaction: Interaction,
    server: str = "EU",
    type: int = 1,
    season_id: str = None,
    ephemeral: bool = True
):
    await interaction.response.defer(thinking=True, ephemeral=ephemeral)
    await interaction.edit_original_response(
        view=await ui.build_slay_ranking_ui(
            ui.SlayRankingUIInfo(server, type, season_id)
        )
    )

    stats_for_new_command_request(interaction)

@command_tree.command(name="help")
async def show_help_documentation(interaction: Interaction, location: str = "1", ephemeral: bool = True):
    await interaction.response.defer(thinking=True, ephemeral=ephemeral)
    await interaction.edit_original_response(view=await ui.build_help_ui(location))

    stats_for_new_command_request(interaction)

@command_tree.command(name="current")
async def show_slay_current_activity(
    interaction: Interaction, ephemeral: bool = True
):
    await interaction.response.defer(thinking=True, ephemeral=ephemeral)
    await interaction.edit_original_response(view=await ui.build_slay_current_activity_ui())

    stats_for_new_command_request(interaction)

@command_tree.command(name="peak")
@choices(
    timezone=[
        Choice(name="-11 (American Samoa)", value=-11.0),
        Choice(name="-10 (Hawaii)", value=-10.0),
        Choice(name="-9 (Alaska)", value=-9.0),
        Choice(name="-8 (PST - Los Angeles/Vancouver)", value=-8.0),
        Choice(name="-7 (MST - Denver/Phoenix)", value=-7.0),
        Choice(name="-6 (CST - Chicago/Mexico City)", value=-6.0),
        Choice(name="-5 (EST - New York/Toronto)", value=-5.0),
        Choice(name="-4 (AST - Santiago/Halifax)", value=-4.0),
        Choice(name="-3 (Brazil - Sao Paulo/Buenos Aires)", value=-3.0),
        Choice(name="-2 (Mid-Atlantic)", value=-2.0),
        Choice(name="-1 (Azores/Cape Verde)", value=-1.0),
        Choice(name="+0 (UTC/GMT - London/Lisbon)", value=0.0),
        Choice(name="+1 (CET - Paris/Berlin/Rome)", value=1.0),
        Choice(name="+2 (EET - Cairo/Kyiv/Johannesburg)", value=2.0),
        Choice(name="+3 (MSK - Moscow/Istanbul/Nairobi)", value=3.0),
        Choice(name="+3.5 (Tehran)", value=3.5),
        Choice(name="+4 (Dubai/Baku)", value=4.0),
        Choice(name="+5.5 (IST - Mumbai/New Delhi)", value=5.5),
        Choice(name="+7 (Bangkok/Jakarta/Hanoi)", value=7.0),
        Choice(name="+8 (CST - Beijing/Hong Kong/Singapore)", value=8.0),
        Choice(name="+9 (JST - Tokyo/Seoul)", value=9.0),
        Choice(name="+9.5 (Adelaide/Darwin)", value=9.5),
        Choice(name="+10 (AEST - Sydney/Melbourne/Guam)", value=10.0),
        Choice(name="+11 (Solomon Islands/Magadan)", value=11.0),
        Choice(name="+12 (Auckland/Fiji)", value=12.0),
    ],

    time_unit=[
        Choice(name="year", value=0),
        Choice(name="month", value=1),
        Choice(name="week", value=604800),
        Choice(name="day", value=86400),
        Choice(name="hour (default)", value=3600)
    ],

    server=[
        Choice(name="eu_&_am_&_asia", value="EU AM ASIA"),
        Choice(name="eu", value="EU"),
        Choice(name="am", value="AM"),
        Choice(name="asia", value="ASIA"),
        Choice(name="eu_&_am", value="EU AM"),
        Choice(name="am_&_asia", value="AM ASIA"),
        Choice(name="eu_&_asia", value="EU ASIA")
    ],
)
async def show_peak_chart(
    interaction: Interaction, timezone: Optional[Choice[float]] = None, time_unit: Optional[Choice[int]] = None,
    server: Optional[str] = None,
    past_years: Range[int, 0, 4] = None,
    past_months: Range[int, 0, 12] = None,
    past_weeks: Range[int, 0, 5] = None,
    past_days: Range[int, 0, 7] = None,
    past_hours: Range[int, 0, 24] = None,
    no_dots: bool = False, ephemeral: bool = True
):
    await interaction.response.defer(thinking=True, ephemeral=ephemeral)

    layout_view, chart_image_file = await ui.build_slay_peak_chart_ui(ui.SlayPeakChartInfo(
        server.value.split() if server else ["EU", "AM", "ASIA"],
        time_unit.value if time_unit else 3600,
        timezone.value if timezone else 0,
        past_years,
        past_months,
        past_weeks,
        past_days,
        past_hours,
        no_dots,
    ))

    await interaction.edit_original_response(view=layout_view, attachments=[chart_image_file])

    stats_for_new_command_request(interaction)

@command_tree.command(name="radio")
async def interact_with_slay_radio(
    interaction: ui.Interaction, voice: bool = False, dms: bool = None, ephemeral: bool = True
):
    await interaction.response.defer(thinking=True, ephemeral=ephemeral)

    await slay_radio.process_interaction(interaction, slay_radio.RadioInteractionInfo(dms, 1 if voice else 0))

    stats_for_new_command_request(interaction)


@command_tree.command(name="replay")
@choices(
    server=[
        Choice(name="all", value="SERVER_INDEX IN (0, 1, 2)"),
        Choice(name="eu", value="SERVER_INDEX = 0"),
        Choice(name="am", value="SERVER_INDEX = 1"),
        Choice(name="asia", value="SERVER_INDEX = 2"),
        Choice(name="eu_&_am", value="SERVER_INDEX IN (0, 1)"),
        Choice(name="am_&_asia", value="SERVER_INDEX IN (1, 2)"),
        Choice(name="eu_&_asia", value="SERVER_INDEX IN (0, 2)")
    ],

    mode=[
        Choice(name="all", value="MODE_INDEX IN (1, 2, 4, 5)"),
        Choice(name="team_deathmatch", value="MODE_INDEX = 1"),
        Choice(name="capture_the_flag", value="MODE_INDEX = 2"),
        Choice(name="deathmatch", value="MODE_INDEX = 4"),
        Choice(name="infection", value="MODE_INDEX = 5"),
        Choice(name="tdm_&_ctf", value="MODE_INDEX IN (1, 2)"),
        Choice(name="tdm_&_dm", value="MODE_INDEX IN (1, 4)"),
        Choice(name="tdm_&_inf", value="MODE_INDEX IN (1, 5)"),
        Choice(name="ctf_&_dm", value="MODE_INDEX IN (2, 4)"),
        Choice(name="ctf_&_inf", value="MODE_INDEX IN (2, 5)"),
        Choice(name="dm_&_inf", value="MODE_INDEX IN (4, 5)"),
        Choice(name="tdm_&_ctf_&_dm", value="MODE_INDEX IN (1, 2, 4)"),
        Choice(name="tdm_&_ctf_&_inf", value="MODE_INDEX IN (1, 2, 5)"),
        Choice(name="tdm_&_dm_&_inf", value="MODE_INDEX IN (1, 4, 5)"),
        Choice(name="ctf_&_dm_&_inf", value="MODE_INDEX IN (2, 4, 5)")
    ]
)
async def show_replays(
    interaction: ui.Interaction,
    server: Optional[str] = None,
    mode: Optional[str] = None,
    replay_id: str = None,
    ephemeral: bool = True
):
    await interaction.response.defer(thinking=True, ephemeral=ephemeral)

    slay_replay_ui_info = ui.SlayReplayUIInfo()
    if server: slay_replay_ui_info.db_server_query = server
    if mode: slay_replay_ui_info.db_mode_query = mode
    if replay_id: slay_replay_ui_info.replay_id = replay_id

    await interaction.edit_original_response(view=await ui.build_slay_replay_ui(slay_replay_ui_info))

    stats_for_new_command_request(interaction)