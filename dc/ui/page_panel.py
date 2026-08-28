from typing import Callable, Coroutine
from dataclasses import dataclass

from discord import Interaction

from dc import ui

BuildFunc = Callable[[], Coroutine] | Callable[[int], Coroutine] | Callable[[object], Coroutine] | Callable[[object, int], Coroutine]

@dataclass(slots=True)
class PagePanelInfo:
    build_func: BuildFunc
    arg: object | None = None
    total_pages: int = None
    current_page: int = None
    timeout: float = 180

    def return_build_coroutine(self):
        if self.arg:
            if self.total_pages == None:
                return self.build_func(self.arg)
            else:
                return self.build_func(self.arg, self.current_page)
        elif self.total_pages == None:
            return self.build_func()
        else:
            return self.build_func(self.current_page)


class ReloadButton(ui.Button):
    def __init__(self, info: PagePanelInfo):
        self.info = info

        super().__init__(label="Reload")

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        await interaction.edit_original_response(view=await self.info.return_build_coroutine())

class FirstPageButton(ui.Button):
    def __init__(self, info: PagePanelInfo):
        self.info = info

        super().__init__(label="First")

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()

        self.info.current_page = 1
        await interaction.edit_original_response(view=await self.info.return_build_coroutine())

class LastPageButton(ui.Button):
    def __init__(self, info: PagePanelInfo):
        self.info = info

        super().__init__(label="Last")

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()

        self.info.current_page = self.info.total_pages
        await interaction.edit_original_response(view=await self.info.return_build_coroutine())

class PreviousPageButton(ui.Button):
    def __init__(self, info: PagePanelInfo):
        self.info = info

        super().__init__(label="◀")

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()

        self.info.current_page -= 1
        await interaction.edit_original_response(view=await self.info.return_build_coroutine())

class NextPageButton(ui.Button):
    def __init__(self, info: PagePanelInfo):
        self.info = info

        super().__init__(label="▶")

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()

        self.info.current_page += 1
        await interaction.edit_original_response(view=await self.info.return_build_coroutine())

class PageSearchButton(ui.Button):
    def __init__(self, info: PagePanelInfo):
        self.info = info

        super().__init__(label="Page Search")

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(PageSearchModal(self.info))

class PageSearchModal(ui.MyModal):
    page_number_input = ui.TextInput(label="Page Number Input", placeholder="5", max_length=9)

    def __init__(self, info: PagePanelInfo):
        self.info = info

        super().__init__(title="Page Search")

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer()

        self.info.current_page = int(self.page_number_input.value)
        await interaction.edit_original_response(view=await self.info.return_build_coroutine())

def make_page_panel_container(info: PagePanelInfo):
    if info.total_pages < 2:
        return ui.add_expiration_time_text(ui.Container().add_item(ui.ActionRow(ReloadButton(info))), info.timeout)

    container = ui.Container(ui.TextDisplay(f"Page {info.current_page}/{info.total_pages}"))
    first_action_row = ui.ActionRow()

    if info.current_page == 1:
        first_page_button = FirstPageButton(info)
        first_page_button.disabled = True

        previous_page_button = PreviousPageButton(info)
        previous_page_button.disabled = True

        first_action_row.add_item(first_page_button).add_item(previous_page_button)
    else:
        first_action_row.add_item(FirstPageButton(info)).add_item(PreviousPageButton(info))

    if info.current_page == info.total_pages:
        next_page_button = NextPageButton(info)
        next_page_button.disabled = True

        last_page_button = LastPageButton(info)
        last_page_button.disabled = True

        first_action_row.add_item(next_page_button).add_item(last_page_button)
    else:
        first_action_row.add_item(NextPageButton(info)).add_item(LastPageButton(info))

    first_action_row.add_item(ReloadButton(info))
    container.add_item(first_action_row).add_item(ui.ActionRow(PageSearchButton(info)))

    return ui.add_expiration_time_text(container)