import io, math
from dataclasses import dataclass

import discord
from slay import Info, Socket

import database
from database import slay_replay
from dc import ui

ServerNames = ("EU Server", "AM Server", "Asia Server")

@dataclass(slots=True)
class SlayReplayUIInfo:
    db_server_query: str = "SERVER_INDEX IN (0, 1, 2)"
    db_mode_query: str = "MODE_INDEX IN (1, 2, 4, 5)"
    replay_id: str = ""
    page: int = 1
    replay_metadata: slay_replay.ReplayMetadata = None

slay_replay_database = database.SlayReplay()

class ServerSelect(ui.Select):
    def __init__(self, info: SlayReplayUIInfo):
        self.info = info

        options = [
            ui.SelectOption(label="All Servers", value="SERVER_INDEX IN (0, 1, 2)"),
            ui.SelectOption(label="EU", value="SERVER_INDEX = 0"),
            ui.SelectOption(label="AM", value="SERVER_INDEX = 1"),
            ui.SelectOption(label="Asia", value="SERVER_INDEX = 2"),
            ui.SelectOption(label="EU and AM", value="SERVER_INDEX IN (0, 1)"),
            ui.SelectOption(label="AM and Asia", value="SERVER_INDEX IN (1, 2)"),
            ui.SelectOption(label="EU and Asia", value="SERVER_INDEX IN (0, 2)")
        ]

        for option in options:
            if option.value == info.db_server_query:
                option.default = True

        super().__init__(options=options)

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        self.info.db_server_query = self.values[0]
        await interaction.edit_original_response(view=await ui.build_slay_replay_ui(self.info))

class ModeSelect(ui.Select):
    def __init__(self, info: SlayReplayUIInfo):
        self.info = info

        options = [
            ui.SelectOption(label="All Modes", value="MODE_INDEX IN (1, 2, 4, 5)"),
            ui.SelectOption(label="Team Deathmatch", value="MODE_INDEX = 1"),
            ui.SelectOption(label="Capture the Flag", value="MODE_INDEX = 2"),
            ui.SelectOption(label="Deathmatch", value="MODE_INDEX = 4"),
            ui.SelectOption(label="Infection", value="MODE_INDEX = 5"),
            ui.SelectOption(label="Team Deathmatch and Capture the Flag", value="MODE_INDEX IN (1, 2)"),
            ui.SelectOption(label="Team Deathmatch and Deathmatch", value="MODE_INDEX IN (1, 4)"),
            ui.SelectOption(label="Team Deathmatch and Infection", value="MODE_INDEX IN (1, 5)"),
            ui.SelectOption(label="Capture the Flag and Deathmatch", value="MODE_INDEX IN (2, 4)"),
            ui.SelectOption(label="Capture the Flag and Infection", value="MODE_INDEX IN (2, 5)"),
            ui.SelectOption(label="Deathmatch and Infection", value="MODE_INDEX IN (4, 5)"),
            ui.SelectOption(label="Team Deathmatch, Capture the Flag and Deathmatch", value="MODE_INDEX IN (1, 2, 4)"),
            ui.SelectOption(label="Team Deathmatch, Capture the Flag and Infection", value="MODE_INDEX IN (1, 2, 5)"),
            ui.SelectOption(label="Team Deathmatch, Deathmatch and Infection", value="MODE_INDEX IN (1, 4, 5)"),
            ui.SelectOption(label="Capture the Flag, Deathmatch and Infection", value="MODE_INDEX IN (2, 4, 5)")
        ]

        for option in options:
            if option.value == info.db_mode_query:
                option.default = True

        super().__init__(options=options)

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        self.info.db_mode_query = self.values[0]
        await interaction.edit_original_response(view=await ui.build_slay_replay_ui(self.info))

class BackToReplaySearchButton(ui.Button):
    def __init__(self, info: SlayReplayUIInfo):
        self.info = info

        super().__init__(label="Back to Replay Search")


    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        self.info.replay_id = ""
        await interaction.edit_original_response(view=await ui.build_slay_replay_ui(self.info))

class ShowReplayFileButton(ui.Button):
    def __init__(self, info: SlayReplayUIInfo):
        self.info = info
        
        super().__init__(label="Send Me Replay File")

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        await interaction.followup.send(
            file=discord.File(
                io.BytesIO(slay_replay_database.fetch_replay_json_by_id(self.info.replay_id).encode("utf-8")),
                self.info.replay_id+".json"
            ),
            ephemeral=True
        )

class ShowReplayFileButtonForEveryone(ui.Button):
    def __init__(self, info: SlayReplayUIInfo):
        self.info = info
        
        super().__init__(label="Send Everyone Replay File")

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        metadata = self.info.replay_metadata

        await interaction.followup.send(
            (
                f"## {ServerNames[metadata.server_index]}, {Info.GameMode(metadata.mode_index).text}"
                f"\n### {metadata.title}\n{metadata.info}"
            ),
            file=discord.File(
                io.BytesIO(slay_replay_database.fetch_replay_json_by_id(self.info.replay_id).encode("utf-8")),
                self.info.replay_id+".json"
            ),
            ephemeral=False
        )

class ViewReplayButton(ui.Button):
    def __init__(self, info: SlayReplayUIInfo, replay_id: int):
        self.info = info
        self.replay_id = replay_id

        super().__init__(label="View")


    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        self.info.replay_id = self.replay_id
        await interaction.edit_original_response(view=await ui.build_slay_replay_ui(self.info))

async def build_slay_replay_ui(info: SlayReplayUIInfo, current_page: int = -1):
    if current_page == -1:
        current_page = info.page
    else:
        info.page = current_page

    layout_view = ui.MyLayoutView()

    if info.replay_id:
        metadata = slay_replay_database.fetch_replay_metadata_by_id(info.replay_id)
        info.replay_metadata = metadata

        if metadata:
            layout_view.add_item(ui.add_expiration_time_text(ui.Container(
                ui.ActionRow(BackToReplaySearchButton(info)),
                ui.TextDisplay(
                f"## {ServerNames[metadata.server_index]}, {Info.GameMode(metadata.mode_index).text}"
                f"\n### {metadata.title}\n{metadata.info}"
                ),
                ui.ActionRow(ShowReplayFileButton(info), ShowReplayFileButtonForEveryone(info))
            )))
            
        else:
            layout_view.add_item(ui.Container(ui.TextDisplay(f"## Did not find any replay using ID `{info.replay_id}`")))
    else:
        all_metadata, total_records = slay_replay_database.fetch_replay_metadata_by_filter(
            info.db_server_query, info.db_mode_query, (current_page-1)*5, 5
        )

        container = ui.Container(
            ui.TextDisplay(
                f"### Space: {round(slay_replay.max_used_space_size/1_000_000_000, 2)}/{round(slay_replay.used_space_size/1_000_000_000, 2)} (GB)\n"
                "Note: The oldest replay will be deleted if reaching the maximum of space."
            ),
            ui.ActionRow(ServerSelect(info)), ui.ActionRow(ModeSelect(info))
        )

        count_of_metadata = 0
        for metadata in all_metadata:
            container.add_item(ui.Section(metadata.title, accessory=ViewReplayButton(info, metadata.id)))
            count_of_metadata += 1

        if count_of_metadata == 0:
            container.add_item(ui.TextDisplay("No Replays Found."))

        container.add_item(ui.TextDisplay("-# Only save the games that last at least 5 minutes."))

        layout_view.add_item(container).add_item(
            ui.make_page_panel_container(ui.PagePanelInfo(build_slay_replay_ui, info, math.ceil(total_records / 5), current_page))
        )


    return layout_view