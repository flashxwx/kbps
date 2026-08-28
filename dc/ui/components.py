from discord import MediaGalleryItem, SelectOption, Interaction
from discord.ui import (
    LayoutView, Container, TextDisplay, Section, Button, Modal, ActionRow, TextInput, Separator, MediaGallery, Select
)

from dc.error import handle_interaction_error

class MyLayoutView(LayoutView):
    def __init__(self, *, timeout = 210):
        super().__init__(timeout=timeout)

    async def on_error(self, interaction, error, item):
        await handle_interaction_error(interaction, error)

class MyModal(Modal):
    async def on_error(self, interaction, error):
        await handle_interaction_error(interaction, error)