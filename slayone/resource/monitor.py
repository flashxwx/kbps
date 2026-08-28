import requests, datetime as dt, hashlib, asyncio
from email.utils import parsedate_to_datetime

from threading import Event, Thread
from dataclasses import dataclass

from dc.client import bot, send_dev_message

PathStr = str

monitoring_event = Event()

@dataclass(slots=True)
class TargetInfo:
    last_modified_date: dt.datetime = dt.datetime.fromtimestamp(0, tz=dt.UTC)
    sha256: str = ""

target_info_dict: dict[PathStr, TargetInfo] = {}

def monitoring_loop():
    while not monitoring_event.is_set():
        for path_str, target_info in target_info_dict.items():
            has_been_modified, date_text = func(path_str, target_info)

            if has_been_modified:
                send_dev_message(f"{path_str} has been modifed at {date_text}")

        is_set = monitoring_event.wait(86400)
        if is_set:
            return

def func(path_str: str, target_info: TargetInfo):
    try:
        response = requests.get(f"https://slay.one/{path_str}")
        response.raise_for_status()

        date_text = response.headers.get("Last-Modified")

        new_last_modified_date = parsedate_to_datetime(response.headers.get("Last-Modified"))

        if new_last_modified_date < target_info.last_modified_date:
            return False, date_text

        new_sha256 = hashlib.sha256(response.content).hexdigest()

        if new_sha256 == target_info.sha256:
            return False, date_text

        target_info.last_modified_date = new_last_modified_date
        target_info.sha256 = new_sha256

        return True, date_text

    except Exception as e:
        print(e)

async def notify(message: str):
    admin_channel = bot.get_channel(1504839020218290298)
    if not admin_channel:
        admin_channel = await bot.fetch_channel(1504839020218290298)

    await admin_channel.send(message)

def start_monitoring():
    monitoring_event.clear()

    with open("slayone/resource/targets.txt", "a+", encoding="utf-8") as file:
        file.seek(0)

        for line in file:
            target_info_dict[line[:-1]] = TargetInfo()

    Thread(target=monitoring_loop).start()

def stop_monitoring():
    monitoring_event.set()