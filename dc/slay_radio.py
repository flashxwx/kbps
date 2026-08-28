# This feature aims for few servers and small user base, not scalable. 

import time, asyncio, threading

from typing import NamedTuple
from dataclasses import dataclass
from queue import Queue

import edge_tts, io
from discord import VoiceClient, FFmpegPCMAudio

import database
from dc import ui, client

from slayone.stats import return_all_broadcast_message

@dataclass(slots=True)
class RadioInteractionInfo:
    dms_switch: bool | None
    voice_switch: int
    """-1: disconnect, 0: False, >0: True, this can store the boolean as number and the vc_id"""

@dataclass(slots=True)
class RadioVCInfo:
    voice_client: VoiceClient
    queue: Queue | None
    queue_lock = threading.Lock()

server_texts = {
    0: "Server of Europe",
    1: "Server of America",
    2: "Server of Asia",
}

broadcast_messages: dict[str, str] = {}
broadcast_messages_lock = threading.Lock()

broadcast_messages_process_event = threading.Event()

radio_vc_dict: dict[int, RadioVCInfo] = {}
radio_vc_dict_lock = threading.Lock()

users_database = database.Users()

def add_broadcast_message(content: str, type: str):
    with broadcast_messages_lock:
        broadcast_messages[type] = content

def text_to_speech_buffer(text: str, voice: str = "en-GB-SoniaNeural"):
    communicate = edge_tts.Communicate(text, voice, rate="-15%")
    buffer = io.BytesIO()

    for chunk in communicate.stream_sync():
        if chunk["type"] == "audio":
            buffer.write(chunk["data"])

    buffer.seek(0)
    return buffer

def process_broadcast_messages(bot: client.Client):
    users_database = database.Users()

    while True:
        if broadcast_messages_process_event.wait(30):
            broadcast_messages_process_event.clear()

        if bot.is_closed():
            break

        with broadcast_messages_lock:
            if "all" in broadcast_messages:
                message_content = broadcast_messages["all"]
            else:
                message_content = "\n and ".join(broadcast_messages.values())

                if len(message_content) == 0:
                    broadcast_messages.clear()
                    continue

                message_content = "In the past 30 seconds, " + message_content

            broadcast_messages.clear()

        layout_view = asyncio.run_coroutine_threadsafe(ui.build_dms_radio_ui(message_content), bot.loop).result()

        for radio_receiver in users_database.radio_receivers():
            user = asyncio.run_coroutine_threadsafe(bot.fetch_user(radio_receiver[0]), bot.loop).result()

            asyncio.run_coroutine_threadsafe(user.send(view=layout_view), bot.loop)

        if len(radio_vc_dict) == 0:
            continue

        speech_buffer = text_to_speech_buffer(message_content)

        with radio_vc_dict_lock:
            for voice_radio_info in radio_vc_dict.values():
                with voice_radio_info.queue_lock:
                    if voice_radio_info.queue != None:
                        voice_radio_info.queue.put(speech_buffer)
                        continue

                voice_radio_info.queue = Queue()
                voice_radio_info.queue.put(speech_buffer)

                def after_func(error):
                    with voice_radio_info.queue_lock:
                        if voice_radio_info.queue.empty():
                            voice_radio_info.queue = None
                            return

                    voice_radio_info.voice_client.play(
                        FFmpegPCMAudio(voice_radio_info.queue.get(), pipe=True, before_options="-f mp3"),
                        after=after_func
                    )

                after_func(None)

async def process_interaction(interaction: ui.Interaction, info: RadioInteractionInfo, force_ui: bool = False):
    warning_response_content = ""

    if info.dms_switch == None:
        if users_database.fetch_radio_receiver(interaction.user.id):
            info.dms_switch = True
    elif info.dms_switch:
        users_database.insert_radio_receiver(interaction.user.id)

        if len(message := return_all_broadcast_message()) != 0:
            add_broadcast_message(message, "all")
            broadcast_messages_process_event.set()
    else:
        users_database.delete_radio_receiver(interaction.user.id)

    # if dms_switch:
    #     dms_radio_message = "You have already turned **ON* the radio in DMs (Make sure you didn't block the DMs from bots.)\n\n"
    # else:
    #     dms_radio_message = "Radio in DMs is **OFF** right now.\n\n"

    if interaction.guild:

        if voice_client := interaction.guild.voice_client:
            if info.voice_switch == -1:
                await voice_client.disconnect()
                info.voice_switch = 0
            else:
                info.voice_switch = voice_client.channel.id

        elif info.voice_switch:
            if interaction.user.voice:
                vc = interaction.user.voice.channel

                if vc.permissions_for(interaction.guild.me).connect:
                    voice_client = await vc.connect(reconnect=False)

                    with radio_vc_dict_lock:
                        radio_vc_dict[voice_client.channel.id] = RadioVCInfo(voice_client, None)

                    if len(message := return_all_broadcast_message()) != 0:
                        add_broadcast_message(message, "all")
                        broadcast_messages_process_event.set()

                    info.voice_switch = vc.id
                else:
                    warning_response_content = f"Kbps **doesn't have permission** to join <#{vc.id}>."
                    info.voice_switch = False
            else:
                warning_response_content = f"You have to **join a voice channel** to turn on radio in voice."
                info.voice_switch = False
    elif info.voice_switch:
        warning_response_content = "You **cannot** turn on radio in voice in DMs channel."

    if force_ui:
        await interaction.edit_original_response(view=await ui.build_slay_radio_ui(info))

    if warning_response_content:
        return await interaction.followup.send(warning_response_content, ephemeral=True)

    if not force_ui:
        await interaction.edit_original_response(view=await ui.build_slay_radio_ui(info))

def start(bot: client.Client):
    threading.Thread(target=process_broadcast_messages, args=(bot,)).start()