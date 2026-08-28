import database
from dc import ui
from dc.slay_radio import RadioInteractionInfo, process_interaction

class DMsRadioSwitch(ui.Button):
    def __init__(self, info: RadioInteractionInfo):
        self.info = info

        super().__init__(label="Turn Off Radio in DMs" if info.dms_switch else "Turn On Radio in DMs")

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        self.info.dms_switch = not self.info.dms_switch

        await process_interaction(interaction, self.info)

class VoiceRadioSwitch(ui.Button):
    def __init__(self, info: RadioInteractionInfo):
        self.info = info

        super().__init__(label="Turn On Radio in Voice" if info.voice_switch < 1 else "Turn Off Radio in Voice")

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        self.info.voice_switch = -1 if self.info.voice_switch > 0 else 1

        await process_interaction(interaction, self.info)

class TurnOffDMsRadioButton(ui.Button):
    def __init__(self):
        super().__init__(label="Turn Off Radio in DMs")

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        users_database = database.Users()
        users_database.delete_radio_receiver(interaction.user.id)
        users_database.connection.close()

        await interaction.followup.send("You have already turned **OFF** radio in DMs.", ephemeral=True)

async def build_slay_radio_ui(info: RadioInteractionInfo):
    return ui.MyLayoutView().add_item(
        ui.Container(
            ui.TextDisplay(
                "## Slay.one Radio Panel\n" + (
                    "You have already turned **ON** the radio in DMs. (Make sure you have allowed DMs from bots.)\n\n"
                    if info.dms_switch else "Radio in DMs is **OFF** right now.\n\n"
                ) + (
                    f"Radio in voice is **ON** right now, in <#{info.voice_switch}>."
                    if info.voice_switch else "Radio in voice is **OFF** right now."
                )
            )
        )
    ).add_item(ui.add_expiration_time_text(ui.Container(ui.ActionRow(DMsRadioSwitch(info), VoiceRadioSwitch(info))), 180))

async def build_dms_radio_ui(content: str):
    return ui.MyLayoutView().add_item(
        ui.add_expiration_time_text(
            ui.Container(ui.TextDisplay(content), ui.ActionRow(TurnOffDMsRadioButton())), 180
        )
    )