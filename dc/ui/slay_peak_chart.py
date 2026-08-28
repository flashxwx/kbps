import datetime as dt, io, asyncio
from concurrent.futures import ThreadPoolExecutor
from dateutil.relativedelta import relativedelta

import matplotlib
from matplotlib import pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.patches import Patch

matplotlib.use("Agg")
plt.style.use("dark_background")
plt.rcParams["figure.facecolor"] = "070709"
plt.rcParams["axes.facecolor"] = "1A1A1E"

from typing import MutableSequence

import discord

import database
from dc import ui

chart_thread_pool = ThreadPoolExecutor(max_workers=10)

line_colors = {
    "EU": "blue",
    "AM": "gold",
    "ASIA": "red"
}

units = {
    0: "Year",
    1: "Month",
    3600: "Hour",
    604800: "week",
    86400: "day"
}

class SlayPeakChartInfo:
    def __init__(
        self,
        server_names: MutableSequence[str],
        unit_index: int,
        timezone: float,
        past_years: int | None,
        past_months: int | None,
        past_weeks: int | None,
        past_days: int | None,
        past_hours: int | None,
        no_dots: bool = False
    ):
        self.server_names = server_names
        self.unit_index = unit_index
        self.timezone = dt.timezone(dt.timedelta(
            hours=timezone), name=f"UTC{f"+{timezone}" if timezone >= 0 else timezone}")

        if (
            past_years == None and past_months == None
            and past_weeks == None and past_days == None
            and past_hours == None
        ):
            self.total_time = relativedelta(days=1)
        else:
            self.total_time = relativedelta(
                years=past_years if past_years != None else 0,
                months=past_months if past_months != None else 0,
                weeks=past_weeks if past_weeks != None else 0,
                days=past_days if past_days != None else 0,
                hours=past_hours if past_hours != None else 0
            )
        
        self.no_dots = no_dots

class ChartTimeZoneSelect(ui.Select):
    def __init__(self, info: SlayPeakChartInfo):
        self.info = info

        options = ui.new_timezone_select_options()

        current_timezone_value = info.timezone.utcoffset(None).total_seconds() / 3600
        for option in options:
            if (float(option.value) == current_timezone_value):
                option.default = True

        super().__init__(options=options)

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        self.info.timezone = dt.timezone(dt.timedelta(hours=float(self.values[0])))

        layout_view, chart_image_file = await build_slay_peak_chart_ui(self.info)
        await interaction.edit_original_response(view=layout_view, attachments=[chart_image_file])

class ChartServerSelect(ui.Select):
    def __init__(self, info: SlayPeakChartInfo):
        self.info = info

        options = [
            ui.SelectOption(label="All", value="EU AM ASIA"),
            ui.SelectOption(label="EU", value="EU"),
            ui.SelectOption(label="AM", value="AM"),
            ui.SelectOption(label="Asia", value="ASIA"),
            ui.SelectOption(label="EU and AM", value="EU AM"),
            ui.SelectOption(label="AM and Asia", value="AM ASIA"),
            ui.SelectOption(label="EU and Asia", value="EU ASIA")
        ]

        current_server_value = " ".join(info.server_names)
        for option in options:
            if option.value == current_server_value:
                option.default = True

        super().__init__(options=options)

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        self.info.server_names = self.values[0].split()

        layout_view, chart_image_file = await build_slay_peak_chart_ui(self.info)
        await interaction.edit_original_response(view=layout_view, attachments=[chart_image_file])

class ChartTimeUnit(ui.Select):
    def __init__(self, info: SlayPeakChartInfo):
        self.info = info

        options = [
            ui.SelectOption(label="year", value="0"),
            ui.SelectOption(label="month", value="1"),
            ui.SelectOption(label="week", value="604800"),
            ui.SelectOption(label="day", value="86400"),
            ui.SelectOption(label="hour", value="3600")
        ]

        current_time_unit_index = info.unit_index
        for option in options:
            if int(option.value) == current_time_unit_index:
                option.default = True
        
        super().__init__(options=options)

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        self.info.unit_index = int(self.values[0])

        layout_view, chart_image_file = await build_slay_peak_chart_ui(self.info)
        await interaction.edit_original_response(view=layout_view, attachments=[chart_image_file])

class EditChartButton(ui.Button):
    def __init__(self, info: SlayPeakChartInfo):
        self.info = info

        super().__init__(label="Edit Chart Time")

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.send_modal(EditChartTimeModal(self.info))

class EditChartTimeModal(ui.MyModal):
    past_years_input = ui.TextInput(
        label="Past Years (only integer 0-4)",
        placeholder="Example: 3",
        required=False
    )

    past_months_input = ui.TextInput(
        label="Past Months (only integer 0-12)",
        placeholder="Example: 3",
        required=False
    )

    past_weeks_input = ui.TextInput(
        label="Past Weeks (only integer 0-5)",
        placeholder="Example: 3",
        required=False
    )

    past_days_input = ui.TextInput(
        label="Past Days (only integer 0-7)",
        placeholder="Example: 3",
        required=False
    )

    past_hours_input = ui.TextInput(
        label="Past Hours (only integer 0-24)",
        placeholder="Example: 12",
        required=False
    )

    def __init__(self, info: SlayPeakChartInfo):
        self.info = info

        super().__init__(title="Edit Time of Peak Chart")
    
    async def on_submit(self, interaction: ui.Interaction):
        await interaction.response.defer()

        past_years = (
            int(self.past_years_input.value)
            if self.past_years_input.value else 0
        )
        past_months = (
            int(self.past_months_input.value)
            if self.past_months_input.value else 0
        )
        past_weeks = (
            int(self.past_weeks_input.value)
            if self.past_weeks_input.value else 0
        )
        past_days = (
            int(self.past_days_input.value)
            if self.past_days_input.value else 0
        )
        past_hours = (
            int(self.past_hours_input.value)
            if self.past_hours_input.value else 0
        )

        try:
            if past_years > 4 or past_years < 0:
                await interaction.followup.send(
                    "Past years input can't be bigger than 4,"
                    " and can't be smaller than 0."
                )
                return
            
            if past_months > 12 or past_months < 0:
                await interaction.followup.send(
                    "Past months input can't be bigger than 12,"
                    " and can't be smaller than 0."
                )
                return
            
            if past_weeks > 5 or past_weeks < 0:
                await interaction.followup.send(
                    "Past weeks input can't be bigger than 5,"
                    " and can't be smaller than 0."
                )
            
            if past_days > 7 or past_days < 0:
                await interaction.followup.send(
                    "Past days input can't be bigger than 7,"
                    " and can't be smaller than 0."
                )
            
            if past_hours > 24 or past_hours < 0:
                await interaction.followup.send(
                    "Past hours input can't be bigger than 24,"
                    " and can't be smaller than 0."
                )
        except:
            await interaction.followup.send(
                "The chart time inputs must be integer."
            )
            return

        self.info.total_time = relativedelta(
            years=past_years,
            months=past_months,
            weeks=past_weeks,
            days=past_days,
            hours=past_hours
        )

        layout_view, chart_image_file = await build_slay_peak_chart_ui(self.info)

        await interaction.edit_original_response(view=layout_view, attachments=[chart_image_file])

class DotDisplaySwitchButton(ui.Button):
    def __init__(self, info: SlayPeakChartInfo):
        self.info = info

        super().__init__(label="Draw Dots" if info.no_dots else "Erase Dots")

    async def callback(self, interaction: ui.Interaction):
        await interaction.response.defer()

        self.info.no_dots = not self.info.no_dots

        layout_view, chart_image_file = await build_slay_peak_chart_ui(self.info)
        await interaction.edit_original_response(view=layout_view, attachments=[chart_image_file])

async def build_slay_peak_chart_ui(info: SlayPeakChartInfo):
    chart_container = ui.Container(ui.MediaGallery(ui.MediaGalleryItem("attachment://chart_of_slay_peaks.png")))

    chart_image_file = await asyncio.get_running_loop().run_in_executor(chart_thread_pool, generate_peak_chart_image_file, info)
    # chart_image_file = await asyncio.to_thread(generate_peak_chart_image_file, info)

    return ui.MyLayoutView().add_item(chart_container).add_item(ui.add_expiration_time_text(ui.Container(
        ui.TextDisplay("**Chart Timezone**"), ui.ActionRow(ChartTimeZoneSelect(info)),
        ui.TextDisplay("**Chart Server**"), ui.ActionRow(ChartServerSelect(info)),
        ui.TextDisplay("**Chart Time Unit**"), ui.ActionRow(ChartTimeUnit(info)),
        ui.Separator(visible=False),
        ui.ActionRow(EditChartButton(info), DotDisplaySwitchButton(info))
    ), 180)), chart_image_file

def generate_peak_chart_image_file(info: SlayPeakChartInfo):

    from_datetime = dt.datetime.now(info.timezone).replace(
        minute=0, second=0, microsecond=0
    )

    if info.unit_index > 1:
        all_peaks_data = __get_peaks_data_1(
            info.server_names, from_datetime, info.total_time, info.unit_index
        )
    else:
        all_peaks_data = {}
        slay_peaks_database = database.SlayPeaks()

        for server_name in info.server_names:
            peaks_data = __get_peaks_data_2(
                slay_peaks_database,
                server_name,
                from_datetime,
                info.total_time,
                info.unit_index
            )

            all_peaks_data[server_name] = peaks_data

        slay_peaks_database.connection.close()

    fig, ax = plt.subplots(figsize=(10, 6))

    x_data = list(map(lambda x: x[0], next(iter(all_peaks_data.values()))))

    for server_name, peaks_data in all_peaks_data.items():
        y_data = list(map(
            lambda x: -1 if (x := x[1]) == None else x, peaks_data
        ))

        ax.plot(
            x_data, y_data,
            color=line_colors[server_name],
            linestyle="-",
            marker=None if info.no_dots else ".",
            label=server_name+" Server"
        )

    x_data_len = len(x_data)
    x_tick_values = [
        x_data[i]
        for i in range(0, x_data_len, x_data_len//7 if x_data_len > 6 else 1)
    ]
    x_tick_labels = [
        dt.datetime.fromtimestamp(
            timestamp, info.timezone
        ).strftime("%Y/%m/%d %H:00")
        for timestamp in x_tick_values
    ]

    ax.set_xticks(x_tick_values, x_tick_labels)
    fig.autofmt_xdate(rotation=20)

    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    ymin, ymax = ax.get_ylim()

    if ymax - ymin < 1:
        ax.set_ylim(ymin - 1, ymax + 1)

    ax.set_title(
        f"Chart of Slay Peaks ({info.timezone})"
    )
    ax.set_xlabel(f"Time ({units[info.unit_index]})")
    ax.set_ylabel("Real Player Count")

    extra_label = Patch(color="none", label='-1 represents "No Record"')

    handles, _ = ax.get_legend_handles_labels()
    handles.append(extra_label)
    ax.legend(handles=handles)

    chart_image_buffer = io.BytesIO()

    fig.savefig(chart_image_buffer, format="png")
    chart_image_buffer.seek(0)

    chart_image_file = discord.File(
        chart_image_buffer, "chart_of_slay_peaks.png"
    )

    plt.close(fig)
    
    return chart_image_file

def __get_peaks_data_1(
    server_names: MutableSequence[str],
    from_datetime: dt.datetime,
    total_time: relativedelta,
    unit_index: int
):
    slay_peaks_database = database.SlayPeaks()
    all_peaks_data = {}

    for server_name in server_names:

        if unit_index == 3600:
            from_timestamp = int(from_datetime.timestamp())
            to_timestamp = int((from_datetime - total_time).timestamp())
            
            peaks_data = slay_peaks_database.fetch_peaks_between_timestamps(
                server_name, from_timestamp, to_timestamp
            )

        elif unit_index == 604800:
            pointer_from_datetime = from_datetime.replace(
                day=from_datetime.day-from_datetime.weekday(), hour=0
            )

            pointer_from_timestamp = int(pointer_from_datetime.timestamp())

            d = slay_peaks_database.fetch_highest_peak_between_timestamps(
                server_name,
                int(from_datetime.timestamp()),
                int(pointer_from_datetime.timestamp())
            )

            to_timestamp = int((pointer_from_datetime - total_time).timestamp())

            peaks_data = slay_peaks_database.fetch_highest_peaks_in_intervals(
                server_name,
                int(pointer_from_datetime.timestamp()),
                to_timestamp,
                unit_index
            )

        else:
            pointer_from_datetime = from_datetime.replace(
                hour=0
            )

            d = slay_peaks_database.fetch_highest_peak_between_timestamps(
                server_name,
                int(from_datetime.timestamp()),
                int(pointer_from_datetime.timestamp())
            )

            to_timestamp = int((pointer_from_datetime - total_time).timestamp())
            peaks_data = slay_peaks_database.fetch_highest_peaks_in_intervals(
                server_name,
                int(pointer_from_datetime.timestamp()),
                to_timestamp,
                unit_index
            )

            peaks_data.append(d)

        all_peaks_data[server_name] = peaks_data

    slay_peaks_database.connection.close()

    return all_peaks_data

def __get_peaks_data_2(
    slay_peaks_database: database.SlayPeaks,
    server_name: str,
    from_datetime: dt.datetime,
    total_time: relativedelta,
    unit_index: int
):
    peaks_data = []

    if unit_index == 0:
        pointer_from_datetime = from_datetime.replace(month=1, day=1, hour=0)
        from_timestamp = int(pointer_from_datetime.timestamp())

        pointer_to_datetime = pointer_from_datetime - total_time

        while True:
            pointer_from_datetime = pointer_to_datetime + relativedelta(years=1)

            pointer_from_timestamp = int(pointer_from_datetime.timestamp())
            pointer_to_timestamp = int(pointer_to_datetime.timestamp())

            d = slay_peaks_database.fetch_highest_peak_between_timestamps(
                server_name,
                pointer_from_timestamp,
                pointer_to_timestamp
            )

            peaks_data.append(d)

            if pointer_from_timestamp > from_timestamp:
                break

            pointer_to_datetime = pointer_from_datetime
    
    else:
        pointer_from_datetime = from_datetime.replace(day=1, hour=0)
        from_timestamp = int(pointer_from_datetime.timestamp())

        pointer_to_datetime = pointer_from_datetime - total_time

        while True:
            pointer_from_datetime = (
                pointer_to_datetime + relativedelta(months=1)
            )

            pointer_from_timestamp = int(pointer_from_datetime.timestamp())
            pointer_to_timestamp = int(pointer_to_datetime.timestamp())

            d = slay_peaks_database.fetch_highest_peak_between_timestamps(
                server_name,
                pointer_from_timestamp,
                pointer_to_timestamp
            )

            peaks_data.append(d)

            if pointer_from_timestamp > from_timestamp:
                break

            pointer_to_datetime = pointer_from_datetime

    return peaks_data