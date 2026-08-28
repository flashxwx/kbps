import traceback, time

from discord import Interaction

from dc import ui, bot_logger

async def handle_interaction_error(interaction: Interaction, error: Exception):
    print(error.args)
    traceback_info = traceback.format_exc()

    layout_view = ui.build_a_message_ui(
        f"### Error: \n```bash\n{traceback_info[-1800:]}```\n"
        f"Occur at <t:{int(time.time())}:f>. Contact @flashqwq on discord for support."
        "You can also join https://discord.com/invite/DV8df6c3dr for more about Kbps."
    )

    bot_logger.error(traceback_info)

    try:
        if interaction.response.is_done():
            await interaction.followup.send(view=layout_view, ephemeral=True)
        else:
            await interaction.response.send_message(view=layout_view, ephemeral=True)
    except:
        bot_logger.error(traceback.format_exc())