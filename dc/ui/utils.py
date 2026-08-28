import time

from dc import ui

def build_a_message_ui(message: str):
    return ui.MyLayoutView().add_item(ui.Container(ui.TextDisplay(message)))

def add_expiration_time_text(container: ui.Container, timeout: float = 180):
    return container.add_item(ui.TextDisplay(
        "-# Expiration Time of This Message Interaction: "
        + f"<t:{int(time.time()+timeout)}:R>"
    ))

def new_timezone_select_options():
    return [
        ui.SelectOption(label="-11 (American Samoa)", value="-11.0"),
        ui.SelectOption(label="-10 (Hawaii)", value="-10.0"),
        ui.SelectOption(label="-9 (Alaska)", value="-9.0"),
        ui.SelectOption(
            label="-8 (PST - Los Angeles/Vancouver)", value="-8.0"
        ),
        ui.SelectOption(label="-7 (MST - Denver/Phoenix)", value="-7.0"),
        ui.SelectOption(label="-6 (CST - Chicago/Mexico City)", value="-6.0"),
        ui.SelectOption(label="-5 (EST - New York/Toronto)", value="-5.0"),
        ui.SelectOption(label="-4 (AST - Santiago/Halifax)", value="-4.0"),
        ui.SelectOption(
            label="-3 (Brazil - Sao Paulo/Buenos Aires)", value="-3.0"
        ),
        ui.SelectOption(label="-2 (Mid-Atlantic)", value="-2.0"),
        ui.SelectOption(label="-1 (Azores/Cape Verde)", value="-1.0"),
        ui.SelectOption(label="+0 (UTC/GMT - London/Lisbon)", value="0.0"),
        ui.SelectOption(label="+1 (CET - Paris/Berlin/Rome)", value="1.0"),
        ui.SelectOption(
            label="+2 (EET - Cairo/Kyiv/Johannesburg)", value="2.0"
        ),
        ui.SelectOption(
            label="+3 (MSK - Moscow/Istanbul/Nairobi)", value="3.0"
        ),
        ui.SelectOption(label="+3.5 (Tehran)", value="3.5"),
        ui.SelectOption(label="+4 (Dubai/Baku)", value="4.0"),
        ui.SelectOption(label="+5.5 (IST - Mumbai/New Delhi)", value="5.5"),
        ui.SelectOption(label="+7 (Bangkok/Jakarta/Hanoi)", value="7.0"),
        ui.SelectOption(
            label="+8 (CST - Beijing/Hong Kong/Singapore)", value="8.0"
        ),
        ui.SelectOption(label="+9 (JST - Tokyo/Seoul)", value="9.0"),
        ui.SelectOption(label="+9.5 (Adelaide/Darwin)", value="9.5"),
        ui.SelectOption(
            label="+10 (AEST - Sydney/Melbourne/Guam)", value="10.0"
        ),
        ui.SelectOption(label="+11 (Solomon Islands/Magadan)", value="11.0"),
        ui.SelectOption(label="+12 (Auckland/Fiji)", value="12.0"),
    ]