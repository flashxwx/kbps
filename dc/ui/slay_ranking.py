from dataclasses import dataclass
from typing import Callable

import database
from database import slay_ranking
from dc import ui

slay_ranking_database = database.SlayRanking()
user_database = database.Users()

@dataclass(slots=True)
class SlayRankingUIInfo():
    server_name: str = "EU"
    type_id: int = 1
    season_id: str | None = None
    x_current_page: int = 1

@dataclass(slots=True)
class SlayPlayerRankUIInfo():
    dc_user_id: int
    player_id: int = None
    searched_nickname: str = None
    server_name: str = "EU"
    season_id: str = None
    ranking_ui_info: SlayRankingUIInfo = None
    page_index: int = 0
    """ 0: favorite players, 1: search, 2: details, 3: logs"""

@dataclass(slots=True)
class SlayClanRankUIInfo():
    dc_user_id: int
    clan_tag: str = None
    searched_clan_tag: str = None
    server_name: str = "EU"
    season_id: str = None
    last_ui_info: tuple[int, SlayRankingUIInfo | SlayPlayerRankUIInfo] = None
    """ 0: ranking ui info, 1: player_rank_ui_info"""
    page_index: int = 0
    """ 0: favorite players, 1: search, 2: details, 3: logs"""

class BackToRankingButton(ui.Button):
    def __init__(self, info: SlayRankingUIInfo):
        self.info = info

        super().__init__(label="Back to Ranking")

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()
        await interaction.edit_original_response(view=await build_slay_ranking_ui(self.info, self.info.x_current_page))

class BackToPlayerDetailsButton(ui.Button):
    def __init__(self, info: SlayPlayerRankUIInfo):
        self.info = info

        super().__init__(label="Back to Player Details")

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()
        await interaction.edit_original_response(view=await build_slay_player_rank_ui(self.info))

class FavoriteClanButton(ui.Button):
    def __init__(self, info: SlayClanRankUIInfo):
        self.info = info
        self.is_favorite_clan = user_database.is_favorite_clan(self.info.dc_user_id, self.info.clan_tag)

        super().__init__(label="Remove from Favorites" if self.is_favorite_clan else "Save as Favorite")

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        if self.is_favorite_clan:
            user_database.delete_favorite_clan(self.info.dc_user_id, self.info.clan_tag)
        else:
            if user_database.favorite_clans_count(self.info.dc_user_id) > 9:
                return await interaction.followup.send("Sorry, you can't save more than 10 favorite clans.")

            user_database.insert_favorite_clan(self.info.dc_user_id, self.info.clan_tag)

        await interaction.edit_original_response(view=await build_slay_clan_rank_ui(self.info))

class FavoritePlayerButton(ui.Button):
    def __init__(self, info: SlayPlayerRankUIInfo, nickname: str):
        self.info = info
        self.nickname = nickname
        self.is_favorite_player = user_database.is_favorite_player(self.info.dc_user_id, self.info.player_id)

        super().__init__(label="Remove from Favorites" if self.is_favorite_player else "Save as Favorite")

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        if self.is_favorite_player:
            user_database.delete_favorite_player(self.info.dc_user_id, self.info.player_id)
        else:
            if user_database.favorite_players_count(self.info.dc_user_id) > 9:
                return await interaction.followup.send("Sorry, you can't save more than 10 favorite players.")

            user_database.insert_favorite_player(self.info.dc_user_id, self.info.player_id, self.nickname)

        await interaction.edit_original_response(view=await build_slay_player_rank_ui(self.info))

class ClanSearchButton(ui.Button):
    def __init__(self, info: SlayClanRankUIInfo):
        self.info = info

        super().__init__(label="Search Ranked Clan")

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.send_modal(ClanSearchModal(self.info))

class ClanDetailsButton(ui.Button):
    def __init__(self, info: SlayClanRankUIInfo | SlayRankingUIInfo | SlayPlayerRankUIInfo, clan_tag: str, from_index: int = 0):
        self.info = info
        self.clan_tag = clan_tag
        self.from_index = from_index

        super().__init__(label="Clan Details" if from_index == 2 else "Details")

    async def callback(self, interaction):
        await interaction.response.defer()

        if self.from_index:
            self.info = SlayClanRankUIInfo(
                interaction.user.id,
                self.clan_tag,
                server_name=self.info.server_name,
                season_id=self.info.season_id,
                last_ui_info=(self.from_index, self.info),
                page_index=2
            )
        else:
            self.info.clan_tag = self.clan_tag
            self.info.page_index = 2

        await interaction.edit_original_response(view=await build_slay_clan_rank_ui(self.info))

class DMPlayerSearchButton(ui.Button):
    def __init__(self, info: SlayPlayerRankUIInfo):
        self.info = info

        super().__init__(label="Search Ranked Player")

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.send_modal(DMPlayerSearchModal(self.info))

class DMPlayerDetailsButton(ui.Button):
    def __init__(self, info: SlayPlayerRankUIInfo, player_id: int, from_ranking_ui: bool = False):
        self.info = info
        self.player_id = player_id
        self.from_ranking_ui = from_ranking_ui

        super().__init__(label="Details")

    async def callback(self, interaction):
        await interaction.response.defer()

        if self.from_ranking_ui:
            self.info = SlayPlayerRankUIInfo(
                interaction.user.id,
                self.player_id,
                server_name=self.info.server_name,
                season_id=self.info.season_id,
                ranking_ui_info=self.info,
                page_index=2
            )
        else:
            self.info.player_id = self.player_id
            self.info.page_index = 2

        await interaction.edit_original_response(view=await build_slay_player_rank_ui(self.info))

class RecentLogButton(ui.Button):
    def __init__(self, info: SlayPlayerRankUIInfo, for_index: int):
        self.info = info
        self.for_index = for_index

        super().__init__(label="Recent Logs")

    async def callback(self, interaction):
        await interaction.response.defer()

        self.info.page_index = 3

        if self.for_index == 1:
            await interaction.edit_original_response(view=await build_slay_player_rank_ui(self.info))
        elif self.for_index == 2:
            await interaction.edit_original_response(view=await build_slay_clan_rank_ui(self.info))
class DMPlayerSearchModal(ui.MyModal):
    nickname_input = ui.TextInput(
        label="Input player Nickname that you want to search",
        placeholder="flash"
    )

    def __init__(self, info: SlayPlayerRankUIInfo):
        self.info = info

        super().__init__(title="Ranked Player Search")

    async def on_submit(self, interaction: ui.Interaction):
        await interaction.response.defer()

        self.info.searched_nickname = self.nickname_input.value
        self.info.page_index = 1
        
        await interaction.edit_original_response(view=await build_slay_player_rank_ui(self.info))

class ClanSearchModal(ui.MyModal):
    clan_tag_input = ui.TextInput(
        label="Input clan Tag that you want to search",
        placeholder="bnq"
    )

    def __init__(self, info: SlayClanRankUIInfo):
        self.info = info

        super().__init__(title="Ranked Clan Search")

    async def on_submit(self, interaction: ui.Interaction):
        await interaction.response.defer()

        self.info.searched_clan_tag = self.clan_tag_input.value
        self.info.page_index = 1
        
        await interaction.edit_original_response(view=await build_slay_clan_rank_ui(self.info))

class ServerSelect(ui.Select):
    def __init__(self, info: SlayRankingUIInfo, for_index: int):
        self.info = info
        self.for_index = for_index

        options = [
            ui.SelectOption(label="EU Server", value="EU"),
            ui.SelectOption(label="AM Server", value="AM"),
            ui.SelectOption(label="ASIA Server", value="ASIA")
        ]

        for option in options:
            if option.value == info.server_name:
                option.default = True

        super().__init__(options=options)

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        self.info.server_name = self.values[0]

        if self.for_index == 0:
            await interaction.edit_original_response(view=await ui.build_slay_ranking_ui(self.info))
        elif self.for_index == 1:
            await interaction.edit_original_response(view=await ui.build_slay_player_rank_ui(self.info))
        elif self.for_index == 2:
            await interaction.edit_original_response(view=await ui.build_slay_clan_rank_ui(self.info))

class TypeSelect(ui.Select):
    def __init__(self, info: SlayRankingUIInfo):
        self.info = info

        options = [
            ui.SelectOption(label="Deathmatch Player ELO", value="1"),
            ui.SelectOption(label="Deathmatch Clan ELO", value="2"),
            ui.SelectOption(label="Deathmatch Kills", value="3"),
            ui.SelectOption(label="Deathmatch Bot Kills", value="4")
        ]

        for option in options:
            if int(option.value) == info.type_id:
                option.default = True

        super().__init__(options=options)

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        self.info.type_id = int(self.values[0])
        await interaction.edit_original_response(view=await ui.build_slay_ranking_ui(self.info))

class SeasonSelect(ui.Select):
    def __init__(self, info: SlayRankingUIInfo, for_index: int):
        self.info = info
        self.for_index = for_index

        options = []
        for season_id in reversed(database.SlayRanking.existed_season_ids_in_history):
            options.append(
                ui.SelectOption(
                    label=season_id,
                    value=season_id,
                    default=True if season_id == info.season_id else False
                )
            )
        super().__init__(options=options)

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        self.info.season_id = self.values[0]
        if self.for_index == 0:
            await interaction.edit_original_response(view=await ui.build_slay_ranking_ui(self.info))
        elif self.for_index == 1:
            await interaction.edit_original_response(view=await ui.build_slay_player_rank_ui(self.info))
        elif self.for_index == 2:
            await interaction.edit_original_response(view=await ui.build_slay_clan_rank_ui(self.info))
class PageSelect(ui.Select):
    def __init__(self, info: SlayPlayerRankUIInfo | SlayClanRankUIInfo, for_index: int):
        self.info = info
        self.for_index = for_index

        if for_index == 1:
            options: list[ui.SelectOption] = [ui.SelectOption(label="Favorite Players", value="0")]

            if info.searched_nickname:
                options.append(ui.SelectOption(label="Ranked Player Search", value="1"))
            if info.player_id:
                options.append(ui.SelectOption(label="Player Details", value="2"))
                options.append(ui.SelectOption(label="Player Recent Logs", value="3"))
        elif for_index == 2:
            options: list[ui.SelectOption] = [ui.SelectOption(label="Favorite Clans", value="0")]

            if info.searched_clan_tag:
                options.append(ui.SelectOption(label="Ranked Clan Search", value="1"))
            if info.clan_tag:
                options.append(ui.SelectOption(label="Clan Details", value="2"))
                options.append(ui.SelectOption(label="Clan Recent Logs", value="3"))

        for option in options:
            if int(option.value) == info.page_index:
                option.default = True

        super().__init__(options=options)

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        self.info.page_index = int(self.values[0])

        if self.for_index == 1:
            await interaction.edit_original_response(view=await ui.build_slay_player_rank_ui(self.info))
        elif self.for_index == 2:
            await interaction.edit_original_response(view=await ui.build_slay_clan_rank_ui(self.info))

async def build_slay_ranking_ui(info: SlayRankingUIInfo, current_page: int = 1):
    info.x_current_page = current_page

    if info.season_id == None:
        info.season_id = database.SlayRanking.existed_season_ids_in_history[-1]

    container = ui.Container(
        ui.ActionRow(ServerSelect(info, 0)),
        ui.ActionRow(TypeSelect(info)),
        ui.ActionRow(SeasonSelect(info, 0))
    )

    if info.type_id == 2:
        clans, current_page, max_page = slay_ranking_database.fetch_clan_by_ranking_page(info.server_name, info.season_id, current_page)

        rank = (current_page * 10) - 9
        for clan in clans:
            container.add_item(ui.Section(
                f"{rank}. **{clan.name} [{clan.tag}]** |\\| **ELO**:{clan.elo}\n",
                accessory=ClanDetailsButton(info, clan.tag, 1)
            ))
            rank += 1

        if len(clans) == 0:
            container.add_item(ui.TextDisplay("No ranking found."))
    else:
        if info.type_id == 1:
            column_name = "ELO"
        elif info.type_id == 3:
            column_name = "KILLS"
        elif info.type_id == 4:
            column_name = "BOT_KILLS"

        dm_players, current_page, max_page = slay_ranking_database.fetch_dm_players_by_ranking_page(
            info.server_name, column_name, info.season_id, current_page
        )

        rank = (current_page * 5) - 4
        for dm_player in dm_players:
            container.add_item(ui.Section(
                f"{rank}. **{dm_player.nickname}** |\\| ID:{dm_player.id} |\\| "
                +(
                    f"**ELO**:{dm_player.elo}" if info.type_id == 1
                    else f"**Kills**:{dm_player.kills}" if info.type_id == 3
                    else f"**Bot Kills**:{dm_player.bot_kills}"
                )+(f" |\\| CLAN:{dm_player.clan_tag}" if dm_player.clan_tag else "")+"\n",
                accessory=DMPlayerDetailsButton(info, player_id=dm_player.id, from_ranking_ui=True)
            ))
            rank += 1

        if len(dm_players) == 0:
            container.add_item(ui.TextDisplay("No ranking found."))

    if info.type_id == 2:
        container.add_item(ui.TextDisplay("-# You can only view first 1000 clans here at most. Use /rankedclan command to see the rank of any specified clan."))
    else:
        container.add_item(ui.TextDisplay("-# You can only view first 1000 players here at most. Use /rankedplayer command to see the rank of any specified player."))

    layout_view = ui.MyLayoutView().add_item(container).add_item(
        ui.make_page_panel_container(ui.PagePanelInfo(build_slay_ranking_ui, info, max_page, current_page))
    )
    return layout_view

async def build_slay_player_rank_ui(info: SlayPlayerRankUIInfo):
    if info.season_id == None:
        info.season_id = database.SlayRanking.existed_season_ids_in_history[-1]

    container = ui.Container(
        ui.ActionRow(ServerSelect(info, 1)),
        ui.ActionRow(SeasonSelect(info, 1)),
        ui.ActionRow(PageSelect(info, 1))
    )

    top_buttons = ui.ActionRow(DMPlayerSearchButton(info))
    container.add_item(top_buttons)

    if info.ranking_ui_info:
        top_buttons.add_item(BackToRankingButton(info.ranking_ui_info))

    if info.page_index == 0:
        favorite_players = user_database.favorite_players(info.dc_user_id)

        container.add_item(ui.TextDisplay("### Favorite players you saved:"))
        if len(favorite_players) == 0:
            container.add_item(ui.TextDisplay("You haven't marked any player as favorite player. You can try to search."))
        else:
            for player_id, nickname in favorite_players:
                container.add_item(
                    ui.Section(
                        f"{nickname} ({player_id})",
                        accessory=DMPlayerDetailsButton(info, player_id)
                    )
                )

    elif info.page_index == 1:
        searched_dm_players = slay_ranking_database.search_dm_player(
            info.server_name,
            info.searched_nickname,
            info.season_id
        )

        container.add_item(ui.TextDisplay(f"### Search Results for \"{info.searched_nickname}\":"))

        if len(searched_dm_players) == 0:
            container.add_item(ui.TextDisplay(f"Couldn't find any nickname match your search."))
        else:
            for dm_player in searched_dm_players:
                container.add_item(
                    ui.Section(
                        f"{dm_player.nickname} {f"[{dm_player.clan_tag}] " if dm_player.clan_tag else ""}({dm_player.id})",
                        accessory=DMPlayerDetailsButton(info, dm_player.id)
                    )
                )

            container.add_item(ui.TextDisplay(f"-# Can only search up to 8 results, please make sure nickname input as accurate as possible."))

    elif info.page_index == 2:
        dm_player = slay_ranking_database.fetch_dm_player(info.server_name, info.player_id, info.season_id)
        if not dm_player:
            container.add_item(ui.TextDisplay(f"Couldn't find player whose ID is {info.player_id}. Check if the ID & server & season input are correct."))
        else:
            ranks = slay_ranking_database.fetch_dm_player_ranks(info.server_name, info.player_id, info.season_id)

            container.add_item(ui.TextDisplay(
                f"**Nickname:** {dm_player.nickname} (ID: {dm_player.id})\n"
                f"**Clan:** {dm_player.clan_tag}\n"
                f"**ELO Score:** {dm_player.elo} (Rank #{ranks[2]})\n"
                f"**Kills:** {dm_player.kills} (Rank #{ranks[0]})\n"
                f"**Bot Kills:** {dm_player.bot_kills} (Rank #{ranks[1]})\n"
                f"**Ranked Match Count:** {dm_player.match_played_count}"
            ))

            bottomButtons = ui.ActionRow(
                FavoritePlayerButton(
                    info,
                    dm_player.nickname + (f" [{dm_player.clan_tag}]" if dm_player.clan_tag else "")
                )
            )

            if dm_player.clan_tag:
                bottomButtons.add_item(ClanDetailsButton(info, dm_player.clan_tag, 2))

            bottomButtons.add_item(RecentLogButton(info, 1))

            container.add_item(bottomButtons)

    elif info.page_index == 3:
        dm_player = slay_ranking_database.fetch_dm_player(info.server_name, info.player_id, info.season_id)
        if not dm_player:
            container.add_item(ui.TextDisplay(f"Couldn't find player whose ID is {info.player_id}."))
        else:
            container.add_item(ui.TextDisplay(dm_player.logs if dm_player.logs else f"Player **{dm_player.nickname} ({dm_player.id})** doesn't have any logs yet."))

    layout_view = ui.MyLayoutView().add_item(ui.add_expiration_time_text(container))
    #print(layout_view.total_children_count)
    return layout_view

async def build_slay_clan_rank_ui(info: SlayClanRankUIInfo):
    if info.season_id == None:
        info.season_id = database.SlayRanking.existed_season_ids_in_history[-1]

    container = ui.Container(
        ui.ActionRow(ServerSelect(info, 2)),
        ui.ActionRow(SeasonSelect(info, 2)),
        ui.ActionRow(PageSelect(info, 2))
    )

    top_buttons = ui.ActionRow(ClanSearchButton(info))
    container.add_item(top_buttons)

    if info.last_ui_info:
        if info.last_ui_info[0] == 1:
            top_buttons.add_item(BackToRankingButton(info.last_ui_info[1]))
        else:
            top_buttons.add_item(BackToPlayerDetailsButton(info.last_ui_info[1]))

    if info.page_index == 0:
        favorite_clans = user_database.favorite_clans(info.dc_user_id)

        container.add_item(ui.TextDisplay("### Favorite clans you saved:"))
        if len(favorite_clans) == 0:
            container.add_item(ui.TextDisplay("You haven't marked any clan as favorite. You can try to search."))
        else:
            for data in favorite_clans:
                clan_tag = data[0]
                container.add_item(ui.Section(f"[{clan_tag}]", accessory=ClanDetailsButton(info, clan_tag)))
    elif info.page_index == 1:
        searched_clans = slay_ranking_database.search_clan(
            info.server_name,
            info.searched_clan_tag,
            info.season_id
        )

        container.add_item(ui.TextDisplay(f"### Search Results for \"{info.searched_clan_tag}\""))

        if len(searched_clans) == 0:
            container.add_item(ui.TextDisplay(f"Couldn't find any clan tag match your search."))
        else:
            for clan in searched_clans:
                container.add_item(
                    ui.Section(f"[{clan.tag}]", accessory=ClanDetailsButton(info, clan.tag))
                )

            container.add_item(ui.TextDisplay(f"-# Can only search up to 8 results, please make sure clan tag input as accurate as possible."))

    elif info.page_index == 2:
        clan = slay_ranking_database.fetch_clan(info.server_name, info.clan_tag, info.season_id)
        if not clan:
            container.add_item(ui.TextDisplay(f"Couldn't find clan tag that is [{info.clan_tag}]. Check if the clan-tag & server & season input are correct."))
        else:
            ranks = slay_ranking_database.fetch_clan_ranks(info.server_name, info.clan_tag, info.season_id)

            container.add_item(ui.TextDisplay(
                f"**Tag:** {clan.tag}\n"
                f"**Name:** {clan.name}\n"
                f"**ELO Score:** {clan.elo} (Rank #{ranks[0]})\n"
                f"**ELO Addend**: {clan.elo_addend}\n"
                f"**ELO Subtrahend**: {clan.elo_subtrahend}\n"
            ))

            container.add_item(ui.ActionRow(FavoriteClanButton(info), RecentLogButton(info, 2)))

    elif info.page_index == 3:
        clan = slay_ranking_database.fetch_clan(info.server_name, info.clan_tag, info.season_id)
        if not clan:
            container.add_item(ui.TextDisplay(f"Couldn't find clan tag that is [{info.clan_tag}]. Check if the clan-tag & server & season input are correct."))
        else:
            container.add_item(ui.TextDisplay(clan.logs if clan.logs else f"Clan **[{clan.tag}]** doesn't have any logs yet."))

    layout_view = ui.MyLayoutView().add_item(ui.add_expiration_time_text(container))
    return layout_view