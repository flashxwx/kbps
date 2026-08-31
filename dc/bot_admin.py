import subprocess, asyncio, os
from typing import Literal
import discord
from discord import Message, Interaction, app_commands
from discord.app_commands import CommandTree, AppCommandError

from dc import bot
from dc.command import command_tree, get_stats_for_command_request
from dc.ui.help import load_help_doc
from dc.error import handle_interaction_error
from slayone.watcher import watching_game_room_id_set_of_each_server

if os.environ.get("TEST_MODE"):
    command_prefix = "?"
else:
    command_prefix = "!"

@command_tree.command(name="adminpower")
@app_commands.guilds(1443569912017715214)
async def use_admin_power(
    interaction: Interaction,
    custom_spell: str = None,
    ready_spell: Literal[
        ".command_draft",
        ".sync_commands",
        ".status",
        ".safely_shutdown",
        ".safely_restart",
        ".command_stats",
        ".load_help_docs"
    ] = None
):
    terminal_command = ""
    response_message = ""

    if custom_spell:
        spell = custom_spell
    elif ready_spell:
        spell = ready_spell
    else:
        spell = ".command_draft"

    match spell:
        case ".load_help_docs":
            load_help_doc()
            response_message = "Loaded help docs."
        case ".command_stats":
            response_message = get_stats_for_command_request()
        case ".status":
            response_message = (
                f"slayone.watcher.watching_game_room_id_set_of_each_server: {watching_game_room_id_set_of_each_server}"
            )
        case ".sync_commands":
            synced_commands = (
                await command_tree.sync()
                + await command_tree.sync(guild=discord.Object(id=1443569912017715214))
            )

            if not os.environ.get("TEST_MODE"):
                synced_commands.extend(await command_tree.sync(guild=discord.Object(id=1120432082846486638)))

            response_message = f"Synced commands: {", ".join(command.name for command in synced_commands)}"
        case ".command_draft":
            with open("dc/command_draft", encoding="utf-8") as file:
                response_message = file.read()[:2000]

        case ".safely_shutdown":
            await interaction.response.send_message("Shuting Down Kbps Safely...")
            return await bot.close()
        case ".safely_restart":
            import main_state

            await interaction.response.send_message("Restarting Kbps Safely...")
            main_state.need_restart = True

            await bot.close()
            return
        case _:
            terminal_command = spell

    if terminal_command:
        result = subprocess.run(
            terminal_command, shell=True, capture_output=True, text=True
        )

        if result.stderr:
            response_message = result.stderr[:2000]
        elif result.stdout:
            response_message = result.stdout[:2000]

    if response_message:
        await interaction.response.send_message(response_message, ephemeral=True)

async def process_bot_admin_command(message: Message):
    splitted_command_str = message.content[1:].split(maxsplit=1)

    match splitted_command_str[0]:
        case "sync_commands":

            synced_commands = (
                await command_tree.sync()
                + await command_tree.sync(guild=discord.Object(id=1443569912017715214))
            )

            if not os.environ.get("TEST_MODE"):
                synced_commands.extend(await command_tree.sync(guild=discord.Object(id=1120432082846486638)))

            await message.reply(f"Synced commands: {", ".join(command.name for command in synced_commands)}")
        case "c":
            if len(splitted_command_str) == 1:
                with open("dc/command_draft", encoding="utf-8") as file:
                    await message.reply(file.read()[:2000])
                return

            result = subprocess.run(
                splitted_command_str[1], shell=True, capture_output=True, text=True
            )

            if result.stderr:
                await message.reply(result.stderr[:2000])
            elif result.stdout:
                await message.reply(result.stdout[:2000])
        case "status":
            ...

        case "safely_shutdown":
            await message.reply("Shuting Down Kbps Safely...")
            await bot.close()

        case "safely_restart":
            import main_state

            await message.reply("Restarting Kbps Safely...")
            main_state.need_restart = True

            await bot.close()
            