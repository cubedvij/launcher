import flet as ft

from ..settings import settings
from ..config import RAM_SIZE, RAM_STEP, JVM_ARGS


class SettingsPage(ft.View):
    def __init__(self, page: ft.Page):
        super().__init__(route="/settings")
        self.page = page
        self.controls = []
        self.build_ui()

    def build_ui(self):
        self._appbar = ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
                on_click=self.go_index,
                tooltip="На головну",
            ),
            title=ft.Text("Налаштування", size=20),
            leading_width=64,
            center_title=False,
            shape=ft.RoundedRectangleBorder(radius=8),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )
        self._min_ram_field = ft.TextField(
            value=settings.min_use_ram,
            width=200,
            input_filter=ft.InputFilter(regex_string=r"^[0-9]*$"),
            suffix=ft.Row(
                alignment=ft.MainAxisAlignment.END,
                tight=True,
                spacing=16,
                controls=[
                    ft.Text("МБ"),
                    ft.IconButton(
                        padding=ft.Padding(0, 0, 0, 0),
                        width=24,
                        height=24,
                        icon_size=16,
                        scale=1.5,
                        icon=ft.Icons.KEYBOARD_ARROW_UP,
                        on_click=self._inscare_min_ram_value,
                    ),
                    ft.IconButton(
                        padding=ft.Padding(0, 0, 0, 0),
                        width=24,
                        height=24,
                        icon_size=16,
                        scale=1.5,
                        icon=ft.Icons.KEYBOARD_ARROW_DOWN,
                        on_click=self._decrease_min_ram_value,
                    ),
                ],
            ),
        )

        self._max_ram_field = ft.TextField(
            value=settings.max_use_ram,
            width=200,
            suffix_text="МБ",
            input_filter=ft.InputFilter(regex_string=r"^[0-9]*$"),
            border_color=ft.Colors.SECONDARY_CONTAINER,
            suffix=ft.Row(
                alignment=ft.MainAxisAlignment.END,
                tight=True,
                spacing=16,
                controls=[
                    ft.Text("МБ"),
                    ft.IconButton(
                        padding=ft.Padding(0, 0, 0, 0),
                        width=24,
                        height=24,
                        icon_size=16,
                        scale=1.5,
                        icon=ft.Icons.KEYBOARD_ARROW_UP,
                        on_click=self._inscare_max_ram_value,
                    ),
                    ft.IconButton(
                        padding=ft.Padding(0, 0, 0, 0),
                        width=24,
                        height=24,
                        icon_size=16,
                        scale=1.5,
                        icon=ft.Icons.KEYBOARD_ARROW_DOWN,
                        on_click=self._decrease_max_ram_value,
                    ),
                ],
            ),
        )
        self._java_args_field = ft.TextField(
            value=" ".join(settings.java_args),
            multiline=True,
            expand=True,
            min_lines=32,
            text_size=14,
            border_color=ft.Colors.SECONDARY_CONTAINER,
        )
        self._card_ram = ft.Card(
            shape=ft.RoundedRectangleBorder(radius=8),
            content=ft.Container(
                padding=ft.Padding(8, 8, 8, 8),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text("Пам'ять", size=16),
                        ft.Divider(height=4),
                        ft.ListTile(
                            title=ft.Text("Мінімальний обсяг виділеної пам'яті:"),
                            trailing=self._min_ram_field,
                        ),
                        ft.ListTile(
                            title=ft.Text("Максимальний обсяг виділеної пам'яті:"),
                            trailing=self._max_ram_field,
                        ),
                    ],
                ),
            ),
        )
        self._card_java_args = ft.Card(
            expand=True,
            shape=ft.RoundedRectangleBorder(radius=8),
            content=ft.Container(
                padding=ft.Padding(8, 8, 8, 8),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text("Аргументи Java", size=16),
                        ft.Divider(height=4),
                        self._java_args_field,
                    ],
                ),
            ),
        )
        self._is_fullscreen_game = ft.ListTile(
            title=ft.Text("Повноекранний режим:"),
            trailing=ft.Checkbox(value=settings.fullscreen),
        )
        self._game_window_width = ft.ListTile(
            title=ft.Text("Ширина:"),
            trailing=ft.TextField(
                value=settings.window_width,
                width=200,
                input_filter=ft.InputFilter(regex_string=r"^[0-9]*$"),
                suffix=ft.Text("px"),
            ),
        )
        self._game_window_eight = ft.ListTile(
            title=ft.Text("Висота:"),
            trailing=ft.TextField(
                value=settings.window_height,
                width=200,
                input_filter=ft.InputFilter(regex_string=r"^[0-9]*$"),
                suffix=ft.Text("px"),
            ),
        )
        self._game_window_settings = ft.Card(
            shape=ft.RoundedRectangleBorder(radius=8),
            content=ft.Container(
                padding=ft.Padding(8, 8, 8, 8),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text("Вікно гри", size=16),
                        ft.Divider(height=4),
                        self._is_fullscreen_game,
                        self._game_window_width,
                        self._game_window_eight,
                    ],
                ),
            ),
        )
        self._minimize_launcher = ft.ListTile(
            title=ft.Text("Мінімізувати лаунчер при запуску гри:"),
            trailing=ft.Checkbox(value=settings.minimize_launcher),
        )
        self._quit_launcher = ft.ListTile(
            title=ft.Text("Закривати лаунчер при запуску гри:"),
            trailing=ft.Checkbox(value=settings.close_launcher),
        )
        self._launcher_settings = ft.Card(
            expand=True,
            shape=ft.RoundedRectangleBorder(radius=8),
            content=ft.Container(
                padding=ft.Padding(8, 8, 8, 8),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text("Налаштування лаунчера", size=16),
                        ft.Divider(height=4),
                        self._minimize_launcher,
                        self._quit_launcher,
                    ],
                ),
            ),
        )
        # self._logs_text_field = ft.Text(
        #     value="",
        #     expand=True,
        #     selectable=True,
        #     enable_interactive_selection=True,

        # )
        # self._logs_field = ft.ListView(expand=True, auto_scroll=True, controls=[self._logs_text_field])
        # self._logs_controls = ft.Row(
        #     alignment=ft.MainAxisAlignment.END,
        #     controls=[
        #         ft.FilledTonalButton(
        #             text="Очистити",
        #             icon=ft.Icons.CLEAR,
        #             on_click=lambda _: print("Clear logs"),
        #         ),
        #         ft.FilledTonalButton(
        #             text="Скопіювати",
        #             icon=ft.Icons.COPY,
        #             on_click=lambda _: print("Copy logs"),
        #         ),
        #         ft.FilledButton(
        #             text="Add text",
        #             icon=ft.Icons.ADD,
        #             on_click=self._add_text_to_logs,
        #         ),
        #     ],
        # )
        # self._logs_card = ft.Card(
        #     expand=True,
        #     shape=ft.RoundedRectangleBorder(radius=8),
        #     content=ft.Container(
        #         padding=ft.Padding(8, 8, 8, 8),
        #         content=ft.Column(
        #             controls=[
        #                 self._logs_controls,
        #                 self._logs_field
        #             ],
        #         ),
        #     ),
        # )
        self._java_settins_tab = ft.Tab(
            text="Java",
            content=ft.Column(
                spacing=4,
                controls=[self._card_ram, self._card_java_args],
            ),
        )
        self._game_settings_tab = ft.Tab(
            text="Гра",
            content=ft.Column(
                spacing=4,
                controls=[
                    self._game_window_settings,
                    self._launcher_settings,
                ],
            ),
        )
        # self._game_logs_tab = ft.Tab(
        #     text="Логи",
        #     content=ft.Column(
        #         spacing=4,
        #         controls=[self._logs_card],
        #     ),
        # )
        self._tabs = ft.Tabs(
            expand=True,
            tabs=[
                self._java_settins_tab,
                self._game_settings_tab,
                # self._game_logs_tab,
            ],
        )
        self.pagelet = ft.Pagelet(
            expand=True,
            appbar=self._appbar,
            content=self._tabs,
        )

        self.controls.append(self.pagelet)
        self.page.update()

    # def _add_text_to_logs(self, event):
    #     print("Add text")
    #     self._logs_text_field.value += "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam eget nunc nec nunc ultricies ultricies. Nullam nec nunc nec nunc ultricies ultricies. Nullam nec nunc nec nunc ultricies ultricies.\n"
    #     self.page.update()

    def _inscare_min_ram_value(self, event):
        value = int(self._min_ram_field.value)
        if value + RAM_STEP > self._max_ram_field.value:
            return
        self._min_ram_field.value = value + RAM_STEP
        self.page.update()

    def _decrease_min_ram_value(self, event):
        value = int(self._min_ram_field.value)
        if value - RAM_STEP < RAM_STEP:
            return
        self._min_ram_field.value = value - RAM_STEP
        self.page.update()

    def _inscare_max_ram_value(self, event):
        value = int(self._max_ram_field.value)
        if value + RAM_STEP > RAM_SIZE:
            return
        self._max_ram_field.value = value + RAM_STEP
        self.page.update()

    def _decrease_max_ram_value(self, event):
        value = int(self._max_ram_field.value)
        if value - RAM_STEP < self._min_ram_field.value:
            return
        self._max_ram_field.value = value - RAM_STEP
        self.page.update()

    def go_index(self, event):
        # Save settings
        settings.min_use_ram = int(self._min_ram_field.value)
        settings.max_use_ram = int(self._max_ram_field.value)
        settings.java_args = self._java_args_field.value.split(" ")
        settings.fullscreen = self._is_fullscreen_game.trailing.value
        settings.window_width = int(self._game_window_width.trailing.value)
        settings.window_height = int(self._game_window_eight.trailing.value)
        settings.minimize_launcher = self._minimize_launcher.trailing.value
        settings.close_launcher = self._quit_launcher.trailing.value
        settings.save()
        self.page.go("/")