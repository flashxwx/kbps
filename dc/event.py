import traceback, os, time, sys

import discord
from discord import Message

from dc import bot, bot_logger, admin_discord_ids, slay_radio, send_dev_message
from dc.bot_admin import process_bot_admin_command, command_prefix

from slayone.stats import return_all_broadcast_message

x = True # Hmm... this solves the dead lock... this is embarrassed

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    global x

    if member.id == bot.user.id:
        if after.channel is None and (x):
            with slay_radio.radio_vc_dict_lock:
                slay_radio.radio_vc_dict.pop(before.channel.id, None)

        elif after.channel and (len(after.channel.members) == 1):
            with slay_radio.radio_vc_dict_lock:
                radio_voice_info = slay_radio.radio_vc_dict.pop(before.channel.id)
                await radio_voice_info.voice_client.disconnect()

        return

    if before.channel and (len(before.channel.members) == 1) and (before.channel.members[0].id == bot.user.id):
        x = False
        with slay_radio.radio_vc_dict_lock:
            radio_voice_info = slay_radio.radio_vc_dict.pop(before.channel.id)
            await radio_voice_info.voice_client.disconnect()
        x = True

        return

    if after.channel and (after.channel.id in slay_radio.radio_vc_dict):
        if len(message := return_all_broadcast_message()) != 0:
            slay_radio.add_broadcast_message(message, "all")
            slay_radio.broadcast_messages_process_event.set()

@bot.event
async def on_error(event: str, *args, **kwargs):
    # exc_type, _, _ = sys.exc_info()

    bot_logger.error(traceback.format_exc())

@bot.event
async def on_ready():
    bot.start_running_time = time.time()

    bot_logger.info(f"{bot.user} is online.")

    slay_radio.start(bot)

    if not os.environ.get("TEST_MODE"):

        await bot.change_presence(activity=discord.CustomActivity(name="Listening to /help"))

        send_dev_message("I am online.")

@bot.event
async def on_message(message: Message):
    if message.content and (message.author.id in admin_discord_ids):
        if message.content[0] == command_prefix and len(message.content) != 1:

            try:
                await process_bot_admin_command(message)
            except:
                await message.reply(traceback.format_exc()[:2000])