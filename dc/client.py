import os, logging, asyncio

from discord import Client, Intents

client_intents = Intents.default()
client_intents.message_content = False

bot = Client(intents=client_intents)
bot.start_running_time = 0

admin_discord_ids = set(map(int, os.environ.get("ADMIN_DISCORD_IDS").split(",")))

bot_logger = logging.getLogger("dc.bot")
bot_logger.setLevel(logging.INFO)

command_use_rate_of_each_server: dict[int, tuple[str, int, int]] = {}

class LogHandler(logging.Handler):
    def __init__(self):
        self.file_handler = logging.FileHandler("dc.log", encoding="utf-8")
        self.stream_handler = logging.StreamHandler()

        super().__init__()

    def emit(self, record):
        try:
            self.file_handler.emit(record)
            self.stream_handler.emit(record)
        except Exception:
            self.handleError(record)

    def setFormatter(self, fmt):
        self.file_handler.setFormatter(fmt)
        self.stream_handler.setFormatter(fmt)

logging_handler = LogHandler()
logging_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s"))

bot_logger.addHandler(logging_handler)

def send_dev_message(content: str):
    async def send():
        dev_channel = bot.get_channel(1504839020218290298)
        if not dev_channel:
            dev_channel = await bot.fetch_channel(1504839020218290298)

        await dev_channel.send(f"<@512179557072109571>\n{content}")

    asyncio.run_coroutine_threadsafe(send(), bot.loop)

def update_command_use_rate():
    ...

def run_bot(token: str):
    bot.run(token, log_handler=LogHandler())