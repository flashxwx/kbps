import json
from dc import ui

help_doc = []

def load_help_doc():
    global help_doc

    with open("docs/help.json", "r", encoding="utf-8") as file:
        help_doc = json.loads(file.read())

class NagivationButton(ui.Button):
    def __init__(self, location: str = "1", name: str = "More", last_ui_stuff: tuple = None):
        self.location = location
        self.last_ui_stuff = last_ui_stuff

        super().__init__(label=name)

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()
        await interaction.edit_original_response(view= await build_help_ui(self.location, self.last_ui_stuff))

class BackToLastUIButton(ui.Button):
    def __init__(self, last_ui_stuff: tuple):
        self.last_ui_stuff = last_ui_stuff

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()
        await interaction.edit_original_response(view=await self.last_ui_stuff[0](*self.last_ui_stuff[1]))

class BackButton(ui.Button):
    def __init__(self, location: str = "1"):
        self.location = location

        super().__init__(label="Back")

class HomeButton(ui.Button):
    def __init__(self, location: str = "1"):
        self.location = location

        super().__init__(label="Home")

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

async def build_help_ui(location: str = "1", last_ui_stuff: tuple = None):
    if location[0] == "p":
        need_pin = True
        location = location[1:]
    else:
        need_pin = False

    layout_view = ui.MyLayoutView()
    container = ui.Container()
    splited_location = location.split("-")

    section = help_doc
    sub_section = help_doc
    index = 1
    error_message = ""

    top_buttons = ui.ActionRow()
    last_dash_sign_index = location.rfind("-")
    if last_dash_sign_index > 0:
        top_buttons.add_item(NagivationButton("1", "Home"))
        top_buttons.add_item(NagivationButton(location[:last_dash_sign_index], "Back"))
    if last_ui_stuff:
        top_buttons.add_item(BackToLastUIButton(last_ui_stuff))

    location_for_website = location if last_dash_sign_index == -1 else location[:last_dash_sign_index]

    top_buttons.add_item(ui.Button(label="Read on Website", url=f"https://flashxwx.github.io/kbps/?doc={location_for_website}"))
    container.add_item(top_buttons)
    container.add_item(ui.TextDisplay(f"-# Location Query Text: {location}"))

    for index_str in splited_location:
        if not index_str:
            error_message = f"Incorrect Location Format - \"{location}\". Index cannot be empty."
            break

        try:
            index = int(index_str)-1
        except:
            error_message = f"Incorrect Location Format - \"{location}\". Index must be number."
            break

        old_section = section

        try:
            if not sub_section:
                error_message = f"Location Not Exists - \"{location}\"."

            section = sub_section
            sub_section = section[index].get("more", None)
        except TypeError:
            error_message = f"Location Not Exists - \"{location}\"."
            section = old_section

    if error_message:
        layout_view.add_item(ui.Container(ui.TextDisplay("Error: " + error_message)))

    if need_pin:
        content = ""
        data = section[index]
        main_data = data["main"]
        if isinstance(main_data, list):
            for line in main_data:
                content += line + "\n"
        else:
            content += main_data + "\n"

        if data.get("more"):
            container.add_item(ui.Section(content, accessory=NagivationButton(str(index+1)+"-1")))
        else:
            container.add_item(ui.TextDisplay(content))

    for i, data in enumerate(section):
        if need_pin and i == index:
            continue

        content = ""

        main_data = data["main"]
        if isinstance(main_data, list):
            for line in main_data:
                if no_newline := (line[-1:] == "\\"):
                    line = line[:-1]

                content += line

                if not no_newline:
                    content += "\n\n"
        else:
            content += main_data + "\n"

        if data.get("more"):
            container.add_item(ui.Section(content, accessory=NagivationButton(str(i+1)+"-1")))
        else:
            container.add_item(ui.TextDisplay(content))

    layout_view.add_item(container)

    return layout_view

load_help_doc()