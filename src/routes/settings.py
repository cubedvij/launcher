import flet as ft

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
                on_click=lambda _: self.page.go("/"),
                tooltip="На головну",
            ),
            title=ft.Text("Налаштування", size=20),
            leading_width=64,
            center_title=False,
            shape=ft.RoundedRectangleBorder(radius=8),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )
        self._min_ram_field = ft.TextField(
            value=RAM_SIZE // 4,
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
            value=RAM_SIZE // 2,
            width=200,
            suffix_text="МБ",
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
            value=" ".join(JVM_ARGS),
            multiline=True,
            expand=True,
            min_lines=5,
            text_size=14,
        )
        self._card_ram = ft.Card(
            shape=ft.RoundedRectangleBorder(radius=8),
            margin=ft.Margin(0, 8, 0, 0),
            content=ft.Container(
                padding=ft.Padding(8, 16, 8, 16),
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
            margin=ft.Margin(0, 0, 0, 8),
            shape=ft.RoundedRectangleBorder(radius=8),
            content=ft.Container(
                padding=ft.Padding(8, 16, 8, 16),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text("Java аргументи", size=16),
                        ft.Divider(height=4),
                        self._java_args_field,
                    ],
                ),
            ),
        )
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
                    ft.Text("Гра"),
                ],
            ),
        )

        self._tabs = ft.Tabs(
            expand=True,
            tabs=[
                self._java_settins_tab,
                self._game_settings_tab,
            ],
        )
        self.pagelet = ft.Pagelet(
            expand=True,
            appbar=self._appbar,
            content=self._tabs,
        )

        self.controls.append(self.pagelet)
        self.page.update()

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
